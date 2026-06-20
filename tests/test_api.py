from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from repopilot_lite.main import app, get_storage
from repopilot_lite.storage import Storage


def test_task_lifecycle(tmp_path: Path) -> None:
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Sample\n\nFastAPI service demo.", encoding="utf-8")
    (repo / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    storage = Storage(tmp_path / "data")
    app.dependency_overrides[get_storage] = lambda: storage
    client = TestClient(app)

    create_response = client.post(
        "/tasks",
        json={"repo_path": str(repo), "question": "How does the FastAPI service start?"},
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["status"] == "PENDING"

    run_response = client.post(f"/tasks/{created['task_id']}/run")
    assert run_response.status_code == 200
    task = run_response.json()
    assert task["status"] == "SUCCESS"
    assert task["plan"]
    assert task["result"]["key_files"]

    logs_response = client.get(f"/tasks/{created['task_id']}/logs")
    assert logs_response.status_code == 200
    assert any(log["step"] == "list_files" for log in logs_response.json())

    app.dependency_overrides.clear()


def test_tools_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/tools")
    assert response.status_code == 200
    tool_names = {tool["name"] for tool in response.json()}
    assert {"list_files", "read_file", "search_text", "summarize_repo"} <= tool_names
