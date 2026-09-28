import json
from pathlib import Path

import pytest

from fyndit_helper.evaluation import Case, load_cases, score
from fyndit_helper.pipeline import Message

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = REPO_ROOT / "data" / "eval" / "cases.json"

SK = (
    "Ahoj! Skús skontrolovať región svojej session a otvoriť si ten item ručne "
    "na Vinted. Ak sa nedá doručiť do tvojho regiónu, autocop ho nekúpi."
)
EN = (
    "Hey! Check your session region and open the item manually on Vinted. If it "
    "cannot be shipped to your region, autocop will not buy it."
)


def answer(proposal: str = SK, to_send: str = EN) -> str:
    return f"**NÁVRH (SK)**\n{proposal}\n\n**NA ODOSLANIE**\n{to_send}"


def case(expects: str = "answer", must_mention: tuple[str, ...] = ()) -> Case:
    return Case(
        id="t",
        question="q",
        language="en",
        expects=expects,
        must_mention=must_mention,
        note="",
    )


# --- loading the set -------------------------------------------------------


def test_the_real_set_loads():
    cases = load_cases(CASES_PATH)

    assert len(cases) >= 10
    assert all(c.expects in {"answer", "gap"} for c in cases)
    assert all(c.question.strip() for c in cases)


def test_the_set_contains_both_types():
    """Without gap cases, invention is never measured."""
    cases = load_cases(CASES_PATH)

    assert any(c.expects == "gap" for c in cases)
    assert any(c.expects == "answer" for c in cases)


def test_no_case_overlaps_with_the_examples_in_the_prompt():
    """A regression: the test questions came from the same source as the
    examples in the prompt, so the model recited the answers."""
    template = (REPO_ROOT / "prompts" / "system_prompt.md").read_text(encoding="utf-8")
    cases = load_cases(CASES_PATH)

    for c in cases:
        # Meaningful words are compared, not whole sentences.
        words = {w.lower() for w in c.question.split() if len(w) > 6}
        overlap = {w for w in words if w in template.lower()}
        assert len(overlap) < 4, f"case '{c.id}' is too close to an example in the prompt"


def test_every_gap_carries_evidence_that_it_really_is_absent():
    """A regression: THREE of my five 'gaps' did have an answer in the docs -
    only in a different file from the one I searched. I was labelling them by
    what a human said in the ticket, not by what the documentation says.

    Every gap case now has to carry a grep that proves the absence.
    """
    raw = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    for entry in raw["cases"]:
        if entry.get("expects") == "gap":
            assert entry.get("verified_absent"), (
                f"case '{entry['id']}' is labelled a gap but has no "
                "'verified_absent' - the evidence that it really is not in the docs"
            )


def test_a_missing_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_cases(tmp_path / "nothing.json")


def test_a_case_without_expects_is_an_error(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"cases": [{"id": "a", "question": "q"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="expects"):
        load_cases(path)


# --- scoring ---------------------------------------------------------------


def test_a_good_answer_passes():
    result = score(case(), answer(), ticket_sk="t")

    assert result.passed
    assert result.reasons == ()


def test_a_missing_marker_on_a_gap_is_a_failure():
    """The most important test of the whole evaluation: the model made an answer
    up."""
    result = score(case(expects="gap"), answer(), ticket_sk="t")

    assert not result.passed
    assert any("marker" in r for r in result.reasons)


def test_the_marker_on_a_gap_passes():
    result = score(
        case(expects="gap"),
        answer(proposal=f"⚠️ Toto v docs nie je.\n{SK}"),
        ticket_sk="t",
    )

    assert result.passed


def test_a_marker_where_an_answer_exists_is_a_failure():
    """The opposite mistake: the model excuses itself with a gap although the
    answer is in the docs."""
    result = score(
        case(expects="answer"),
        answer(proposal=f"⚠️ Toto v docs nie je.\n{SK}"),
        ticket_sk="t",
    )

    assert not result.passed


def test_a_missing_required_mention_is_a_failure():
    result = score(case(must_mention=("timeout",)), answer(), ticket_sk="t")

    assert not result.passed
    assert any("timeout" in r for r in result.reasons)


def test_a_required_mention_is_matched_case_insensitively():
    result = score(case(must_mention=("REGION",)), answer(), ticket_sk="t")

    assert result.passed


def test_one_of_the_alternatives_is_enough():
    """The customer's message is in their language - an English word need not
    appear in it. Without alternatives a Spanish answer would be marked wrong."""
    result = score(case(must_mention=("autocop|gratuito|zadarmo",)), answer(), ticket_sk="t")

    assert result.passed


def test_when_no_alternative_matches_it_is_a_failure():
    result = score(case(must_mention=("gratuito|zadarmo",)), answer(), ticket_sk="t")

    assert not result.passed


def test_an_error_from_the_automatic_checks_is_a_failure():
    result = score(
        case(),
        answer(to_send=f"⚠️ Not in our docs. {EN}"),
        ticket_sk="t",
    )

    assert not result.passed
    assert any("marker_leaked" in r for r in result.reasons)


def test_a_scored_case_has_no_error():
    result = score(case(), answer(), ticket_sk="t")

    assert result.evaluated
    assert result.error is None


def test_a_case_that_never_ran_does_not_count_as_a_model_failure():
    """A regression: provider outages counted as model mistakes. A run looked
    like 6/12 when it really was 6/7."""
    from fyndit_helper.evaluation import CaseResult

    result = CaseResult(
        case_id="t",
        passed=False,
        reasons=(),
        findings=(),
        answer="",
        ticket_sk="",
        error="the provider returned 503",
    )

    assert not result.evaluated


def test_an_unsplittable_answer_is_a_failure():
    result = score(case(), "Just one block of text with no sections.", ticket_sk="t")

    assert not result.passed


# --- threads in the eval set -----------------------------------------------


def write_cases(tmp_path, cases):
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"cases": cases}), encoding="utf-8")
    return path


def test_a_single_question_loads_as_a_thread_with_one_message(tmp_path):
    """Old cases have to keep working unchanged - they are the majority of the
    set."""
    path = write_cases(tmp_path, [
        {"id": "a", "question": "why is autocop broken", "expects": "answer"},
    ])

    case = load_cases(path)[0]

    assert len(case.thread) == 1
    assert case.thread[0].role == "customer"
    assert case.thread[0].text == "why is autocop broken"


def test_a_thread_loads_whole(tmp_path):
    path = write_cases(tmp_path, [
        {"id": "a", "expects": "answer", "thread": [
            {"role": "customer", "text": "where do i see my monitors"},
            {"role": "helper", "text": "in the dashboard"},
            {"role": "customer", "text": "i dont have that"},
        ]},
    ])

    case = load_cases(path)[0]

    assert [m.role for m in case.thread] == ["customer", "helper", "customer"]


def test_the_question_is_the_last_customer_message(tmp_path):
    """The checks need to know what the model answered - that is the last
    message, not the first."""
    path = write_cases(tmp_path, [
        {"id": "a", "expects": "answer", "thread": [
            {"role": "customer", "text": "where do i see my monitors"},
            {"role": "helper", "text": "in the dashboard"},
            {"role": "customer", "text": "i dont have that screen"},
        ]},
    ])

    assert load_cases(path)[0].question == "i dont have that screen"


def test_a_case_with_neither_question_nor_thread_is_an_error(tmp_path):
    path = write_cases(tmp_path, [{"id": "a", "expects": "answer"}])

    with pytest.raises(ValueError, match="question|thread"):
        load_cases(path)


def test_a_thread_has_to_end_with_the_customer(tmp_path):
    """Otherwise there is nothing to answer and the pipeline would refuse it
    anyway."""
    path = write_cases(tmp_path, [
        {"id": "a", "expects": "answer", "thread": [
            {"role": "customer", "text": "hello"},
            {"role": "helper", "text": "hi"},
        ]},
    ])

    with pytest.raises(ValueError, match="customer"):
        load_cases(path)


# --- substance kept apart from style ---------------------------------------


def test_the_right_marker_is_substantively_right_even_when_the_case_fails():
    """In one run a model raised the marker correctly on a gap but wrote 'our
    documentation' to the customer. The case failed on style and the summary
    made it look as though the gap had not been recognised. It had."""
    result = score(
        case(expects="gap"),
        answer(proposal=f"⚠️ Toto v docs nie je.\n{SK}",
               to_send=f"{EN} I could not find it in our documentation."),
        ticket_sk="t",
    )

    assert not result.passed          # a style mistake still fails the case
    assert result.marker_correct      # but the model got the substance right


def test_a_missing_marker_on_a_gap_is_not_substantively_right():
    result = score(case(expects="gap"), answer(), ticket_sk="t")

    assert not result.marker_correct


def test_a_superfluous_marker_on_an_answer_is_not_substantively_right():
    result = score(
        case(expects="answer"),
        answer(proposal=f"⚠️ Toto v docs nie je.\n{SK}"),
        ticket_sk="t",
    )

    assert not result.marker_correct


def test_clean_answers_are_substantively_right():
    assert score(case(expects="answer"), answer(), ticket_sk="t").marker_correct


def test_an_unsplittable_answer_is_not_substantively_right():
    """When the answer cannot be split, nothing can be said about the marker -
    and nothing means 'unverifiable', not 'fine'."""
    result = score(case(expects="gap"), "one block with no sections", ticket_sk="t")

    assert not result.marker_correct


def test_must_not_mention_catches_an_extra_topic():
    """The opposite of must_mention. It came from the instruction 'offer
    whitelabel only when asked' - that cannot be measured through must_mention,
    which only verifies what SHOULD be in the answer."""
    c = Case(
        id='x', question='how do i start?', language='en', expects='answer',
        must_mention=(), note='', must_not_mention=('whitelabel|white label',),
        thread=(Message(role='customer', text='how do i start?'),),
    )
    given = (
        """
**NÁVRH (SK)**

Ahoj, zacni tutorialmi.

**NA ODOSLANIE**

Hey! Start with the tutorials. We also offer whitelabel for your own server."""
    )

    result = score(c, answer=given, ticket_sk='Ako zacnem?')

    assert any('whitelabel' in r for r in result.reasons)


def test_must_not_mention_stays_quiet_when_the_topic_is_absent():
    """A control for the test above - without it a pattern that always fires
    would pass too."""
    c = Case(
        id='x', question='how do i start?', language='en', expects='answer',
        must_mention=(), note='', must_not_mention=('whitelabel|white label',),
        thread=(Message(role='customer', text='how do i start?'),),
    )
    given = (
        """
**NÁVRH (SK)**

Ahoj, zacni tutorialmi.

**NA ODOSLANIE**

Hey! Start with the tutorials and set up your first monitor."""
    )

    result = score(c, answer=given, ticket_sk='Ako zacnem?')

    assert not [r for r in result.reasons if 'whitelabel' in r]


# --- must_mention_sent -----------------------------------------------------


def test_a_mention_only_in_the_draft_is_not_enough_when_the_customer_needs_it():
    """Exactly the mistake seen in the thread replays.

    The model knew the answer, wrote it into the NÁVRH - and sent the customer an
    empty promise, 'I'll check and get back to you'. must_mention searches the
    whole answer, so it considered that correct.
    """
    c = Case(
        id="t", question="q", language="en", expects="gap",
        must_mention=(), note="", must_mention_sent=("api",),
    )
    result = score(c, answer(proposal="through the api", to_send="I'll get back to you"),
                   ticket_sk="t")

    assert not result.passed
    assert any("NA ODOSLANIE" in r for r in result.reasons)


def test_a_mention_in_the_sent_part_passes():
    c = Case(
        id="t", question="q", language="en", expects="answer",
        must_mention=(), note="", must_mention_sent=("api",),
    )
    result = score(c, answer(to_send="we buy through the API"), ticket_sk="t")

    assert result.passed
