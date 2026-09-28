from pathlib import Path

import pytest

from fyndit_helper.docs import Document
from fyndit_helper.prompt import (
    DOCUMENTS_PLACEHOLDER,
    PromptError,
    build_system_prompt,
    load_template,
    render_documents,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "prompts" / "system_prompt.md"
TRANSLATE_PROMPT_PATH = REPO_ROOT / "prompts" / "translate_prompt.md"


def make_doc(slug: str, content: str = "Body.") -> Document:
    return Document(
        slug=slug,
        source=f"https://www.fyndit.app/docs/{slug}",
        title=slug.title(),
        content=content,
    )


# --- load_template ---------------------------------------------------------


def test_loads_the_template_from_a_file(tmp_path):
    path = tmp_path / "p.md"
    path.write_text(f"Instructions.\n\n{DOCUMENTS_PLACEHOLDER}\n", encoding="utf-8")

    assert load_template(path) == f"Instructions.\n\n{DOCUMENTS_PLACEHOLDER}"


def test_an_html_comment_is_stripped(tmp_path):
    path = tmp_path / "p.md"
    path.write_text(
        f"<!--\nA note for a human.\n-->\n\nInstructions.\n\n{DOCUMENTS_PLACEHOLDER}\n",
        encoding="utf-8",
    )

    template = load_template(path)

    assert "A note for a human" not in template
    assert "<!--" not in template
    assert template.startswith("Instructions.")


def test_a_missing_placeholder_is_an_error(tmp_path):
    path = tmp_path / "p.md"
    path.write_text("Instructions with no room for docs.\n", encoding="utf-8")

    with pytest.raises(PromptError, match="documents"):
        load_template(path)


def test_a_missing_template_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_template(tmp_path / "nothing.md")


def test_the_real_template_loads():
    template = load_template(PROMPT_PATH)

    assert DOCUMENTS_PLACEHOLDER in template
    assert "<!--" not in template
    assert "Toto v docs nie je" in template


def test_the_examples_are_marked_as_tone_not_a_source_of_facts():
    """The model takes examples as knowledge. When one contains a fact that is
    not in the docs, it delivers it as verified - and the founding rule quietly
    stops holding."""
    template = load_template(PROMPT_PATH)

    assert "TONE ONLY" in template


def test_the_examples_contain_no_facts_from_outside_the_documentation():
    """A regression: the examples once held three answers from real chats. The
    model recited them verbatim and claimed things that are nowhere in the
    docs."""
    template = load_template(PROMPT_PATH)

    leaked_facts = [
        "flagging the account for botting",
        "takes over your session",
        "set the size filter on Vinted itself",
    ]

    for fact in leaked_facts:
        assert fact not in template, f"a fact from outside the docs is back in the examples: {fact!r}"


def test_the_template_requires_the_draft_and_the_sent_text_to_match():
    """The helper approves the Slovak draft, but the foreign-language version is
    what gets sent. When they differ, something unapproved goes out."""
    template = load_template(PROMPT_PATH)

    assert "same message, differing only by language" in template


def test_the_translation_prompt_has_a_single_job():
    """A short prompt with one job is followed more reliably."""
    template = load_template(TRANSLATE_PROMPT_PATH, require_documents=False)

    assert "That is your only job" in template
    assert "do not answer the question" in template.lower()
    # The translation prompt must have no docs placeholder - it does not need
    # them.
    assert DOCUMENTS_PLACEHOLDER not in template


def test_the_template_forbids_a_negative_conclusion_from_a_gap():
    """A regression: the model wrote '(sk) is not in the docs' and immediately
    concluded that Slovakia is not supported. Absence is not evidence of
    non-existence."""
    template = load_template(PROMPT_PATH)

    assert "not evidence that something does not exist" in template


def test_the_template_forbids_invented_lists():
    """A regression: the model listed domains fr, de, pl, it... that are not in
    the docs."""
    template = load_template(PROMPT_PATH)

    assert "Never produce a list" in template


def test_the_template_insists_on_slovak_in_the_draft():
    """A regression: given an Italian question it returned the whole output in
    Italian, including the part the helper reads. Translation is a separate step
    now, but the answering prompt has to hold Slovak in the NÁVRH firmly."""
    template = load_template(PROMPT_PATH)

    assert "The NÁVRH is ALWAYS in Slovak" in template


def test_the_sent_text_must_not_contain_the_customers_question():
    """A regression: the model put the customer's question, translated back into
    their language, into NA ODOSLANIE instead of an answer."""
    template = load_template(PROMPT_PATH)

    assert "never the customer's question" in template


def test_the_internal_marker_must_not_reach_the_customer():
    """A regression: '⚠️ This isn't listed in the official docs' ended up in the
    customer's text. The marker is an internal signal."""
    template = load_template(PROMPT_PATH)

    assert "Nothing internal goes in here" in template


def test_the_answering_prompt_no_longer_translates():
    """Translation moved into a separate step - this prompt has one job
    fewer."""
    template = load_template(PROMPT_PATH)

    assert "You do not translate anything" in template


def test_the_hard_rule_appears_twice_in_the_template():
    """Repeating the key instruction reduces invention - and it has to be
    word-for-word identical, so the model does not read two wordings as two
    different rules."""
    template = load_template(PROMPT_PATH)

    assert template.count("Answer only from the official documentation") == 2


# --- render_documents ------------------------------------------------------


def test_every_document_carries_its_source():
    rendered = render_documents([make_doc("rules"), make_doc("sessions")])

    assert 'source="https://www.fyndit.app/docs/rules"' in rendered
    assert 'source="https://www.fyndit.app/docs/sessions"' in rendered


def test_the_document_content_is_in_the_text():
    rendered = render_documents([make_doc("rules", content="Autocop buys an item.")])

    assert "Autocop buys an item." in rendered


def test_the_documents_are_separated_by_tags():
    rendered = render_documents([make_doc("a"), make_doc("b")])

    assert rendered.count("<document ") == 2
    assert rendered.count("</document>") == 2


def test_an_empty_list_is_an_error():
    with pytest.raises(PromptError, match="no documents"):
        render_documents([])


# --- build_system_prompt ---------------------------------------------------


def test_the_placeholder_is_replaced_by_the_documents():
    template = f"Instructions.\n\n{DOCUMENTS_PLACEHOLDER}"

    result = build_system_prompt(template, [make_doc("rules")])

    assert DOCUMENTS_PLACEHOLDER not in result
    assert "Instructions." in result
    assert "https://www.fyndit.app/docs/rules" in result


def test_the_instructions_stay_ahead_of_the_documents():
    template = f"INSTRUCTIONS\n\n{DOCUMENTS_PLACEHOLDER}"

    result = build_system_prompt(template, [make_doc("rules")])

    assert result.index("INSTRUCTIONS") < result.index("<document ")


# --- rules added after an evaluation ---------------------------------------


def test_the_template_forbids_the_word_documentation_to_the_customer():
    """The most common mistake across every model (27 times in 7 runs): the
    customer received 'I couldn't find it in our documentation'. The original
    rule forbade a sentence, so the models wrote a different wording and
    considered themselves compliant. The ban has to be on the WORDS, not on a
    sentence."""
    template = load_template(PROMPT_PATH)

    assert '"documentation", "docs"' in template
    assert "must never appear" in template


def test_the_template_also_guards_against_over_refusing():
    """The opposite mistake (12 times): the model raised the marker on a question
    the docs do answer, only in different words. Research (Art of Refusal, 2024)
    says too many instructions about caution make a model defensive - a
    counterweight is needed too."""
    template = load_template(PROMPT_PATH)

    assert "only when the fact itself is absent" in template


def test_the_template_shows_a_refusal_too_not_only_answers():
    """All three original examples were 'answer this'. None showed what a
    well-handled gap looks like - and a pair of examples (answered plus refused)
    is the technique research points to."""
    template = load_template(PROMPT_PATH)

    assert "What a flagged gap looks like" in template
    assert "can i pay with paypal" in template.lower()


def test_the_gap_example_is_not_among_the_tone_examples():
    """The gap example demonstrates STRUCTURE and contains a fact from the docs.
    Standing under the heading 'TONE ONLY - never treat their content as
    knowledge', it would give the model two contradictory instructions at
    once."""
    template = load_template(PROMPT_PATH)

    gap_example = template.index("What a flagged gap looks like")
    tone_section = template.index("TONE ONLY")

    assert gap_example < tone_section, "the gap example is back among the tone examples"


def test_the_template_forbids_filling_a_gap_with_its_own_knowledge():
    """A regression: after the counterweight against over-refusing was added, a
    model started answering 'what is AND in a whitelist' with lookaheads
    (/(?=.*a)(?=.*b)/) that are not in the docs. The model knows regex - but
    whether the Fyndit parser handles it does not follow from the documentation.
    In a real ticket exactly this cost a customer an hour of debugging."""
    template = load_template(PROMPT_PATH)

    assert "even\n  when you are sure it is correct" in template
    assert "Lookaheads" in template


def test_the_template_has_one_binding_answer_about_refunds():
    """The original rule only forbade the word 'refund'. But the owner really did
    give a free month, and a helper elsewhere wrote 'I will try my best to ask
    for compensation'. Customers know about it and ask for it.

    CHANGED on the owner's instruction. A --repeat 5 measurement showed that on
    the same refund question the model picked from four different strategies:
    once it quoted the terms ('generally non-refundable'), once it sent the
    customer to an email address, once it escalated without the marker, twice it
    was right. Forbidding is no longer enough - there has to be ONE binding
    answer.

    The test holds its substance, not its wording: it covers every shape of the
    request, forbids quoting the terms and forbids sending the customer
    elsewhere."""
    template = " ".join(load_template(PROMPT_PATH).split())

    assert "Money back" in template
    assert "same answer every single time" in template

    # Compensation has many shapes - banning one word, the model goes around it
    # with another.
    assert "free days or a free month" in template

    # Quoting the terms IS a decision about entitlement, however careful it
    # sounds.
    assert "do not tell them a period is non-refundable" in template

    # Sending them to an email means the customer tells the whole story twice.
    assert "Do not send them to an email address" in template


def test_notes_must_not_contradict_the_documentation():
    """When a documentation page turned out to hold outdated information about
    colours, we fixed THAT PAGE - not a note that would contradict it. One fact
    should have one place, otherwise the model picks between two sources."""
    template = " ".join(load_template(PROMPT_PATH).split())

    assert "The documentation wins any disagreement" in template
    assert "never to contradict it" in template


def test_the_template_knows_the_channel_with_the_bot():
    """Without it the tool could not answer the most common ticket - onboarding,
    where the person has to be sent to where the bot is operated."""
    template = load_template(PROMPT_PATH)

    assert "🖥️-use-vinted-bot-here" in template
    assert "these five" in template


def test_the_template_prescribes_the_shape_of_a_channel_name():
    """Discord only links the exact '#name-with-emoji' form. Without it the name
    stays plain text and the customer hunts for the channel by hand."""
    template = " ".join(load_template(PROMPT_PATH).split())

    assert "leading `#` and its full name, emoji included" in template
    assert "#🔥-subscriptions" in template


def test_the_template_tells_onboarding_from_an_ambiguous_question():
    """An onboarding message is not a question but an ANSWER to a question from
    our own bot. Asking back there means asking the same thing twice - and a
    monitor cannot be set up from a list of brands anyway."""
    template = " ".join(load_template(PROMPT_PATH).split())

    assert "Someone starting out is not an ambiguous question" in template
    assert "Do not ask them what they need help with" in template


def test_the_template_does_not_show_channels_in_backticks():
    """The model copies the shape it sees, not the rule it read.

    The template used to write channels in backticks in nine places including
    the sample answer - and the model wrote them that way in 56% of answers. In
    Discord such a mention is not linked."""
    import re

    template = load_template(PROMPT_PATH)
    # Precisely: a backtick right before a channel name. A wider pattern would
    # catch whole paragraphs between two unrelated backticks.
    wrong = re.findall(r'`#?[📼🖥🔥🧐🛎][^`]*', template)

    assert wrong == [], f'channels in backticks: {wrong}'
