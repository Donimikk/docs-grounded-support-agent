"""LLM provider implementations.

Each provider is one class with a complete() method. Swapping them is a change
to LLM_PROVIDER in .env - the endpoint code does not change.

The wire formats are taken from the official documentation:
- Mistral:  POST https://api.mistral.ai/v1/chat/completions  (OpenAI-compatible)
- Gemini:   POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
"""

from __future__ import annotations

import logging
import os
import threading
import time

import httpx

from fyndit_helper.llm import LLMClient, LLMError

REQUEST_TIMEOUT_SECONDS = 120.0

#: Free tiers cap the number of requests per minute, not the volume. One of
#: them allows about two a minute - an evaluation with 24 calls would fail
#: without waiting. Across five attempts the waits add up to 4+8+16+32 = 60s,
#: exactly on the edge of the minute window, and runs were failing just before
#: the limit lifted. A sixth attempt moves the total to 124s and clears it.
MAX_RETRIES_ON_RATE_LIMIT = 6
BACKOFF_BASE_SECONDS = 4.0

#: Cap on the value from the retry-after header. The number comes from the
#: provider and we used to trust it without question: 'retry-after: 86400'
#: would mean waiting a whole day, and a negative value would make time.sleep
#: raise an exception that is not an LLMError and would escape entirely.
MAX_RETRY_AFTER_SECONDS = 120.0

#: Two policies, because there are two completely different users.
#:
#: A batch run (the evaluation) can afford to wait - nobody is sitting in front
#: of it and waiting beats losing the result. An interactive ticket on the page
#: cannot: with 6 attempts and a 120s timeout a single call can take 844s, and a
#: ticket makes two calls - up to 28 minutes. The browser and the host give up
#: long before, and the person sees only 'the server did not respond'.
#:
#: For the page, a fast and truthful error beats a silent endless wait.
INTERACTIVE_TIMEOUT_SECONDS = 60.0
INTERACTIVE_MAX_ATTEMPTS = 2

#: A cap on the WHOLE time including retries, not on a single call.
#:
#: 'At most 2 attempts' is not enough on its own. During one provider outage
#: the page returned an error only after 114s - two attempts of 60s. A person
#: sat in front of it for two minutes to learn that it was not working.
#:
#: The difference is in the COST of a failure. A 503 arrives in half a second
#: and retrying it is cheap and useful. A read timeout costs the whole limit,
#: and a second 60-second wait on a hanging provider almost never helps.
#:
#: A budget solves it without special-casing an error type: on a 503 it is
#: almost untouched and the call is retried, on a hanging connection it is
#: spent and we give up. A batch run has no budget - there, waiting beats
#: losing the result.
INTERACTIVE_BUDGET_SECONDS = 70.0

#: Reasoning levels. When nothing is sent, the model runs on 'medium' - so
#: everything measured so far measured one setting we did not know we had.
#:
#: Measured on a single question through one provider:
#:   none    6 s,  243 output tokens,     0 spent on reasoning
#:   medium 14 s,  607 output tokens,   246 spent on reasoning
#:   max    79 s, 4034 output tokens,  3624 spent on reasoning
#:
#: Reasoning is billed as output, so 'max' is more expensive and above all 6x
#: slower. Over a whole evaluation that is the difference between ten minutes
#: and an hour.
REASONING_LEVELS = ("none", "low", "medium", "high", "xhigh", "max")

#: Statuses that retrying can fix. They are temporary states on the provider's
#: side - 429 is the limit, the rest is overload or a gateway outage. Errors
#: like 401 or 404 never get better by retrying.
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})


logger = logging.getLogger(__name__)


class _Pacer:
    """Spaces calls out so the limit is never reached.

    Reacting only to a 429 is expensive: every collision costs 60 seconds of
    waiting and a failed request often counts towards the limit anyway. Waiting
    a few seconds up front is cheaper.
    """

    def __init__(self, min_interval_seconds: float | None) -> None:
        self.min_interval = min_interval_seconds
        self._last_call: float | None = None
        # A lock: in a parallel evaluation several threads share one client.
        # Without it they would overwrite each other's _last_call, wait at the
        # same time, and --rpm would stop holding exactly when it is needed.
        self._lock = threading.Lock()

    def wait_for_slot(self) -> None:
        if self.min_interval is None:
            return

        # The wait is INSIDE the lock on purpose. The spacing applies to the
        # whole run, not to each thread separately - otherwise eight threads
        # would fire eight calls at once and only then start pacing.
        with self._lock:
            if self._last_call is not None:
                remaining = self.min_interval - (time.monotonic() - self._last_call)
                if remaining > 0:
                    time.sleep(remaining)
            self._last_call = time.monotonic()


def _sleep_for_retry(response: httpx.Response, attempt: int) -> None:
    """Wait before the next attempt.

    If the provider sends a retry-after header, follow it - it knows better
    than our estimate. Otherwise wait exponentially longer.
    """
    header = response.headers.get("retry-after")
    seconds = BACKOFF_BASE_SECONDS * (2**attempt)

    if header:
        try:
            # Retry-After can also be an HTTP date - then float() fails and our
            # own estimate stands, which is fine.
            seconds = min(max(float(header), 0.0), MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            pass

    reason = "rate limit" if response.status_code == 429 else f"overload ({response.status_code})"

    logger.warning(
        "%s - waiting %.0fs and trying again (attempt %d of %d)",
        reason,
        seconds,
        attempt + 2,
        MAX_RETRIES_ON_RATE_LIMIT,
    )
    time.sleep(seconds)


def _error_detail(response: httpx.Response) -> str:
    """Pull a readable message out of an error response."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]

    if isinstance(body, dict):
        if isinstance(body.get("error"), dict):
            return str(body["error"].get("message", body["error"]))
        if "message" in body:
            return str(body["message"])

    return str(body)[:200]


def _post_with_retry(
    http: httpx.Client,
    url: str,
    headers: dict[str, str],
    payload: dict,
    provider: str,
    pacer: _Pacer | None = None,
    max_attempts: int = MAX_RETRIES_ON_RATE_LIMIT,
    max_seconds: float | None = None,
    attempt_timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> httpx.Response:
    """Send the request and, on a temporary failure, wait and try again.

    Only the statuses in RETRYABLE_STATUS are retried. Errors like 401 or 404
    do not improve with retrying - it would only add delay.

    Args:
        max_seconds: cap on the whole time including retries. None = no cap
            (a batch run).
        attempt_timeout: the timeout of a single attempt. Needed to tell
            whether the next attempt fits into the budget at all.
    """
    started = time.monotonic()

    def next_would_not_fit() -> bool:
        """Is there time left for a WHOLE further attempt?

        Asking 'have I spent the budget' is not enough. With a 60s limit and a
        70s budget, 60s were gone after the first attempt - the budget was
        still 'valid', so a second attempt started and the page waited 124s.
        The question has to be whether the next attempt fits in what is left,
        not whether what is left is already zero.
        """
        if max_seconds is None:
            return False
        return (time.monotonic() - started) + attempt_timeout > max_seconds

    def send() -> httpx.Response:
        if pacer is not None:
            pacer.wait_for_slot()
        return http.post(url, headers=headers, json=payload)

    last = max_attempts - 1
    response = None

    for attempt in range(max_attempts):
        # A dropped connection is not an HTTP response - it has no status code,
        # so it would never pass through RETRYABLE_STATUS. Without this branch
        # the raw httpx exception escapes; an evaluation once died on case 27
        # of 37 and everything finished was lost.
        try:
            response = send()
        except httpx.TransportError as exc:
            if attempt == last or next_would_not_fit():
                # The number of attempts is the one ACTUALLY made, not the one
                # allowed - with the budget spent, 'after 2 attempts' would be
                # a lie.
                raise LLMError(
                    f"{provider}: the connection failed after {attempt + 1} "
                    f"attempts ({exc.__class__.__name__}). Try again shortly."
                ) from exc
            logger.warning(
                "%s: connection failed (%s), waiting and trying again (attempt %d of %d)",
                provider, exc.__class__.__name__, attempt + 2, max_attempts,
            )
            time.sleep(BACKOFF_BASE_SECONDS * (2**attempt))
            continue

        if response.status_code not in RETRYABLE_STATUS:
            return response
        if attempt == last or next_would_not_fit():
            break

        _sleep_for_retry(response, attempt)

    if response.status_code in RETRYABLE_STATUS:
        reason = (
            "the rate limit"
            if response.status_code == 429
            else f"the provider is overloaded ({response.status_code})"
        )
        raise LLMError(
            f"{provider}: {reason} still applies after {max_attempts} "
            "attempts. Try again shortly, or use a different provider."
        )

    return response


class OpenAICompatibleClient:
    """A shared base for services with a /chat/completions interface.

    Several providers speak the same protocol; only the base URL, the name in
    error messages and the default model differ. A subclass overrides those
    three attributes and nothing else.
    """

    BASE_URL = ""
    NAME = ""
    DEFAULT_MODEL = ""

    def __init__(
        self,
        api_key: str,
        model: str = "",
        http_client: httpx.Client | None = None,
        min_interval_seconds: float | None = None,
        reasoning_effort: str = "",
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_attempts: int = MAX_RETRIES_ON_RATE_LIMIT,
        max_seconds: float | None = None,
    ) -> None:
        model = model or self.DEFAULT_MODEL
        self.reasoning_effort = reasoning_effort.strip().lower()
        self.api_key = api_key
        self.model = model
        self._http = http_client or httpx.Client(timeout=timeout_seconds)
        self.max_attempts = max_attempts
        self.max_seconds = max_seconds
        self.timeout_seconds = timeout_seconds
        self._pacer = _Pacer(min_interval_seconds)

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def complete(self, system_prompt: str, user_message: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort

        response = _post_with_retry(
            self._http,
            f"{self.BASE_URL}/chat/completions",
            self._headers,
            payload,
            provider=self.NAME,
            pacer=self._pacer,
            max_attempts=self.max_attempts,
            max_seconds=self.max_seconds,
            attempt_timeout=self.timeout_seconds,
        )

        if response.status_code != 200:
            raise LLMError(f"{self.NAME} returned {response.status_code}: {_error_detail(response)}")

        choices = response.json().get("choices") or []
        if not choices:
            raise LLMError(f"{self.NAME} returned an empty answer (no choices)")

        return choices[0]["message"]["content"]

    def list_models(self) -> list[str]:
        """List the models this key has access to."""
        response = self._http.get(f"{self.BASE_URL}/models", headers=self._headers)

        if response.status_code != 200:
            raise LLMError(f"{self.NAME} returned {response.status_code}: {_error_detail(response)}")

        return [m["id"] for m in response.json().get("data", [])]


class MistralClient(OpenAICompatibleClient):
    """https://api.mistral.ai"""

    BASE_URL = "https://api.mistral.ai/v1"
    NAME = "Mistral"
    DEFAULT_MODEL = "mistral-small-latest"


class SmartApiClient(OpenAICompatibleClient):
    """https://api.smartapi.shop - a broker in front of several models.

    NOTE: this is not the model vendor but a middleman. Every prompt passes
    through their server in readable form. That is acceptable for evaluation
    (the questions are anonymised, the docs are public); for live tickets
    carrying customers' situations it is a deliberate decision, not a given.
    """

    BASE_URL = "https://api.smartapi.shop/v1"
    NAME = "SmartAPI"
    DEFAULT_MODEL = "sonnet-5"


class OpenRouterClient(OpenAICompatibleClient):
    """https://openrouter.ai - a gateway to models from several providers.

    Unlike calling a vendor directly, upstream sees only the OpenRouter
    account. Account settings can forbid routing to providers that train on
    data, and it can be restricted per request as well.
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    NAME = "OpenRouter"
    DEFAULT_MODEL = "openai/gpt-5.6-luna"


class OpenAIClient(OpenAICompatibleClient):
    """OpenAI directly, with no broker in between.

    This is the path for production: tickets contain customers' situations and
    should not travel through a third-party server that sees them in readable
    form. The broker stays for evaluation, where the questions are anonymised.
    """

    BASE_URL = "https://api.openai.com/v1"
    NAME = "OpenAI"
    DEFAULT_MODEL = "gpt-5.6-luna"


class GeminiClient:
    """https://generativelanguage.googleapis.com

    The key goes in the x-goog-api-key header, not as a query parameter - keys
    in a URL end up in server and proxy logs.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        http_client: httpx.Client | None = None,
        min_interval_seconds: float | None = None,
        timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_attempts: int = MAX_RETRIES_ON_RATE_LIMIT,
        max_seconds: float | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._http = http_client or httpx.Client(timeout=timeout_seconds)
        self.max_attempts = max_attempts
        self.max_seconds = max_seconds
        self.timeout_seconds = timeout_seconds
        self._pacer = _Pacer(min_interval_seconds)

    @property
    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

    def complete(self, system_prompt: str, user_message: str) -> str:
        response = _post_with_retry(
            self._http,
            f"{self.BASE_URL}/models/{self.model}:generateContent",
            self._headers,
            {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_message}]}],
            },
            provider="Gemini",
            pacer=self._pacer,
            max_attempts=self.max_attempts,
            max_seconds=self.max_seconds,
            attempt_timeout=self.timeout_seconds,
        )

        if response.status_code != 200:
            raise LLMError(f"Gemini returned {response.status_code}: {_error_detail(response)}")

        candidates = response.json().get("candidates") or []
        if not candidates:
            # Gemini returns 200 even when safety filters blocked the answer.
            raise LLMError("Gemini returned an empty answer (no candidates)")

        return candidates[0]["content"]["parts"][0]["text"]

    def list_models(self) -> list[str]:
        """List text generation models. Embedding models are filtered out."""
        response = self._http.get(f"{self.BASE_URL}/models", headers=self._headers)

        if response.status_code != 200:
            raise LLMError(f"Gemini returned {response.status_code}: {_error_detail(response)}")

        return [
            m["name"].removeprefix("models/")
            for m in response.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]


#: The providers the app can use.
#:
#: The choice for production is made by evaluation, not by preference. The
#: broker entry is there for comparing models during evaluation - customer
#: tickets should not flow through a third party.
PROVIDERS = {
    "mistral": (MistralClient, "MISTRAL_API_KEY", "MISTRAL_MODEL"),
    "gemini": (GeminiClient, "GEMINI_API_KEY", "GEMINI_MODEL"),
    "smartapi": (SmartApiClient, "SMARTAPI_API_KEY", "SMARTAPI_MODEL"),
    "openai": (OpenAIClient, "OPENAI_API_KEY", "OPENAI_MODEL"),
    "openrouter": (OpenRouterClient, "OPENROUTER_API_KEY", "OPENROUTER_MODEL"),
}


def build_client_from_env(
    min_interval_seconds: float | None = None,
    timeout_seconds: float | None = None,
    max_attempts: int | None = None,
    max_seconds: float | None = None,
) -> LLMClient:
    """Build a client from the environment variables.

    Args:
        min_interval_seconds: spacing between calls. Free tiers cap requests
            per minute - spacing prevents that instead of reacting to it after
            the fact.
        timeout_seconds: timeout of a single call. None = the batch value.
        max_attempts: how many attempts on overload. None = the batch value.
        max_seconds: cap on the whole time including retries. None = no cap.

            These two parameters exist because of the INTERACTIVE_* constants
            above. They could not be passed through at first: the constants were
            defined and the clients could accept them, but build_client_from_env
            dropped them - so the page ran on the batch ladder and waited
            minutes before saying 'the server is unavailable'.

    Raises:
        LLMError: unknown provider or a missing key.
    """
    name = os.getenv("LLM_PROVIDER", "mistral").strip().lower()

    if name not in PROVIDERS:
        raise LLMError(
            f"Unknown LLM_PROVIDER '{name}'. Supported: {', '.join(sorted(PROVIDERS))}"
        )

    cls, key_var, model_var = PROVIDERS[name]

    api_key = os.getenv(key_var, "").strip()
    if not api_key:
        raise LLMError(f"{key_var} is missing from .env - {name} cannot be called without it")

    model = os.getenv(model_var, "").strip()
    kwargs = {"api_key": api_key, "min_interval_seconds": min_interval_seconds}

    # Only when given - otherwise None would reach the client and overwrite its
    # own default.
    if timeout_seconds is not None:
        kwargs["timeout_seconds"] = timeout_seconds
    if max_attempts is not None:
        kwargs["max_attempts"] = max_attempts
    if max_seconds is not None:
        kwargs["max_seconds"] = max_seconds

    # Only the /chat/completions clients take a reasoning level. Gemini has its
    # own request shape and does not know this parameter.
    effort = os.getenv("REASONING_EFFORT", "").strip().lower()
    if effort:
        if effort not in REASONING_LEVELS:
            raise LLMError(
                f"Unknown REASONING_EFFORT '{effort}'. "
                f"Supported: {', '.join(REASONING_LEVELS)}"
            )
        if issubclass(cls, OpenAICompatibleClient):
            kwargs["reasoning_effort"] = effort

    return cls(**kwargs, model=model) if model else cls(**kwargs)
