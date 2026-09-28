from fyndit_helper.language import describe_language

# --- recognition -----------------------------------------------------------


def test_recognises_english():
    assert describe_language("Hi, I've made two monitors, how do I view them separately") == "English"


def test_recognises_italian():
    assert describe_language(
        "Ciao, ho creato due monitor ma non riesco a vederli separatamente"
    ) == "Italian"


def test_recognises_spanish():
    assert describe_language(
        "Hola, tengo dos monitores y no consigo verlos por separado"
    ) == "Spanish"


# --- when unsure, stay silent ----------------------------------------------


def test_stays_silent_on_a_short_message():
    """Two words are not enough to determine a language. A wrong guess is worse
    than none - the model would receive something invented as a fact."""
    assert describe_language("help pls") is None


def test_empty_text_stays_silent():
    assert describe_language("   ") is None


def test_a_language_we_know_comes_back_by_name():
    text = "Sveiki, sukūriau du monitorius ir noriu juos matyti atskirai prašau"

    assert describe_language(text) == "Lithuanian"


# --- better silent than wrong ----------------------------------------------


def test_a_list_of_proper_nouns_is_not_classified():
    """'Reselling, Ralph Lauren and Dio' came back as German with confidence
    1.00. The model got 'The customer writes in German' as a FACT and dutifully
    replied in German. An English customer received a German answer - and it was
    our mechanism that did it, not the model."""
    assert describe_language("Reselling, Ralph Lauren and Dio") is None


def test_an_uncertain_detection_is_discarded():
    """'looking for oakley, g star, billabong etc snipes' -> tl:0.43, no:0.43.
    Nothing can be claimed at that confidence."""
    assert describe_language("looking for oakley, g star, billabong etc snipes") is None


def test_an_unknown_code_never_reaches_the_prompt():
    """A bare 'tl' went into the prompt as a fact. A code we have no name for is
    worse than no value at all - the model invents something from it."""
    from fyndit_helper.language import LANGUAGE_NAMES

    assert "tl" not in LANGUAGE_NAMES


def test_a_real_sentence_is_still_determined():
    """Tightening the rules must not silence ordinary tickets."""
    assert describe_language(
        "my autocop is broken and i dont know why it keeps failing on checkout"
    ) == "English"


def test_an_italian_ticket_passes():
    """it:0.86 - the threshold must not sit so high that it discards real
    messages."""
    assert describe_language(
        "Ciao, ho creato due monitor ma non riesco a vederli separatamente"
    ) == "Italian"


def test_our_own_attachment_marker_does_not_determine_the_language():
    """'[obrázok]' is OUR marker and happens to be a Slovak word.

    A message of 'item link + screenshot' is everyday in this support queue, and
    detection turned it into 'Slovak' - the prompt then ORDERED the model to
    answer in Slovak. Not a silent safeguard, but one pointing the wrong way."""
    assert describe_language('https://www.vinted.es/items/1234567890 [obrázok]') is None


def test_a_short_romance_sentence_can_be_wrong_and_confident():
    """A KNOWN LIMIT, not a bug in the code.

    'Ciao, ho comprato Plus ma non vedo il dashboard, cosa devo fare?' comes out
    as Portuguese with confidence 0.9999 - far above our threshold of 0.80. The
    threshold protects against uncertainty, not against a confident mistake.

    Mitigation: the pipeline determines the language from the WHOLE thread, not
    from one message - with a second sentence it comes out right. The risk
    remains on a very first short message, and this test keeps it from being
    forgotten."""
    short = 'Ciao, ho comprato Plus ma non vedo il dashboard, cosa devo fare?'
    longer = short + ' Grazie mille, non riesco a trovare il pulsante.'

    assert describe_language(short) == 'Portuguese'
    assert describe_language(longer) == 'Italian'
