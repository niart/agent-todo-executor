import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """

    API key is read from OPENAI_API_KEY env var.
    Model can be overridden at runtime.
    """

    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("AGENT_TODO_MODEL", "gpt-4o-mini")

    def __post_init__(self):
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Export it in your environment "
                "before running the agent."
            )
