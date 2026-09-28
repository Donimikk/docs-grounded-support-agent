"""Run the eval set through a model and print a table.

Usage:
    python scripts/run_eval.py                      # provider from .env
    python scripts/run_eval.py --provider gemini    # one-off override
    python scripts/run_eval.py --provider mistral --model mistral-medium-latest

A free tier can cap you at 20 requests a day, and a full run is two calls per
case, so it never fits. Hence --skip-translation:

    python scripts/run_eval.py --provider gemini --skip-translation --rpm 4

Results are stored in data/eval/results/ so runs can be compared.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
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

from fyndit_helper.docs import load_documents  # noqa: E402
from fyndit_helper.evaluation import CaseResult, load_cases, score  # noqa: E402
from fyndit_helper.llm import LLMError  # noqa: E402
from fyndit_helper.pipeline import run as run_pipeline  # noqa: E402
from fyndit_helper.prompt import build_system_prompt, load_template  # noqa: E402
from fyndit_helper.prompt_store import fingerprint  # noqa: E402
from fyndit_helper.prompt_store import save as save_prompt  # noqa: E402
from fyndit_helper.providers import (  # noqa: E402
    PROVIDERS,
    REASONING_LEVELS,
    build_client_from_env,
)  # noqa: E402
from fyndit_helper.knowledge import load_notes  # noqa: E402
from fyndit_helper.videos import load_videos  # noqa: E402

CASES_PATH = REPO_ROOT / "data" / "eval" / "cases.json"
RESULTS_DIR = REPO_ROOT / "data" / "eval" / "results"
STABILITY_DIR = RESULTS_DIR / "stability"
#: Deliberately NOT under results/ - that directory is in .gitignore, so the
#: prompts would vanish with every clean clone, exactly like the one behind the
#: best score we ever measured.
PROMPTS_DIR = REPO_ROOT / "data" / "eval" / "prompts"
DOCS_DIR = REPO_ROOT / "data" / "docs" / "en"
VIDEOS_PATH = REPO_ROOT / "data" / "knowledge" / "videos.json"
NOTES_DIR = REPO_ROOT / "data" / "knowledge" / "notes"
PROMPT_PATH = REPO_ROOT / "prompts" / "system_prompt.md"
TRANSLATE_PROMPT_PATH = REPO_ROOT / "prompts" / "translate_prompt.md"


#: Modules whose change alters the outcome of a run even when the prompt stays
#: the same. Language detection was once fixed in pipeline.py and language.py -
#: prompt_sha stayed identical, so two 'comparable' runs were not comparable at
#: all. The prompt fingerprint says WHAT the model received; this one says how
#: we built it and how we counted.
BEHAVIOUR_FILES = (
    "pipeline.py",
    "language.py",
    "checks.py",
    "evaluation.py",
    "prompt.py",
)


def code_sha() -> str:
    """Fingerprint of the code that influences the outcome."""
    h = hashlib.sha256()
    for name in BEHAVIOUR_FILES:
        h.update((REPO_ROOT / "src" / "fyndit_helper" / name).read_bytes())
    return h.hexdigest()[:12]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the eval set through a model.")
    parser.add_argument("--provider", choices=sorted(PROVIDERS), help="overrides LLM_PROVIDER")
    parser.add_argument("--model", help="overrides the model of that provider")
    parser.add_argument(
        "--models",
        help=(
            "several models in a row, comma separated, as provider:model. "
            "For example smartapi:gpt-5.6-luna,smartapi:gpt-5.6-terra,gemini:gemini-3.6-flash. "
            "A comparison is printed at the end. They run one after another, not "
            "at once - two models through the same provider would create rate "
            "limits for each other."
        ),
    )
    parser.add_argument(
        "--case", help="run only these cases, ids separated by commas"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "how many cases to process at once. Cases are independent, so they "
            "parallelise; the two calls within one case (translate, answer) are "
            "necessarily sequential. --rpm applies to the whole run, not per "
            "thread. At 1 nothing changes and the progress is visible step by step."
        ),
    )
    parser.add_argument(
        "--effort",
        choices=list(REASONING_LEVELS),
        help=(
            "the model's reasoning level. Without it the model runs on 'medium' - "
            "so every measurement so far comes from that. A higher level is "
            "markedly slower: measured at 6 s for none, 14 s for medium and 79 s "
            "for max on a single call."
        ),
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=0,
        help=(
            "after the run, automatically repeat the cases that DID NOT COMPLETE "
            "because of a provider error. It does not touch cases that ran and "
            "failed - repeating those would be dressing up the result."
        ),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help=(
            "run each selected case N times and report whether it is stable or "
            "flaky, and how much the answers differ. Only with --case, so the "
            "whole set is not accidentally run N times."
        ),
    )
    parser.add_argument(
        "--fill",
        help=(
            "run only the cases that did not complete in a given results file "
            "(an API error) and write them BACK into it. No need to run the whole "
            "set because of one 400. It warns on a prompt mismatch - a mixed run "
            "cannot be compared."
        ),
    )
    parser.add_argument(
        "--expects",
        choices=["answer", "gap"],
        help=(
            "run only the cases of that type. The full set already exceeds some "
            "free daily caps, and admitting a gap is the main thing we measure - "
            "'--expects gap' always fits."
        ),
    )
    parser.add_argument(
        "--rpm",
        type=float,
        help=(
            "space the calls to this many per minute, so the limit is never hit. "
            "Without it you only wait after a collision and every collision costs "
            "~60s. The limit is not only on requests but on TOKENS per minute, and "
            "one call is the whole corpus. That is why free tiers take 2-3, not "
            "8-10."
        ),
    )
    parser.add_argument(
        "--skip-translation",
        action="store_true",
        help=(
            "skip the translation step - half the calls. Necessary for a free "
            "tier with a daily request cap. It measures the answering step only, "
            "not the whole flow."
        ),
    )
    return parser.parse_args()


def print_reasons(result: CaseResult) -> None:
    for reason in result.reasons:
        print(f"          - {reason}")


def parse_specs(args) -> list[tuple[str, str]]:
    """Return the (provider, model) pairs to run.

    Either one from --provider/--model, or several from --models. The format is
    'provider:model', because the provider cannot be guessed from a model name -
    and guessing would be worse here than a command one word longer.
    """
    if not args.models:
        provider = args.provider or os.environ.get("LLM_PROVIDER", "mistral")
        return [(provider, args.model or "")]

    specs = []
    for raw in args.models.split(","):
        raw = raw.strip()
        if ":" not in raw:
            raise ValueError(
                f"'{raw}' is not in the provider:model form (e.g. smartapi:gpt-5.6-luna)"
            )
        provider, model = raw.split(":", 1)
        if provider not in PROVIDERS:
            raise ValueError(
                f"unknown provider '{provider}'. Available: {', '.join(sorted(PROVIDERS))}"
            )
        specs.append((provider, model.strip()))
    return specs


def run_one(
    provider: str,
    model: str,
    cases: list,
    system_prompt: str,
    translate_prompt: str,
    args,
) -> dict | None:
    """Run the set through one model. Returns a summary, or None if it could not start."""
    os.environ["LLM_PROVIDER"] = provider
    if model:
        _, _, model_var = PROVIDERS[provider]
        os.environ[model_var] = model

    try:
        llm = build_client_from_env(
            min_interval_seconds=60.0 / args.rpm if args.rpm else None
        )
    except LLMError as exc:
        print(f"\nERROR ({provider}): {exc}\n")
        return None

    model = getattr(llm, "model", model or "?")

    calls_per_case = 1 if args.skip_translation else 2
    print(f"\n{'=' * 62}")
    print(f"Provider: {provider}   Model: {model}   Cases: {len(cases)}")
    print(f"Calls to the model: {len(cases) * calls_per_case}")

    if args.skip_translation:
        print("Translation skipped - only the answering step is measured.")

    print("Free tiers cap requests per minute - waiting is normal.\n")

    run_started = time.monotonic()
    results: list[tuple[CaseResult, str, float]] = []
    interrupted = False

    def process(case, on_step=None):
        """One case. Returns (result, seconds) and NEVER raises except on an
        interrupt - a single crash must not bring the run down.
        """
        started = time.monotonic()
        try:
            draft = run_pipeline(
                llm,
                translate_prompt=translate_prompt,
                system_prompt=system_prompt,
                thread=list(case.thread),
                on_step=on_step,
                translate=not args.skip_translation,
            )
            result = score(case, answer=draft.answer, ticket_sk=draft.ticket_sk)
        except LLMError as exc:
            result = CaseResult(
                case_id=case.id, passed=False, reasons=(), findings=(),
                answer="", ticket_sk="", error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            # Deliberately broad: one unexpected crash must not bring down the
            # whole run and discard the finished cases. That once lost 26 of 37
            # results, because httpx.ReadError was not an LLMError and escaped.
            result = CaseResult(
                case_id=case.id, passed=False, reasons=(), findings=(),
                answer="", ticket_sk="",
                error=f"unexpected error: {exc.__class__.__name__}: {exc}",
            )
        return result, time.monotonic() - started

    def report_line(index, case, result, seconds, with_head=True):
        """The line is assembled WHOLE and printed with one print call.

        It used to be two calls with the first one lacking a newline. A retry
        warning from a worker thread (providers logs 'connection failed, waiting
        and trying again') can drop in between and cut the line in half - four
        times as likely with --workers 4.
        """
        if not result.evaluated:
            verdict = "--- "
        elif result.passed:
            verdict = "OK  "
        else:
            verdict = "FAIL"

        head = f"  [{index:2}/{len(cases)}] {case.id:26} " if with_head else ""
        print(f"{head} {verdict} {case.expects:6} {seconds:5.1f}s", flush=True)
        if result.error:
            print(f"          ! did not run: {result.error}")
        print_reasons(result)

    if args.workers > 1:
        # Order and output are two different things and want opposite handling:
        #   - RESULTS must be in the order of the set, otherwise rescore and
        #     --fill drift apart -> hence an array by index, not append in
        #     completion order.
        #   - OUTPUT should arrive continuously, otherwise it stays silent for a
        #     long time and then dumps everything at once -> hence as_completed,
        #     not map. executor.map would give ordering for free, but it would
        #     hold the output back behind the slowest case ahead of it.
        #
        # Threads, not asyncio: the calls are I/O, the GIL is released during
        # them, and for dozens of concurrent requests asyncio is a needless
        # rebuild. httpx.Client is deliberately thread-safe and sharing one
        # instance beats a client per thread - a shared connection pool.
        by_index: list = [None] * len(cases)
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(process, c): i for i, c in enumerate(cases)}
            try:
                for f in as_completed(futures):
                    i = futures[f]
                    result, seconds = f.result()
                    by_index[i] = (result, cases[i].expects, seconds)
                    done += 1
                    report_line(done, cases[i], result, seconds)
            except KeyboardInterrupt:
                print()
                print("  Interrupted. The results so far will be saved.")
                interrupted = True
                pool.shutdown(wait=False, cancel_futures=True)
        results = [r for r in by_index if r is not None]

    else:
        for index, case in enumerate(cases, start=1):
            prefix = f"  [{index:2}/{len(cases)}] {case.id:26}"
            print(f"{prefix} ", end="", flush=True)

            started = time.monotonic()
            try:
                draft = run_pipeline(
                    llm,
                    translate_prompt=translate_prompt,
                    system_prompt=system_prompt,
                    thread=list(case.thread),
                    on_step=lambda step: print(f"{step}... ", end="", flush=True),
                    translate=not args.skip_translation,
                )
                result = score(case, answer=draft.answer, ticket_sk=draft.ticket_sk)
            except KeyboardInterrupt:
                print("\n\n  Interrupted. The results so far will be saved.\n")
                interrupted = True
                break
            except LLMError as exc:
                result = CaseResult(
                    case_id=case.id,
                    passed=False,
                    reasons=(),
                    findings=(),
                    answer="",
                    ticket_sk="",
                    error=str(exc),
                )
            except Exception as exc:  # noqa: BLE001
                # Deliberately broad, for the same reason as above.
                result = CaseResult(
                    case_id=case.id,
                    passed=False,
                    reasons=(),
                    findings=(),
                    answer="",
                    ticket_sk="",
                    error=f"unexpected error: {exc.__class__.__name__}: {exc}",
                )

            seconds = time.monotonic() - started
            results.append((result, case.expects, seconds))

            if not result.evaluated:
                verdict = "--- "
            elif result.passed:
                verdict = "OK  "
            else:
                verdict = "FAIL"

            print(f" {verdict} {case.expects:6} {seconds:5.1f}s", flush=True)

            if result.error:
                print(f"          ! did not run: {result.error}")
            print_reasons(result)

    if not results:
        print("  Nothing was evaluated in time.\n")
        return None

    # Catching up on outages. A provider error says nothing about the model, so
    # there is no point running everything again - repeating those cases is
    # enough.
    for round_index in range(getattr(args, "retry", 0)):
        missing = [i for i, (r, _, _) in enumerate(results) if not r.evaluated]
        if not missing:
            break
        print()
        print(f"  retrying {len(missing)} unfinished cases "
              f"(attempt {round_index + 1} of {args.retry})")
        for i in missing:
            case = cases[i]
            print(f"    {case.id}...", end=" ", flush=True)
            started = time.monotonic()
            try:
                draft = run_pipeline(
                    llm,
                    translate_prompt=translate_prompt,
                    system_prompt=system_prompt,
                    thread=list(case.thread),
                    # Has to match the main loop, otherwise a retried case would
                    # be translated in a run where translation is skipped.
                    translate=not args.skip_translation,
                )
                r = score(case, answer=draft.answer, ticket_sk=draft.ticket_sk)
                print("OK" if r.passed else "FAIL")
            except KeyboardInterrupt:
                print()
                print("  Interrupted during the retry.")
                interrupted = True
                break
            except Exception as exc:  # noqa: BLE001
                # Broad on purpose, same as in the main loop. Catching only
                # LLMError once cost 26 finished results - and the retry path
                # repeated that mistake.
                r = CaseResult(
                    case_id=case.id, passed=False, reasons=(), findings=(),
                    answer="", ticket_sk="",
                    error=(str(exc) if isinstance(exc, LLMError)
                           else f"unexpected error: {exc.__class__.__name__}: {exc}"),
                )
                print("still did not finish")
            results[i] = (r, case.expects, time.monotonic() - started)

    evaluated = [(r, e) for r, e, _ in results if r.evaluated]
    passed = sum(1 for r, _ in evaluated if r.passed)
    skipped = len(results) - len(evaluated)
    # The sum of the case durations, NOT the wall time of the run. With
    # --workers > 1 these are two entirely different numbers: the sum
    # overstates, because the cases ran at the same time.
    total_seconds = sum(s for _, _, s in results)
    wall_seconds = time.monotonic() - run_started

    if interrupted:
        print(f"  Partial result: {len(results)} of {len(cases)} cases.")

    print(f"\n  {passed}/{len(evaluated)} passed of those that were evaluated")

    if skipped:
        print(
            f"  {skipped} did not run (provider outage or limit) "
            "- that says nothing about the model"
        )

    gap_cases = [(r, e) for r, e in evaluated if e == "gap"]
    if gap_cases:
        gap_passed = sum(1 for r, _ in gap_cases if r.passed)
        gap_marker = sum(1 for r, _ in gap_cases if r.marker_correct)
        print(f"  of those, gaps: {gap_passed}/{len(gap_cases)} without a single mistake")
        # Without this line one style mistake drowns out the thing we measure
        # most - whether the model recognised that it does not know.
        print(f"                  {gap_marker}/{len(gap_cases)} correctly recognised "
              "(the marker fits, the rest are style mistakes)")

    # r.undelivered is excluded on purpose: the marker can be right and the
    # customer still receive nothing. Calling that a "style mistake" and saying
    # the model decided correctly would hide the worst shape of failure.
    style_only = [
        r for r, _ in evaluated
        if not r.passed and r.marker_correct and not r.undelivered
    ]
    undelivered = [r for r, _ in evaluated if r.undelivered]

    # The evaluation measures the FIRST attempt - it deliberately does not
    # rewrite, because tuning the prompt needs to show what the model produced
    # on its own. The live path (/ask) does have a hard error rewritten, so some
    # of these failures would never reach a customer. Without this line that is
    # invisible and the result looks worse than production is.
    would_be_rewritten = [
        r for r, _ in evaluated
        if not r.passed and any(f.severity == "error" for f in r.findings)
    ]
    if would_be_rewritten:
        print(
            f"  {len(would_be_rewritten)} of the failures are hard errors - the live "
            "path would have the answer rewritten and the customer would not see it"
        )

    # A gap case in which the model cited a note may not be a gap any more. This
    # is hard evidence, not a word-overlap heuristic: the model said itself
    # where it drew from.
    #
    # Why this is not a test: the heuristic in test_consistency.py looks for
    # shared words and once failed on a case where the note is in Slovak and the
    # question in English, leaving three words in common. A citation does not
    # have that problem, but it can only be read from a finished run.
    # The second element of the pair is case.expects (a string), not a Case - so
    # the id comes from the result.
    stale_labels = [
        r.case_id for r, e in evaluated
        if e == "gap" and "poznamky:" in (r.answer or "")
    ]
    if stale_labels:
        print(
            "  NOTE: a gap in which the model cited a note - the label may no "
            "longer hold: " + ", ".join(stale_labels)
        )
    if undelivered:
        print(
            f"  {len(undelivered)} cases: the model HAD the answer but did not send "
            "it to the customer"
        )
    if style_only:
        print(
            f"  {len(style_only)} cases failed on style ALONE - the model decided "
            "correctly on the substance"
        )

    if args.workers > 1:
        print(f"  wall time: {wall_seconds:.0f}s   (sum of case durations: {total_seconds:.0f}s,"
              f" {args.workers} at a time)")
    else:
        print(f"  time: {wall_seconds:.0f}s")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = RESULTS_DIR / f"{provider}-{model}-{stamp}.json"

    payload = json.loads(
        json.dumps(
            {
                "provider": provider,
                "model": model,
                "prompt_sha": getattr(args, "prompt_sha", None),
                "code_sha": code_sha(),
                "effort": os.environ.get("REASONING_EFFORT", "") or "(default)",
                # Without this a run with the translation skipped would not be
                # distinguishable from a full one and a comparison would lie.
                "skip_translation": args.skip_translation,
                "interrupted": interrupted,
                "passed": passed,
                "evaluated": len(evaluated),
                "skipped": skipped,
                "total": len(results),
                "seconds": round(wall_seconds, 1),
                "seconds_case_total": round(total_seconds, 1),
                "workers": args.workers,
                "cases": [
                    {
                        "id": r.case_id,
                        "expects": e,
                        "evaluated": r.evaluated,
                        "passed": r.passed,
                        "error": r.error,
                        "reasons": list(r.reasons),
                        "seconds": round(s, 1),
                        "ticket_sk": r.ticket_sk,
                        "answer": r.answer,
                    }
                    for r, e, s in results
                ],
            },
            ensure_ascii=False,
        )
    )

    if getattr(args, "repeat", 1) > 1:
        # Its own directory, so rescore.py does not treat a stability
        # measurement as an ordinary run - the same id appears N times in it and
        # the score would make no sense.
        STABILITY_DIR.mkdir(parents=True, exist_ok=True)
        out_path = STABILITY_DIR / f"repeat-{model}-{stamp}.json"
        payload["repeat"] = args.repeat
        seen: dict[str, int] = {}
        for entry in payload["cases"]:
            seen[entry["id"]] = seen.get(entry["id"], 0) + 1
            entry["run_index"] = seen[entry["id"]]

    if getattr(args, "fill", None):
        # A filled-in case goes back to its original position, so the order
        # matches the run's output. The summaries are recomputed from the whole,
        # not from the subset.
        out_path = Path(args.fill).resolve()
        merged = json.loads(out_path.read_text(encoding="utf-8"))
        new_cases = {c["id"]: c for c in payload["cases"]}
        existing = {c["id"] for c in merged["cases"]}
        merged["cases"] = [new_cases.get(c["id"], c) for c in merged["cases"]] + [
            c for c in payload["cases"] if c["id"] not in existing
        ]
        finished = [c for c in merged["cases"] if c.get("evaluated")]
        merged["evaluated"] = len(finished)
        merged["passed"] = sum(1 for c in finished if c["passed"])
        merged["skipped"] = len(merged["cases"]) - len(finished)
        merged["total"] = len(merged["cases"])
        merged["interrupted"] = merged["skipped"] > 0
        merged["seconds"] = round(merged.get("seconds", 0) + total_seconds, 1)
        merged["filled"] = sorted(new_cases)
        payload = merged
        print(
            f"  filled in: {len(new_cases)} cases, the run is now "
            f"{merged['passed']}/{merged['evaluated']}"
        )

    # The WHOLE assembled prompt is stored, not the template. Storing only the
    # template rested on the docs and notes being committed - which at the time
    # of a run they need not be. Two runs with byte-identical templates scored
    # differently because the docs or notes differed, and that text could not be
    # recovered from anywhere. A number without its prompt is just a number.
    #
    # The file is named after its fingerprint, so a repeated run on the same
    # prompt adds nothing.
    try:
        _, target = save_prompt(system_prompt, PROMPTS_DIR)
        payload["prompt_file"] = str(target.relative_to(REPO_ROOT)).replace("\\", "/")
    except OSError as exc:
        # A safeguard, not a condition - the result is written either way.
        print(f"  (the prompt was not stored: {exc})")

    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        where = out_path.relative_to(REPO_ROOT)
    except ValueError:
        # the file may sit outside the repository (e.g. a copy in a temp dir)
        where = out_path
    print(f"  written: {where}\n")

    if getattr(args, "repeat", 1) > 1:
        print_stability(payload)

    gaps = [r for r, e in evaluated if e == "gap"]
    return {
        "label": f"{model}",
        "passed": passed,
        "evaluated": len(evaluated),
        "gap_passed": sum(1 for r in gaps if r.passed),
        "gap_marker": sum(1 for r in gaps if r.marker_correct),
        "gap_total": len(gaps),
        "leaks": sum(
            1
            for r, _ in evaluated
            if any("mentions_docs" in x for x in r.reasons)
        ),
        "seconds": total_seconds,
        "interrupted": interrupted,
    }


def print_comparison(summaries: list[dict]) -> None:
    """A comparison at the end, so it need not be assembled by hand each time."""
    print("=" * 62)
    print("COMPARISON")
    print("=" * 62)
    print(f"{'model':<22}{'overall':>9}{'gaps':>10}{'recogn':>9}{'leak':>6}{'time':>7}")
    print("-" * 63)
    for s in summaries:
        print(
            f"{s['label']:<22}{s['passed']}/{s['evaluated']:<7}"
            f"{s['gap_passed']}/{s['gap_total']:<8}"
            f"{s['gap_marker']}/{s['gap_total']:<7}"
            f"{s['leaks']:>5}{s['seconds']:>7.0f}s"
        )
    print()
    print("  gaps    = admitted without a single further mistake")
    print("  recogn  = the model decided correctly whether it knows (the marker fits)")
    print("  leak    = how many times the customer was told about our documentation")
    print()


def print_stability(payload: dict) -> None:
    # Two questions answered at once: how often it happens and how much the
    # answers differ. Without both there is no telling whether a case is flaky.
    from collections import Counter, defaultdict

    try:
        from fyndit_helper.checks import split_sections
    except Exception:
        split_sections = None

    groups = defaultdict(list)
    for c in payload["cases"]:
        groups[c["id"]].append(c)

    print("=" * 62)
    print(f"STABILITY  ({payload.get('repeat')} repeats per case)")
    print("=" * 62)

    for case_id, runs in groups.items():
        finished = [r for r in runs if r.get("evaluated")]
        print()
        if not finished:
            print(f"{case_id}: not a single attempt finished")
            continue
        passed_count = sum(1 for r in finished if r["passed"])
        marker_count = sum(1 for r in finished if "⚠️" in (r.get("answer") or ""))
        if passed_count == len(finished):
            verdict = "STABLY OK"
        elif passed_count == 0:
            verdict = "STABLY FAILING"
        else:
            verdict = "FLAKY"
        print(f"{case_id}  [{runs[0].get('expects')}]  -> {verdict}")
        print(f"  passed {passed_count}/{len(finished)}    the marker was in {marker_count}/{len(finished)}")

        texts = []
        for r in finished:
            whole = r.get("answer") or ""
            part = ""
            if split_sections is not None:
                try:
                    sections = split_sections(whole)
                    part = sections.to_send if sections else ""
                except Exception:
                    part = ""
            texts.append(part or whole)

        lengths = [len(t) for t in texts]
        print(f"  length for the customer: {min(lengths)}-{max(lengths)} characters")

        word_sets = [set(t.lower().split()) for t in texts]
        pairs = [
            len(a & b) / len(a | b)
            for i, a in enumerate(word_sets)
            for b in word_sets[i + 1:]
            if (a | b)
        ]
        if pairs:
            mean = sum(pairs) / len(pairs)
            print(
                f"  overlap between the answers: {min(pairs):.2f} to {max(pairs):.2f}"
                f", mean {mean:.2f}"
            )

        counts = Counter(" | ".join(r["reasons"]) or "(no mistake)" for r in finished)
        for reason, n in counts.most_common():
            print(f"    {n}x  {reason}")
    print()


def main() -> int:
    args = parse_args()
    load_dotenv()

    # So the message is visible while waiting on a rate limit.
    logging.basicConfig(level=logging.WARNING, format="\n  ! %(message)s")

    try:
        specs = parse_specs(args)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    cases = load_cases(CASES_PATH)
    if args.case:
        wanted = {x.strip() for x in args.case.split(",") if x.strip()}
        missing = wanted - {c.id for c in cases}
        if missing:
            print(f"ERROR: these cases are not in the set: {', '.join(sorted(missing))}")
            return 1
        cases = [c for c in cases if c.id in wanted]
    if args.repeat > 1:
        if not args.case:
            print("ERROR: --repeat can only be used with --case")
            return 1
        if args.fill:
            print("ERROR: --repeat and --fill cannot be combined")
            return 1
        cases = [c for c in cases for _ in range(args.repeat)]

    if args.expects:
        cases = [c for c in cases if c.expects == args.expects]
        if not cases:
            print(f"ERROR: no cases of type '{args.expects}'")
            return 1

    if args.effort:
        os.environ["REASONING_EFFORT"] = args.effort

    documents = load_documents(DOCS_DIR)
    # The videos have to go into the prompt here as well, otherwise the
    # evaluation measures a different prompt from production and video links
    # would never be tested.
    videos = load_videos(VIDEOS_PATH)
    notes = load_notes(NOTES_DIR)
    system_prompt = build_system_prompt(load_template(PROMPT_PATH), documents, videos, notes)
    translate_prompt = load_template(TRANSLATE_PROMPT_PATH, require_documents=False)

    # The prompt fingerprint is stored with every run. Without it there is no
    # way to tell afterwards whether two runs are being compared on the same
    # prompt - and that once cost half a day of guessing.
    args.prompt_sha = fingerprint(system_prompt)

    if args.fill:
        fill_path = Path(args.fill)
        if not fill_path.exists():
            print("ERROR: the file does not exist: " + args.fill)
            return 1
        original = json.loads(fill_path.read_text(encoding="utf-8"))
        # An interrupted run does not have those cases in the file AT ALL - so
        # looking only for the ones with an error would not be enough. Missing
        # is every case of the set that is not finished in there.
        finished_ids = {c["id"] for c in original["cases"] if c.get("evaluated")}
        missing = [c.id for c in cases if c.id not in finished_ids]
        if not missing:
            print("  Every case in that run finished - there is nothing to fill in.")
            return 0

        old_prompt = original.get("prompt_sha")
        if old_prompt is None:
            print()
            print("  ! That run has no stored prompt fingerprint, so there is no way")
            print("    to verify that the prompt has not changed since. The filled-in")
            print("    cases may come from a different prompt than the rest.")
            print()
        old_code = original.get("code_sha")
        if old_code is not None and old_code != code_sha():
            print()
            print(f"  ! THE CODE HAS CHANGED ({old_code} -> {code_sha()}).")
            print("    The prompt matches, but the pipeline or the scoring changed,")
            print("    so the filled-in cases would be measured differently.")
            print()
            return 1

        elif old_prompt != args.prompt_sha:
            print()
            print(f"  ! THE PROMPT HAS CHANGED ({old_prompt} -> {args.prompt_sha}).")
            print("    Filling in would produce a run from two different prompts and")
            print("    its score would belong to neither. Run the whole set.")
            print()
            return 1

        cases = [c for c in cases if c.id in set(missing)]
        print()
        print(f"  Filling in {len(cases)} unfinished cases in {fill_path.name}")

    print(f"\nDocuments in the prompt: {len(documents)}   Models to run: {len(specs)}")

    summaries = []
    for provider, model in specs:
        summary = run_one(provider, model, cases, system_prompt, translate_prompt, args)
        if summary is None:
            # A wrong model name or a missing key must not bring down the other
            # runs.
            continue
        summaries.append(summary)
        if summary["interrupted"]:
            print("  Interrupted - the remaining models are not started.\n")
            break

    if not summaries:
        return 1
    if len(summaries) > 1:
        print_comparison(summaries)

    return 0 if all(s["passed"] == s["evaluated"] for s in summaries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
