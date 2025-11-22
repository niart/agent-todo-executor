from __future__ import annotations

from openai import OpenAI
from .config import Settings


def get_client(settings: Settings) -> OpenAI:
    """
    Returns an OpenAI client configured with the user's API key.
    """
    return OpenAI(api_key=settings.api_key)


def chat_completion_json(settings: Settings, messages, response_format=None):
    """
    Small helper to call chat.completions.create and return the text content.
    """
    client = get_client(settings)

    kwargs = {}
    if response_format is not None:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(
        model=settings.model,
        messages=messages,
        **kwargs,
    )

    # We expect a single choice, single message
    content = response.choices[0].message.content
    return content
