"""The second layer of knowledge: what we know from practice but the official
documentation does not say.

Why it is separate from the docs:
Behind data/docs/ stands the vendor's own site - fetch it again and you have the
truth. Behind this stands a person on the team. So every note carries WHO
confirmed it and WHEN, and it is cited differently from a documentation page.

Why the model treats it as a full source:
When a note answers the question, the model answers normally - it does not
raise the "this is not in the docs" marker. Otherwise the tool would report a
gap for things we do know, and the second layer would be pointless. The
difference stays visible in the SOURCE section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: Distinguishes a note citation from a documentation URL.
KNOWLEDGE_PREFIX = "poznamky:"

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    content: str
    #: Who confirmed the note. Without it, it is just a claim.
    verified_by: str
    verified_on: str

    @property
    def source(self) -> str:
        """How the note is cited in the SOURCE section."""
        return f"{KNOWLEDGE_PREFIX}{self.id}"


def _parse(text: str, path: Path) -> Note:
    found = _FRONTMATTER.match(text)
    if not found:
        raise ValueError(f"{path.name}: frontmatter between --- is missing")

    fields = {}
    for line in found.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip()
            # Only a surrounding PAIR of quotes is removed. A plain .strip('"')
            # would cut the opening quote of a title like '"Invalid link" on a
            # monitor' and leave the closing one unpaired.
            if len(value) > 1 and value[0] == value[-1] == '"':
                value = value[1:-1]
            fields[key.strip()] = value

    for required in ("id", "title", "verified_by", "verified_on"):
        if not fields.get(required):
            raise ValueError(f"{path.name}: '{required}' missing from frontmatter")

    return Note(
        id=fields["id"],
        title=fields["title"],
        content=text[found.end():].strip(),
        verified_by=fields["verified_by"],
        verified_on=fields["verified_on"],
    )


def load_notes(directory: Path | str) -> list[Note]:
    """Load the notes from a directory.

    A missing or empty directory is NOT an error - the second layer is optional
    and the project works without it. That is the difference from the docs,
    where empty means something went wrong.

    Raises:
        ValueError: a note has no frontmatter or is missing a required field.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []

    return [
        _parse(path.read_text(encoding="utf-8"), path)
        for path in sorted(directory.glob("*.md"))
    ]


def render_notes(notes: list[Note]) -> str:
    """Render the notes as a block for the prompt.

    The <note> tag differs from <document> on purpose, so the model can see it
    is a different kind of source and cite it correctly in SOURCE.
    """
    if not notes:
        return ""

    # Note titles quote error messages, so quotation marks are common in them.
    # Unescaped they would break the tag and the model would not see where the
    # note ends.
    def attr(value: str) -> str:
        return value.replace("&", "&amp;").replace('"', "&quot;")

    return "\n\n".join(
        f'<note source="{attr(n.source)}" title="{attr(n.title)}" '
        f'verified_by="{attr(n.verified_by)}" verified_on="{attr(n.verified_on)}">\n'
        f"{n.content}\n</note>"
        for n in notes
    )
