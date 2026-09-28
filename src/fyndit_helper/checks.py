"""Automatic checks on a proposed answer - layer 1 of the evaluation.

These checks are deterministic and cost nothing: no model call. They catch the
mistakes a rule can verify rather than a judgement - a leaked internal marker,
an invented channel, a repeated question, the wrong language.

Factual correctness (is every claim backed by the docs?) is not their job -
that is layer 2, and it needs real question-answer pairs.

Every finding here has its origin in a real failure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from langdetect import DetectorFactory, LangDetectException, detect

# Without a fixed seed langdetect returns different results on every run.
DetectorFactory.seed = 0

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

#: The only channels an answer may mention.
#:
#: 🖥️-use-vinted-bot-here is here even though the documentation never mentions
#: it: that is where the bot is actually operated, and during onboarding it is
#: the single most useful place to send someone. Without it the tool could not
#: answer the most common ticket there is.
#: 🛎-success is where the owner points people with pre-sale questions ("is Pro
#: worth it?"). It is the only place with real results from other users - and
#: that is exactly what those questions are missing.
ALLOWED_CHANNELS = {
    "📼-quick-tutorials",
    "🧐-documentation",
    "🔥-subscriptions",
    "🖥️-use-vinted-bot-here",
    "🛎-success",
}

#: Below this length langdetect guesses - a short Slovak sentence came back as
#: Croatian. Better not to check than to accuse falsely.
MIN_CHARS_FOR_LANGUAGE_CHECK = 80

#: Slovak and Czech are commonly confused; both are acceptable to us.
SLOVAK_LIKE = {"sk", "cs"}

#: Languages langdetect confuses Slovak with. When the question comes back as
#: one of these, the customer's language counts as undetermined and the
#: language check is skipped - otherwise we would accuse correct answers to
#: Slovak customers.
CONFUSABLE_WITH_SLOVAK = SLOVAK_LIKE | {"hr", "sl", "pl"}

#: A customer question is often short ("how do I view them separately") and
#: waiting for 80 characters would disable the check exactly where it is
#: needed. Telling "Slovak or not" apart needs a smaller sample than naming the
#: language.
MIN_CHARS_FOR_QUESTION_LANGUAGE = 25

#: When one part is markedly shorter, they are not the same message.
LENGTH_RATIO_LIMIT = 2.0

MARKER = "⚠️"

_DOCS_MENTIONS = re.compile(
    r"\b(docs|documentation|dokument[áa]ci)", re.IGNORECASE
)

# The range has to start at U+1F000, not U+1F300: 🆘 is U+1F198 and sits in the
# Enclosed Alphanumeric Supplement block, below the pictograms. A narrower
# range missed it and the invented channel `🆘-support` went through unnoticed.
_CHANNEL = re.compile(
    r"[#`]?([\U0001F000-\U0001FAFF☀-➿⬀-⯿][\wÀ-ſ-]+)"
)

#: The bot's slash commands. They work, but the owner TURNED THEM OFF so that
#: one path (the Dashboard) and one tutorial exist instead of two for the same
#: thing. A customer who types such a command gets nothing - and comes back
#: more confused than before.
#:
#: The documentation still lists them as a "fallback command", so the model has
#: them in front of it on 16 of 38 pages. A rule in the prompt does not hold
#: against that; this check does, because it does not depend on the model
#: obeying anything.
COMMANDS = ("monitors", "sessions", "session_groups", "my_info", "preferences")

#: The (?<![\w/]) lookbehind is deliberate: the URL .../docs/sessions ends in
#: /sessions, but there is a letter before the slash, so it is not flagged.
_COMMAND = re.compile(r"(?<![\w/])/(?:" + "|".join(COMMANDS) + r")\b")

#: Characters around a mention that stop Discord from making it a link.
_WRAPPERS = "`'\"‘’“”"

_SECTION_NAVRH = re.compile(r"\**\s*N[ÁA]VRH[^\n]*\**", re.IGNORECASE)
_SECTION_SEND = re.compile(r"\**\s*NA\s+ODOSLANIE[^\n]*\**", re.IGNORECASE)
_SECTION_SOURCE = re.compile(r"\n\s*\**\s*ZDROJ\s*\**\s*\n", re.IGNORECASE)

#: The document URL in a citation. It has to match what goes into the prompt as
#: source="..." - otherwise the citation cannot be verified.
#:
#: Models often wrap the URL in markdown (`url`, <url>, (url)) or put it at the
#: end of a sentence with a full stop. Those characters are not part of the
#: URL - because of them the check once called five CORRECT citations invented.
_SOURCE_URL = re.compile(r"https?://[^\s`'\"<>()\[\],;]+")

#: Punctuation that can stick to the end of a URL.
_URL_TRAILING = "/.,;:!?`'\"*_)>]"

#: A citation of a note from the second knowledge layer (data/knowledge/notes/).
_NOTE_SOURCE = re.compile(r"poznamky:[\w-]+")

# A link to a specific video - short and long form. A link to the whole channel
# (/@name) deliberately does not match: that one cannot be "almost" invented.
_VIDEO_LINK = re.compile(
    r"https?://(?:www\.)?(?:youtu\.be/|youtube\.com/watch\?v=)([\w-]{6,})"
)


class CheckError(ValueError):
    """The answer cannot be split into the expected parts."""


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    detail: str


@dataclass(frozen=True)
class Sections:
    proposal: str
    to_send: str
    #: Where the model drew from. Empty when it gave nothing - older answers
    #: have none at all and must not bring the whole analysis down.
    source: str = ""


def split_sections(answer: str) -> Sections:
    """Split the answer into NÁVRH, NA ODOSLANIE and ZDROJ.

    ZDROJ is optional, the other two are not.

    Raises:
        CheckError: NÁVRH or NA ODOSLANIE is missing.
    """
    send_match = _SECTION_SEND.search(answer)
    if send_match is None:
        raise CheckError("the answer has no NA ODOSLANIE part")

    before = answer[: send_match.start()]
    rest = answer[send_match.end() :]

    # A second NA ODOSLANIE heading. It used to stay, with its whole block, in
    # the text meant for the customer, so the Copy button handed them the
    # heading and a second version of the answer. Which one is the real one we
    # cannot tell - hence a report, not a silent trim.
    if _SECTION_SEND.search(rest) is not None:
        raise CheckError("the NA ODOSLANIE part appears twice")

    # ZDROJ stands AFTER NA ODOSLANIE and has to be cut off. Otherwise a
    # documentation URL would count as part of the customer's text and the leak
    # check would fire on every answer.
    source = ""
    source_match = _SECTION_SOURCE.search(rest)
    if source_match is not None:
        source = rest[source_match.end() :].strip()
        rest = rest[: source_match.start()]

    # ZDROJ belongs after NA ODOSLANIE. When it stands before it, it falls into
    # the NÁVRH and 'source' stays empty - the invented-source check then has
    # nothing to verify and goes quiet exactly when the output is broken.
    if _SECTION_SOURCE.search(before) is not None:
        raise CheckError("the ZDROJ part stands before NA ODOSLANIE")

    proposal_match = _SECTION_NAVRH.search(before)
    if proposal_match is None:
        raise CheckError("the answer has no NÁVRH part")

    proposal = before[proposal_match.end() :].strip().strip("-").strip()

    return Sections(proposal=proposal, to_send=rest.strip(), source=source)


def _normalize(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", text.lower()) if len(w) > 3}


def _check_marker_leak(sections: Sections) -> Finding | None:
    if MARKER in sections.to_send:
        return Finding(
            check="marker_leaked",
            severity=SEVERITY_ERROR,
            detail="the ⚠️ marker is an internal signal and must not reach the customer",
        )
    return None


def _check_docs_mention(sections: Sections) -> Finding | None:
    """Does the customer's text talk about our documentation?

    The names of the allowed channels are removed before the search. The
    channel '#🧐-documentation' has the word in its name and the prompt
    explicitly allows it - without this, every link to it would count as a leak.
    """
    text = sections.to_send
    for channel in ALLOWED_CHANNELS:
        text = text.replace(f"#{channel}", " ").replace(channel, " ")

    match = _DOCS_MENTIONS.search(text)
    if match:
        return Finding(
            check="mentions_docs_to_customer",
            severity=SEVERITY_ERROR,
            detail=f"the customer's text mentions the documentation: {match.group(0)!r}",
        )
    return None


def _check_channels(sections: Sections) -> Finding | None:
    found = {m.strip("`#") for m in _CHANNEL.findall(sections.proposal + "\n" + sections.to_send)}
    unknown = {c for c in found if c not in ALLOWED_CHANNELS}

    if unknown:
        return Finding(
            check="unknown_channel",
            severity=SEVERITY_ERROR,
            detail=f"channel outside the allowed list: {', '.join(sorted(unknown))}",
        )
    return None


def _check_channel_format(sections: Sections) -> Finding | None:
    """Is the channel name written so that Discord turns it into a link?

    Discord only links the exact '#name-with-emoji' form. Without the hash it
    stays plain text and the customer has to hunt for the channel by hand.

    Only the customer's text is checked - the NÁVRH is read outside Discord.
    """
    text = sections.to_send
    without_hash = [
        channel for channel in ALLOWED_CHANNELS
        if channel in text and f"#{channel}" not in text
    ]

    if without_hash:
        return Finding(
            check="channel_without_hash",
            severity=SEVERITY_ERROR,
            detail=(
                "a channel without '#' is not linked in Discord: "
                + ", ".join(sorted(without_hash))
            ),
        )
    return None


def _check_channel_decoration(sections: Sections) -> Finding | None:
    """Is the channel name wrapped, or glued to punctuation?

    Discord only links a mention that stands on its own. Measured over 123
    answers: 56% wrapped the name in backticks and 40% glued a full stop or
    comma to it. Both look right in the text and had to be rewritten by hand.

    The cause was in the prompt - it showed channels in backticks, so the model
    copied the shape, not the rule. This check keeps it from coming back.
    """
    text = sections.to_send
    wrapped, glued = [], []

    for channel in ALLOWED_CHANNELS:
        at = text.find(f'#{channel}')
        while at != -1:
            before = text[at - 1] if at else ''
            after = text[at + len(channel) + 1 : at + len(channel) + 2]
            if before and before in _WRAPPERS:
                wrapped.append(channel)
            if after and after in '.,;:!?':
                glued.append(channel)
            at = text.find(f'#{channel}', at + 1)

    if wrapped or glued:
        reasons = []
        if wrapped:
            reasons.append('in quotes/backticks: ' + ', '.join(sorted(set(wrapped))))
        if glued:
            reasons.append('with punctuation attached: ' + ', '.join(sorted(set(glued))))
        return Finding(
            check='channel_not_linkable',
            severity=SEVERITY_ERROR,
            detail='Discord will not make a link out of this - ' + '; '.join(reasons),
        )
    return None


def _check_command(sections: Sections) -> Finding | None:
    """Is it sending the customer a command that does not work?

    NA ODOSLANIE is what gets checked, because that is what a person actually
    receives. The severity is error, not warning: a command is an instruction
    that sends the customer down a dead end, and the answer is better rewritten
    than sent.
    """
    found = sorted(set(_COMMAND.findall(sections.to_send)))
    if found:
        return Finding(
            check="command_to_customer",
            severity=SEVERITY_ERROR,
            detail=(
                f"the customer's text points at a disabled command: {', '.join(found)}"
                " - everything is done through the Dashboard"
            ),
        )
    return None


def _check_echoes_question(sections: Sections, question: str) -> Finding | None:
    question_words = _normalize(question)
    if not question_words:
        return None

    opening = " ".join(sections.to_send.split()[:25])
    overlap = question_words & _normalize(opening)

    if len(overlap) >= max(3, len(question_words) * 0.6):
        return Finding(
            check="echoes_question",
            severity=SEVERITY_WARNING,
            detail="the customer's text opens with their own question instead of an answer",
        )
    return None


def _check_length_match(sections: Sections) -> Finding | None:
    """Are both parts the same message? Measured by their length ratio.

    On a flagged gap this is NOT measured. There the prompt explicitly requires
    the parts to differ: the NÁVRH carries the marker and an internal note,
    while the customer gets a short sentence saying it will be checked.
    Reporting that as an error means shouting at behaviour we prescribed
    ourselves - and in production it would light up on every escalated ticket.
    """
    if MARKER in sections.proposal:
        return None

    a, b = len(sections.proposal), len(sections.to_send)
    if not a or not b:
        return None

    ratio = max(a, b) / min(a, b)
    if ratio > LENGTH_RATIO_LIMIT:
        return Finding(
            check="length_mismatch",
            severity=SEVERITY_WARNING,
            detail=f"the parts differ in length by {ratio:.1f}x - they are not the same message",
        )
    return None


def _check_proposal_language(sections: Sections) -> Finding | None:
    text = sections.proposal
    if len(text) < MIN_CHARS_FOR_LANGUAGE_CHECK:
        return None

    try:
        language = detect(text)
    except LangDetectException:
        return None

    if language not in SLOVAK_LIKE:
        return Finding(
            check="proposal_not_in_slovak",
            severity=SEVERITY_ERROR,
            detail=f"the NÁVRH should be in Slovak, detected language: {language}",
        )
    return None


def _check_send_language(sections: Sections, question: str) -> Finding | None:
    """Is the customer's message in Slovak when the customer does not write it?

    A real failure: the model received the ticket together with its Slovak
    translation and wrote BOTH parts from the translation. The helper would
    have sent a Slovak answer to an English speaker.

    The check is deliberately cautious and stays quiet rather than accusing a
    correct answer - a Slovak customer gets both parts in Slovak quite
    rightly.
    """
    text = sections.to_send
    if len(text) < MIN_CHARS_FOR_LANGUAGE_CHECK or len(question) < MIN_CHARS_FOR_QUESTION_LANGUAGE:
        return None

    try:
        send_language = detect(text)
        question_language = detect(question)
    except LangDetectException:
        return None

    # The question came back as Slovak, or as something the detector confuses
    # it with -> the customer's language is uncertain and there is nothing to
    # complain about.
    if question_language in CONFUSABLE_WITH_SLOVAK:
        return None

    if send_language in SLOVAK_LIKE:
        return Finding(
            check="wrong_language_for_customer",
            severity=SEVERITY_ERROR,
            detail=(
                f"NA ODOSLANIE is in Slovak, but the customer writes "
                f"'{question_language}' - they would get a message they cannot read"
            ),
        )
    return None


def _check_video_links(sections: Sections, known_urls: frozenset[str]) -> Finding | None:
    """Does the answer link to a video that does not exist?

    This is the only factual check that can be done without a model: the list
    of videos is finite and known. Models like to fill in an id - the link
    looks perfect but leads to somebody else's video or nowhere, and the
    customer finds out only after clicking.
    """
    text = sections.proposal + "\n" + sections.to_send
    invented = [m.group(0) for m in _VIDEO_LINK.finditer(text) if m.group(0) not in known_urls]

    if invented:
        return Finding(
            check="invented_link",
            severity=SEVERITY_ERROR,
            detail=f"a link to a video that is not in the list: {', '.join(sorted(invented))}",
        )
    return None


def _check_source(sections: Sections, known_sources: frozenset[str]) -> Finding | None:
    """Does the citation point at a document that really exists?

    The model sees all the pages at once and we have no way of knowing which
    one it used - other than being told. But it can also fill in a URL from the
    topic ('.../docs/pickup-points'), and such a citation is worse than none:
    the reader believes it and stops checking.

    The list of documents is finite and known, so this can be verified without
    a model.
    """
    if not sections.source or not known_sources:
        return None

    # A citation can point at a page (a URL) or at a note (poznamky:something).
    # Both need verifying - one is as easy to invent as the other.
    cited = _SOURCE_URL.findall(sections.source) + _NOTE_SOURCE.findall(sections.source)

    invented = [c for c in cited if c.rstrip(_URL_TRAILING) not in known_sources]

    if invented:
        return Finding(
            check="invented_source",
            severity=SEVERITY_ERROR,
            detail=f"a citation of a page that is not in the documentation: {', '.join(invented)}",
        )
    return None


def _known_document_sources() -> frozenset[str]:
    """Sources that may be cited: the corpus pages and the notes.

    The notes have to be in the same list - otherwise the check would call
    every second-layer citation an invented source.

    When they cannot be loaded, the check is skipped.
    """
    from pathlib import Path

    from fyndit_helper.docs import load_documents
    from fyndit_helper.knowledge import load_notes

    data = Path(__file__).resolve().parents[2] / "data"
    try:
        sources = {d.source.rstrip(_URL_TRAILING) for d in load_documents(data / "docs" / "en")}
    except (FileNotFoundError, ValueError):
        return frozenset()

    try:
        sources |= {n.source for n in load_notes(data / "knowledge" / "notes")}
    except ValueError:
        pass

    return frozenset(sources)


def _known_video_urls() -> frozenset[str]:
    """Links from data/knowledge/videos.json. Missing file, check skipped."""
    from pathlib import Path

    from fyndit_helper.videos import VideoError, load_videos

    path = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "videos.json"
    try:
        return frozenset(v.url for v in load_videos(path))
    except (FileNotFoundError, VideoError):
        return frozenset()


def run_checks(
    answer: str,
    ticket_sk: str,
    question: str,
    video_urls: frozenset[str] | None = None,
    document_sources: frozenset[str] | None = None,
) -> list[Finding]:
    """Run every automatic check and return the findings.

    An empty list means the answer passed - it says nothing about factual
    correctness, which only layer 2 measures.
    """
    if video_urls is None:
        video_urls = _known_video_urls()
    if document_sources is None:
        # Videos belong among the allowed sources. The prompt says a video
        # counts as documentation - then citing one is honest, and calling it
        # an invented source is the check's mistake, not the model's.
        document_sources = _known_document_sources() | _known_video_urls()
    try:
        sections = split_sections(answer)
    except CheckError as exc:
        return [Finding(check="missing_section", severity=SEVERITY_ERROR, detail=str(exc))]

    candidates = [
        _check_marker_leak(sections),
        _check_docs_mention(sections),
        _check_channels(sections),
        _check_channel_format(sections),
        _check_channel_decoration(sections),
        _check_command(sections),
        _check_echoes_question(sections, question),
        _check_length_match(sections),
        _check_proposal_language(sections),
        _check_send_language(sections, question),
        _check_video_links(sections, video_urls),
        _check_source(sections, document_sources),
    ]

    return [f for f in candidates if f is not None]


@dataclass(frozen=True)
class Inspection:
    """The result of inspecting one answer on the live path."""

    #: The model admitted a gap - the marker is in the NÁVRH. This is the
    #: escalation flag: the machine-readable form of a decision the model has
    #: already made. It is NOT asked for separately - it is derived from what
    #: was written, so it costs no extra call and no change to the prompt.
    escalate: bool
    findings: tuple[Finding, ...]

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity == SEVERITY_ERROR)


def inspect_answer(answer: str, ticket_sk: str, question: str) -> Inspection:
    """Check an answer on the live path. NEVER raises.

    Why never: this runs on the path an answer takes to the helper. A bug in a
    check must not bring down the answer itself - the check is an aid, not a
    condition. When it fails, the findings come back empty and the answer moves
    on.
    """
    try:
        sections = split_sections(answer)
        escalate = MARKER in sections.proposal
    except CheckError:
        # The answer cannot be split. run_checks reports that as a finding, but
        # we know nothing about the marker - and guessing that there is no gap
        # would be worse than admitting we do not know.
        escalate = False
    except Exception:  # noqa: BLE001
        return Inspection(escalate=False, findings=())

    try:
        findings = tuple(run_checks(answer, ticket_sk=ticket_sk, question=question))
    except Exception:  # noqa: BLE001
        findings = ()

    return Inspection(escalate=escalate, findings=findings)
