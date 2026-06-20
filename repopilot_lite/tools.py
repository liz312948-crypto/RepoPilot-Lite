from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build"}
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".env",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    handler: Callable[..., dict[str, Any]]


class ToolRegistry:
    """Registers tool handlers and exposes one invocation point for the executor."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., dict[str, Any]],
    ) -> None:
        self._tools[name] = RegisteredTool(name=name, description=description, handler=handler)

    def call(self, name: str, **kwargs: Any) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Tool is not registered: {name}")
        return tool.handler(**kwargs)

    def list_tools(self) -> list[dict[str, str]]:
        return [{"name": tool.name, "description": tool.description} for tool in self._tools.values()]


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("list_files", "List readable files in a repository.", list_files)
    registry.register("read_file", "Read a text file from a repository by relative path.", read_file)
    registry.register("search_text", "Search text keywords inside repository files.", search_text)
    registry.register("summarize_repo", "Generate a simple repository summary from collected tool results.", summarize_repo)
    return registry


def list_files(repo_path: str, max_files: int = 200) -> dict[str, Any]:
    repo = _resolve_repo(repo_path)
    files: list[str] = []

    for path in repo.rglob("*"):
        if len(files) >= max_files:
            break
        if _should_skip(path, repo) or not path.is_file():
            continue
        files.append(path.relative_to(repo).as_posix())

    return {"files": files, "count": len(files), "truncated": len(files) >= max_files}


def read_file(repo_path: str, file_path: str, max_chars: int = 12000) -> dict[str, Any]:
    repo = _resolve_repo(repo_path)
    target = _resolve_inside_repo(repo, file_path)

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    text = _read_text_safely(target, max_chars=max_chars)
    return {
        "file_path": target.relative_to(repo).as_posix(),
        "content": text,
        "truncated": target.stat().st_size > max_chars,
    }


def search_text(repo_path: str, keywords: list[str], max_matches: int = 50) -> dict[str, Any]:
    repo = _resolve_repo(repo_path)
    normalized_keywords = [item.lower() for item in keywords if item.strip()]
    matches: list[dict[str, Any]] = []

    if not normalized_keywords:
        return {"matches": matches, "count": 0, "keywords": []}

    for path in repo.rglob("*"):
        if len(matches) >= max_matches:
            break
        if _should_skip(path, repo) or not path.is_file() or not _looks_text_file(path):
            continue

        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()
            hit_keywords = [word for word in normalized_keywords if word in lowered]
            if not hit_keywords:
                continue
            matches.append(
                {
                    "file_path": path.relative_to(repo).as_posix(),
                    "line_number": line_number,
                    "line": line.strip()[:300],
                    "keywords": hit_keywords,
                }
            )
            if len(matches) >= max_matches:
                break

    return {"matches": matches, "count": len(matches), "keywords": normalized_keywords}


def summarize_repo(
    repo_path: str,
    question: str,
    files: list[str],
    readme: str | None = None,
    search_matches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    repo = _resolve_repo(repo_path)
    search_matches = search_matches or []
    key_files = _select_key_files(files, search_matches)

    readme_summary = _compact_text(readme, max_chars=600) if readme else "No README content was found."
    summary = (
        f"Repository '{repo.name}' contains {len(files)} indexed files. "
        f"The question is: {question}. "
        f"README signal: {readme_summary}"
    )

    suggestions = [
        "Start with README and project configuration files to confirm setup and runtime assumptions.",
        "Inspect the listed key files before changing behavior.",
        "Add focused tests around the requested behavior before making code changes.",
    ]

    if search_matches:
        suggestions.insert(1, "Review keyword matches because they are the most direct links to the question.")

    return {"repo_summary": summary, "key_files": key_files, "suggestions": suggestions}


def _resolve_repo(repo_path: str) -> Path:
    repo = Path(repo_path).expanduser().resolve()
    if not repo.exists() or not repo.is_dir():
        raise FileNotFoundError(f"Repository path does not exist or is not a directory: {repo_path}")
    return repo


def _resolve_inside_repo(repo: Path, file_path: str) -> Path:
    target = (repo / file_path).resolve()
    if repo not in target.parents and target != repo:
        raise ValueError(f"File path is outside repository: {file_path}")
    return target


def _should_skip(path: Path, repo: Path) -> bool:
    relative_parts = path.relative_to(repo).parts
    return any(part in IGNORED_DIRS for part in relative_parts)


def _looks_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.name.lower() in {"readme", "dockerfile", "makefile"}


def _read_text_safely(path: Path, max_chars: int) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text[:max_chars]


def _select_key_files(files: list[str], search_matches: list[dict[str, Any]]) -> list[str]:
    weighted: list[str] = []
    for match in search_matches:
        file_path = str(match.get("file_path", ""))
        if file_path and file_path not in weighted:
            weighted.append(file_path)

    priority_names = ("README", "pyproject.toml", "requirements.txt", "main.py", "app.py")
    for file_path in files:
        name = Path(file_path).name
        if any(name.startswith(priority) or name == priority for priority in priority_names):
            if file_path not in weighted:
                weighted.append(file_path)

    for file_path in files[:10]:
        if file_path not in weighted:
            weighted.append(file_path)

    return weighted[:10]


def _compact_text(text: str | None, max_chars: int) -> str:
    if not text:
        return ""
    compacted = " ".join(text.split())
    if len(compacted) <= max_chars:
        return compacted
    return compacted[: max_chars - 3] + "..."
