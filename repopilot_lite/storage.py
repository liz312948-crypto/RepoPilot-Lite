from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from repopilot_lite.models import StepLog, TaskRecord, TaskStatus


class Storage:
    """Small JSON-file persistence layer for tasks and execution logs."""

    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.tasks_file = self.data_dir / "tasks.json"
        self.logs_file = self.data_dir / "logs.json"
        self._lock = Lock()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_file(self.tasks_file, {})
        self._ensure_file(self.logs_file, {})

    def create_task(self, task: TaskRecord) -> TaskRecord:
        with self._lock:
            tasks = self._read_json(self.tasks_file)
            tasks[task.task_id] = task.model_dump(mode="json")
            self._write_json(self.tasks_file, tasks)
        return task

    def get_task(self, task_id: str) -> TaskRecord | None:
        tasks = self._read_json(self.tasks_file)
        raw_task = tasks.get(task_id)
        if raw_task is None:
            return None
        return TaskRecord.model_validate(raw_task)

    def update_task(self, task: TaskRecord) -> TaskRecord:
        task.updated_at = datetime.now(timezone.utc)
        with self._lock:
            tasks = self._read_json(self.tasks_file)
            tasks[task.task_id] = task.model_dump(mode="json")
            self._write_json(self.tasks_file, tasks)
        return task

    def update_status(
        self,
        task: TaskRecord,
        status: TaskStatus,
        error: str | None = None,
    ) -> TaskRecord:
        task.status = status
        task.error = error
        return self.update_task(task)

    def add_log(self, log: StepLog) -> StepLog:
        with self._lock:
            logs = self._read_json(self.logs_file)
            logs.setdefault(log.task_id, []).append(log.model_dump(mode="json"))
            self._write_json(self.logs_file, logs)
        return log

    def get_logs(self, task_id: str) -> list[StepLog]:
        logs = self._read_json(self.logs_file)
        return [StepLog.model_validate(item) for item in logs.get(task_id, [])]

    @staticmethod
    def _ensure_file(path: Path, default_value: object) -> None:
        if not path.exists():
            path.write_text(json.dumps(default_value, indent=2), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        return json.loads(text)

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp_path.replace(path)
