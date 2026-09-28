"""Protecting /ask with a key in the header.

A public URL is public to bots as well. Without a key anyone could spend the
provider quota or push their own text into the prompt.
"""

import pytest
from fastapi.testclient import TestClient

from fyndit_helper.api import API_KEY_HEADER, app, get_llm_client
from fyndit_helper.llm import ScriptedClient

client = TestClient(app)

KEY = "secret-test-key"
QUESTION = {"question": "why is my autocop broken?"}


@pytest.fixture
def fake_llm(monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    scripted = ScriptedClient(["translation", "NÁVRH (SK)\nx\n\nNA ODOSLANIE\ny"])
    app.dependency_overrides[get_llm_client] = lambda: scripted
    yield scripted
    app.dependency_overrides.clear()


def test_the_right_key_passes(fake_llm):
    response = client.post("/ask", json=QUESTION, headers={API_KEY_HEADER: KEY})

    assert response.status_code == 200


def test_without_the_header_it_is_refused(fake_llm):
    response = client.post("/ask", json=QUESTION)

    assert response.status_code == 401


def test_a_wrong_key_is_refused(fake_llm):
    response = client.post("/ask", json=QUESTION, headers={API_KEY_HEADER: "guess"})

    assert response.status_code == 401


def test_the_model_is_not_called_at_all_on_refusal(fake_llm):
    """Otherwise the quota would be spent just by trying keys."""
    client.post("/ask", json=QUESTION, headers={API_KEY_HEADER: "guess"})

    assert fake_llm.calls == []


def test_with_no_key_set_the_endpoint_is_locked(monkeypatch):
    """A forgotten environment variable must not mean an open endpoint. Better a
    broken endpoint than a publicly available one."""
    monkeypatch.delenv("API_KEY", raising=False)
    app.dependency_overrides[get_llm_client] = lambda: ScriptedClient(["a", "b"])

    response = client.post("/ask", json=QUESTION, headers={API_KEY_HEADER: "anything"})
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "API_KEY" in response.json()["detail"]


def test_health_works_without_a_key(monkeypatch):
    """The host calls the health check without a header - otherwise it would
    declare the app dead."""
    monkeypatch.setenv("API_KEY", KEY)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_swagger_works_without_a_key(monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)

    assert client.get("/docs").status_code == 200


def test_a_signed_out_browser_gets_401_even_without_an_api_key(monkeypatch):
    """A regression found in an audit.

    A browser with no cookie and no key used to get 503 'API_KEY is not set'.
    But /ask is available to it without API_KEY - the password is enough.
    Removing that variable would therefore break the page with an error about a
    variable it does not need, and the interface would show a server error
    instead of 'sign in again'.
    """
    monkeypatch.setenv("APP_PASSWORD", "secret")
    monkeypatch.delenv("API_KEY", raising=False)

    r = TestClient(app).post("/ask", json={"question": "how?"})

    assert r.status_code == 401


def test_a_call_with_a_key_still_reports_the_missing_api_key(monkeypatch):
    """A script that DID send a key should learn that the server has none."""
    monkeypatch.delenv("API_KEY", raising=False)

    r = TestClient(app, headers={API_KEY_HEADER: "anything"}).post(
        "/ask", json={"question": "how?"}
    )

    assert r.status_code == 503
    assert "API_KEY" in r.json()["detail"]
