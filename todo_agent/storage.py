# todo_agent/storage.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4
from datetime import datetime

from .config import Settings
from .models import SessionState, Task, TaskStatus

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def generate_session_id() -> str:
    return uuid4().hex


def _session_path(session_id: str) -> Path:
    return DATA_DIR / f"{session_id}.json"


def save_session(state: SessionState, session_id: str) -> None:
    """
    Persist the whole session to disk as JSON.

    JSON shape:
    {
      "session_id": "...",
      "created_at": "...",
      "updated_at": "...",
      "state": { ... SessionState.to_dict() ... }
    }
    """
    path = _session_path(session_id)

    created_at = _now_iso()
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            created_at = existing.get("created_at", created_at)
        except Exception:
            # best effort; if file corrupted, we keep a fresh created_at
            pass

    payload = {
        "session_id": session_id,
        "created_at": created_at,
        "updated_at": _now_iso(),
        "state": state.to_dict(),
    }

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session(session_id: str, settings: Settings) -> SessionState:
    """
    Load a SessionState from disk for a given session_id.
    """
    path = _session_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"Session {session_id} not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    state_data = data.get("state", {})
    goal = state_data.get("goal", "")
    mode = state_data.get("mode", "confirm")
    tasks_data = state_data.get("tasks", [])
    logs = state_data.get("logs", [])

    state = SessionState(goal=goal, mode=mode, settings=settings)
    state.logs = list(logs)

    tasks: List[Task] = []
    for raw in tasks_data:
        status_str = str(raw.get("status", "pending"))
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.PENDING

        tasks.append(
            Task(
                id=int(raw.get("id", len(tasks) + 1)),
                title=str(raw.get("title", "")),
                description=str(raw.get("description", "")),
                status=status,
                result=raw.get("result"),
                reflection=raw.get("reflection"),
            )
        )

    state.tasks = tasks
    return state


def list_sessions() -> List[Dict[str, Any]]:
    """
    Return lightweight metadata for all saved sessions.
    """
    sessions: List[Dict[str, Any]] = []

    for path in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        state_data = data.get("state", {})
        sessions.append(
            {
                "session_id": data.get("session_id", path.stem),
                "goal": state_data.get("goal", ""),
                "mode": state_data.get("mode", ""),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "num_tasks": len(state_data.get("tasks", [])),
            }
        )

    # newest first
    sessions.sort(key=lambda s: s.get("created_at") or "", reverse=True)
    return sessions
