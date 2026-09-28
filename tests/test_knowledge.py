"""The second knowledge layer - what we know from practice but the official
docs do not say.

The essential difference from the docs: behind the docs stands the vendor's
server, behind this stands somebody on the team. So every note carries WHO
confirmed it and WHEN.
"""

from pathlib import Path

import pytest

from fyndit_helper.knowledge import KNOWLEDGE_PREFIX, Note, load_notes, render_notes

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "data" / "knowledge" / "notes"


def write(tmp_path, name, text):
    (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


NOTE = """---
id: test-note
title: A test note
verified_by: the helper
verified_on: 2026-08-16
---

# Heading

The body of the note.
"""


# --- loading ---------------------------------------------------------------


def test_loads_a_note(tmp_path):
    write(tmp_path, "a.md", NOTE)

    notes = load_notes(tmp_path)

    assert len(notes) == 1
    assert notes[0].id == "test-note"
    assert notes[0].title == "A test note"
    assert notes[0].verified_by == "the helper"
    assert "The body of the note." in notes[0].content


def test_an_empty_directory_is_not_an_error(tmp_path):
    """Unlike the docs, the second layer is optional - the project works
    without it."""
    assert load_notes(tmp_path) == []


def test_a_missing_directory_is_not_an_error(tmp_path):
    assert load_notes(tmp_path / "nothing") == []


def test_a_note_without_confirmation_is_an_error(tmp_path):
    """Without who confirmed it, it is just a claim. The docs have a server
    behind them, this has a person - and that person has to be named."""
    write(tmp_path, "a.md", NOTE.replace("verified_by: the helper\n", ""))

    with pytest.raises(ValueError, match="verified_by"):
        load_notes(tmp_path)


def test_a_note_without_an_id_is_an_error(tmp_path):
    write(tmp_path, "a.md", NOTE.replace("id: test-note\n", ""))

    with pytest.raises(ValueError, match="id"):
        load_notes(tmp_path)


# --- rendering into the prompt ---------------------------------------------


def test_the_rendering_carries_the_id_and_the_title():
    out = render_notes([Note(id="x", title="Heading", content="body",
                             verified_by="the helper", verified_on="2026-08-16")])

    assert "x" in out
    assert "Heading" in out
    assert "body" in out


def test_the_rendering_marks_it_as_not_official_documentation():
    """The model has to know this carries different weight from the docs - even
    though it answers from it normally."""
    out = render_notes([Note(id="x", title="N", content="t",
                             verified_by="the helper", verified_on="2026-08-16")])

    assert "note" in out.lower()


def test_an_empty_list_renders_empty_text():
    assert render_notes([]) == ""


# --- the real content ------------------------------------------------------


def test_the_real_notes_load():
    notes = load_notes(NOTES_DIR)

    assert len(notes) >= 1
    assert all(n.id and n.title and n.verified_by for n in notes)


def test_a_note_citation_has_its_own_prefix():
    """A citation has to be distinguishable from a documentation URL, otherwise
    there is no telling whether an answer rests on an official source or on our
    own experience."""
    notes = load_notes(NOTES_DIR)

    assert all(n.source.startswith(KNOWLEDGE_PREFIX) for n in notes)


# --- quotation marks in a title --------------------------------------------


def test_a_title_with_quotes_is_loaded_whole(tmp_path):
    """Note titles quote error messages, so quotation marks are common."""
    write(tmp_path, "a.md", NOTE.replace(
        "title: A test note", 'title: "Invalid link" on a monitor'))

    assert load_notes(tmp_path)[0].title == '"Invalid link" on a monitor'


def test_quotes_in_a_title_do_not_break_the_tag():
    """Without escaping, title="..." would produce a broken tag and the model
    would not know where the note ends."""
    out = render_notes([Note(id="x", title='"Invalid link" on a monitor',
                             content="body", verified_by="the helper",
                             verified_on="2026-08-16")])

    header = out.split("\n")[0]

    assert header.count('"') % 2 == 0, f"odd number of quotes: {header}"
    assert header.endswith(">")
    assert "&quot;" in header
