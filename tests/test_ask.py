import pytest
from fastapi.testclient import TestClient

from fyndit_helper.api import API_KEY_HEADER, app, get_llm_client
from fyndit_helper.llm import LLMError, RecordingClient, ScriptedClient

API_KEY = "test-key"

# The key is sent on every call - otherwise every test would measure the
# protection instead of what it is meant to measure. The protection itself is
# tested by test_auth.py.
client = TestClient(app, headers={API_KEY_HEADER: API_KEY})

TRANSLATION = "Preco mi nejde autocop?"
ANSWER = "NÁVRH (SK)\n...\n\nNA ODOSLANIE\n..."


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", API_KEY)


@pytest.fixture
def fake_llm():
    """A double for both steps: the translation first, then the answer."""
    scripted = ScriptedClient([TRANSLATION, ANSWER])
    app.dependency_overrides[get_llm_client] = lambda: scripted
    yield scripted
    app.dependency_overrides.clear()


def test_without_a_provider_key_it_returns_503(monkeypatch):
    """The keys are deleted explicitly, so the test does not depend on whether
    the developer has a .env."""
    app.dependency_overrides.clear()
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    response = client.post("/ask", json={"question": "Preco mi nejde autocop?"})

    assert response.status_code == 503
    assert "MISTRAL_API_KEY" in response.json()["detail"]


def test_it_returns_the_translation_and_the_answer(fake_llm):
    payload = client.post("/ask", json={"question": "why is my autocop broken?"}).json()

    assert payload["ticket_sk"] == TRANSLATION
    assert payload["answer"] == ANSWER


def test_both_steps_ran(fake_llm):
    client.post("/ask", json={"question": "Question"})

    assert len(fake_llm.calls) == 2


def test_the_translation_step_does_not_get_the_docs(fake_llm):
    """The docs run to tens of thousands of tokens - sending them into a
    translation is pointless."""
    client.post("/ask", json={"question": "Question"})

    translate_system = fake_llm.calls[0][0]
    assert "<document " not in translate_system


def test_the_answering_step_gets_the_docs(fake_llm):
    client.post("/ask", json={"question": "Question"})

    answer_system = fake_llm.calls[1][0]
    assert "<document " in answer_system
    assert "https://www.fyndit.app/docs" in answer_system


def test_the_answering_step_gets_the_original_and_the_translation(fake_llm):
    client.post("/ask", json={"question": "why is my autocop broken?"})

    answer_user = fake_llm.calls[1][1]
    assert "why is my autocop broken?" in answer_user
    assert TRANSLATION in answer_user


def test_docs_mode_when_there_is_no_draft(fake_llm):
    payload = client.post("/ask", json={"question": "Question"}).json()

    assert payload["mode"] == "docs"


def test_polish_mode_when_there_is_a_draft(fake_llm):
    payload = client.post(
        "/ask",
        json={"question": "Question", "draft": "wrong link, point them at the tutorial"},
    ).json()

    assert payload["mode"] == "polish"
    assert "wrong link" in fake_llm.calls[1][1]


def test_it_reports_how_many_documents_went_into_the_prompt(fake_llm):
    payload = client.post("/ask", json={"question": "Question"}).json()

    assert payload["documents_used"] >= 38


def test_an_empty_question_is_refused(fake_llm):
    response = client.post("/ask", json={"question": "   "})

    assert response.status_code == 400
    assert fake_llm.calls == []


def test_a_provider_failure_returns_502():
    recorder = RecordingClient(reply="x", fail_with=LLMError("provider down"))
    app.dependency_overrides[get_llm_client] = lambda: recorder

    response = client.post("/ask", json={"question": "Question"})

    assert response.status_code == 502
    assert "provider down" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_polish_mode_does_not_get_the_docs(fake_llm):
    """When notes are attached, the answering step MUST NOT get the docs.

    This is the bug that made the mode not work. The notes were added as a line
    in the user message while the system prompt stayed the same - 175,000
    characters whose entire point is "answer only from the documentation, else
    raise the marker". The model checked the notes against the docs, did not find
    them there (they are new, which is why they are being written) and rejected
    them.

    It failed silently: an answer came back, the mode was correctly "polish",
    everything looked fine - only the content was a refusal. Hence this test.
    """
    client.post("/ask", json={"question": "Question", "draft": "refunds are handled by vinted"})

    polish_system = fake_llm.calls[1][0]
    assert "<document " not in polish_system
    assert "refunds are handled by vinted" in fake_llm.calls[1][1]


def test_ask_returns_an_id_and_stores_the_ticket(fake_llm):
    payload = client.post("/ask", json={"question": "Question"}).json()

    assert payload["conversation_id"]
    listing = client.get("/history").json()
    assert [r["id"] for r in listing] == [payload["conversation_id"]]
    assert listing[0]["title"] == "Question"


def test_the_same_id_continues_the_ticket(fake_llm):
    """The whole thread travels with every call - without an id, one ticket
    would produce as many records as messages you had drafted."""
    first = client.post("/ask", json={"question": "Question"}).json()["conversation_id"]

    fake_llm.replies.extend([TRANSLATION, ANSWER])
    second = client.post(
        "/ask",
        json={
            "thread": [
                {"role": "customer", "text": "Question"},
                {"role": "helper", "text": "Answer"},
                {"role": "customer", "text": "And one more thing"},
            ],
            "conversation_id": first,
        },
    ).json()["conversation_id"]

    assert second == first
    assert len(client.get("/history").json()) == 1
    detail = client.get(f"/history/{first}").json()
    assert len(detail["answers"]) == 2
    assert len(detail["thread"]) == 3


def test_deleting_a_ticket(fake_llm):
    ticket = client.post("/ask", json={"question": "Question"}).json()["conversation_id"]

    assert client.delete(f"/history/{ticket}").status_code == 200
    assert client.get("/history").json() == []
    assert client.get(f"/history/{ticket}").status_code == 404


# --- the checks on the live path -------------------------------------------


def _answer(proposal: str, to_send: str) -> str:
    return f"**NÁVRH (SK)**\n{proposal}\n\n**NA ODOSLANIE**\n{to_send}"


def test_the_escalation_flag_when_the_marker_is_there(fake_llm):
    """The marker is still only text in the draft; /ask has to return it in a
    machine-readable form."""
    fake_llm.replies[:] = [
        TRANSLATION,
        _answer("⚠️ Toto v docs nie je.\nTreba overit u majitela.",
                "Hey! Let me check that and get back to you."),
    ]

    payload = client.post("/ask", json={"question": "can i pay with paypal?"}).json()

    assert payload["escalate"] is True


def test_no_marker_means_no_escalation(fake_llm):
    fake_llm.replies[:] = [TRANSLATION, _answer("Ahoj, funguje to takto.", "Hey, it works like this.")]

    assert client.post("/ask", json={"question": "how?"}).json()["escalate"] is False


def test_the_word_documentation_leaking_is_reported(fake_llm):
    """Exactly the mistake checks.py used to catch - but only in the
    evaluation."""
    fake_llm.replies[:] = [
        TRANSLATION,
        _answer("Ahoj.", "Sorry, that is not in our documentation."),
    ]

    payload = client.post("/ask", json={"question": "how?"}).json()

    assert any(f["check"] == "mentions_docs_to_customer" for f in payload["findings"])


def test_the_escalation_is_stored_in_the_history(fake_llm):
    """Without it there is no way to find in the list what is waiting on the
    owner."""
    fake_llm.replies[:] = [
        TRANSLATION,
        _answer("⚠️ Toto v docs nie je.", "Hey! Let me check that for you."),
    ]

    client.post("/ask", json={"question": "can i pay with paypal?"})

    assert client.get("/history").json()[0]["escalate"] is True


# --- the automatic rewrite on a hard error ---------------------------------

# The word "documentation" leaking to the customer is a hard error.
BAD = _answer("Ahoj, funguje to takto.", "Sorry, that is not in our documentation.")
GOOD = _answer("Ahoj, funguje to takto.", "Hey, it works like this.")


def test_a_hard_error_gets_the_answer_rewritten(fake_llm):
    """Most of these errors are random variation - the machine handles it."""
    fake_llm.replies[:] = [TRANSLATION, BAD, GOOD]

    payload = client.post("/ask", json={"question": "how?"}).json()

    assert payload["regenerated"] is True
    assert payload["findings"] == []
    assert "documentation" not in payload["answer"]


def test_the_rewrite_does_not_repeat_the_translation(fake_llm):
    """The translation is a separate call and has nothing to do with an error in
    the answer."""
    fake_llm.replies[:] = [TRANSLATION, BAD, GOOD]

    client.post("/ask", json={"question": "how?"})

    assert len(fake_llm.calls) == 3
    assert "<document " not in fake_llm.calls[0][0]   # translation
    assert "<document " in fake_llm.calls[1][0]       # answer
    assert "<document " in fake_llm.calls[2][0]       # rewrite


def test_clean_answers_are_not_rewritten(fake_llm):
    fake_llm.replies[:] = [TRANSLATION, GOOD]

    payload = client.post("/ask", json={"question": "how?"}).json()

    assert payload["regenerated"] is False
    assert len(fake_llm.calls) == 2


def test_a_warning_does_not_trigger_a_rewrite(fake_llm):
    """A warning is a notice, not a failure - the evaluation treats it the same
    way."""
    # With diacritics on purpose: Slovak without them comes out of langdetect as
    # Slovenian and the language check would fire instead of the length one.
    long_text = "Ahoj. " + "Veľmi dlhá slovenská odpoveď s množstvom detailov. " * 12
    fake_llm.replies[:] = [TRANSLATION, _answer(long_text, "Hey."), GOOD]

    payload = client.post("/ask", json={"question": "how?"}).json()

    assert payload["regenerated"] is False
    assert [f["severity"] for f in payload["findings"]] == ["warning"]


def test_a_worse_rewrite_is_discarded(fake_llm):
    """Returning the second answer blindly could trade one error for two."""
    worse = (
        "**NÁVRH (SK)**\nAhoj.\n\n"
        "**NA ODOSLANIE**\nSorry, that is not in our documentation.\n\n"
        "**ZDROJ**\n`https://www.fyndit.app/docs/invented-page` — nothing"
    )
    fake_llm.replies[:] = [TRANSLATION, BAD, worse]

    payload = client.post("/ask", json={"question": "how?"}).json()

    assert payload["regenerated"] is True
    assert payload["answer"] == BAD
    assert [f["check"] for f in payload["findings"]] == ["mentions_docs_to_customer"]


def test_a_failed_rewrite_does_not_cost_the_first_answer(fake_llm, monkeypatch):
    """The rewrite is a bonus, not a condition - the first answer still beats a
    502."""
    from fyndit_helper import api

    def explode(*a, **kw):
        raise LLMError("the provider went down")

    fake_llm.replies[:] = [TRANSLATION, BAD]
    monkeypatch.setattr(api, "draft_answer", explode)

    payload = client.post("/ask", json={"question": "how?"}).json()

    assert payload["answer"] == BAD
    assert [f["check"] for f in payload["findings"]] == ["mentions_docs_to_customer"]
