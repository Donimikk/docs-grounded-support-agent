"""Turning a Discord thread into the messages the pipeline works with.

A pure data transformation: the input is messages the way the Discord API
returns them, the output is our list. No network, no state - which is why it
can be tested long before the bot ever sits on the server.

It deliberately does NOT parse text copied out of the Discord app. The bot will
receive structured messages from the API; a parser for the human-readable dump
would be thrown away the day it connects.

Every decision below came out of real tickets.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from fyndit_helper.pipeline import ROLE_CUSTOMER, ROLE_HELPER, ROLE_OWNER, Message

#: Stands in for an image. Models can read images, but we have not verified how
#: well - until then the model should at least know something is there and can
#: ask about it.
IMAGE_MARKER = "[obrázok]"

#: The bot opens the ticket and wraps the customer's original message in a
#: form. Dropping the whole bot message would lose what the customer came with.
_ISSUE = re.compile(
    r"Issue Description:?\s*\n(.+?)(?=\n\s*(?:Opened by|Category|Time)\b|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def _kind(message: dict, staff_ids: set[str], owner_ids: set[str]) -> str | None:
    """Return the speaker's role, or None for the bot."""
    author = message.get("author") or {}
    if author.get("bot"):
        return None

    author_id = str(author.get("id", ""))
    if author_id in owner_ids:
        return ROLE_OWNER
    if author_id in staff_ids:
        return ROLE_HELPER
    return ROLE_CUSTOMER


def _text_of(message: dict) -> str:
    """The message text plus one marker per attachment."""
    parts = [(message.get("content") or "").strip()]
    parts += [IMAGE_MARKER] * len(message.get("attachments") or [])
    return "\n".join(p for p in parts if p).strip()


def first_question(content: str) -> str:
    """Return the first line containing a question mark, or an empty string.

    The bot's onboarding message runs to forty lines, but the actual question
    comes first - and that holds in every language version of the template. The
    rest (greeting, feature list, example answers) is not part of the
    conversation.
    """
    for line in (content or "").splitlines():
        line = line.strip()
        if "?" in line:
            return line
    return ""


def extract_issue(content: str) -> str:
    """Pull 'Issue Description' out of the form the bot opens a ticket with.

    Returns an empty string when the message is not such a form.
    """
    found = _ISSUE.search(content or "")
    return found.group(1).strip() if found else ""


def to_thread(
    messages: Iterable[dict],
    staff_ids: set[str] | None = None,
    owner_ids: set[str] | None = None,
) -> list[Message]:
    """Convert Discord messages into a thread for the pipeline.

    Args:
        messages: messages oldest first, shaped as the Discord API returns
            them - we need author.id, author.bot, content and attachments.
        staff_ids: Discord ids of the helpers. Anyone who is neither in here
            nor an owner counts as a customer.
        owner_ids: Discord ids of the owner.

    It does not decide whether an answer is due - the pipeline checks that.
    When a thread ends with a helper, we are waiting on the customer and the
    bot has nothing to propose.
    """
    staff_ids = staff_ids or set()
    owner_ids = owner_ids or set()

    thread: list[Message] = []
    last_author: str | None = None
    # A question from the bot the customer has not answered yet.
    pending_question: str = ""

    for message in messages:
        role = _kind(message, staff_ids, owner_ids)

        if role is None:
            # From a bot message we care about the ticket description and the
            # question the customer is answering. The rest (welcome walls,
            # '@Helper user needs help') is noise.
            #
            # A bot message between two helper messages does NOT change
            # last_author - otherwise it would break their merge while not
            # being part of the conversation itself.
            issue = extract_issue(message.get("content", ""))
            if issue and not thread:
                thread.append(Message(role=ROLE_CUSTOMER, text=issue))
                last_author = "__ticket__"
            else:
                pending_question = first_question(message.get("content", ""))
            continue

        text = _text_of(message)
        if not text:
            continue

        author_id = str((message.get("author") or {}).get("id", ""))

        # Without the question the model would see a bare answer ('Reselling,
        # Ralph Lauren') and ask what it can help with - repeating the question
        # the customer had just answered.
        if pending_question and role == ROLE_CUSTOMER:
            thread.append(Message(role=ROLE_HELPER, text=pending_question))
            last_author = None
        pending_question = ""

        # Consecutive messages from the same person are merged: people type in
        # pieces, and three messages would read as three separate turns.
        if thread and author_id == last_author:
            previous = thread[-1]
            thread[-1] = Message(
                role=previous.role,
                text=f"{previous.text}\n{text}",
                name=previous.name,
            )
            continue

        thread.append(
            Message(
                role=role,
                text=text,
                # The name is kept for staff only - for a customer it is
                # personal data the model does not need.
                name="" if role == ROLE_CUSTOMER else (message.get("author") or {}).get("username", ""),
            )
        )
        last_author = author_id

    return thread
