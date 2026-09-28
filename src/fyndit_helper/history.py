"""Ticket history: what we have already answered, stored on disk.

Why at all:
The pipeline is deliberately stateless - the whole thread travels with every
call and nothing is shared between tickets. That is good for the model and bad
for the person: close the tab and the answer was gone, and there was no way to
start a "new chat" because no old one existed.

Why JSON and not a database:
There are a handful of writes a day and they are read whole. A database would
add a dependency, migrations and one more server - and would solve nothing yet.
Once a file stops being enough (several processes, thousands of tickets) this
module gets replaced, not its callers.

Why it is NOT committed:
These are real customer messages. The directory belongs in .gitignore.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

#: How many tickets are kept. Older ones are dropped oldest first. Without a
#: cap the file would grow forever and be read whole on every write.
MAX_TICKETS = 500

#: Length of the title in the list. A whole first message is often a paragraph -
#: it does not fit a sidebar and says nothing extra.
TITLE_LENGTH = 80

#: Writes arrive from FastAPI, which runs synchronous endpoints in threads.
#: Without the lock two concurrent tickets would read the same state and one
#: would overwrite the other.
_LOCK = threading.Lock()


class HistoryError(RuntimeError):
    """The history cannot be read or written."""


@dataclass(frozen=True)
class Record:
    """One ticket with everything we produced for it."""

    id: str
    created_at: str
    updated_at: str
    #: The whole thread as it last arrived. A thread only grows, so the latest
    #: one contains all the previous messages - storing it again per round
    #: would inflate the file quadratically.
    thread: list[dict]
    #: What we answered, in order. Each answer remembers which message it
    #: followed - otherwise there is no telling what it responded to.
    answers: list[dict]

    @property
    def title(self) -> str:
        """The first customer message, shortened. Used as the title in the list."""
        for message in self.thread:
            if message.get("role") == "customer" and message.get("text", "").strip():
                text = " ".join(message["text"].split())
                if len(text) > TITLE_LENGTH:
                    return text[: TITLE_LENGTH - 1] + "…"
                return text
        return "(no question)"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "thread": self.thread,
            "answers": self.answers,
        }

    def summary(self) -> dict:
        """A row for the list - without the body, so not everything is sent."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "title": self.title,
            "message_count": len(self.thread),
            "answer_count": len(self.answers),
            # Based on the LAST answer - that is the state of the ticket now.
            # An earlier round may have been a gap the next round answered.
            "escalate": bool(self.answers and self.answers[-1].get("escalate")),
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path: Path) -> list[dict]:
    """Records from the file. A missing file is empty history, not an error."""
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HistoryError(f"{path.name}: history file is corrupted ({exc})") from exc
    if not isinstance(data, list):
        raise HistoryError(f"{path.name}: expected a list of tickets")
    return data


def _write(path: Path, records: list[dict]) -> None:
    """Write through a temporary file and a rename.

    Writing straight into the target means a crash halfway leaves the file
    truncated - and that loses the WHOLE history, not the last ticket.
    os.replace is atomic within one filesystem.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".tmp")
    partial.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(partial, path)


def record_round(
    path: Path,
    *,
    conversation_id: str | None,
    thread: list[dict],
    ticket_sk: str,
    answer: str,
    mode: str,
    escalate: bool = False,
    findings: list[dict] | None = None,
    regenerated: bool = False,
) -> str:
    """Append one round to a ticket and return its id.

    When conversation_id is missing or unknown, a new ticket is created. "New
    chat" in the interface is therefore not an operation at all - it is just a
    new id.
    """
    with _LOCK:
        records = _load(path)

        round_entry = {
            "at": _now(),
            "after_message": len(thread),
            "ticket_sk": ticket_sk,
            "answer": answer,
            "mode": mode,
            # Stored, not derived on read: what counted as an escalation at the
            # time of answering should stay that way even if the prompt changes.
            "escalate": escalate,
            # Stored with the answer for the same reason: the checks keep
            # evolving and a reopened ticket should show what held back then.
            "findings": findings or [],
            # How many rewrites it took says something about the run, not about
            # the ticket - but without it there is no way to find out later.
            "regenerated": regenerated,
        }

        for record in records:
            if conversation_id and record.get("id") == conversation_id:
                record["thread"] = thread
                record.setdefault("answers", []).append(round_entry)
                record["updated_at"] = round_entry["at"]
                _write(path, records)
                return conversation_id

        new_id = conversation_id or uuid.uuid4().hex[:12]
        records.append(
            {
                "id": new_id,
                "created_at": round_entry["at"],
                "updated_at": round_entry["at"],
                "thread": thread,
                "answers": [round_entry],
            }
        )
        # The cap applies to the oldest CREATED, not the least recently used -
        # otherwise a long-running ticket would drop out mid-conversation.
        if len(records) > MAX_TICKETS:
            del records[: len(records) - MAX_TICKETS]

        _write(path, records)
        return new_id


def _as_record(raw: dict) -> Record:
    return Record(
        id=raw.get("id", ""),
        created_at=raw.get("created_at", ""),
        updated_at=raw.get("updated_at", ""),
        thread=raw.get("thread", []),
        answers=raw.get("answers", []),
    )


def list_records(path: Path) -> list[dict]:
    """Overview of the tickets, most recently used first."""
    with _LOCK:
        records = _load(path)
    overview = [_as_record(r).summary() for r in records]
    overview.sort(key=lambda r: r["updated_at"], reverse=True)
    return overview


def load(path: Path, ticket_id: str) -> dict | None:
    """The whole ticket, or None when there is no such ticket."""
    with _LOCK:
        for raw in _load(path):
            if raw.get("id") == ticket_id:
                return _as_record(raw).to_dict()
    return None


def delete(path: Path, ticket_id: str) -> bool:
    """Delete a ticket. Returns whether it was there at all."""
    with _LOCK:
        records = _load(path)
        remaining = [r for r in records if r.get("id") != ticket_id]
        if len(remaining) == len(records):
            return False
        _write(path, remaining)
        return True
