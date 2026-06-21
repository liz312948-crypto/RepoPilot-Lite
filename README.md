# RepoPilot Lite

RepoPilot Lite is a lightweight coding-agent backend prototype for repository understanding and modification planning. A user submits a local repository path and a question. The system creates a task, plans a small analysis workflow, reads repository context through registered tools, and returns a repository summary, key files, a modification plan, risk notes, and suggestions.

This project is intentionally small. It is not a full IDE, does not automatically modify code, and does not provide a production-grade autonomous coding agent. Its focus is the backend shape of a coding-agent workflow: task state, planning, tool execution, logs, fallback behavior, and explainable modification planning.

## Features

- Create and run repository understanding tasks.
- Fixed Planner steps: `list_files`, `read_readme`, `search_keywords`, `summarize`.
- Lightweight Agent Loop in `search_keywords`: if the first search has no matches, the Executor broadens keywords and retries at most two times.
- Modification planning output with target files, actions, and reasons.
- Optional OpenAI-compatible LLM summarizer controlled by environment variables.
- Rule-based summarizer fallback when no API key is configured or the LLM call fails.
- JSON persistence for tasks and logs.
- FastAPI routes for task lifecycle, logs, and tool discovery.

## Project Structure

```text
repopilot-lite/
+-- repopilot_lite/
|   +-- main.py        # FastAPI app and routes
|   +-- models.py      # Pydantic request, response, task, log, and result models
|   +-- planner.py     # Fixed task planning logic
|   +-- executor.py    # Step execution, retry loop, and logging
|   +-- tools.py       # ToolRegistry and repository tools
|   +-- llm_client.py  # Optional OpenAI-compatible summarizer client
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

## Optional LLM Configuration

The app runs without LLM credentials. When no key is configured, `summarize_repo` uses the rule-based fallback and returns `llm_used: false`.

To enable the optional OpenAI-compatible summarizer:

```bash
set OPENAI_API_KEY=your_key
set OPENAI_BASE_URL=https://api.openai.com/v1
set OPENAI_MODEL=gpt-4o-mini
```

If the LLM request fails, the tool falls back to the rule summarizer and still returns a valid task result with `llm_used: false`.

## API Examples

### Create Task

```bash
curl -X POST http://127.0.0.1:8000/tasks ^
  -H "Content-Type: application/json" ^
  -d "{\"repo_path\":\"D:\\RepoPilot-Lite\",\"question\":\"How should we add a new repository analysis feature?\"}"
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

The response includes task status, plan, result, and error information. The v0.2 result includes:

```json
{
  "repo_summary": "Repository summary text",
  "key_files": ["README.md", "repopilot_lite/main.py"],
  "modification_plan": [
    {
      "title": "Confirm existing behavior",
      "target_files": ["README.md"],
      "action": "Read the key files and map the current request flow before editing.",
      "reason": "The requested change should be grounded in the current implementation first."
    }
  ],
  "risk_notes": ["This prototype only plans changes; it does not edit files automatically."],
  "llm_used": false,
  "suggestions": ["Inspect the listed key files before changing behavior."]
}
```

### Get Logs

```bash
curl http://127.0.0.1:8000/tasks/{task_id}/logs
```

Retry logs from the Agent Loop use `status: RETRY`.

### Get Tools

```bash
curl http://127.0.0.1:8000/tools
```

## API Execution Flow

1. `POST /tasks` creates a `PENDING` task and stores it in `data/tasks.json`.
2. `POST /tasks/{task_id}/run` changes the task to `PLANNING`.
3. `Planner` creates a small fixed plan.
4. `Executor` changes the task to `RUNNING`, executes steps through `ToolRegistry`, and writes logs.
5. `search_keywords` may retry with broader keywords if no matches are found.
6. `summarize_repo` generates repository understanding and modification planning output.
7. The task ends in `SUCCESS` or `FAILED`.

## Agent Loop

RepoPilot Lite keeps the loop intentionally small and bounded:

```text
initial keyword search
  -> if matches found: continue
  -> if no matches: broaden keywords and retry
  -> retry at most 2 times
  -> write RETRY logs for each retry
```

This avoids infinite execution while showing how an Executor can adapt tool calls based on intermediate results.

## Modification Planning

The output is planning-focused. Each modification step contains:

- `title`: the planning step name.
- `target_files`: likely files or directories to inspect or change.
- `action`: what a coding agent or developer should do next.
- `reason`: why the step matters.

RepoPilot Lite does not automatically edit files. It helps identify what to inspect, where changes may belong, and what risks should be checked first.

## Demo Case

1. Start the server with Uvicorn.
2. Create a task for this repository:

```json
{
  "repo_path": "D:\\RepoPilot-Lite",
  "question": "How should we add a new repository analysis feature?"
}
```

3. Run the task.
4. Inspect `/tasks/{task_id}` for `modification_plan`, `risk_notes`, and `llm_used`.
5. Inspect `/tasks/{task_id}/logs` to see each tool step and any `RETRY` logs.

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

This is enough for a prototype and easy to inspect manually. It is not intended for high concurrency or production durability.

## Roadmap

- Add more repository analysis tools, such as dependency file detection and entrypoint discovery.
- Add richer modification planning heuristics by language or framework.
- Add safer path allowlists for local repository access.
- Add stronger tests for failure paths and retry behavior.
- Add pagination or response trimming for large repositories.
- Replace JSON storage if concurrent task execution becomes important.
- Keep the app backend-only unless a frontend becomes necessary for demo workflows.
