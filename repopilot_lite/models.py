from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class TaskCreate(BaseModel):
    repo_path: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)


class TaskCreated(BaseModel):
    task_id: str
    status: TaskStatus


class PlanStep(BaseModel):
    name: str
    description: str
    args: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    repo_summary: str
    key_files: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class TaskRecord(BaseModel):
    task_id: str
    repo_path: str
    question: str
    status: TaskStatus = TaskStatus.PENDING
    plan: list[PlanStep] = Field(default_factory=list)
    result: TaskResult | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StepLog(BaseModel):
    task_id: str
    step: str
    status: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolInfo(BaseModel):
    name: str
    description: str
