from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any

from .config import Settings


class TaskStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    NEEDS_FOLLOW_UP = "needs-follow-up"


@dataclass
class Task:
    id: int
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    reflection: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass
class SessionState:
    goal: str
    mode: str  # "confirm" or "auto"
    settings: Settings
    tasks: List[Task] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        print(message)
        self.logs.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "mode": self.mode,
            "settings": {"model": self.settings.model},
            "tasks": [t.to_dict() for t in self.tasks],
            "logs": self.logs,
        }
