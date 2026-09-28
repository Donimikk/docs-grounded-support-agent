"""The prompt store.

That a file can be written is not tested. What is tested are our two decisions:
the fingerprint scheme (every stored run hangs on it) and the fact that the same
prompt does not produce a second file.
"""

import hashlib

from fyndit_helper.prompt_store import fingerprint, save


def test_fingerprint_is_the_first_12_characters_of_sha256():
    """The scheme must not change silently - the runs stored so far carry a
    fingerprint in this shape and could not be paired with new ones after a
    change."""
    assert fingerprint("abc") == hashlib.sha256(b"abc").hexdigest()[:12]


def test_the_same_prompt_is_not_stored_twice(tmp_path):
    first_sha, first_path = save("prompt", tmp_path)
    second_sha, second_path = save("prompt", tmp_path)

    assert (first_sha, first_path) == (second_sha, second_path)
    assert [p.name for p in tmp_path.iterdir()] == [f"{first_sha}.md"]


def test_a_different_prompt_gets_its_own_file(tmp_path):
    _, one = save("one", tmp_path)
    _, other = save("other", tmp_path)

    assert one != other
    assert one.read_text(encoding="utf-8") == "one"
    assert other.read_text(encoding="utf-8") == "other"


def test_no_temporary_file_is_left_behind(tmp_path):
    """The write goes through a temporary file. If one were left behind, the
    directory would eventually look like the aftermath of a crash and there
    would be no telling which prompt is complete."""
    save("prompt", tmp_path)

    assert [p.suffix for p in tmp_path.iterdir()] == [".md"]
