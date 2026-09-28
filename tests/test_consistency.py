"""Consistency checks between things that can be changed separately.

Every test here replaces an item of a change checklist that would otherwise
rely on somebody remembering it. A list in a file is a request; this is a rule.
"""

import json
from pathlib import Path

from fyndit_helper.checks import ALLOWED_CHANNELS
from fyndit_helper.docs import load_documents
from fyndit_helper.evaluation import load_cases
from fyndit_helper.knowledge import load_notes
from fyndit_helper.prompt import build_system_prompt, load_template
from fyndit_helper.videos import load_videos

REPO = Path(__file__).resolve().parent.parent
PROMPT = REPO / "prompts" / "system_prompt.md"
CASES = REPO / "data" / "eval" / "cases.json"


def _all_content() -> str:
    """Everything the model can draw from: the docs plus the notes."""
    docs = " ".join(d.content for d in load_documents(REPO / "data" / "docs" / "en"))
    notes = " ".join(n.content for n in load_notes(REPO / "data" / "knowledge" / "notes"))
    return (docs + " " + notes).lower()


def test_the_allowed_channels_are_in_the_prompt_too():
    """The channel list lives in two places - in the code and in the prompt.
    When they drift apart, the model either uses a channel the check rejects or
    fails to use one it is allowed to."""
    template = load_template(PROMPT)

    for channel in ALLOWED_CHANNELS:
        assert channel in template, f"channel '{channel}' is in the code but not in the prompt"

    # And the other way round. The test used to claim it covered both and
    # covered one: an extra channel in the prompt would be used by the model and
    # rejected by the check as invented.
    import re

    in_prompt = set(re.findall(r"#([🀀-🫿☀-➿][\w-]+)", template))
    extra = in_prompt - set(ALLOWED_CHANNELS)

    assert not extra, f"a channel is in the prompt but not in ALLOWED_CHANNELS: {extra}"


def test_must_mention_words_can_be_found_in_the_content():
    """A regression: a case required the word 'non-refundable', which does NOT
    occur in the corpus - the docs put it entirely differently. The model had no
    way to pass and I was drawing conclusions about its quality from that.

    Only one alternative from each group is checked: for
    'free|gratis|zadarmo' it is enough that the content has at least one."""
    content = _all_content()
    problems = []

    for case in load_cases(CASES):
        if case.expects != "answer":
            continue
        for term in case.must_mention:
            alternatives = [a.strip().lower() for a in term.split("|") if a.strip()]
            if not any(a in content for a in alternatives):
                problems.append(f"{case.id}: '{term}'")

    assert not problems, (
        "must_mention requires words that are in neither the docs nor the notes:\n  "
        + "\n  ".join(problems)
    )


def test_must_not_mention_can_be_found_in_the_content():
    """The mirror of the test above, for the opposite field.

    The point of must_not_mention is to stop the model from raising a topic it
    KNOWS - whitelabel, say, when nobody asked. When the term cannot be found in
    the content, the model does not know about it and the rule has nothing to
    catch: it is either a typo or decoration. The test would stay silent about
    that, because it cannot fail."""
    content = _all_content()
    suspicious = []

    for case in load_cases(CASES):
        for term in case.must_not_mention:
            alternatives = [a.strip().lower() for a in term.split("|") if a.strip()]
            if not any(a in content for a in alternatives):
                suspicious.append(f"{case.id}: '{term}'")

    assert not suspicious, (
        "must_not_mention forbids a topic that is not in the content - a typo or "
        "a pointless rule: " + ", ".join(suspicious)
    )


def test_every_gap_case_is_still_a_gap():
    """A regression: after a note was added, one case stopped being a gap but
    its label stayed. The model answered correctly, cited the note, and the
    evaluation punished it for that.

    A shared-word heuristic will never be precise - on its first run it flagged
    a case that still is a gap. So it does not ask for correctness but for a
    ONE-OFF DECISION: once the overlap is reviewed and it is still a gap, write
    'overlap_ok' into the case with the reason and the test goes quiet.

    That turns it into what it should be - a forced read on every new note, not
    permanent noise that stops being read."""
    raw = {c["id"]: c for c in json.loads(CASES.read_text(encoding="utf-8"))["cases"]}
    notes = load_notes(REPO / "data" / "knowledge" / "notes")
    suspicious = []

    for case in load_cases(CASES):
        if case.expects != "gap" or raw[case.id].get("overlap_ok"):
            continue
        words = {w for w in case.question.lower().split() if len(w) > 5}
        # A second signal: the note's name inside the case id. Word overlap does
        # not work across languages - the notes are in Slovak, the questions in
        # the customer's language. That is how 'white-label-price' versus the
        # note 'whitelabel' slipped through silently.
        bare_id = case.id.replace("-", "").lower()
        for note in notes:
            text = (note.title + " " + note.content).lower()
            shared = {w for w in words if w in text}
            if len(shared) >= 4:
                suspicious.append(f"{case.id} vs {note.id}: {sorted(shared)}")
            elif note.id.replace("-", "") in bare_id:
                suspicious.append(f"{case.id} vs {note.id}: the names match")

    assert not suspicious, (
        "a gap case overlaps with a note - it may no longer be a gap:\n  "
        + "\n  ".join(suspicious)
    )


def test_the_videos_really_reach_the_prompt():
    """The original test read

        assert "{videos}" in template or all(v.url in template ...)

    but "{videos}" is the template's placeholder, so the left side was ALWAYS
    true and the right side never evaluated. The test verified nothing from the
    day it was written.

    Now the ASSEMBLED prompt is checked, not the template - when the placeholder
    is renamed or dropped, the videos silently disappear and the model stops
    pointing at tutorials."""
    videos = load_videos(REPO / "data" / "knowledge" / "videos.json")
    prompt = build_system_prompt(
        load_template(PROMPT),
        load_documents(REPO / "data" / "docs" / "en"),
        videos,
        load_notes(REPO / "data" / "knowledge" / "notes"),
    )

    assert videos, "videos.json is empty - the test would verify nothing"
    missing = [v.url for v in videos if v.url not in prompt]

    assert not missing, f"the videos are not in the assembled prompt: {missing}"


def test_no_case_has_a_duplicate_id():
    """rescore.py SILENTLY skips an unknown id - a duplicate or a typo would
    show up as a better result, not as an error."""
    raw = json.loads(CASES.read_text(encoding="utf-8"))
    ids = [c["id"] for c in raw["cases"]]

    assert len(ids) == len(set(ids))
