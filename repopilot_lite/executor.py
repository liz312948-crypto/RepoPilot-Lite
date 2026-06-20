from __future__ import annotations

from pathlib import Path
from typing import Any

from repopilot_lite.models import StepLog, TaskRecord, TaskResult, TaskStatus
from repopilot_lite.storage import Storage
from repopilot_lite.tools import ToolRegistry


class Executor:
    """Runs planned steps and stores observable logs for each step."""

    def __init__(self, registry: ToolRegistry, storage: Storage) -> None:
        self.registry = registry
        self.storage = storage

    def run(self, task: TaskRecord) -> TaskRecord:
        context: dict[str, Any] = {
            "files": [],
            "readme": None,
            "search_matches": [],
            "summary_result": None,
        }
        self.storage.update_status(task, TaskStatus.RUNNING)

        try:
            for step in task.plan:
                self._log(task, step.name, "STARTED", step.description)
                output = self._run_step(task, step.name, step.args, context)
                self._log(task, step.name, "SUCCESS", "Step completed.", self._preview(output))

            result = context["summary_result"]
            if result is None:
                result = self.registry.call(
                    "summarize_repo",
                    repo_path=task.repo_path,
                    question=task.question,
                    files=context["files"],
                    readme=context["readme"],
                    search_matches=context["search_matches"],
                )
            task.result = TaskResult.model_validate(result)
            self.storage.update_status(task, TaskStatus.SUCCESS)
        except Exception as exc:
            self._log(task, "executor", "FAILED", str(exc))
            self.storage.update_status(task, TaskStatus.FAILED, error=str(exc))

        return self.storage.get_task(task.task_id) or task

    def _run_step(
        self,
        task: TaskRecord,
        step_name: str,
        args: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if step_name == "list_files":
            output = self.registry.call("list_files", repo_path=task.repo_path, **args)
            context["files"] = output["files"]
            return output

        if step_name == "read_readme":
            readme_path = self._find_readme(context["files"])
            if readme_path is None:
                return {"file_path": None, "content": None, "message": "README not found."}
            output = self.registry.call("read_file", repo_path=task.repo_path, file_path=readme_path)
            context["readme"] = output["content"]
            return output

        if step_name == "search_keywords":
            output = self.registry.call("search_text", repo_path=task.repo_path, **args)
            context["search_matches"] = output["matches"]
            return output

        if step_name == "summarize":
            output = self.registry.call(
                "summarize_repo",
                repo_path=task.repo_path,
                question=task.question,
                files=context["files"],
                readme=context["readme"],
                search_matches=context["search_matches"],
            )
            context["summary_result"] = output
            return output

        raise ValueError(f"Unknown plan step: {step_name}")

    def _log(
        self,
        task: TaskRecord,
        step: str,
        status: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.storage.add_log(
            StepLog(
                task_id=task.task_id,
                step=step,
                status=status,
                message=message,
                data=data or {},
            )
        )

    @staticmethod
    def _find_readme(files: list[str]) -> str | None:
        for file_path in files:
            name = Path(file_path).name.lower()
            if name == "readme" or name.startswith("readme."):
                return file_path
        return None

    @staticmethod
    def _preview(output: dict[str, Any]) -> dict[str, Any]:
        preview = dict(output)
        if "content" in preview and isinstance(preview["content"], str):
            preview["content"] = preview["content"][:500]
        if "files" in preview and isinstance(preview["files"], list):
            preview["files"] = preview["files"][:20]
        if "matches" in preview and isinstance(preview["matches"], list):
            preview["matches"] = preview["matches"][:10]
        return preview
