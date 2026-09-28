"""Loading the product documentation from files on disk.

The unit is a whole page, not a chunk. No embeddings, no retrieval - the
documentation goes into the prompt in one piece.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FRONTMATTER_DELIMITER = "---"


class DocumentFormatError(ValueError):
    """A file has no usable frontmatter, or the directory holds no docs."""


@dataclass(frozen=True)
class Document:
    """A single documentation page."""

    slug: str
    source: str
    title: str
    content: str


def _parse(raw: str, filename: str) -> tuple[dict[str, str], str]:
    if not raw.startswith(FRONTMATTER_DELIMITER):
        raise DocumentFormatError(f"{filename}: frontmatter is missing")

    parts = raw.split(FRONTMATTER_DELIMITER, 2)
    if len(parts) < 3:
        raise DocumentFormatError(f"{filename}: frontmatter is not closed")

    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    return meta, parts[2].strip()


def load_documents(directory: Path) -> list[Document]:
    """Load every .md file in a directory, ordered by file name.

    Raises:
        FileNotFoundError: the directory does not exist.
        DocumentFormatError: the directory is empty or a file is malformed.
    """
    if not directory.is_dir():
        raise FileNotFoundError(f"documentation directory does not exist: {directory}")

    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise DocumentFormatError(f"no .md files in {directory}")

    documents = []
    for path in paths:
        meta, content = _parse(path.read_text(encoding="utf-8"), path.name)

        for required in ("source", "title"):
            if required not in meta:
                raise DocumentFormatError(
                    f"{path.name}: '{required}' missing from frontmatter"
                )

        documents.append(
            Document(
                slug=path.stem,
                source=meta["source"],
                title=meta["title"],
                content=content,
            )
        )

    return documents


# A rough, provider-independent estimate. The exact token count depends on each
# provider's own tokenizer.
CHARS_PER_TOKEN_ESTIMATE = 3.6


@dataclass(frozen=True)
class CorpusStats:
    """Summary of the loaded corpus."""

    document_count: int
    word_count: int
    char_count: int
    estimated_tokens: int


def corpus_stats(documents: list[Document]) -> CorpusStats:
    """Measure the corpus. The counts are exact, the token figure is a guess."""
    char_count = sum(len(d.content) for d in documents)
    word_count = sum(len(d.content.split()) for d in documents)

    return CorpusStats(
        document_count=len(documents),
        word_count=word_count,
        char_count=char_count,
        estimated_tokens=int(char_count / CHARS_PER_TOKEN_ESTIMATE),
    )
