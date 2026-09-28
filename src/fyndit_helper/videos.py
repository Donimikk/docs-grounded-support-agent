"""Tutorial videos from the vendor's YouTube channel.

The videos are neither downloaded nor transcribed - all we keep is the link and
what each one covers, so the model can point at the RIGHT video instead of
repeating the same one or inventing a URL.

Why a separate file and not part of the documentation: a video is not
documentation. Inside a <document> block the model would start quoting content
it cannot see. What belongs here is only the map "topic -> link".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class VideoError(ValueError):
    """The video list cannot be used."""


@dataclass(frozen=True)
class Video:
    title: str
    url: str
    #: Topics the video answers. The model picks by these.
    covers: tuple[str, ...]


def load_videos(path: Path | str) -> list[Video]:
    """Load videos.json.

    Raises:
        FileNotFoundError: the file does not exist.
        VideoError: a field is missing or the list is empty.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"video list does not exist: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("videos", [])

    videos = []
    for item in raw:
        for field in ("title", "url"):
            if not item.get(field):
                raise VideoError(f"video is missing '{field}': {item}")
        videos.append(
            Video(
                title=item["title"],
                url=item["url"],
                covers=tuple(item.get("covers", [])),
            )
        )

    if not videos:
        raise VideoError("no videos - an empty list is a mistake, not an empty channel")

    return videos


def render_videos(videos: list[Video]) -> str:
    """Render the videos as a block for the prompt."""
    return "\n".join(
        f"- {v.title} — {v.url}\n  covers: {', '.join(v.covers)}" for v in videos
    )
