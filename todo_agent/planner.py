from __future__ import annotations

import json
from typing import List

from .config import Settings
from .models import Task, SessionState
from .openai_client import chat_completion_json


PLANNER_SYSTEM_PROMPT = """
You are a helpful planning agent.

Given a high-level goal from the user, you will break it down into a structured TODO list.
You MUST respond ONLY with valid JSON matching this schema:

{
  "tasks": [
    {
      "title": "short task title",
      "description": "1-3 sentences describing the task in concrete terms"
    },
    ...
  ]
}

Guidelines:
- 5 to 10 tasks is usually enough.
- Tasks should be concrete and actionable, not vague.
- Order tasks in a sensible execution order.
- Do NOT include any extra text outside of the JSON.
"""


def _parse_tasks_from_json(json_str: str) -> List[Task]:
    data = json.loads(json_str)
    if "tasks" not in data or not isinstance(data["tasks"], list):
        raise ValueError("Planner response JSON missing 'tasks' list")

    tasks: List[Task] = []
    for i, raw in enumerate(data["tasks"], start=1):
        title = str(raw.get("title", f"Task {i}")).strip()
        description = str(raw.get("description", "")).strip()
        tasks.append(Task(id=i, title=title, description=description))
    return tasks


def propose_todo_list(goal: str, settings: Settings) -> List[Task]:
    """
    Calls the LLM to propose a structured TODO list for the given goal.
    """
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"My high-level goal is:\n{goal}\n\n"
                       f"Please output only the JSON described above.",
        },
    ]

    # Ask the model to strictly return JSON
    raw = chat_completion_json(
        settings,
        messages,
        response_format={"type": "json_object"},
    )
    return _parse_tasks_from_json(raw)


def edit_tasks_interactively(state: SessionState) -> None:
    """
    Simple interactive editor: iterate tasks and allow user to tweak
    title / description one by one.
    """
    print("\nEntering interactive edit mode. Press ENTER to keep existing values.")

    for task in state.tasks:
        print(f"\nTask [{task.id}]")
        print(f"Current title: {task.title}")
        new_title = input("New title (or ENTER to keep): ").strip()
        if new_title:
            task.title = new_title

        print(f"Current description: {task.description}")
        new_desc = input("New description (or ENTER to keep): ").strip()
        if new_desc:
            task.description = new_desc

    print("\nFinished editing tasks.")
