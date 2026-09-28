"""The page used every day.

These tests are deliberately shallow - they verify that the page is served and
that it is not locked. They do not measure behaviour in a browser.
"""

from fastapi.testclient import TestClient

from fyndit_helper.api import INDEX_PATH, LOGIN_PATH, app

client = TestClient(app)


def test_the_root_without_a_session_gives_the_sign_in_screen():
    """The page used to be open with the key typed into it. That was workable on
    a desktop and tiresome on a phone, so access moved to a password and a
    cookie."""
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Enter the password" in response.text


def test_the_page_files_exist():
    """Guards against a renamed directory - otherwise the error would only show
    up in the browser."""
    assert INDEX_PATH.is_file()
    assert LOGIN_PATH.is_file()


def test_the_page_calls_the_right_endpoint_and_sends_the_cookie():
    """When an endpoint is renamed or the cookie stops being sent, the page
    breaks silently - the server keeps running and the fault only shows at
    runtime.

    The X-API-Key header used to be guarded here. The page no longer sends it;
    the header path is guarded by test_gate.py."""
    html = INDEX_PATH.read_text(encoding="utf-8")

    assert '"/ask"' in html
    assert 'credentials: "same-origin"' in html
    assert "X-API-Key" not in html


def test_the_password_is_not_verified_in_the_browser():
    """If the sign-in screen had a script, the password would have to be in its
    source - and anyone can view that."""
    assert "<script" not in LOGIN_PATH.read_text(encoding="utf-8")


# --- the contract between the page and the server --------------------------

import re

import pytest

from fyndit_helper.api import API_KEY_HEADER, get_llm_client
from fyndit_helper.llm import ScriptedClient

API_KEY = "test-key"

#: Fields the server deliberately does not send in a successful response.
OUTSIDE_THE_CONTRACT = {
    # FastAPI returns it on an error (4xx/5xx), not on success.
    "detail",
}


def _fields_the_page_reads() -> set[str]:
    html = INDEX_PATH.read_text(encoding="utf-8")
    fields: set[str] = set()
    for variable in ("data", "last", "item"):
        fields |= set(re.findall(rf"\b{variable}\.([a-z_]+)", html))
    return fields - OUTSIDE_THE_CONTRACT


def test_the_page_reads_only_fields_the_server_actually_sends(monkeypatch):
    """The quietest possible failure in the whole product.

    The JS reads data.escalate; if the server stopped sending it, the page would
    NOT crash - a piece of the interface would silently stop working and nobody
    would notice until somebody missed it. So the fields are read straight out of
    the HTML: the test stays truthful even when the interface changes.
    """
    monkeypatch.setenv("API_KEY", API_KEY)
    answer = "**NÁVRH (SK)**\nAhoj.\n\n**NA ODOSLANIE**\nHey."
    app.dependency_overrides[get_llm_client] = lambda: ScriptedClient(
        ["Ticket translation", answer]
    )
    try:
        c = TestClient(app, headers={API_KEY_HEADER: API_KEY})

        ask = c.post("/ask", json={"question": "how?"}).json()
        listing = c.get("/history").json()
        detail = c.get(f"/history/{ask['conversation_id']}").json()
    finally:
        app.dependency_overrides.clear()

    sent = set(ask) | set(listing[0]) | set(detail)
    sent |= set(detail["answers"][0])

    missing = sorted(_fields_the_page_reads() - sent)

    assert not missing, (
        "the page reads fields the server does not send: " + ", ".join(missing)
    )


def test_the_whole_browser_path_through_the_cookie(monkeypatch):
    """How it is actually used - sign in with a password, then only the cookie.

    Every other /ask test goes through the API key, that is, a DIFFERENT branch
    in require_access. The path a person really uses was therefore never
    exercised: sign in, ticket, history, continuing a thread, deleting.
    """
    monkeypatch.setenv("APP_PASSWORD", "secret")
    monkeypatch.delenv("API_KEY", raising=False)

    answer = "**NÁVRH (SK)**\nAhoj.\n\n**NA ODOSLANIE**\nHey."
    scripted = ScriptedClient(["Translation", answer, "Translation 2", answer])
    app.dependency_overrides[get_llm_client] = lambda: scripted
    try:
        c = TestClient(app)

        # 1. without signing in, nothing is reachable
        assert c.post("/ask", json={"question": "how?"}).status_code == 401

        # 2. sign in with the password
        login = c.post("/login", data={"password": "secret"}, follow_redirects=False)
        assert login.status_code == 303

        # 3. the page is now served as the application
        assert "Fyndit Support Helper" in c.get("/").text

        # 4. a ticket without any key - the cookie carries it
        first = c.post("/ask", json={"question": "how?"})
        assert first.status_code == 200
        ticket = first.json()["conversation_id"]

        # 5. the history sees it
        assert [r["id"] for r in c.get("/history").json()] == [ticket]

        # 6. continuing the same thread does not create a new record
        c.post("/ask", json={
            "conversation_id": ticket,
            "thread": [
                {"role": "customer", "text": "how?"},
                {"role": "helper", "text": "Hey."},
                {"role": "customer", "text": "and what about this?"},
            ],
        })
        assert len(c.get("/history").json()) == 1
        assert len(c.get(f"/history/{ticket}").json()["answers"]) == 2

        # 7. deleting
        assert c.delete(f"/history/{ticket}").status_code == 200
        assert c.get("/history").json() == []

        # 8. logging out closes the door
        c.get("/logout")
        assert c.post("/ask", json={"question": "how?"}).status_code == 401
    finally:
        app.dependency_overrides.clear()
