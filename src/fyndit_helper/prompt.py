"""Assembling the system prompt from an editable template and the loaded docs.

The template lives in prompts/system_prompt.md and is meant to be edited by
hand - the code only loads it and fills the documents in.
"""

from __future__ import annotations

import re
from pathlib import Path

from fyndit_helper.docs import Document
from fyndit_helper.knowledge import Note, render_notes
from fyndit_helper.videos import Video, render_videos

DOCUMENTS_PLACEHOLDER = "{documents}"
VIDEOS_PLACEHOLDER = "{videos}"
KNOWLEDGE_PLACEHOLDER = "{knowledge}"

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


class PromptError(ValueError):
    """The prompt template cannot be used."""


def load_template(path: Path, *, require_documents: bool = True) -> str:
    """Load the template and strip HTML comments from it.

    Comments are notes for a human - they are not sent to the model.

    Args:
        require_documents: True for the answering prompt, which makes no sense
            without the docs. False for prompts that need no documentation -
            the translation prompt, for instance.

    Raises:
        FileNotFoundError: the template does not exist.
        PromptError: the template has no place for the documents (when required).
    """
    if not path.is_file():
        raise FileNotFoundError(f"prompt template does not exist: {path}")

    template = _HTML_COMMENT.sub("", path.read_text(encoding="utf-8")).strip()

    if require_documents and DOCUMENTS_PLACEHOLDER not in template:
        raise PromptError(
            f"{path.name}: the {DOCUMENTS_PLACEHOLDER} placeholder is missing, "
            "the model would get no docs at all"
        )

    return template


def render_documents(documents: list[Document]) -> str:
    """Render the documents as tagged blocks that carry their source.

    The source sits in the tag so the model can cite the page it drew from.

    Raises:
        PromptError: empty list - a prompt without docs makes no sense.
    """
    if not documents:
        raise PromptError("no documents - the prompt would have nothing to answer from")

    blocks = [
        f'<document source="{d.source}" title="{d.title}">\n{d.content}\n</document>'
        for d in documents
    ]

    return "\n\n".join(blocks)


def build_system_prompt(
    template: str,
    documents: list[Document],
    videos: list[Video] | None = None,
    notes: list[Note] | None = None,
) -> str:
    """Fill the documents, videos and notes into the template.

    Videos and notes are optional - a template without their placeholder keeps
    working.
    """
    prompt = template.replace(DOCUMENTS_PLACEHOLDER, render_documents(documents))

    if VIDEOS_PLACEHOLDER in prompt:
        prompt = prompt.replace(
            VIDEOS_PLACEHOLDER, render_videos(videos) if videos else "(no videos)"
        )

    if KNOWLEDGE_PLACEHOLDER in prompt:
        prompt = prompt.replace(
            KNOWLEDGE_PLACEHOLDER,
            render_notes(notes) if notes else "(no notes yet)",
        )

    return prompt
