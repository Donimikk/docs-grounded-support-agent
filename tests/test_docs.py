from pathlib import Path

import pytest

from fyndit_helper.docs import Document, DocumentFormatError, load_documents

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "data" / "docs" / "en"


def write_doc(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(body, encoding="utf-8")
    return path


def test_parses_the_frontmatter_and_the_body(tmp_path):
    write_doc(
        tmp_path,
        "docs_rules.md",
        "---\nsource: https://www.fyndit.app/docs/rules\ntitle: Rules\n---\n\n# Rules\n\nText.\n",
    )

    docs = load_documents(tmp_path)

    assert len(docs) == 1
    doc = docs[0]
    assert doc.slug == "docs_rules"
    assert doc.source == "https://www.fyndit.app/docs/rules"
    assert doc.title == "Rules"
    assert doc.content == "# Rules\n\nText."


def test_the_frontmatter_is_not_part_of_the_content(tmp_path):
    write_doc(
        tmp_path,
        "a.md",
        "---\nsource: https://x/a\ntitle: A\n---\n\nBody.\n",
    )

    doc = load_documents(tmp_path)[0]

    assert "source:" not in doc.content
    assert "---" not in doc.content


def test_a_title_with_a_colon_does_not_break(tmp_path):
    write_doc(
        tmp_path,
        "a.md",
        "---\nsource: https://x/a\ntitle: Sessions: Setup\n---\n\nBody.\n",
    )

    assert load_documents(tmp_path)[0].title == "Sessions: Setup"


def test_the_result_is_ordered_by_slug(tmp_path):
    for name in ("c.md", "a.md", "b.md"):
        write_doc(tmp_path, name, f"---\nsource: https://x/{name}\ntitle: {name}\n---\n\nT.\n")

    assert [d.slug for d in load_documents(tmp_path)] == ["a", "b", "c"]


def test_a_missing_frontmatter_is_an_error(tmp_path):
    write_doc(tmp_path, "a.md", "# No frontmatter\n")

    with pytest.raises(DocumentFormatError, match="a.md"):
        load_documents(tmp_path)


def test_a_missing_source_is_an_error(tmp_path):
    write_doc(tmp_path, "a.md", "---\ntitle: A\n---\n\nBody.\n")

    with pytest.raises(DocumentFormatError, match="source"):
        load_documents(tmp_path)


def test_a_missing_directory_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_documents(tmp_path / "nothing")


def test_an_empty_directory_is_an_error(tmp_path):
    with pytest.raises(DocumentFormatError, match="no .md files"):
        load_documents(tmp_path)


def test_the_real_docs_load():
    docs = load_documents(DOCS_DIR)

    assert len(docs) >= 38
    # The corpus is no longer only /docs - pricing, FAQ and tutorials live
    # elsewhere on the site.
    assert all(d.source.startswith("https://www.fyndit.app/") for d in docs)
    assert all(d.content.strip() for d in docs)
    assert all(isinstance(d, Document) for d in docs)
