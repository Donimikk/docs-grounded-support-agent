"""The HTTP layer. Thin - all the logic lives in docs.py, prompt.py and llm.py,
so that a Discord layer can later call it without going through HTTP.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import uuid
from pathlib import Path
from urllib.parse import parse_qs

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from fyndit_helper import history
from fyndit_helper.checks import inspect_answer
from fyndit_helper.docs import corpus_stats, load_documents
from fyndit_helper.llm import LLMClient, LLMError
from fyndit_helper.pipeline import Message, ThreadError, draft_answer
from fyndit_helper.pipeline import run as run_pipeline
from fyndit_helper.prompt import build_system_prompt, load_template
from fyndit_helper.providers import (
    INTERACTIVE_BUDGET_SECONDS,
    INTERACTIVE_MAX_ATTEMPTS,
    INTERACTIVE_TIMEOUT_SECONDS,
    PROVIDERS,
    build_client_from_env,
)
from fyndit_helper.knowledge import load_notes
from fyndit_helper.videos import load_videos

load_dotenv()

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
# The page lives next to the code, not in REPO_ROOT - it belongs to the app and
# should be deployed with it, not sit in the repository as a loose file.
INDEX_PATH = Path(__file__).resolve().parent / "static" / "index.html"
LOGIN_PATH = Path(__file__).resolve().parent / "static" / "login.html"
DOCS_DIR = REPO_ROOT / "data" / "docs" / "en"
VIDEOS_PATH = REPO_ROOT / "data" / "knowledge" / "videos.json"
NOTES_DIR = REPO_ROOT / "data" / "knowledge" / "notes"
PROMPT_PATH = REPO_ROOT / "prompts" / "system_prompt.md"
TRANSLATE_PROMPT_PATH = REPO_ROOT / "prompts" / "translate_prompt.md"
POLISH_PROMPT_PATH = REPO_ROOT / "prompts" / "polish_prompt.md"

#: How many answers may be generated for one ticket when the first one carries
#: a hard error. 2 = one rewrite.
#:
#: Why at all: most of these errors are random variation, not a stable failure -
#: the word "documentation" leaked to the customer in 1 run out of 5. Reporting
#: such an error to a person hands them work a machine can do. Only when it
#: repeats on the second answer is it worth attention - by then it is not
#: variation any more.
MAX_ANSWER_ATTEMPTS = 2

# Real customer messages - which is why data/history/ belongs in .gitignore.
#
# The path can be overridden by an environment variable. The reason is not
# convenience: on a platform with an ephemeral disk the history is wiped on
# every restart or deploy. To survive, the file has to sit on a mounted
# persistent disk - and that path can only be set from outside.
HISTORY_PATH = Path(
    os.environ.get("FYNDIT_HISTORY_PATH", REPO_ROOT / "data" / "history" / "tickets.json")
)

app = FastAPI(
    title="Fyndit Support Helper",
    description="Answers support questions strictly from the official documentation.",
    version="0.2.0",
)

# The docs, videos and template do not change while the process runs - they are
# loaded once.
_documents = load_documents(DOCS_DIR)
_videos = load_videos(VIDEOS_PATH)
_notes = load_notes(NOTES_DIR)
_stats = corpus_stats(_documents)
_system_prompt = build_system_prompt(load_template(PROMPT_PATH), _documents, _videos, _notes)
_translate_prompt = load_template(TRANSLATE_PROMPT_PATH, require_documents=False)
# The polish prompt deliberately gets NO documentation - in that mode the
# helper's notes are the only source of facts, hence require_documents=False.
_polish_prompt = load_template(POLISH_PROMPT_PATH, require_documents=False)


API_KEY_HEADER = "X-API-Key"

# auto_error=False: a missing header should be refused with our own message.
# A side effect is that Swagger gets an "Authorize" button.
_api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def require_api_key(provided: str | None = Depends(_api_key_scheme)) -> None:
    """Let through only a call with the right key in the header.

    The key is read per request, not at startup - otherwise it could not be
    changed in tests or during local debugging without a restart.

    When API_KEY is not set, the endpoint LOCKS. The opposite choice would mean
    that a forgotten environment variable opens /ask to the whole internet.
    """
    expected = os.environ.get("API_KEY", "").strip()

    if not expected:
        raise HTTPException(
            status_code=503,
            detail="API_KEY is not set - the endpoint is locked on purpose",
        )

    # compare_digest instead of ==: the comparison does not take a different
    # amount of time depending on how many characters match, so the key cannot
    # be guessed character by character.
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=401,
            detail=f"the {API_KEY_HEADER} header is missing or wrong",
        )


COOKIE_NAME = "fyndit_gate"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # a month, so a phone does not log in daily


def _gate_token() -> str | None:
    """The value the cookie should carry, or None when no password is set.

    The cookie deliberately carries a fingerprint derived from the password,
    not the password. That has two consequences, both intended: the password
    never reaches the browser or the logs, and changing the variable
    immediately invalidates every device already signed in.
    """
    password = os.environ.get("APP_PASSWORD", "").strip()
    if not password:
        return None
    return hmac.new(password.encode(), b"fyndit-gate-v1", hashlib.sha256).hexdigest()


def _gate_open(request: Request) -> bool:
    """Does this browser have a valid session?"""
    expected = _gate_token()
    if expected is None:
        # With no password set, the gate NEVER opens. The same choice as with
        # API_KEY: a forgotten variable should lock, not unlock.
        return False
    given = request.cookies.get(COOKIE_NAME)
    return bool(given) and secrets.compare_digest(given, expected)


def _login_page(error: str = "") -> HTMLResponse:
    html = LOGIN_PATH.read_text(encoding="utf-8")
    if error:
        html = html.replace(
            "<!-- ERROR_SLOT -->", f'<p class="error">{error}</p>'
        )
    return HTMLResponse(html)


def require_access(
    request: Request, provided: str | None = Depends(_api_key_scheme)
) -> None:
    """Let through a signed-in browser OR a call with the right key.

    Two paths on purpose: the page goes through the cookie so no key has to be
    typed on a phone; scripts and tests keep using the header.
    """
    if _gate_open(request):
        return

    # No cookie and no key = a person in a browser who is not signed in. They
    # should get 401, not a 503 about a missing variable: /ask is available to
    # them without API_KEY, they only have to sign in with the password.
    #
    # Without this, removing API_KEY would break the page with an error about a
    # variable it does not need - and the interface would show a server error
    # instead of 'sign in again'. 503 stays for a call that DID send a key.
    if provided is None:
        raise HTTPException(
            status_code=401,
            detail="not signed in - open the page and enter the password",
        )

    require_api_key(provided)


def get_llm_client() -> LLMClient:
    """Return a client according to .env.

    Tests substitute a double here through dependency_overrides.
    """
    try:
        # An interactive policy, not a batch one. For the page a fast and
        # truthful error beats a silent endless wait - with batch values one
        # ticket can wait tens of minutes and the browser gives up long before.
        return build_client_from_env(
            timeout_seconds=INTERACTIVE_TIMEOUT_SECONDS,
            max_attempts=INTERACTIVE_MAX_ATTEMPTS,
            max_seconds=INTERACTIVE_BUDGET_SECONDS,
        )
    except LLMError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


#: Caps on the input. Without them anyone signed in can send a megabyte-sized
#: ticket - the prompt already runs to ~35k tokens and every one is paid for.
#: The numbers are generous: the longest real ticket was a few thousand
#: characters.
MAX_CHARS = 8000
MAX_MESSAGES = 60


class ThreadMessage(BaseModel):
    role: str = Field(description="'customer' or 'helper'")
    text: str = Field(max_length=MAX_CHARS)


class AskRequest(BaseModel):
    question: str | None = Field(
        default=None,
        max_length=MAX_CHARS,
        description="Shorthand for a thread with a single customer message.",
        examples=["What is the difference between whitelist and blacklist?"],
    )
    thread: list[ThreadMessage] | None = Field(
        default=None,
        max_length=MAX_MESSAGES,
        description=(
            "The whole ticket thread, oldest message first. The last one must be "
            "from the customer. Use instead of 'question' once a conversation is "
            "running - the model then will not ask again what it already asked."
        ),
        examples=[None],
    )
    conversation_id: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Optional. The id of a ticket already started - the answer is appended "
            "to it. When missing, a new one is created and its id returned. 'New "
            "chat' is therefore just a new id; nothing is deleted."
        ),
        examples=[None],
    )
    draft: str | None = Field(
        default=None,
        max_length=MAX_CHARS,
        description=(
            "Optional. Rough notes from the helper when the answer is already "
            "known - the model rewrites them into a proper reply instead of "
            "searching the docs. LEAVE EMPTY or remove the line entirely if you "
            "want an answer from the documentation."
        ),
        examples=[None],
    )


class FindingOut(BaseModel):
    """One finding from the automatic checks."""

    check: str = Field(description="Name of the check, e.g. 'mentions_docs_to_customer'.")
    severity: str = Field(description="'error' or 'warning'.")
    detail: str = Field(description="What exactly is wrong, in plain words.")


class AskResponse(BaseModel):
    ticket_sk: str = Field(description="The ticket translated into Slovak (a separate step).")
    answer: str = Field(description="NÁVRH (SK) and NA ODOSLANIE exactly as the model returned them.")
    mode: str = Field(description="'docs' = answered from the documentation, 'polish' = notes rewritten.")
    documents_used: int = Field(description="How many documentation pages went into the prompt.")
    conversation_id: str = Field(
        description="Id of the ticket in the history. Send it with the next message of the same thread."
    )
    escalate: bool = Field(
        description=(
            "The model admitted a gap - the marker is in the NÁVRH. The machine-readable "
            "form of a decision it already made; we do not ask for it separately, it is "
            "derived from the answer."
        )
    )
    regenerated: bool = Field(
        default=False,
        description=(
            "The first answer had a hard error and was rewritten. When the findings are "
            "empty the rewrite helped; when they are not, the error repeated and is worth "
            "attention."
        ),
    )
    findings: list[FindingOut] = Field(
        default_factory=list,
        description=(
            "Findings of the automatic checks (checks.py). An empty list does not mean the "
            "answer is factually right - only that no known mistake matches it."
        ),
    )


@app.get("/", include_in_schema=False)
def index(request: Request, error: int = 0) -> Response:
    """The app for a signed-in browser, the sign-in page otherwise.

    Nobody types the key into the page any more - that was workable on a desktop
    and tiresome on a phone. You sign in once with a password and the cookie
    does the rest.
    """
    if _gate_open(request):
        return FileResponse(INDEX_PATH, media_type="text/html")

    if _gate_token() is None:
        return _login_page(
            "APP_PASSWORD is not set - this page is locked on purpose."
        )
    return _login_page("Wrong password." if error else "")


@app.post("/login", include_in_schema=False)
async def login(request: Request) -> Response:
    """Verify the password and set the cookie. No accounts, one shared password.

    The form is parsed by hand with parse_qs: FastAPI's Form() would need
    python-multipart, and a new dependency is not worth one field.
    """
    body = (await request.body()).decode("utf-8", errors="replace")
    given = parse_qs(body).get("password", [""])[0]

    expected = os.environ.get("APP_PASSWORD", "").strip()
    if not expected or not secrets.compare_digest(given, expected):
        # A redirect, not a render: otherwise the password stays in the request
        # body, which the browser offers to send again on refresh.
        return RedirectResponse("/?error=1", status_code=303)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        _gate_token() or "",
        max_age=COOKIE_MAX_AGE,
        httponly=True,      # JavaScript cannot reach it
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@app.get("/logout", include_in_schema=False)
def logout() -> Response:
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


def _running_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "").strip().lower() or "(not set)"


def _running_model() -> str:
    """The model the app will ACTUALLY use - not the one in .env on disk.

    Without this there is no way to verify from outside that the deployed
    instance runs what we think it runs. One deployment ran on a provider we had
    dropped two days earlier, and it only came out through a rate-limit error.
    """
    entry = PROVIDERS.get(_running_provider())
    if entry is None:
        return "(unknown provider)"
    client_class, _, model_variable = entry
    from_environment = os.environ.get(model_variable, "").strip()
    if from_environment:
        return from_environment
    # With the variable missing, the class default is used - and that is exactly
    # the case where a person believes something else is running.
    default = getattr(client_class, "DEFAULT_MODEL", "")
    return f"{default} (default)" if default else "(unknown)"


@app.get("/health")
def health() -> dict[str, object]:
    """Verify that the app is up and the docs were loaded.

    It also reports whether the access variables are set - without that there is
    no way to tell "wrong password" from "the variable never reached the
    process", and those are two entirely different faults.
    """
    return {
        "status": "ok",
        "provider": _running_provider(),
        "model": _running_model(),
        "password_set": _gate_token() is not None,
        "api_key_set": bool(os.environ.get("API_KEY", "").strip()),
        "documents": _stats.document_count,
        "words": _stats.word_count,
        "characters": _stats.char_count,
        "estimated_tokens": _stats.estimated_tokens,
    }


@app.post("/ask", response_model=AskResponse, dependencies=[Depends(require_access)])
def ask(request: AskRequest, llm: LLMClient = Depends(get_llm_client)) -> AskResponse:
    """Propose an answer to a support ticket. It sends nothing - it proposes.

    Two steps: translate the ticket into Slovak first, then answer from the
    documentation.
    """
    if request.thread:
        thread = [Message(role=m.role, text=m.text) for m in request.thread]
    elif request.question and request.question.strip():
        thread = [Message(role="customer", text=request.question)]
    else:
        raise HTTPException(
            status_code=400,
            detail="both 'question' and 'thread' are missing - there is nothing to answer",
        )

    try:
        result = run_pipeline(
            llm,
            translate_prompt=_translate_prompt,
            system_prompt=_system_prompt,
            thread=thread,
            draft=request.draft,
            polish_prompt=_polish_prompt,
        )
    except ThreadError as exc:
        # A fault in the caller's input, not at the provider.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # The checks run HERE, on the finished answer. They used to run only in the
    # evaluation - nothing checked the tickets that went to customers.
    # inspect_answer() never raises, so a failing check cannot deprive the
    # helper of an answer.
    question = thread[-1].text
    answer = result.answer
    inspection = inspect_answer(answer, ticket_sk=result.ticket_sk, question=question)

    # A hard error gets the answer rewritten. Warnings do not - they are a
    # notice, not a failure, and the evaluation does not treat them as one
    # either.
    #
    # The translation is NOT repeated. It is a separate call and has nothing to
    # do with an error in the answer, so repeating costs half.
    attempts = 1
    while attempts < MAX_ANSWER_ATTEMPTS and inspection.errors:
        attempts += 1
        try:
            retry = draft_answer(
                llm,
                system_prompt=_polish_prompt if result.mode == "polish" else _system_prompt,
                thread=thread,
                latest_sk=result.ticket_sk or None,
                draft=request.draft,
            )
        except LLMError as exc:
            # The rewrite is a bonus, not a condition. When it fails, the first
            # answer goes out with its findings - still more than a 502.
            logger.warning("rewriting the answer failed: %s", exc)
            break

        retry_inspection = inspect_answer(
            retry, ticket_sk=result.ticket_sk, question=question
        )
        # Fewer errors wins; on a tie, the newer one. Returning the second one
        # blindly could mean trading one error for three.
        if len(retry_inspection.errors) <= len(inspection.errors):
            answer, inspection = retry, retry_inspection

    # The history is written AFTER the answer and its failure does not bring the
    # answer down. The answer is what matters; losing it because a file write
    # failed would be absurd. When the write fails the id is returned anyway -
    # the next message of that thread will use it and the record is created then.
    conversation_id = request.conversation_id or uuid.uuid4().hex[:12]
    try:
        conversation_id = history.record_round(
            HISTORY_PATH,
            conversation_id=request.conversation_id,
            thread=[{"role": m.role, "text": m.text} for m in thread],
            ticket_sk=result.ticket_sk,
            answer=answer,
            mode=result.mode,
            escalate=inspection.escalate,
            findings=[
                {"check": f.check, "severity": f.severity, "detail": f.detail}
                for f in inspection.findings
            ],
            regenerated=attempts > 1,
        )
    except (history.HistoryError, OSError) as exc:
        logger.warning("the history was not written: %s", exc)

    return AskResponse(
        ticket_sk=result.ticket_sk,
        answer=answer,
        mode=result.mode,
        # In polish mode no documentation is sent at all, so the full count
        # would be a lie - and it is the one value in the interface that shows
        # whether the docs were really used.
        documents_used=0 if result.mode == "polish" else _stats.document_count,
        conversation_id=conversation_id,
        escalate=inspection.escalate,
        regenerated=attempts > 1,
        findings=[
            FindingOut(check=f.check, severity=f.severity, detail=f.detail)
            for f in inspection.findings
        ],
    )


@app.get("/history", dependencies=[Depends(require_access)])
def history_list() -> list[dict]:
    """Overview of the stored tickets, most recently used first."""
    try:
        return history.list_records(HISTORY_PATH)
    except (history.HistoryError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/history/{ticket_id}", dependencies=[Depends(require_access)])
def history_detail(ticket_id: str) -> dict:
    """A whole ticket with its answers, for reopening it in the interface."""
    try:
        record = history.load(HISTORY_PATH, ticket_id)
    except (history.HistoryError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="no such ticket in the history")
    return record


@app.delete("/history/{ticket_id}", dependencies=[Depends(require_access)])
def history_delete(ticket_id: str) -> dict:
    """Delete a ticket from the history. Nothing is left on disk."""
    try:
        deleted = history.delete(HISTORY_PATH, ticket_id)
    except (history.HistoryError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="no such ticket in the history")
    return {"deleted": ticket_id}
