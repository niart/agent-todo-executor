# Agent-Driven TODO Executor

This project is a small agentic prototype that:

1. Takes a high-level goal from the user.
2. Uses an LLM to **chat-plan** a structured TODO list.
3. Executes tasks in an **agent loop**, marking each as `pending`, `done`, `failed`, or `needs-follow-up`.
4. Persists sessions so you can come back later, via **CLI** or **web UI**.

---

## 1. Setup

```bash
git clone https://github.com/niart/agent-todo-executor.git
cd agent-todo-executor-main

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Configure the API key as an environment variable:

```bash
export OPENAI_API_KEY="the key"   # Linux/macOS
# PowerShell: $env:OPENAI_API_KEY="the key"
```

Optional model override (otherwise a default is used):

```bash
export AGENT_TODO_MODEL="gpt-4o-mini"
```

Also ensure folders exist:

```bash
mkdir -p data static
```

---

## 2. How to Run

### 2.1 Simple CLI Version (ffrom Terminal)

```bash
python run_agent.py
```

Flow:

1. You’re prompted for a **goal** (e.g., “Build a small coupon marketplace web app”).
2. The agent calls the planner LLM to produce a **JSON TODO list**.
3. In `confirm` mode, you:
   - Approve the list
   - Edit tasks interactively
   - Regenerate
   - Or cancel  
   (In `auto` mode, it just proceeds.)
4. The agent then runs the **execution loop** and prints logs to the terminal.
5. A final JSON snapshot of the session is saved as `session-<timestamp>.json`.

You can also provide arguments:

```bash
python run_agent.py   --mode auto   --goal "Create a minimal coupon marketplace web app with CRUD coupon listings."
```
<p align="center">
<img src="https://github.com/niart/agent-todo-executor/blob/7b50e9f672d357ad421621fc0fac22238a1a10af/cli.png" width=50% height=50%>
</p>

### 2.2 Web UI Version (Browser)

Start the FastAPI server:

```bash
uvicorn web_app:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

In the UI you can:

- Create a new **session** (goal + mode + optional model).
- See **existing sessions** stored in `data/`.
- Inspect a session:
  - Task table (id, title, description, status, reflection)
  - Logs (step-by-step trace)
- Execute tasks:
  - **Execute one step**: run the next pending task.
  - **Execute all**: run until no tasks are pending.
  - **Refresh**: reload state from disk.

All state is persisted as `data/<session_id>.json`.

---
<p align="center">
<img src="https://github.com/niart/agent-todo-executor/blob/7b50e9f672d357ad421621fc0fac22238a1a10af/web.png" width=50% height=50%>
</p>

## 3. How the Loop Works

### 3.1 Chat-Planning → TODO List

The planning phase is implemented in `todo_agent/planner.py`:

1. We send a **system prompt** that instructs the LLM to output a JSON object:
   ```json
   {
     "tasks": [
       { "title": "...", "description": "..." },
       ...
     ]
   }
   ```
2. The user’s goal is passed as the **user message**.
3. `response_format={"type": "json_object"}` is used so the model returns valid JSON.
4. The JSON is parsed into a list of `Task` objects with `id`, `title`, `description`, and initial status `pending`.

In the web UI, this happens when you create a session with `POST /api/sessions`.

### 3.2 Execution Loop

Execution logic is in `todo_agent/executor.py`:

- **Single step** (`run_execution_step`):
  1. Find the first task with `status == pending`.
  2. Send a JSON payload to the LLM:
     ```json
     {
       "goal": "...",
       "task": { "id": ..., "title": "...", "description": "..." }
     }
     ```
  3. The LLM responds with:
     ```json
     {
       "result": "...",
       "status": "done | failed | needs-follow-up",
       "reflection": "..."
     }
     ```
  4. We update `task.result`, `task.status`, and `task.reflection`, and log what happened.
  5. Return whether there are still any `pending` tasks.

- **Full loop** (`run_execution_loop` for CLI):
  - Repeatedly call `run_execution_step` until no tasks remain `pending`.

### 3.3 Persistence

Persistence is handled in `todo_agent/storage.py`:

- Each session has a `session_id` and is stored in `data/<session_id>.json` as:
  ```json
  {
    "session_id": "...",
    "created_at": "...",
    "updated_at": "...",
    "state": { ... SessionState.to_dict() ... }
  }
  ```
- `save_session` writes the updated `SessionState` after planning and after each execution step.
- `load_session` reconstructs a `SessionState` from disk (used by the web API).
- `list_sessions` returns lightweight metadata for all saved sessions (shown in the UI list).

---

## 4. How I’d Extend This Prototype with More Time

Currently, this prototype demonstrates the end-to-end pattern:

> **Goal → Chat-based planning → Structured TODOs → Agentic execution loop → Persistent trace and state.**

If this were developed further, I’d focus on:

1. **Richer Task Graph & Scheduling**
   - Add dependencies (`depends_on`), priorities, and estimates.
   - Use a simple graph-based scheduler instead of always picking the first `pending` task.
   - Allow re-ordering or splitting tasks based on execution reflections.

2. **Tool Integration (“Real Work”)**
   - Let the executor call tools (e.g., file I/O, shell commands, HTTP requests).
   - Add a tool spec so the model can choose between:
     - Writing files (code, configs)
     - Running tests/linters
     - Calling external APIs
   - Log tool calls separately for better traceability.

3. **Better Editing & Review Flow**
   - In the UI:
     - Edit tasks (title/description/status) directly.
     - Add new tasks or delete existing ones.
     - Trigger a “re-plan” that keeps completed tasks and regenerates the rest.

4. **Session Management & Auth**
   - User accounts + authentication (so multiple users can have their own sessions).
   - Tag sessions (e.g., “coupon app”, “data pipeline”) and filter/search.
   - Export sessions (e.g., Markdown or PDF summaries).

5. **Streaming & Observability**
   - Stream LLM output to the browser for long-running tasks.
   - Add a timeline view of task status changes.
   - Store logs in a more queryable format (e.g., SQLite) instead of only JSON.

6. **Safety & Guardrails**
   - Add simple “policies” around what the agent is allowed to do.
   - Validate model outputs more strictly before applying them (e.g., JSON schemas, allowed status values).

