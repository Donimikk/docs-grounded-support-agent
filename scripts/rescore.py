"""Re-score a stored evaluation run against the current expectations in cases.json.

What for:
Every run stores the model's full answers. When a case later turns out to have
been labelled wrong - which has happened more than once - there is no reason to
pay for the same answers again. The old run is scored by the new rules and that
is that.

Usage:
    python scripts/rescore.py                       # the latest run
    python scripts/rescore.py data/eval/results/gemini-....json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fyndit_helper.evaluation import load_cases, score  # noqa: E402

CASES_PATH = REPO_ROOT / "data" / "eval" / "cases.json"
RESULTS_DIR = REPO_ROOT / "data" / "eval" / "results"


def latest_run() -> Path | None:
    """The newest run by write time.

    Not by name: the files start with the provider's name, so alphabetically
    'mistral-...' would always beat a newer 'gemini-...'.
    """
    runs = sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return runs[-1] if runs else None


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_run()

    if path is None or not path.is_file():
        print("No stored run found.")
        return 1

    run = json.loads(path.read_text(encoding="utf-8"))
    cases = {c.id: c for c in load_cases(CASES_PATH)}

    print(f"\nRun:   {path.name}")
    print(f"Model: {run.get('provider')} / {run.get('model')}")
    # Which prompt those answers came from. Without it even a re-scored number
    # is just a number - and that is exactly how a prompt behind the best score
    # we ever measured was lost.
    if run.get("prompt_sha"):
        where = run.get("prompt_file")
        print(f"Prompt: {run['prompt_sha']}" + (f"   {where}" if where else ""))
    if run.get("skip_translation"):
        print("The translation step was skipped in this run.")
    print()

    passed = changed = 0
    evaluated = []

    for entry in run["cases"]:
        case = cases.get(entry["id"])

        if case is None:
            print(f"  {entry['id']:26} -- no longer in the set, skipped")
            continue
        if entry.get("error") or not entry.get("answer"):
            print(f"  {entry['id']:26} -- never ran, cannot be re-scored")
            continue

        result = score(case, answer=entry["answer"], ticket_sk=entry.get("ticket_sk", ""))
        evaluated.append(result)
        passed += result.passed

        was = entry.get("passed")
        mark = "OK  " if result.passed else "FAIL"
        note = ""
        if was is not None and was != result.passed:
            note = "   <- CHANGED from the original run"
            changed += 1

        print(f"  {entry['id']:26} {mark} {case.expects:6}{note}")
        for reason in result.reasons:
            print(f"          - {reason}")

    if not evaluated:
        print("\n  Nothing could be re-scored.\n")
        return 1

    print(f"\n  {passed}/{len(evaluated)} passed")

    gaps = [r for r in evaluated if cases[r.case_id].expects == "gap"]
    if gaps:
        print(f"  of those, gaps: {sum(1 for r in gaps if r.passed)}/{len(gaps)} clean")
        print(f"                  {sum(1 for r in gaps if r.marker_correct)}/{len(gaps)} "
              "correctly recognised")

    if changed:
        print(f"  {changed} cases changed verdict - because of new expectations, not the model")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
