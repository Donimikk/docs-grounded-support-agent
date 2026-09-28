"""Replay a real thread one message at a time and compare with what a human wrote.

Why the eval set is not enough for this: there, every case has one correct
answer. This measures something else - how the bot behaves when a conversation
continues. A customer asks about one thing, gets an answer, and immediately
asks about another. Whether the bot noticed what has already been said can only
be found out by handing it the thread in pieces, exactly as it arrived.

For every customer message the model is called with what it had seen up to that
point - never with the whole thread at once. The result is written next to what
actually followed.

Usage:
    python scripts/replay_thread.py --provider smartapi --model gpt-5.6-luna --rpm 25
    python scripts/replay_thread.py --thread no-items-in-feed
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

from fyndit_helper.checks import MARKER, CheckError, split_sections  # noqa: E402
from fyndit_helper.docs import load_documents  # noqa: E402
from fyndit_helper.knowledge import load_notes  # noqa: E402
from fyndit_helper.llm import LLMError  # noqa: E402
from fyndit_helper.pipeline import Message  # noqa: E402
from fyndit_helper.pipeline import run as run_pipeline  # noqa: E402
from fyndit_helper.prompt import build_system_prompt, load_template  # noqa: E402
from fyndit_helper.prompt_store import fingerprint  # noqa: E402
from fyndit_helper.prompt_store import save as save_prompt  # noqa: E402
from fyndit_helper.providers import PROVIDERS, build_client_from_env  # noqa: E402
from fyndit_helper.videos import load_videos  # noqa: E402

THREADS_PATH = REPO_ROOT / "data" / "eval" / "threads.json"
OUT_DIR = REPO_ROOT / "data" / "eval" / "results" / "threads"
#: Shared with the evaluation - a replay runs on the same prompt, and without
#: its text nothing can be traced back to the report.
PROMPTS_DIR = REPO_ROOT / "data" / "eval" / "prompts"
DOCS_DIR = REPO_ROOT / "data" / "docs" / "en"
VIDEOS_PATH = REPO_ROOT / "data" / "knowledge" / "videos.json"
NOTES_DIR = REPO_ROOT / "data" / "knowledge" / "notes"
PROMPT_PATH = REPO_ROOT / "prompts" / "system_prompt.md"
TRANSLATE_PROMPT_PATH = REPO_ROOT / "prompts" / "translate_prompt.md"

STAMP = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--provider", choices=sorted(PROVIDERS))
    p.add_argument("--model")
    p.add_argument("--thread", nargs="+", help="replay only these threads, by id")
    p.add_argument("--rpm", type=float, help="call spacing, so the limit is never hit")
    return p.parse_args()


def steps(messages: list[dict]) -> list[int]:
    """The indexes up to which the thread should be handed to the model.

    The bot only answers when the last message is from the customer. Two
    customer messages in a row are one round - a person reads them together too.
    """
    out = []
    for i, message in enumerate(messages):
        if message["role"] != "customer":
            continue
        next_is_customer = i + 1 < len(messages) and messages[i + 1]["role"] == "customer"
        if not next_is_customer:
            out.append(i)
    return out


def next_human_reply(messages: list[dict], after: int) -> str:
    for message in messages[after + 1 :]:
        if message["role"] in ("helper", "owner"):
            return message["text"]
    return ""


def save_report(lines: list[str], record: list[dict], thread_count: int,
                rounds: int, started: float, prompt_sha: str) -> Path:
    """Write the result so far.

    Called after EVERY thread, not at the end. This script once died on the 7th
    thread of 8 and all 40 finished calls were lost, because it wrote once at
    the end. The same mistake had already taken down an evaluation.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model = os.environ.get(PROVIDERS[os.environ["LLM_PROVIDER"]][2], "model")
    # Careful with with_suffix: a model name contains dots (gpt-5.6-luna), so it
    # would turn into "gpt-5.json" and every run would overwrite the previous.
    md = OUT_DIR / f"{model}-{STAMP}.md"
    js = OUT_DIR / f"{model}-{STAMP}.json"

    header = [
        "# Replay of real threads",
        "",
        f"Model `{model}`, {thread_count} threads, {rounds} rounds, "
        f"{time.monotonic() - started:.0f} s.",
        "",
        f"Prompt `{prompt_sha}` — full text in "
        f"`data/eval/prompts/{prompt_sha}.md`.",
        "",
        "Every round gave the model **only what was in the thread by then** — never",
        "the whole conversation at once. Below its proposal is what the human",
        "actually replied.",
        "",
        "---",
        "",
    ]
    md.write_text("\n".join(header + lines), encoding="utf-8")
    js.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return md


def main() -> int:
    args = parse_args()
    load_dotenv()
    logging.basicConfig(level=logging.WARNING, format="\n  ! %(message)s")

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
    if args.model:
        _, _, model_variable = PROVIDERS[os.environ["LLM_PROVIDER"]]
        os.environ[model_variable] = args.model

    data = json.loads(THREADS_PATH.read_text(encoding="utf-8"))
    threads = data["threads"]
    if args.thread:
        wanted = set(args.thread)
        threads = [t for t in threads if t["id"] in wanted]
        # A typo in an id would otherwise silently replay fewer threads than you
        # think.
        missing = wanted - {t["id"] for t in threads}
        if missing:
            print(f"ERROR: these threads do not exist: {', '.join(sorted(missing))}")
            return 1

    documents = load_documents(DOCS_DIR)
    system_prompt = build_system_prompt(
        load_template(PROMPT_PATH), documents, load_videos(VIDEOS_PATH), load_notes(NOTES_DIR)
    )
    translate_prompt = load_template(TRANSLATE_PROMPT_PATH, require_documents=False)

    # Without the stored text there is no way to tell later what the model got.
    try:
        prompt_sha, _ = save_prompt(system_prompt, PROMPTS_DIR)
    except OSError as exc:
        prompt_sha = fingerprint(system_prompt)
        print(f"  (the prompt was not stored: {exc})")

    try:
        llm = build_client_from_env(
            min_interval_seconds=60.0 / args.rpm if args.rpm else None
        )
    except LLMError as exc:
        print(f"ERROR: {exc}")
        return 1

    rounds = sum(len(steps(t["messages"])) for t in threads)
    print(f"\nThreads: {len(threads)}   Rounds to replay: {rounds}   Calls: {rounds * 2}\n")

    lines: list[str] = []
    record: list[dict] = []
    started = time.monotonic()
    written_to = None

    for thread_data in threads:
        print(f"{thread_data['id']}")
        lines += [
            f"## {thread_data['id']}",
            "",
            f"*{thread_data['topic']}* · language `{thread_data['language']}`",
            "",
            f"**Why it is here:** {thread_data['why']}",
            "",
        ]

        messages = thread_data["messages"]
        for number, i in enumerate(steps(messages), start=1):
            thread = [Message(role=m["role"], text=m["text"]) for m in messages[: i + 1]]
            prompt_message = messages[i]["text"]

            print(f"  round {number}: {prompt_message[:60]}...", end=" ", flush=True)
            answer, error = "", None
            try:
                result = run_pipeline(
                    llm,
                    translate_prompt=translate_prompt,
                    system_prompt=system_prompt,
                    thread=thread,
                    draft=None,
                )
                answer = result.answer
                print("OK")
            except LLMError as exc:
                error = str(exc)
                print("ERROR")

            # split_sections raises CheckError when the model omits a part.
            # During a replay that is no reason to stop - it is a finding and
            # belongs in the report, because the customer would have received
            # nothing at all.
            sections, malformed = None, None
            if answer:
                try:
                    sections = split_sections(answer)
                except CheckError as exc:
                    malformed = str(exc)

            to_customer = (sections.to_send if sections else "") or ""
            has_marker = MARKER in answer

            heading = "**The bot proposed**" + (" — with the ⚠️ marker" if has_marker else "") + ":"
            body = (
                "> " + to_customer.strip().replace("\n", "\n> ")
                if to_customer
                else f"*(failed: {error or malformed})*"
            )
            lines += [
                f"### Round {number}",
                "",
                "**The customer wrote:**",
                "",
                "> " + prompt_message.replace("\n", "\n> "),
                "",
                heading,
                "",
                body,
                "",
            ]
            if malformed:
                lines += [f"**Malformed answer:** {malformed}", ""]

            human = next_human_reply(messages, i)
            if human:
                lines += [
                    "**What the human actually replied:**",
                    "",
                    "> " + human.replace("\n", "\n> "),
                    "",
                ]

            record.append({
                "thread": thread_data["id"], "round": number,
                "prompt": prompt_message,
                "answer": answer, "marker": has_marker,
                "error": error, "malformed": malformed,
                "human_reply": human,
            })

        # .get, not [""]: a missing summary is unfinished text, not a reason to
        # throw away rounds that already cost calls. A whole run once died on
        # this after the first thread and three finished rounds were lost.
        lines += ["**How it actually turned out:**", "",
                  thread_data.get("outcome", "_(not written up yet)_"), "", "---", ""]
        written_to = save_report(lines, record, len(threads), rounds, started, prompt_sha)

    if written_to:
        print(f"\n  written: {written_to.relative_to(REPO_ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
