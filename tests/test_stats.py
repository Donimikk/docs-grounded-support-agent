from pathlib import Path

from fyndit_helper.docs import CorpusStats, Document, corpus_stats, load_documents

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "data" / "docs" / "en"


def make_doc(slug: str, content: str) -> Document:
    return Document(slug=slug, source=f"https://x/{slug}", title=slug, content=content)


def test_stats_count_documents_words_and_characters():
    docs = [make_doc("a", "one two three"), make_doc("b", "four five")]

    stats = corpus_stats(docs)

    assert stats.document_count == 2
    assert stats.word_count == 5
    assert stats.char_count == len("one two three") + len("four five")


def test_an_empty_list_is_all_zeros():
    stats = corpus_stats([])

    assert stats == CorpusStats(document_count=0, word_count=0, char_count=0, estimated_tokens=0)


def test_the_token_estimate_comes_from_the_characters():
    docs = [make_doc("a", "x" * 3600)]

    stats = corpus_stats(docs)

    assert stats.estimated_tokens == 1000


def test_the_real_corpus_matches_what_was_measured():
    stats = corpus_stats(load_documents(DOCS_DIR))

    assert stats.document_count >= 38
    # Measured after the corpus was extended beyond /docs: 38 pages,
    # ~20,700 words, ~125,000 characters, ~34,800 tokens.
    # The upper bound is a safeguard: if the corpus grew sharply, that belongs
    # in the prompt after some thought, not silently.
    assert 19_500 <= stats.word_count <= 26_000
    assert 118_000 <= stats.char_count <= 160_000
