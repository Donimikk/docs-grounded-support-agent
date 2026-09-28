"""Detecting the language the customer writes in.

What it is for:
The model had to remember on its own which language to reply in - and with a
Slovak translation of the ticket sitting in the same prompt, it took that as
the template and sent an English customer a Slovak reply. A rule in a prompt is
always just a probability. This turns it into a fact: "The customer writes in
English."

Why silence beats guessing:
When the detector is unsure we return None and the prompt falls back to its own
rules. An invented language inserted as a fact is worse than none - the model
would dutifully reply in a language the customer does not speak.
"""

from __future__ import annotations

import re

from langdetect import DetectorFactory, LangDetectException, detect_langs

# Without a fixed seed langdetect returns different results on every run.
DetectorFactory.seed = 0

#: Below this length the language cannot be determined.
#:
#: 40, not 20: "Reselling, Ralph Lauren and Dio" (31 characters) came back as
#: German with confidence 1.00, the model got it as a fact and answered an
#: English customer in German. Short messages tend to be lists of proper nouns
#: with no grammar to reason from.
MIN_CHARS = 40

#: Things that must not reach the detector: they are not the customer's words.
#:
#: '[obrázok]' is OUR OWN attachment marker and happens to be a Slovak word. In
#: a message like 'https://vinted.es/... [obrázok]' - an item link plus a
#: screenshot, an everyday pair in this support queue - detection came back as
#: Slovak with enough confidence, and the prompt then ORDERED the model to
#: answer in Slovak. Not a silent safeguard, but one pointing the wrong way.
#:
#: URLs go too - they are in no language and only dilute the text.
_NOT_FOR_DETECTION = re.compile(
    r"\[[^\]]{1,30}\]|https?://\S+|www\.\S+"
)

#: Below this confidence we say nothing. 'looking for oakley, g star,
#: billabong' came out tl:0.43 / no:0.43 - nothing can be claimed from that.
#: 0.80, not higher: a real Italian ticket came out it:0.86 and that one has to
#: pass.
MIN_CONFIDENCE = 0.80

#: Codes to names. The model understands a code too, but a name is
#: unambiguous - 'sk' can be confused with an abbreviation, 'Slovak' cannot.
#: The list covers the languages that actually arrive in tickets; anything else
#: falls back to the code.
LANGUAGE_NAMES = {
    "en": "English",
    "sk": "Slovak",
    "cs": "Czech",
    "pl": "Polish",
    "de": "German",
    "fr": "French",
    "it": "Italian",
    "es": "Spanish",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ro": "Romanian",
    "hu": "Hungarian",
    "hr": "Croatian",
    "sl": "Slovenian",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "et": "Estonian",
    "fi": "Finnish",
    "sv": "Swedish",
    "da": "Danish",
    "el": "Greek",
    "bg": "Bulgarian",
    "uk": "Ukrainian",
    "tr": "Turkish",
}


def describe_language(text: str) -> str | None:
    """Return the name of the language, or None when it cannot be determined.

    Returns a name ('English'), not a code ('en') - it goes straight into the
    prompt for the model.

    It stays silent at any doubt, because the asymmetry is large: silence means
    the model falls back to a rule in the prompt, while a wrong value sends the
    customer a reply in a language they do not speak.
    """
    text = _NOT_FOR_DETECTION.sub(" ", text)
    text = text.strip()
    if len(text) < MIN_CHARS:
        return None

    try:
        best = detect_langs(text)[0]
    except (LangDetectException, IndexError):
        return None

    if best.prob < MIN_CONFIDENCE:
        return None

    # A code we have no name for never reaches the prompt. A bare 'tl' got in
    # as a fact once and the model replied in Turkish.
    return LANGUAGE_NAMES.get(best.lang)
