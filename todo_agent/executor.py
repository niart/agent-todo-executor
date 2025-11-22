from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Tuple

from .models import SessionState, Task, TaskStatus
from .openai_client import chat_completion_json


EXECUTOR_SYSTEM_PROMPT = """
You are an execution agent helping with a project.

You will receive:
- The overall goal of the project.
- A single TODO task (title and description).

You must:
1. Execute the task as best as possible in natural language (and code if relevant).
2. Decide whether the task is:
   - "done"             (completed successfully)
   - "failed"           (not completed, blocked, or impossible)
   - "needs-follow-up"  (you made progress but more work is clearly needed)
3. Reflect briefly on what you did and any follow-ups.

Respond ONLY with valid JSON of the following shape:

{
  "result": "detailed textual result of your work",
  "status": "done | failed | needs-follow-up",
  "reflection": "1-3 sentence reflection about this specific task"
}

Do NOT include any additional keys. Do NOT include extra commentary outside JSON.
"""


def execute_single_task(state: SessionState, task: Task) -> Tuple[str, TaskStatus, str]:
    """
    Calls the LLM to 'execute' the task, and returns (result, status, reflection).
    """
    messages = [
        {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "goal": state.goal,
                    "task": {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]

    raw = chat_completion_json(
        state.settings,
        messages,
        response_format={"type": "json_object"},
    )
    data = json.loads(raw)

    result = str(data.get("result", "")).strip()
    status_str = str(data.get("status", "done")).strip().lower()
    reflection = str(data.get("reflection", "")).strip()

    if status_str not in {"done", "failed", "needs-follow-up"}:
        status_str = "needs-follow-up"

    status = TaskStatus(status_str)
    return result, status, reflection


def run_execution_step(state: SessionState) -> bool:
    """
    Execute a single pending task (if any).

    Returns:
        True  if there are still pending tasks after this step,
        False if no pending tasks remain.
    """
    pending = [t for t in state.tasks if t.status == TaskStatus.PENDING]
    if not pending:
        state.log("No pending tasks. Execution step did nothing.")
        return False

    task = pending[0]
    state.log(f"\n[Agent] Selected task #{task.id}: {task.title}")
    state.log(f"[Agent] Description: {task.description}")

    try:
        result, status, reflection = execute_single_task(state, task)
        task.result = result
        task.status = status
        task.reflection = reflection

        state.log(f"[Agent] Result status for task #{task.id}: {task.status}")
        state.log(f"[Agent] Reflection: {task.reflection}")
    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.reflection = f"Execution failed with error: {exc}"
        state.log(f"[Agent] ERROR executing task #{task.id}: {exc}")
        state.log("[Agent] Marking task as FAILED.")

    # Are there any pending tasks left?
    return any(t.status == TaskStatus.PENDING for t in state.tasks)


def run_execution_loop(state: SessionState) -> None:
    """
    CLI-style loop: keep executing until all tasks are terminal.
    """
    while run_execution_step(state):
        pass
    state.log("All tasks are in a terminal state. Execution loop finished.")


def save_session_to_file(state: SessionState, path: str | None = None) -> str:
    """
    (CLI-only convenience) Persist the session in a standalone JSON file.
    """
    if path is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = f"session-{timestamp}.json"

    out_path = Path(path).resolve()
    out_path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(out_path)
