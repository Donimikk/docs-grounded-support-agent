"""The layer in front of the LLM provider.

The provider is chosen by evaluation, so the call sits behind a protocol with a
single method. Swapping providers is then a matter of one class, not a change
in the endpoint.
"""

from __future__ import annotations

from typing import Protocol


class LLMError(RuntimeError):
    """The model call failed, or the input made no sense."""


class LLMClient(Protocol):
    """The only thing we need from a provider."""

    def complete(self, system_prompt: str, user_message: str) -> str:
        """Send the prompt to the model and return the text of the answer."""
        ...


class ScriptedClient:
    """Test double for the multi-step flow.

    Returns prepared answers in order and records every call, so each step can
    be checked for what it received.
    """

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.calls.append((system_prompt, user_message))

        if not self.replies:
            raise LLMError("ScriptedClient: more calls than prepared answers")

        return self.replies.pop(0)


class RecordingClient:
    """Test double. Records what it received and returns a prepared answer."""

    def __init__(self, reply: str, fail_with: Exception | None = None) -> None:
        self.reply = reply
        self.fail_with = fail_with
        self.last_system_prompt: str | None = None
        self.last_user_message: str | None = None
        self.call_count = 0

    def complete(self, system_prompt: str, user_message: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_message = user_message
        self.call_count += 1

        if self.fail_with is not None:
            raise self.fail_with

        return self.reply
