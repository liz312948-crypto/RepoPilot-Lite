# RepoPilot Lite

RepoPilot Lite is a small FastAPI demo for a repository-reading and task-planning agent. A user submits a local repository path and a question. The system creates a task, builds a fixed analysis plan, runs repository tools, stores progress in JSON files, and returns a simple repository summary with key files and modification suggestions.

The project intentionally avoids LangChain, queues, databases, frontends, and complex agent frameworks so the architecture stays easy to explain in an interview.

## Features

- Create and run repository analysis tasks.
- Fixed Planner steps: `list_files`, `read_readme`, `search_keywords`, `summarize`.
- Executor runs each step and records logs.
- ToolRegistry provides one place to register and call tools.
- JSON persistence for tasks and logs.
- FastAPI routes for task lifecycle and tool discovery.

## Project Structure

```text
repopilot-lite/
+-- repopilot_lite/
|   +-- main.py        # FastAPI app and routes
|   +-- models.py      # Pydantic request, response, task, log, and result models
|   +-- planner.py     # Fixed task planning logic
|   +-- executor.py    # Step execution and logging
|   +-- tools.py       # ToolRegistry and repository tools
|   +-- storage.py     # JSON file persistence
+-- tests/
|   +-- test_api.py
+-- data/              # Created at runtime for tasks.json and logs.json
+-- requirements.txt
+-- pyproject.toml
+-- README.md
```

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

For tests:

```bash
pip install -e ".[dev]"
```

## Run

```bash
uvicorn repopilot_lite.main:app --reload
```

Open the API docs at:

```text
http://127.0.0.1:8000/docs
```

## API Examples

### Create Task

```bash
curl -X POST http://127.0.0.1:8000/tasks ^
  -H "Content-Type: application/json" ^
  -d "{\"repo_path\":\"D:\\RepoPilot-Lite\",\"question\":\"How is the API structured?\"}"
```

Response:

```json
{
  "task_id": "9e1d47b8-0b42-4e0d-9e4e-9b33c21b8f5a",
  "status": "PENDING"
}
```

### Run Task

```bash
curl -X POST http://127.0.0.1:8000/tasks/{task_id}/run
```

### Get Task

```bash
curl http://127.0.0.1:8000/tasks/{task_id}
```

The response includes task status, plan, result, and error information.

### Get Logs

```bash
curl http://127.0.0.1:8000/tasks/{task_id}/logs
```

### Get Tools

```bash
curl http://127.0.0.1:8000/tools
```

## Architecture

RepoPilot Lite follows a direct request-driven flow:

1. `POST /tasks` creates a `PENDING` task and stores it in `data/tasks.json`.
2. `POST /tasks/{task_id}/run` changes the task to `PLANNING`.
3. `Planner` creates a small fixed plan.
4. `Executor` changes the task to `RUNNING`, executes steps through `ToolRegistry`, and writes logs.
5. Tools inspect the local repository:
   - `list_files` lists repository files.
   - `read_file` reads a relative file path safely inside the repository.
   - `search_text` searches question keywords in text files.
   - `summarize_repo` builds a simple summary, key file list, and suggestions.
6. The task ends in `SUCCESS` or `FAILED`.

## State Machine

```text
PENDING -> PLANNING -> RUNNING -> SUCCESS
                              -> FAILED
```

Failed tasks can be run again. Successful tasks are returned as-is if run again.

## JSON Persistence

Runtime data is stored under `data/`:

- `data/tasks.json`
- `data/logs.json`

This is enough for a demo and easy to inspect manually. It is not intended for high concurrency or production durability.

## Future Improvements

- Add asynchronous background execution for long repositories.
- Add pagination and file-count limits to task responses.
- Add structured repository language detection.
- Add configurable ignore patterns.
- Add stronger keyword extraction.
- Add test coverage for failure paths and storage recovery.
- Replace JSON files with SQLite when concurrency becomes important.
