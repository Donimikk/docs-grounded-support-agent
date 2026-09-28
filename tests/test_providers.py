import httpx
import pytest

from fyndit_helper.llm import LLMError
from fyndit_helper.providers import GeminiClient, MistralClient, build_client_from_env


def mock_client(handler) -> httpx.Client:
    """An httpx client that calls our handler instead of the network."""
    return httpx.Client(transport=httpx.MockTransport(handler))


# --- Mistral ---------------------------------------------------------------


def test_mistral_sends_both_the_system_and_the_user_message():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers.get("authorization")
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": "answer"}}]})

    client = MistralClient(api_key="k", model="mistral-small-latest", http_client=mock_client(handler))

    assert client.complete(system_prompt="SYS", user_message="USER") == "answer"
    assert seen["auth"] == "Bearer k"
    assert seen["url"] == "https://api.mistral.ai/v1/chat/completions"
    assert seen["body"]["model"] == "mistral-small-latest"
    assert seen["body"]["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USER"},
    ]


def test_a_mistral_error_has_a_readable_message():
    def handler(request):
        return httpx.Response(401, json={"message": "Unauthorized"})

    client = MistralClient(api_key="wrong", http_client=mock_client(handler))

    with pytest.raises(LLMError, match="401"):
        client.complete(system_prompt="S", user_message="U")


def test_an_empty_mistral_answer_is_an_error():
    def handler(request):
        return httpx.Response(200, json={"choices": []})

    client = MistralClient(api_key="k", http_client=mock_client(handler))

    with pytest.raises(LLMError, match="empty"):
        client.complete(system_prompt="S", user_message="U")


def test_mistral_lists_the_models():
    def handler(request):
        assert str(request.url) == "https://api.mistral.ai/v1/models"
        return httpx.Response(200, json={"data": [{"id": "mistral-small-latest"}, {"id": "mistral-medium-latest"}]})

    client = MistralClient(api_key="k", http_client=mock_client(handler))

    assert client.list_models() == ["mistral-small-latest", "mistral-medium-latest"]


# --- Gemini ----------------------------------------------------------------


def test_gemini_sends_the_system_instruction_separately():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        seen["body"] = json.loads(request.content)
        seen["key_header"] = request.headers.get("x-goog-api-key")
        seen["url"] = str(request.url)
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": "answer"}]}}]}
        )

    client = GeminiClient(api_key="k", model="gemini-2.5-flash", http_client=mock_client(handler))

    assert client.complete(system_prompt="SYS", user_message="USER") == "answer"
    assert seen["key_header"] == "k"
    # The key must not be in the URL - it ends up in server and proxy logs.
    assert "k" not in httpx.URL(seen["url"]).params.values()
    assert seen["url"].endswith("models/gemini-2.5-flash:generateContent")
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "SYS"
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "USER"


def test_a_gemini_error_has_a_readable_message():
    def handler(request):
        return httpx.Response(400, json={"error": {"message": "API key not valid"}})

    client = GeminiClient(api_key="wrong", http_client=mock_client(handler))

    with pytest.raises(LLMError, match="400"):
        client.complete(system_prompt="S", user_message="U")


def test_a_blocked_gemini_answer_is_an_error():
    """Gemini returns 200 even when it blocked the answer - candidates is
    empty."""

    def handler(request):
        return httpx.Response(200, json={"candidates": []})

    client = GeminiClient(api_key="k", http_client=mock_client(handler))

    with pytest.raises(LLMError, match="empty"):
        client.complete(system_prompt="S", user_message="U")


def test_gemini_lists_the_models():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
                ]
            },
        )

    client = GeminiClient(api_key="k", http_client=mock_client(handler))

    # Embedding models are of no interest - they are filtered out.
    assert client.list_models() == ["gemini-2.5-flash"]


# --- selection from .env ---------------------------------------------------


def test_mistral_is_selected_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.setenv("MISTRAL_API_KEY", "k")

    assert isinstance(build_client_from_env(), MistralClient)


def test_gemini_is_selected_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    assert isinstance(build_client_from_env(), GeminiClient)


def test_a_missing_key_is_a_readable_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    with pytest.raises(LLMError, match="MISTRAL_API_KEY"):
        build_client_from_env()


def test_an_unknown_provider_is_an_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nonexistent")

    with pytest.raises(LLMError, match="nonexistent"):
        build_client_from_env()


# --- the interactive versus the batch policy -------------------------------


def test_the_policy_can_be_passed_into_the_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "smartapi")
    monkeypatch.setenv("SMARTAPI_API_KEY", "x")

    client = build_client_from_env(timeout_seconds=12.0, max_attempts=3)

    assert client.max_attempts == 3


def test_without_being_given_one_the_batch_policy_stays(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "smartapi")
    monkeypatch.setenv("SMARTAPI_API_KEY", "x")

    from fyndit_helper.providers import MAX_RETRIES_ON_RATE_LIMIT

    assert build_client_from_env().max_attempts == MAX_RETRIES_ON_RATE_LIMIT


def test_the_page_runs_on_the_interactive_policy(monkeypatch):
    """A regression: the INTERACTIVE_* constants existed, the clients could
    accept them, but build_client_from_env dropped them and api.py never passed
    them. The fix was dead code and the page waited through the whole batch
    ladder - up to 28 minutes per ticket before saying 'the server is
    unavailable'.

    Nothing caught it, because nothing measured WHAT the client actually runs
    with.
    """
    from fyndit_helper.api import get_llm_client
    from fyndit_helper.providers import INTERACTIVE_MAX_ATTEMPTS

    monkeypatch.setenv("LLM_PROVIDER", "smartapi")
    monkeypatch.setenv("SMARTAPI_API_KEY", "x")

    assert get_llm_client().max_attempts == INTERACTIVE_MAX_ATTEMPTS


# --- the time budget for retries -------------------------------------------


def _counting_client(handler):
    attempts = {"n": 0}

    def counting(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return handler(request)

    return mock_client(counting), attempts


def test_a_spent_budget_stops_the_next_attempt(monkeypatch):
    """A hanging connection costs the whole timeout; a second wait does not
    help.

    Measured: the page returned an error only after 114 s - two attempts of
    60 s. The budget never starts that second attempt.
    """
    from fyndit_helper.providers import SmartApiClient

    def hang(request):
        raise httpx.ReadTimeout("hanging")

    http, attempts = _counting_client(hang)
    # The budget is spent right after the first attempt.
    client = SmartApiClient(api_key="x", http_client=http, max_attempts=5, max_seconds=0.0)

    with pytest.raises(LLMError):
        client.complete(system_prompt="s", user_message="u")

    assert attempts["n"] == 1


def test_without_a_budget_it_keeps_retrying(monkeypatch):
    """A batch run has no budget - there, waiting beats losing the result."""
    from fyndit_helper import providers
    from fyndit_helper.providers import SmartApiClient

    monkeypatch.setattr(providers, "BACKOFF_BASE_SECONDS", 0.0)

    def hang(request):
        raise httpx.ReadTimeout("hanging")

    http, attempts = _counting_client(hang)
    client = SmartApiClient(api_key="x", http_client=http, max_attempts=3)

    with pytest.raises(LLMError):
        client.complete(system_prompt="s", user_message="u")

    assert attempts["n"] == 3


def test_a_cheap_failure_does_not_spend_the_budget(monkeypatch):
    """A 503 arrives in a fraction of a second - retrying it is cheap and
    useful."""
    from fyndit_helper import providers
    from fyndit_helper.providers import SmartApiClient

    monkeypatch.setattr(providers, "_sleep_for_retry", lambda *a, **kw: None)

    def overloaded(request):
        return httpx.Response(503, json={"error": "overloaded"})

    http, attempts = _counting_client(overloaded)
    # A short per-attempt timeout, so all three fit into the budget.
    client = SmartApiClient(
        api_key="x", http_client=http, max_attempts=3,
        max_seconds=30.0, timeout_seconds=1.0,
    )

    with pytest.raises(LLMError):
        client.complete(system_prompt="s", user_message="u")

    assert attempts["n"] == 3


def test_the_message_says_how_many_attempts_there_really_were():
    """With the budget spent, 'after 2 attempts' would be a lie."""
    from fyndit_helper.providers import SmartApiClient

    def hang(request):
        raise httpx.ReadTimeout("hanging")

    http, _ = _counting_client(hang)
    client = SmartApiClient(api_key="x", http_client=http, max_attempts=5, max_seconds=0.0)

    with pytest.raises(LLMError) as exc:
        client.complete(system_prompt="s", user_message="u")

    assert "after 1 attempts" in str(exc.value)


def test_the_budget_accounts_for_the_LENGTH_of_the_next_attempt():
    """A regression: the budget asked 'have I spent it', not 'does the next
    attempt fit'.

    With a 60 s timeout and a 70 s budget, 60 s were gone after the first
    attempt - the budget was still 'valid', so a second one started and the page
    returned an error only after 124 s. The first version of the fix did NOT
    pass this test.
    """
    import time as _time

    from fyndit_helper.providers import SmartApiClient

    def slow_hang(request):
        _time.sleep(1.0)
        raise httpx.ReadTimeout("hanging")

    http, attempts = _counting_client(slow_hang)
    # After the first attempt 1 s of 1.5 s is gone - the budget still holds, but
    # another attempt (1 s) no longer fits into it.
    client = SmartApiClient(
        api_key="x", http_client=http, max_attempts=5,
        max_seconds=1.5, timeout_seconds=1.0,
    )

    with pytest.raises(LLMError):
        client.complete(system_prompt="s", user_message="u")

    assert attempts["n"] == 1
