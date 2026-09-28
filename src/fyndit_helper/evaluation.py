"""Scoring a proposed answer against what was expected.

It joins two layers:
  1. the automatic checks from checks.py - deterministic, no model involved
  2. the expectation from the eval set - is the answer in the docs, or must the
     model admit a gap

The most important thing measured here is not whether the answer is correct. It
is whether the model admits it does not know. A confident answer to an
unanswerable question is worse than none.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fyndit_helper.checks import (
    MARKER,
    SEVERITY_ERROR,
    CheckError,
    Finding,
    run_checks,
    split_sections,
)
from fyndit_helper.pipeline import ROLE_CUSTOMER, Message


EXPECTS_ANSWER = "answer"
EXPECTS_GAP = "gap"
VALID_EXPECTS = {EXPECTS_ANSWER, EXPECTS_GAP}


@dataclass(frozen=True)
class Case:
    """One case of the eval set.

    'question' is the last customer message - what the model answers. 'thread'
    is the whole conversation including the earlier messages. For a
    single-message case the two are the same; they are kept apart because the
    checks need to know WHAT was answered, while the model needs the full
    context.
    """

    id: str
    question: str
    language: str
    expects: str
    must_mention: tuple[str, ...]
    note: str
    # With a default: without one, everything that builds a Case by hand breaks.
    must_not_mention: tuple[str, ...] = ()
    #: Like must_mention, but searched ONLY in NA ODOSLANIE.
    #: must_mention searches the whole answer, so it also passes when the model
    #: knows the thing and writes it into the NÁVRH while sending the customer
    #: an empty promise ("I'll check and get back to you"). That is exactly what
    #: it does with a message asking several questions, one of which is a gap.
    must_mention_sent: tuple[str, ...] = ()
    thread: tuple[Message, ...] = ()


@dataclass(frozen=True)
class CaseResult:
    """The result of one case.

    There are THREE outcomes, not two:
      - error is not None  -> the case could not be run (outage, rate limit).
        That says NOTHING about the model and must not count as a failure.
      - passed=True        -> it ran and the answer fits
      - passed=False       -> it ran and the answer does not fit

    Originally there was only passed/failed and outages counted as model
    mistakes. One run looked like 6/12 when it really was 6/7.
    """

    case_id: str
    passed: bool
    reasons: tuple[str, ...]
    findings: tuple[Finding, ...]
    answer: str
    ticket_sk: str
    error: str | None = None

    #: Did the model decide correctly whether it knows the answer? That is: is
    #: the ⚠️ marker where it belongs, and absent where it does not?
    #:
    #: Kept apart from 'passed', because they are two different things. In one
    #: run a model raised the marker correctly on gaps but wrote "our
    #: documentation" to the customer - the cases failed on style and the
    #: summary looked like 1/9 gaps recognised, when it had actually got 5/9
    #: right. One number drowned out the other.
    marker_correct: bool = False
    #: A required mention was missing from NA ODOSLANIE - so the customer did
    #: not receive what they should have. This is NOT a style issue, even when
    #: the marker is right.
    undelivered: bool = False

    @property
    def evaluated(self) -> bool:
        """True when the case was actually scored."""
        return self.error is None


def load_cases(path: Path) -> list[Case]:
    """Load the eval set.

    Raises:
        FileNotFoundError: the file does not exist.
        ValueError: a case has a missing or invalid field.
    """
    if not path.is_file():
        raise FileNotFoundError(f"eval set does not exist: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))

    cases = []
    for entry in raw.get("cases", []):
        expects = entry.get("expects")
        if expects not in VALID_EXPECTS:
            raise ValueError(
                f"case '{entry.get('id', '?')}': expects must be "
                f"{' or '.join(sorted(VALID_EXPECTS))}, not {expects!r}"
            )

        thread = _read_thread(entry)

        cases.append(
            Case(
                id=entry["id"],
                # The model answers the last message; the checks must compare
                # against that, not against the first message of the thread.
                question=thread[-1].text,
                language=entry.get("language", "en"),
                expects=expects,
                must_mention=tuple(entry.get("must_mention", [])),
                must_mention_sent=tuple(entry.get("must_mention_sent", [])),
                must_not_mention=tuple(entry.get("must_not_mention", [])),
                note=entry.get("note", ""),
                thread=thread,
            )
        )

    return cases


def _read_thread(entry: dict) -> tuple[Message, ...]:
    """Turn a case into a thread.

    A case can be written two ways:
      "question": "..."                  - a single customer message
      "thread": [{"role":..,"text":..}]  - the whole conversation

    The first form is shorthand for the second, so most cases need not be
    written out in full.

    Raises:
        ValueError: both are missing, or the thread does not end with the
            customer.
    """
    case_id = entry.get("id", "?")

    if entry.get("thread"):
        thread = tuple(
            Message(role=m["role"], text=m["text"]) for m in entry["thread"]
        )
    elif entry.get("question"):
        thread = (Message(role=ROLE_CUSTOMER, text=entry["question"]),)
    else:
        raise ValueError(f"case '{case_id}': both 'question' and 'thread' are missing")

    # The same condition holds in the pipeline. Catching it here means a broken
    # case is reported before the run, not in the middle of it after paid-for
    # calls.
    if thread[-1].role != ROLE_CUSTOMER:
        raise ValueError(
            f"case '{case_id}': the thread does not end with a customer message - "
            "there is nothing to answer"
        )

    return thread


def score(case: Case, answer: str, ticket_sk: str) -> CaseResult:
    """Compare the answer with the expectation and return a verdict with reasons."""
    reasons: list[str] = []

    # Language detection gets EVERYTHING the customer wrote, not just the last
    # message. In one ticket the last message was only a link and an image
    # marker, so detection had nothing to work with and the check passed
    # silently - even though the model had answered an English customer in
    # Slovak.
    from_customer = ' '.join(m.text for m in case.thread if m.role == ROLE_CUSTOMER)
    findings = tuple(
        run_checks(answer, ticket_sk=ticket_sk, question=from_customer or case.question)
    )
    reasons.extend(
        f"{f.check}: {f.detail}" for f in findings if f.severity == SEVERITY_ERROR
    )

    try:
        sections = split_sections(answer)
        has_marker = MARKER in sections.proposal
    except CheckError:
        # The automatic checks already added the reason - the marker cannot be
        # judged.
        has_marker = False
        sections = None

    # Unverifiable does not count as correct: when the answer cannot be split,
    # we know nothing about the model's decision.
    marker_correct = sections is not None and has_marker == (case.expects == EXPECTS_GAP)

    if sections is not None:
        if case.expects == EXPECTS_GAP and not has_marker:
            reasons.append(
                "the ⚠️ marker is missing - the answer is not in the docs, but the "
                "model gave one anyway"
            )
        elif case.expects == EXPECTS_ANSWER and has_marker:
            reasons.append(
                "the ⚠️ marker is not needed here - the answer is in the documentation"
            )

    # The message to the customer is in THEIR language, so an English word need
    # not appear in it. A pipe separates alternatives - one match is enough.
    lowered = answer.lower()
    for term in case.must_mention:
        if not any(alt.lower() in lowered for alt in term.split("|")):
            reasons.append(f"the required mention of '{term}' is missing")

    # The opposite of must_mention: topics the model must NOT raise on its own.
    # Without it there is no way to measure an instruction like "offer
    # whitelabel only when asked" - must_mention only verifies what should be
    # there.
    for term in case.must_not_mention:
        if any(alt.lower() in lowered for alt in term.split("|")):
            reasons.append(f"the model must not raise '{term}' on its own")

    # When the answer could not be split we know nothing about NA ODOSLANIE and
    # the automatic checks already reported it - no need to say it twice.
    undelivered = False
    if case.must_mention_sent and sections is not None:
        sent = sections.to_send.lower()
        for term in case.must_mention_sent:
            if not any(alt.lower() in sent for alt in term.split("|")):
                undelivered = True
                reasons.append(
                    f"'{term}' is missing from NA ODOSLANIE - the customer never got it"
                )

    return CaseResult(
        case_id=case.id,
        passed=not reasons,
        reasons=tuple(reasons),
        findings=findings,
        answer=answer,
        ticket_sk=ticket_sk,
        marker_correct=marker_correct,
        undelivered=undelivered,
    )
