import pytest

from fyndit_helper.checks import (
    CheckError,
    Finding,
    run_checks,
    split_sections,
    inspect_answer,
)

SK = (
    "Ahoj! Na dashboard sa dostaneš cez odkaz v kanáli. Ak si kúpil Plus, mal by si "
    "mať prístup ku všetkým funkciám. Skontroluj, či si prihlásený pod tým istým účtom."
)
EN = (
    "Hey! You can reach the dashboard through the link in the channel. If you bought "
    "Plus you should have full access to everything. Check you are on the same account."
)


def answer(proposal: str = SK, to_send: str = EN) -> str:
    return f"**NÁVRH (SK)**\n{proposal}\n\n**NA ODOSLANIE**\n{to_send}"


def codes(findings: list[Finding]) -> set[str]:
    return {f.check for f in findings}


# --- splitting into parts --------------------------------------------------


def test_it_splits_both_parts():
    sections = split_sections(answer())

    assert SK in sections.proposal
    assert EN in sections.to_send
    assert "NA ODOSLANIE" not in sections.proposal


def test_a_missing_part_is_an_error():
    with pytest.raises(CheckError, match="NA ODOSLANIE"):
        split_sections("**NÁVRH (SK)**\nOnly a draft, nothing more.")


def test_it_copes_without_asterisks():
    sections = split_sections(f"NÁVRH (SK)\n{SK}\n\nNA ODOSLANIE\n{EN}")

    assert EN in sections.to_send


# --- clean answers ---------------------------------------------------------


def test_clean_answers_do_not_trip_anything():
    findings = run_checks(answer(), ticket_sk="Nevidim dashboard.", question="i can't see the dashboard")

    assert [f for f in findings if f.severity == "error"] == []


# --- the internal marker must not reach the customer -----------------------


def test_it_catches_the_marker_in_the_customers_text():
    findings = run_checks(
        answer(to_send=f"⚠️ This isn't in the docs. {EN}"),
        ticket_sk="t",
        question="q",
    )

    assert "marker_leaked" in codes(findings)


def test_the_marker_in_the_draft_is_fine():
    findings = run_checks(
        answer(proposal=f"⚠️ Toto v docs nie je.\n{SK}"),
        ticket_sk="t",
        question="q",
    )

    assert "marker_leaked" not in codes(findings)


def test_it_catches_a_mention_of_the_documentation_to_the_customer():
    findings = run_checks(
        answer(to_send=f"This is not covered in the documentation. {EN}"),
        ticket_sk="t",
        question="q",
    )

    assert "mentions_docs_to_customer" in codes(findings)


# --- channels --------------------------------------------------------------


def test_allowed_channels_pass():
    findings = run_checks(
        answer(to_send=f"{EN} Check `📼-quick-tutorials` for more."),
        ticket_sk="t",
        question="q",
    )

    assert "unknown_channel" not in codes(findings)


@pytest.mark.parametrize(
    "channel",
    [
        "🆘-support",  # U+1F198 - sits BELOW the pictogram block, a narrower range missed it
        "📢-updates",
        "❓-faq",
        "🎫-tickets",
    ],
)
def test_it_catches_an_invented_channel(channel):
    findings = run_checks(
        answer(to_send=f"{EN} Write in `{channel}` and we help you."),
        ticket_sk="t",
        question="q",
    )

    assert "unknown_channel" in codes(findings), f"channel not detected: {channel}"


# --- echoing the question --------------------------------------------------


def test_it_catches_the_question_echoed_back_to_the_customer():
    question = "Does Fyndit support vinted.sk? I'm from Slovakia."
    findings = run_checks(
        answer(to_send=f"{question} We will look into it for you shortly."),
        ticket_sk="Podporuje Fyndit vinted.sk?",
        question=question,
    )

    assert "echoes_question" in codes(findings)


# --- matching lengths ------------------------------------------------------


def test_it_catches_a_large_length_difference():
    findings = run_checks(
        answer(to_send="Ciao!"),
        ticket_sk="t",
        question="q",
    )

    assert "length_mismatch" in codes(findings)


# --- the language of the draft ---------------------------------------------


def test_it_catches_a_draft_in_a_foreign_language():
    findings = run_checks(
        answer(proposal=EN, to_send=EN),
        ticket_sk="t",
        question="q",
    )

    assert "proposal_not_in_slovak" in codes(findings)


def test_a_short_draft_is_not_language_checked():
    """langdetect guesses on short texts - better not to check than to accuse
    falsely. A short Slovak sentence was detected as Croatian."""
    findings = run_checks(
        answer(proposal="Áno, Fyndit to podporuje.", to_send="Yes, Fyndit supports it."),
        ticket_sk="t",
        question="q",
    )

    assert "proposal_not_in_slovak" not in codes(findings)


# --- video links -----------------------------------------------------------


def test_a_known_video_link_passes():
    link = "https://youtu.be/kE9EaSxkM9s"

    assert "invented_link" not in codes(
        run_checks(answer(to_send=f"{EN} Watch: {link}"), SK, "q")
    )


def test_it_catches_an_invented_video_link():
    """Models like to fill in a video id - the link looks right but leads
    nowhere."""
    findings = run_checks(
        answer(to_send=f"{EN} Watch: https://youtu.be/aaaaaaaaaaa"), SK, "q"
    )

    assert "invented_link" in codes(findings)


def test_it_catches_one_changed_character_in_a_known_link():
    """kE9EaSxkM9s -> kE9EaSxkM9z: such a link leads to somebody else's video or
    nowhere."""
    findings = run_checks(
        answer(to_send=f"{EN} Watch: https://youtu.be/kE9EaSxkM9z"), SK, "q"
    )

    assert "invented_link" in codes(findings)


def test_it_catches_the_long_form_link_too():
    findings = run_checks(
        answer(to_send=f"{EN} See https://www.youtube.com/watch?v=doesnotexist"), SK, "q"
    )

    assert "invented_link" in codes(findings)


def test_a_link_to_the_whole_channel_passes():
    """A channel link is not an invented link to a specific video."""
    findings = run_checks(
        answer(to_send=f"{EN} See https://www.youtube.com/@the-channel"), SK, "q"
    )

    assert "invented_link" not in codes(findings)


# --- the language of the customer's message --------------------------------

QUESTION_EN = "Hi, I've made two monitors, how do I view them separately"


def test_it_catches_slovak_sent_to_an_english_customer():
    """A real failure: the model received the ticket together with its Slovak
    translation and wrote both parts in Slovak. The helper would have sent a
    message meant for a Slovak to an English speaker."""
    findings = run_checks(answer(proposal=SK, to_send=SK), SK, QUESTION_EN)

    assert "wrong_language_for_customer" in codes(findings)


def test_an_english_answer_to_an_english_customer_passes():
    assert "wrong_language_for_customer" not in codes(
        run_checks(answer(), SK, QUESTION_EN)
    )


def test_a_slovak_customer_may_receive_slovak():
    """When the customer writes Slovak, both parts being the same is correct."""
    question_sk = (
        "Ahoj, vytvoril som si dva monitory a chcel by som ich mat oddelene, "
        "da sa to nejako nastavit v dashboarde?"
    )

    assert "wrong_language_for_customer" not in codes(
        run_checks(answer(proposal=SK, to_send=SK), SK, question_sk)
    )


def test_a_short_question_is_not_language_judged():
    """Three words cannot determine a language - better not to check than to
    accuse."""
    assert "wrong_language_for_customer" not in codes(
        run_checks(answer(proposal=SK, to_send=SK), SK, "help pls")
    )


# --- ZDROJ: where the model drew from --------------------------------------

SOURCE_OK = "https://www.fyndit.app/docs/sessions — Pickup Strategy and Radius"


def answer3(proposal=SK, to_send=EN, source=SOURCE_OK):
    return (f"**NÁVRH (SK)**\n{proposal}\n\n**NA ODOSLANIE**\n{to_send}"
            f"\n\n**ZDROJ**\n{source}")


def test_the_source_is_cut_off_from_the_customers_text():
    """The key to the whole thing: ZDROJ stands AFTER NA ODOSLANIE. If it
    counted into it, it would contain the word 'docs' from the URL and the leak
    check would fire on every single answer."""
    sections = split_sections(answer3())

    assert "fyndit.app" not in sections.to_send
    assert sections.to_send.strip() == EN


def test_the_source_can_be_read_on_its_own():
    assert "Pickup Strategy" in split_sections(answer3()).source


def test_an_answer_without_a_source_still_splits():
    """Older answers, and models that omit ZDROJ, must not bring the whole
    analysis down."""
    sections = split_sections(answer())

    assert sections.to_send.strip() == EN
    assert sections.source == ""


def test_the_source_does_not_trip_the_leak_check():
    assert "mentions_docs_to_customer" not in codes(run_checks(answer3(), SK, "q"))


def test_it_catches_an_invented_source():
    """Models like to fill in a URL from the topic. Such a citation is worse than
    none - the reader believes it and stops checking."""
    findings = run_checks(
        answer3(source="https://www.fyndit.app/docs/pickup-points — Pickup"), SK, "q"
    )

    assert "invented_source" in codes(findings)


def test_a_real_source_passes():
    assert "invented_source" not in codes(run_checks(answer3(), SK, "q"))


def test_a_dash_means_no_source_and_is_fine():
    """With a flagged gap there is nothing to cite."""
    assert "invented_source" not in codes(
        run_checks(answer3(proposal=f"⚠️ Toto v docs nie je.\n{SK}", source="—"), SK, "q")
    )


def test_a_source_in_backticks_passes():
    """A regression: the model wrote the URL as markdown code (`url`) and the
    pattern pulled the backtick into the URL. The check then called FIVE correct
    citations invented and I nearly declared that the model hallucinates."""
    findings = run_checks(answer3(source=f"`{SOURCE_OK}`"), SK, "q")

    assert "invented_source" not in codes(findings)


def test_a_source_with_a_full_stop_at_the_end_passes():
    findings = run_checks(
        answer3(source="https://www.fyndit.app/docs/sessions."), SK, "q"
    )

    assert "invented_source" not in codes(findings)


def test_a_source_in_parentheses_passes():
    findings = run_checks(
        answer3(source="(https://www.fyndit.app/docs/sessions)"), SK, "q"
    )

    assert "invented_source" not in codes(findings)


def test_a_real_note_as_a_source_passes():
    findings = run_checks(
        answer3(source="`poznamky:invalid-monitor-link` — the domain check"), SK, "q"
    )

    assert "invented_source" not in codes(findings)


def test_an_invented_note_is_caught():
    """Without this branch the check would look only at URLs and a citation of a
    non-existent note would go unnoticed."""
    findings = run_checks(answer3(source="poznamky:this-one-does-not-exist"), SK, "q")

    assert "invented_source" in codes(findings)


def test_the_channel_with_the_bot_is_allowed():
    """The documentation does not mention it, but it is the channel where the
    bot is operated - during onboarding the most useful place to point at."""
    assert "unknown_channel" not in codes(
        run_checks(answer(to_send=f"{EN} Have a look at 🖥️-use-vinted-bot-here"), SK, "q")
    )


def test_an_invented_channel_is_still_caught():
    """Widening the list must not mean anything passes."""
    assert "unknown_channel" in codes(
        run_checks(answer(to_send=f"{EN} Ask in 🆘-support"), SK, "q")
    )


# --- the shape of a channel name -------------------------------------------


def test_a_channel_with_a_hash_passes():
    assert "channel_without_hash" not in codes(
        run_checks(answer(to_send=f"{EN} See #🔥-subscriptions"), SK, "q")
    )


def test_a_channel_without_a_hash_is_caught():
    """Without the # Discord does not link it and the customer has to hunt for
    it."""
    findings = run_checks(answer(to_send=f"{EN} See 🔥-subscriptions"), SK, "q")

    assert "channel_without_hash" in codes(findings)


def test_a_channel_described_in_words_is_not_caught():
    """'the subscriptions channel' is not a channel name - the check must not
    fire on every word that happens to look similar."""
    assert "channel_without_hash" not in codes(
        run_checks(answer(to_send=f"{EN} Have a look in the subscriptions channel."), SK, "q")
    )


def test_the_shape_is_only_checked_in_the_customers_text():
    """The NÁVRH is read by a person outside Discord - linking does not matter
    there."""
    assert "channel_without_hash" not in codes(
        run_checks(answer(proposal=f"{SK} Pošli ho do 🔥-subscriptions.",
                          to_send=EN), SK, "q")
    )


def test_the_documentation_channel_is_not_a_leak():
    """A regression: the pattern looked for the word 'documentation' anywhere and
    found it INSIDE the channel name #🧐-documentation - which the prompt
    explicitly allows. The model leaked nothing, the check accused it for
    nothing."""
    assert "mentions_docs_to_customer" not in codes(
        run_checks(answer(to_send=f"{EN} More info in #🧐-documentation."), SK, "q")
    )


def test_a_real_leak_is_still_caught():
    """The fix must not mean anything with the word documentation passes."""
    assert "mentions_docs_to_customer" in codes(
        run_checks(answer(to_send=f"{EN} The documentation doesn't cover that."), SK, "q")
    )


def test_a_leak_is_caught_even_alongside_a_channel():
    """When the model links a channel AND writes about the documentation, the
    second one is still a mistake."""
    assert "mentions_docs_to_customer" in codes(
        run_checks(
            answer(to_send=f"{EN} It's not in our docs. See #🧐-documentation."),
            SK, "q",
        )
    )


def test_the_success_channel_is_allowed():
    """The only place with real results from other users, and exactly what is
    missing for the question 'is Pro worth it?'."""
    assert "unknown_channel" not in codes(
        run_checks(answer(to_send=f"{EN} Have a look at #🛎-success"), SK, "q")
    )


def test_a_channel_in_backticks_or_with_a_full_stop_does_not_pass():
    """Discord only links a mention that stands on its own.

    Measured over 123 live answers: 56% wrapped the channel in backticks and 40%
    glued punctuation to it. Both look right in the text, they just do not link -
    and had to be rewritten by hand."""
    def given(sentence):
        return (
            """**NAVRH (SK)**

Ahoj!

**NA ODOSLANIE**

""" + sentence
        )

    def channel_findings(sentence):
        return [f for f in run_checks(given(sentence), ticket_sk='x', question='y')
                if f.check == 'channel_not_linkable']

    assert not channel_findings('Pozri #📼-quick-tutorials a daj vediet.')

    assert channel_findings('Pozri `#📼-quick-tutorials` a daj vediet.')

    assert channel_findings('Vsetko najdes v #🔥-subscriptions.')


def test_a_dash_after_a_channel_is_fine():
    """Only punctuation stuck directly onto the name is forbidden. A dash with a
    space does not break the mention and is an ordinary way to carry on after
    it."""
    given = (
        """**NAVRH (SK)**

Ahoj!

**NA ODOSLANIE**

Pozri #🔥-subscriptions — the code gives you a discount."""
    )

    assert not [f for f in run_checks(given, ticket_sk='x', question='y') if f.check == 'channel_not_linkable']


def test_a_channel_at_the_end_of_the_message_is_fine():
    """An empty string is a substring of every string, so `after in '.,'`
    returned True whenever the channel stood at the end of the text. The check
    marked 7 correct answers as wrong."""
    given = (
        """**NAVRH (SK)**

Ahoj!

**NA ODOSLANIE**

Dashboard najdes v #🖥️-use-vinted-bot-here"""
    )

    findings = run_checks(given, ticket_sk='x', question='y')

    assert not [f for f in findings if f.check == 'channel_not_linkable']


def test_a_missing_part_is_reported():
    """The one check that had no positive test for a long time - and it catches
    the worst mistake: the draft looks finished, it has a Slovak part and
    sources, but the Copy button would send the customer nothing.

    It happened twice in three days."""
    without_send = """
**NÁVRH (SK)**

Ahoj, toto je odpoved.

**ZDROJ**

—"""

    found = codes(run_checks(without_send, 'ticket', 'question'))

    assert 'missing_section' in found


def test_when_a_part_is_missing_the_other_checks_do_not_run():
    """A deliberate consequence: when the answer cannot be split there is
    nothing to check. It is written down here so nobody wonders why a broken
    answer has no message about language or channels."""
    without_send = """
**NÁVRH (SK)**

Pozri `#🖥️-use-vinted-bot-here`.

**ZDROJ**

—"""

    found = codes(run_checks(without_send, 'ticket', 'question'))

    assert set(found) == {'missing_section'}


def test_a_doubled_na_odoslanie_part_is_reported():
    """The second heading and the second block used to stay in the customer's
    text, so the Copy button handed them the heading and a second version of the
    answer.

    Which of the two is the real one we cannot tell - hence a report, not a
    trim."""
    doubled = """
**NÁVRH (SK)**

Ahoj

**NA ODOSLANIE**

Hey there

**NA ODOSLANIE**

Hey again"""

    with pytest.raises(CheckError, match='twice'):
        split_sections(doubled)


def test_a_source_before_na_odoslanie_is_reported():
    """ZDROJ in the middle fell into the NÁVRH and 'source' stayed empty, so the
    invented-source check had nothing to verify - it went quiet exactly when the
    output was broken."""
    swapped = """
**NÁVRH (SK)**

Ahoj

**ZDROJ**

https://www.fyndit.app/docs/monitors

**NA ODOSLANIE**

Hey there"""

    with pytest.raises(CheckError, match='ZDROJ'):
        split_sections(swapped)


# --- the live path ---------------------------------------------------------


def test_inspect_answer_finds_the_escalation_in_the_draft():
    inspection = inspect_answer(
        "**NÁVRH (SK)**\n⚠️ Toto v docs nie je.\n\n**NA ODOSLANIE**\nI will check.",
        ticket_sk="x", question="how?",
    )

    assert inspection.escalate is True


def test_inspect_answer_does_not_flag_an_escalation_without_the_marker():
    inspection = inspect_answer(
        "**NÁVRH (SK)**\nFunguje to takto.\n\n**NA ODOSLANIE**\nIt works like this.",
        ticket_sk="x", question="how?",
    )

    assert inspection.escalate is False


def test_inspect_answer_survives_the_checks_crashing(monkeypatch):
    """The check is an aid, not a condition.

    It runs on the path an answer takes to the helper. If a crash escaped, a bug
    in a check would be worse than no check at all - it would cost the answer the
    model has already produced and been paid for.
    """
    from fyndit_helper import checks

    monkeypatch.setattr(
        checks, "run_checks", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    inspection = inspect_answer(
        "**NÁVRH (SK)**\n⚠️ Toto v docs nie je.\n\n**NA ODOSLANIE**\nI will check.",
        ticket_sk="x", question="how?",
    )

    assert inspection.findings == ()
    assert inspection.escalate is True


def test_inspect_answer_copes_with_an_unsplittable_answer():
    inspection = inspect_answer("just text with no sections", ticket_sk="x", question="how?")

    assert inspection.escalate is False
    assert [f.check for f in inspection.findings] == ["missing_section"]


def test_a_length_mismatch_is_not_reported_on_a_gap():
    """On a flagged gap the prompt explicitly requires the two halves to DIFFER.

    Without this exception the warning lit up on every escalated ticket and
    people would learn to overlook real findings along with it.
    """
    proposal = "⚠️ Toto v docs nie je.\n" + "Dlhy interny popis pre cloveka. " * 12
    findings = run_checks(
        f"**NÁVRH (SK)**\n{proposal}\n\n**NA ODOSLANIE**\nHey! I will check that.",
        ticket_sk="x", question="can i pay with paypal?",
    )

    assert "length_mismatch" not in [f.check for f in findings]


def test_a_length_mismatch_without_a_gap_is_still_reported():
    proposal = "Ahoj. " + "Velmi dlha slovenska odpoved s mnozstvom detailov. " * 12
    findings = run_checks(
        f"**NÁVRH (SK)**\n{proposal}\n\n**NA ODOSLANIE**\nHey.",
        ticket_sk="x", question="how?",
    )

    assert "length_mismatch" in [f.check for f in findings]


# --- disabled commands -----------------------------------------------------


def _for_the_customer(text: str) -> list[str]:
    findings = run_checks(
        f"**NÁVRH (SK)**\nAhoj.\n\n**NA ODOSLANIE**\n{text}",
        ticket_sk="x", question="how do i do it?",
    )
    return [f.check for f in findings]


def test_a_command_in_the_customers_text_is_an_error():
    """The commands work, but the owner turned them off - there is one path and
    one tutorial. A customer who types such a command gets nothing."""
    assert "command_to_customer" in _for_the_customer("Open /monitors and add it there.")


def test_it_finds_several_commands_at_once():
    assert "command_to_customer" in _for_the_customer("Run /sessions then /my_info.")


def test_a_documentation_url_is_not_a_command():
    """The most important false alarm: /docs/sessions ends the same way as a
    command.

    If the check failed on this, it would flag correct answers and the answer
    would be rewritten over and over for nothing.
    """
    assert "command_to_customer" not in _for_the_customer(
        "See https://www.fyndit.app/docs/sessions for the details."
    )


def test_a_regex_example_is_not_a_command():
    """Customers are advised to use regex - the pattern is in slashes and a
    slash is not a command."""
    assert "command_to_customer" not in _for_the_customer(
        "Use a pattern like /ralph lauren|polo/ in the whitelist."
    )


def test_a_word_without_a_slash_is_not_a_command():
    assert "command_to_customer" not in _for_the_customer(
        "Check your sessions and preferences in the Dashboard."
    )


def test_a_longer_word_after_a_command_is_not_flagged():
    assert "command_to_customer" not in _for_the_customer("Go to /sessionsomething.")


def test_a_command_is_a_hard_error_not_a_warning():
    """The severity decides whether the answer is rewritten automatically. For a
    command it SHOULD be - it is an instruction into a dead end."""
    from fyndit_helper.checks import SEVERITY_ERROR

    findings = run_checks(
        "**NÁVRH (SK)**\nAhoj.\n\n**NA ODOSLANIE**\nOpen /monitors there.",
        ticket_sk="x", question="how?",
    )
    command = [f for f in findings if f.check == "command_to_customer"][0]

    assert command.severity == SEVERITY_ERROR
