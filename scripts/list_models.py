"""List the models your key actually has access to.

Model names change and guessing them is a needless risk - this shows the truth.

Usage:
    python scripts/list_models.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402

from fyndit_helper.llm import LLMError  # noqa: E402
from fyndit_helper.providers import GeminiClient, MistralClient  # noqa: E402


def main() -> int:
    load_dotenv()

    checks = [
        ("Mistral", "MISTRAL_API_KEY", MistralClient),
        ("Gemini", "GEMINI_API_KEY", GeminiClient),
    ]

    found_any_key = False

    for label, key_var, client_cls in checks:
        api_key = os.getenv(key_var, "").strip()

        print(f"\n=== {label} ===")

        if not api_key:
            print(f"  {key_var} is not in .env - skipping")
            continue

        found_any_key = True

        try:
            models = client_cls(api_key=api_key).list_models()
        except LLMError as exc:
            print(f"  ERROR: {exc}")
            continue
        except Exception as exc:  # network, DNS, timeout
            print(f"  CONNECTION ERROR: {exc}")
            continue

        if not models:
            print("  no text generation models")
            continue

        print(f"  {len(models)} models:")
        for name in sorted(models):
            print(f"    {name}")

    if not found_any_key:
        print("\nNo key in .env. Copy .env.example to .env and fill in at least one.")
        return 1

    print("\nWrite the model you pick into .env as MISTRAL_MODEL or GEMINI_MODEL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
