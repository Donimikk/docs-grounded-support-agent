"""Converting a Discord thread into our messages.

The samples are rewritten from real tickets into the shape messages arrive in
from the Discord API - not the shape they have in the app. A parser for copied
text would be thrown away the day the bot connects.
"""

from fyndit_helper.discord import IMAGE_MARKER, to_thread

HELPER = "111"
OWNER = "222"
SECOND_HELPER = "333"

STAFF = {HELPER, SECOND_HELPER}
OWNERS = {OWNER}


def msg(author_id, text="", *, bot=False, name="", attachments=0):
    return {
        "author": {"id": author_id, "username": name or author_id, "bot": bot},
        "content": text,
        "attachments": [{"filename": f"img{i}.png"} for i in range(attachments)],
    }


def convert(*messages):
    return to_thread(list(messages), staff_ids=STAFF, owner_ids=OWNERS)


# --- who is who ------------------------------------------------------------


def test_an_unknown_author_is_a_customer():
    thread = convert(msg("999", "why is my autocop broken"))

    assert [(m.role, m.text) for m in thread] == [("customer", "why is my autocop broken")]


def test_a_helper_is_recognised_by_id():
    thread = convert(msg("999", "question"), msg(HELPER, "answer"))

    assert [m.role for m in thread] == ["customer", "helper"]


def test_the_owner_is_not_a_helper():
    """The prompt says a helper has no access to the system and such things go
    to the owner. Labelling the owner as a helper would show the model a helper
    promising things a helper cannot do - and it would start imitating that."""
    thread = convert(msg("999", "question"), msg(OWNER, "I'll fix it on my side"))

    assert [m.role for m in thread] == ["customer", "owner"]


def test_the_name_is_kept():
    thread = convert(msg(OWNER, "hello", name="Owner"), msg("999", "question"))

    assert thread[0].name == "Owner"


# --- bot messages ----------------------------------------------------------


def test_a_bot_message_never_becomes_a_customer_message():
    """An onboarding wall runs to forty lines. If it passed as a customer
    message, the model would answer the bot."""
    thread = convert(
        msg("bot1", "Welcome to Fyndit! What do you want to do with a Vinted bot?", bot=True),
        msg("999", "i want to resell"),
    )

    assert [m.role for m in thread] == ["helper", "customer"]
    assert thread[-1].text == "i want to resell"


def test_the_ticket_description_is_pulled_out_of_the_bot_message():
    """The bot wraps the customer's first message in a form. Dropping the whole
    thing would lose what the customer came with."""
    thread = convert(
        msg("bot1", bot=True, text=(
            "@Developer @Helper A new ticket has been created.\n"
            "New Technical Support Ticket\n"
            "Issue Description:\n"
            "Where do I see my monitors\n"
            "Opened by @Gameboro\n"
            "Category\nTechnical Support"
        )),
        msg(HELPER, "check the dashboard"),
        msg("999", "i dont get it"),
    )

    assert thread[0].role == "customer"
    assert thread[0].text == "Where do I see my monitors"
    assert "Opened by" not in thread[0].text
    assert "Category" not in thread[0].text


# --- merging ---------------------------------------------------------------


def test_consecutive_messages_from_the_same_person_are_merged():
    """People type in pieces. Three messages in a row would read as three
    separate turns, although they are one thought."""
    thread = convert(
        msg("999", "question"),
        msg(HELPER, "Can you show exactly what you mean"),
        msg(HELPER, "Uuuh all bots now lay in your dms"),
        msg(HELPER, "Because of discord"),
        msg("999", "ok"),
    )

    assert len(thread) == 3
    assert thread[1].text == (
        "Can you show exactly what you mean\n"
        "Uuuh all bots now lay in your dms\n"
        "Because of discord"
    )


def test_only_messages_from_the_same_author_are_merged():
    thread = convert(msg(HELPER, "a"), msg(SECOND_HELPER, "b"), msg("999", "c"))

    assert len(thread) == 3


def test_a_bot_message_in_between_does_not_break_the_merge():
    """The bot often drops 'user needs help' between two helper messages."""
    thread = convert(
        msg(HELPER, "first"),
        msg("bot1", "@Helper user sent a message", bot=True),
        msg(HELPER, "second"),
        msg("999", "question"),
    )

    assert len(thread) == 2
    assert thread[0].text == "first\nsecond"


# --- attachments -----------------------------------------------------------


def test_an_image_is_marked_not_discarded():
    """Models can read images, but we do not yet know how well. The marker at
    least says something is there - the model can ask instead of guessing."""
    thread = convert(msg("999", "look at this", attachments=1))

    assert IMAGE_MARKER in thread[0].text
    assert "look at this" in thread[0].text


def test_a_message_with_only_an_image_is_not_lost():
    thread = convert(msg("999", "", attachments=1))

    assert len(thread) == 1
    assert thread[0].text.strip() == IMAGE_MARKER


# --- edge cases ------------------------------------------------------------


def test_empty_messages_are_skipped():
    thread = convert(msg("999", "   "), msg("999", "a real question"))

    assert [m.text for m in thread] == ["a real question"]


def test_a_thread_may_end_with_someone_other_than_the_customer():
    """The adapter does not decide whether an answer is due - that is the
    pipeline's job. When the owner spoke last, we are waiting on the customer and
    the bot has nothing to propose."""
    thread = convert(msg("999", "question"), msg(OWNER, "Did you create a monitor already?"))

    assert thread[-1].role == "owner"


def test_a_thread_of_bot_messages_only_is_empty():
    thread = convert(msg("bot1", "onboarding", bot=True))

    assert thread == []


# --- a bot question the customer is answering ------------------------------

ONBOARDING = (
    "Welcome to Fyndit\nThe Vinted bot that helps you find deals faster.\n"
    "Create monitors for brands, sizes, prices, countries, keywords, or niches\n"
    "Step 1 of 5\n"
    "Quick question, @Jose: what are you hoping to do with a Vinted bot?\n\n"
    "You can reply here with anything useful, for example:\n"
    "Are you buying for yourself or reselling?\n"
    "What brands, sizes, countries, or niches do you care about?"
)


def test_the_bot_question_stays_when_the_customer_answers_it():
    """Without it the model sees the bare fragment 'Reselling, Ralph Lauren and
    Dio' and asks 'what do you need help with?' - repeating the question the
    customer had just answered."""
    thread = convert(
        msg("bot1", ONBOARDING, bot=True),
        msg("999", "Reselling, Ralph Lauren and Dio"),
    )

    assert len(thread) == 2
    assert thread[0].role == "helper"
    assert "what are you hoping to do" in thread[0].text
    assert thread[1].text == "Reselling, Ralph Lauren and Dio"


def test_only_that_line_is_taken_from_the_question_not_the_whole_wall():
    """The onboarding message runs to forty lines. What belongs in the prompt is
    the question, not the whole welcome text."""
    thread = convert(msg("bot1", ONBOARDING, bot=True), msg("999", "reselling"))

    assert "Welcome to Fyndit" not in thread[0].text
    assert "Step 1 of 5" not in thread[0].text


def test_it_works_in_another_language_too():
    """The template is the same in every language - the main question comes
    first."""
    thread = convert(
        msg("bot1", bot=True, text=(
            "Bienvenue sur Fyndit\nLe bot Vinted...\nÉtape 1 sur 5\n"
            "Petite question, @TOMK : qu'est-ce que tu veux faire avec un bot Vinted ?\n\n"
            "Tu peux répondre ici, par exemple :\nTu achètes pour toi ou pour revendre ?"
        )),
        msg("999", "J'achète pour revendre"),
    )

    assert len(thread) == 2
    assert "qu'est-ce que tu veux faire" in thread[0].text


def test_a_bot_message_without_a_question_is_still_discarded():
    """'A new ticket has been created' is not a question and does not belong in
    the conversation."""
    thread = convert(
        msg("bot1", "@Helper A new ticket has been created.", bot=True),
        msg("999", "question"),
    )

    assert len(thread) == 1


def test_an_unanswered_bot_question_is_not_added():
    """When nobody answered the question there is nothing to put in the
    thread."""
    thread = convert(
        msg("999", "the customer's first message"),
        msg("bot1", ONBOARDING, bot=True),
    )

    assert len(thread) == 1
    assert thread[0].role == "customer"
