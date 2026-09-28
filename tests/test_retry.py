import httpx
import pytest

from fyndit_helper.llm import LLMError
from fyndit_helper import providers
from fyndit_helper.providers import GeminiClient, MistralClient

OK_MISTRAL = {"choices": [{"message": {"content": "answer"}}]}
OK_GEMINI = {"candidates": [{"content": {"parts": [{"text": "answer"}]}}]}


def throttling_transport(fail_times: int, ok_body: dict, retry_after: str | None = None):
    """Return 429 the first N times, then success."""
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] <= fail_times:
            headers = {"retry-after": retry_after} if retry_after else {}
            return httpx.Response(429, json={"message": "rate limited"}, headers=headers)
        return httpx.Response(200, json=ok_body)

    return httpx.Client(transport=httpx.MockTransport(handler)), state


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    """The tests must not actually sleep - the sleep is recorded instead."""
    sleeps = []
    monkeypatch.setattr("fyndit_helper.providers.time.sleep", sleeps.append)
    return sleeps


def test_mistral_waits_and_tries_again(no_waiting):
    http, state = throttling_transport(2, OK_MISTRAL)
    client = MistralClient(api_key="k", http_client=http)

    assert client.complete(system_prompt="S", user_message="U") == "answer"
    assert state["calls"] == 3
    assert len(no_waiting) == 2


def test_gemini_waits_and_tries_again(no_waiting):
    http, state = throttling_transport(1, OK_GEMINI)
    client = GeminiClient(api_key="k", http_client=http)

    assert client.complete(system_prompt="S", user_message="U") == "answer"
    assert state["calls"] == 2


def test_the_wait_grows(no_waiting):
    http, _ = throttling_transport(3, OK_MISTRAL)
    MistralClient(api_key="k", http_client=http).complete(system_prompt="S", user_message="U")

    assert no_waiting == sorted(no_waiting), "the wait should grow, not fluctuate"
    assert no_waiting[0] < no_waiting[-1]


def test_the_retry_after_header_is_respected(no_waiting):
    http, _ = throttling_transport(1, OK_MISTRAL, retry_after="7")
    MistralClient(api_key="k", http_client=http).complete(system_prompt="S", user_message="U")

    assert no_waiting == [7.0]


def test_a_readable_error_once_the_attempts_run_out(no_waiting):
    http, state = throttling_transport(99, OK_MISTRAL)
    client = MistralClient(api_key="k", http_client=http)

    with pytest.raises(LLMError, match="limit"):
        client.complete(system_prompt="S", user_message="U")

    # It will not try forever.
    assert state["calls"] < 10


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_temporary_errors_are_retried(no_waiting, status):
    """Gemini returns 503 with 'Please try again later' when overloaded - which
    is exactly what we do. Originally only 429 was retried and an evaluation
    died on that."""
    state = {"calls": 0}

    def handler(request):
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(status, json={"message": "temporary"})
        return httpx.Response(200, json=OK_MISTRAL)

    client = MistralClient(
        api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    assert client.complete(system_prompt="S", user_message="U") == "answer"
    assert state["calls"] == 2


def test_other_errors_are_not_retried(no_waiting):
    """A 401 does not improve by retrying - trying again is only a delay."""
    state = {"calls": 0}

    def handler(request):
        state["calls"] += 1
        return httpx.Response(401, json={"message": "Unauthorized"})

    client = MistralClient(api_key="wrong", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(LLMError, match="401"):
        client.complete(system_prompt="S", user_message="U")

    assert state["calls"] == 1


# --- connection errors, not responses --------------------------------------


def test_a_dropped_connection_is_retried():
    """An evaluation once died on case 27 of 37 with 'connection forcibly
    closed'. The retry only reacted to status codes, so the exception escaped
    and 26 finished cases were lost."""
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.ReadError("connection forcibly closed")
        return httpx.Response(200, json=OK_MISTRAL)

    client = MistralClient(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.complete(system_prompt="s", user_message="u") == "answer"
    assert attempts["n"] == 2


def test_a_permanently_dropped_connection_ends_in_a_readable_error():
    """When the connection fails every time it has to become an LLMError - not
    a raw httpx exception that brings the whole run down."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unreachable")

    client = MistralClient(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(LLMError, match="connection"):
        client.complete(system_prompt="s", user_message="u")


def test_an_absurd_retry_after_is_clamped(monkeypatch):
    """The value comes from the provider and we trusted it without question.

    'retry-after: 86400' would mean waiting a whole day, and a negative value
    would make time.sleep raise an exception that is not an LLMError and would
    escape - in a thread replay that would take everything finished with it."""
    slept = []
    monkeypatch.setattr(providers.time, 'sleep', slept.append)

    for value in ('86400', '-5', 'Wed, 21 Oct 2026 07:28:00 GMT'):
        response = httpx.Response(429, headers={'retry-after': value})
        providers._sleep_for_retry(response, attempt=0)

    assert all(0 <= s <= providers.MAX_RETRY_AFTER_SECONDS for s in slept), slept
