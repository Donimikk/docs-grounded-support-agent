"""Content-addressed store for assembled prompts.

A score means nothing without the prompt that produced it, and the template
alone is not enough: what the model receives is the template plus the
documentation, the notes and the video list. Two runs can share a template and
still differ. So the whole assembled prompt is stored.

The file is named after the fingerprint of its content, so the same prompt
costs space once no matter how many runs use it. The write goes to a temporary
file and is renamed afterwards; a crash mid-write would otherwise leave a
truncated prompt under a fingerprint nobody can verify.

This module is deliberately absent from `BEHAVIOUR_FILES` in
`scripts/run_eval.py`, which is what `code_sha` is computed from. It does not
influence the outcome of a run, and including it would make every later run
look as if the behaviour had changed.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

#: Every stored run carries a fingerprint of this length. Change it and new
#: runs can no longer be paired with the old ones.
FINGERPRINT_LENGTH = 12


def fingerprint(prompt: str) -> str:
    """Fingerprint of a prompt, in the scheme the stored runs use."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:FINGERPRINT_LENGTH]


def save(prompt: str, directory: Path) -> tuple[str, Path]:
    """Store a prompt under its fingerprint. Returns the fingerprint and path.

    If the file already exists there is nothing to do: the name is derived from
    the content, so an existing file holds the same bytes.
    """
    sha = fingerprint(prompt)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{sha}.md"
    if target.exists():
        return sha, target

    partial = directory / f".{sha}.partial"
    partial.write_text(prompt, encoding="utf-8")
    os.replace(partial, target)
    return sha, target
