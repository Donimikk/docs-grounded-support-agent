"""The password gate in front of the page.

Why it exists: answering has to work from a phone too, and typing an API key in
there every time was unacceptable. No accounts, one shared password from the
APP_PASSWORD variable.

Limits accepted deliberately: one password for everyone means there is no
telling who did what, and revoking access for one person means changing the
password for all. With two people that is enough.

Only OUR decisions are tested, plus the things that can break silently. That a
form posts a form and a cookie comes back on the next request is guaranteed by
the framework - that is not verified here.
"""

import pytest
from fastapi.testclient import TestClient

from fyndit_helper.api import API_KEY_HEADER, COOKIE_NAME, app, get_llm_client
from fyndit_helper.llm import ScriptedClient

client = TestClient(app, follow_redirects=False)

PASSWORD = "secret-test-password"
KEY = "secret-test-key"
QUESTION = {"question": "why is my autocop broken?"}


@pytest.fixture
def gate(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", PASSWORD)
    monkeypatch.setenv("API_KEY", KEY)
    app.dependency_overrides[get_llm_client] = lambda: ScriptedClient(
        ["translation", "NÁVRH (SK)\nx\n\nNA ODOSLANIE\ny"]
    )
    yield
    app.dependency_overrides.clear()


def signed_in_client() -> TestClient:
    response = client.post("/login", content=f"password={PASSWORD}")
    fresh = TestClient(app, follow_redirects=False)
    fresh.cookies.set(COOKIE_NAME, response.cookies[COOKIE_NAME])
    return fresh


def test_a_signed_in_browser_calls_ask_without_a_key(gate):
    """The whole reason the gate exists: nothing to type on a phone."""
    assert signed_in_client().post("/ask", json=QUESTION).status_code == 200


def test_the_key_in_the_header_still_works(gate):
    """Only the page got a gate. Scripts and the evaluation keep using the
    header."""
    response = client.post("/ask", json=QUESTION, headers={API_KEY_HEADER: KEY})

    assert response.status_code == 200


def test_changing_the_password_signs_everyone_out(gate, monkeypatch):
    """The cookie carries a fingerprint derived from the password, not a random
    token - and that is the only way to revoke someone's access. If a random
    token were ever stored in memory instead, changing the password would sign
    nobody out and nobody would notice."""
    old = signed_in_client()
    monkeypatch.setenv("APP_PASSWORD", "an-entirely-different-password")

    assert old.post("/ask", json=QUESTION).status_code == 401


def test_the_password_is_not_in_the_cookie(gate):
    """The tempting shortcut is to put the password straight into the cookie.
    It then ends up in reverse-proxy logs and in the browser history."""
    response = client.post("/login", content=f"password={PASSWORD}")

    assert PASSWORD not in response.headers["set-cookie"]


def test_with_no_password_set_it_is_locked(monkeypatch):
    """The same choice as with API_KEY: a forgotten variable should lock, not
    unlock. And an empty password must not match an empty variable - that is the
    classic hole where `"" == ""` lets anyone in."""
    monkeypatch.delenv("APP_PASSWORD", raising=False)

    assert "APP_PASSWORD is not set" in client.get("/").text
    assert client.post("/login", content="password=").headers["location"] == "/?error=1"


def test_the_cookie_gets_secure_over_https():
    """A regression: we believed the production cookie had Secure. It did not.

    api.py binds secure to request.url.scheme. Behind a proxy, uvicorn by
    default accepts X-Forwarded-Proto only from 127.0.0.1, so the scheme stayed
    'http'. Fixed in render.yaml through --forwarded-allow-ips='*'; this test
    only guards the branch in the code.
    """
    import os

    os.environ["APP_PASSWORD"] = "p"
    https = TestClient(app, base_url="https://fyndit.test")

    header = https.post(
        "/login", data={"password": "p"}, follow_redirects=False
    ).headers.get("set-cookie", "")

    assert "Secure" in header
    assert "HttpOnly" in header


def test_the_cookie_has_no_secure_over_plain_http():
    """Local development runs on http - with Secure the cookie would never be
    stored."""
    import os

    os.environ["APP_PASSWORD"] = "p"
    http = TestClient(app, base_url="http://127.0.0.1")

    header = http.post(
        "/login", data={"password": "p"}, follow_redirects=False
    ).headers.get("set-cookie", "")

    assert "Secure" not in header
