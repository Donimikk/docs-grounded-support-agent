import json

import pytest

from fyndit_helper.videos import Video, VideoError, load_videos, render_videos

REPO_VIDEOS = "data/knowledge/videos.json"


def write(tmp_path, payload):
    path = tmp_path / "videos.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --- loading ---------------------------------------------------------------


def test_loads_the_videos(tmp_path):
    path = write(tmp_path, {"videos": [{"title": "Autocop", "url": "https://youtu.be/a", "covers": ["autocop"]}]})

    videos = load_videos(path)

    assert videos == [Video(title="Autocop", url="https://youtu.be/a", covers=("autocop",))]


def test_a_comment_in_the_file_does_no_harm(tmp_path):
    """videos.json opens with a _comment for a human - it is not a video."""
    path = write(tmp_path, {
        "_comment": ["a note for a human"],
        "videos": [{"title": "A", "url": "https://youtu.be/a", "covers": []}],
    })

    assert len(load_videos(path)) == 1


def test_a_missing_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_videos(tmp_path / "nothing.json")


def test_a_video_without_a_url_is_an_error(tmp_path):
    path = write(tmp_path, {"videos": [{"title": "A", "covers": []}]})

    with pytest.raises(VideoError, match="url"):
        load_videos(path)


def test_an_empty_list_is_an_error(tmp_path):
    """An empty file means something broke - not that no videos exist."""
    path = write(tmp_path, {"videos": []})

    with pytest.raises(VideoError, match="no videos"):
        load_videos(path)


# --- rendering into the prompt ---------------------------------------------


def test_the_rendering_carries_the_title_and_the_url():
    out = render_videos([Video("Create a Monitor", "https://youtu.be/x", ("monitor",))])

    assert "Create a Monitor" in out
    assert "https://youtu.be/x" in out


def test_the_rendering_carries_the_topics_so_the_model_can_choose():
    out = render_videos([Video("A", "https://youtu.be/x", ("autocop", "rules"))])

    assert "autocop" in out
    assert "rules" in out


# --- the real file ---------------------------------------------------------


def test_the_real_file_loads():
    videos = load_videos(REPO_VIDEOS)

    assert len(videos) >= 10
    assert all(v.url.startswith("https://youtu.be/") for v in videos)
    assert all(v.title and v.covers for v in videos)


def test_the_real_urls_are_unique():
    """Two entries with the same link would mean a mistake when writing them."""
    urls = [v.url for v in load_videos(REPO_VIDEOS)]

    assert len(urls) == len(set(urls))
