"""Ticket history.

What is tested is what we decided - not that json.dump works.
"""

import json

import pytest

from fyndit_helper import history


def _round(path, conversation_id=None, text="Question", answer="Answer"):
    return history.record_round(
        path,
        conversation_id=conversation_id,
        thread=[{"role": "customer", "text": text}],
        ticket_sk=text,
        answer=answer,
        mode="docs",
    )


def test_without_an_id_a_new_ticket_is_created(tmp_path):
    path = tmp_path / "tickets.json"

    first = _round(path, text="first")
    second = _round(path, text="second")

    assert first != second
    assert len(history.list_records(path)) == 2


def test_with_an_id_the_same_ticket_continues(tmp_path):
    """'New chat' is a new id - continuing is the same id, not a new record."""
    path = tmp_path / "tickets.json"

    ticket = _round(path, text="first")
    again = _round(path, conversation_id=ticket, text="first and second", answer="next")

    assert again == ticket
    records = history.list_records(path)
    assert len(records) == 1
    assert records[0]["answer_count"] == 2


def test_the_thread_is_replaced_not_appended(tmp_path):
    """The thread arrives whole from the interface, so the latest one contains
    the previous messages as well.

    Appending it on every round would inflate the file quadratically.
    """
    path = tmp_path / "tickets.json"
    ticket = _round(path, text="first")

    history.record_round(
        path,
        conversation_id=ticket,
        thread=[
            {"role": "customer", "text": "first"},
            {"role": "helper", "text": "answer"},
            {"role": "customer", "text": "second"},
        ],
        ticket_sk="second",
        answer="next",
        mode="docs",
    )

    assert len(history.load(path, ticket)["thread"]) == 3


def test_the_title_is_the_first_customer_message(tmp_path):
    path = tmp_path / "tickets.json"
    history.record_round(
        path,
        conversation_id=None,
        thread=[{"role": "customer", "text": "  Why  is\nmy autocop broken? "}],
        ticket_sk="",
        answer="",
        mode="docs",
    )

    assert history.list_records(path)[0]["title"] == "Why is my autocop broken?"


def test_the_cap_drops_the_oldest(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "MAX_TICKETS", 3)
    path = tmp_path / "tickets.json"

    ids = [_round(path, text=f"question {i}") for i in range(5)]

    remaining = {r["id"] for r in history.list_records(path)}
    assert remaining == set(ids[2:])


def test_a_corrupted_file_is_reported(tmp_path):
    """Silently returning an empty history would look like 'you had nothing
    yet'."""
    path = tmp_path / "tickets.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(history.HistoryError):
        history.list_records(path)


def test_a_missing_file_is_not_an_error(tmp_path):
    assert history.list_records(tmp_path / "nothing-yet.json") == []


def test_deleting_an_unknown_ticket_returns_false(tmp_path):
    path = tmp_path / "tickets.json"
    _round(path)

    assert history.delete(path, "does-not-exist") is False
    assert len(history.list_records(path)) == 1


def test_no_temporary_file_is_left_after_a_write(tmp_path):
    """Writes go through .tmp and a rename, so a crash does not wipe the whole
    history."""
    path = tmp_path / "tickets.json"
    _round(path)

    assert [p.name for p in tmp_path.iterdir()] == ["tickets.json"]
    assert json.loads(path.read_text(encoding="utf-8"))
