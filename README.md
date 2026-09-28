# docs-grounded-support-agent

A support assistant for a Discord product community that answers **only from the
product's documentation** — and says so out loud when the documentation does not
contain the answer.

It was built for [Fyndit](https://www.fyndit.app), a Vinted monitoring bot whose
support runs in Discord tickets. A human helper stays in the loop: the tool
writes a proposal, the helper reads it and decides what gets sent.

*Slovak version of this file: [README.sk.md](README.sk.md).*

---

## The problem it solves

Support answers were being written from memory. That is fast and it is wrong
often enough to matter: the documentation says a temporary restriction lasts
about 24 hours, a person under time pressure says "you got banned". The opposite
failure is worse — an answer invented with confidence for a question the
documentation never covered.

So the tool does three things:

1. **Proposes an answer strictly from the corpus.** The whole documentation goes
   into the prompt; there is no retrieval step to blame for a miss.
2. **Marks a gap instead of filling it.** When the answer is not in the corpus,
   the model has to say so and hand the ticket over, rather than infer a
   plausible yes or no. Absence from the documentation is not evidence that
   something is impossible — that mistake is its own test case in the eval set.
3. **Checks the answer before anybody sends it.** Deterministic checks catch a
   leaked internal marker, an invented channel or video link, a question echoed
   back at the customer, and a reply written in the wrong language.

The answer comes in two parts: a Slovak **NÁVRH** for the helper, carrying the
internal notes and the gap marker, and **NA ODOSLANIE** in the customer's own
language, with nothing internal in it. A third section, **ZDROJ**, cites the page
or note the answer came from.

## Architecture

The HTTP layer is deliberately thin, so a Discord bot can later call the same
pipeline without going through it.

| Module | What it does |
| --- | --- |
| `api.py` | FastAPI app: `/ask`, `/health`, `/history`, a password-protected page |
| `pipeline.py` | The two-step flow over a thread: translate first, then answer |
| `prompt.py` | Assembles the system prompt from the template plus the loaded corpus |
| `docs.py` | Loads the documentation pages. Whole pages, no chunking, no embeddings |
| `knowledge.py` | The second layer: what we know from practice but the docs do not say |
| `videos.py` | Tutorial videos — a "topic → link" map, so the model cannot invent a URL |
| `language.py` | Detects the customer's language; returns nothing rather than guessing |
| `checks.py` | Deterministic checks on a proposal — layer 1 of the evaluation |
| `evaluation.py` | Scores a proposal against the expectation — layer 2 |
| `llm.py`, `providers.py` | One class per provider behind a single-method protocol |
| `history.py` | What has already been answered, stored as JSON on disk |
| `prompt_store.py` | Content-addressed store of assembled prompts, so a score can be traced |
| `discord.py` | Turns a Discord thread into the messages the pipeline works with |

Two design choices worth naming, because they are the ones people ask about:

- **No vector database.** The corpus is small enough to fit in a prompt whole.
  A retrieval layer would add a component that can fail silently and be blamed
  for every miss. When the corpus outgrows the context window this changes;
  until then it is a dependency that buys nothing.
- **No memory between calls.** The whole thread is sent every time. What looks
  like a model remembering a conversation is the history being resent, so the
  pipeline does that explicitly instead of pretending to hold state.

## How the measurement works

This is the part the rest of the repository exists to serve.

- **`scripts/run_eval.py`** runs the eval set through a model and prints a table.
  Every run stores the model's full answers, the fingerprint of the assembled
  prompt and the fingerprint of the behaviour-carrying source files, so two runs
  can be compared and a difference can be attributed.
- **`scripts/rescore.py`** re-scores a stored run against the current
  expectations, **without calling the model again**. Cases turn out to be
  labelled wrong more often than the model turns out to be wrong; there is no
  reason to pay for the same answers twice.
- **`scripts/replay_thread.py`** replays a real thread one message at a time. The
  eval set asks "is this one answer right"; this asks whether the bot noticed
  what had already been said. It never sees the whole thread at once.
- **`--repeat`** runs the same case several times, because a case that passes
  three times out of five is a different finding from one that fails.

What the eval set measures first is not correctness. It is whether the model
admits it does not know.

Every case with `expects: gap` must carry a `verified_absent` field with the
concrete search that proves the answer really is missing from the corpus — a
rule that exists because three of the first five "gaps" turned out to have
answers, just in a file nobody had searched. Most of the model's early
"failures" were mistakes in the eval set, and the notes on each case record
which ones.

## The consistency tests

`tests/test_consistency.py` ties the code to the content, which is the part that
rots quietest:

- every channel in `ALLOWED_CHANNELS` also appears in the prompt,
- every `must_mention` word can actually be found in the corpus, so a case
  cannot demand a wording that does not exist,
- every `gap` case is still a gap — adding a note can silently turn a gap into
  an answer and start punishing the model for being right,
- the videos really reach the assembled prompt.

## Running it

```bash
python -m venv .venv
.venv/Scripts/activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # fill in one provider key, API_KEY, APP_PASSWORD
uvicorn fyndit_helper.api:app --reload --app-dir src
```

Then open <http://127.0.0.1:8000>. `/ask` needs `API_KEY`; without it the app
starts but answers 503 deliberately, so a public URL cannot spend the
provider's credit.

The tests need no key and no network:

```bash
pytest -q
```

Five providers are wired up (Mistral, Gemini, OpenAI, OpenRouter and an
OpenAI-compatible gateway); which one runs is a single line in `.env`.
`python scripts/list_models.py` prints the models a key actually has access to.

## About the data in this repository

**The documentation is real.** `data/docs/en/` holds 38 pages of Fyndit's own
public documentation, the same pages published at <https://www.fyndit.app/docs>
and the site's legal pages. The identifying details of the operator have been
removed from the legal pages; nothing else about them was changed, so the
grounding behaviour can be read against a corpus that really exists.

**The eval data comes from real support tickets and is anonymised.** Customer
handles, people's names and the dates that would point back at individual
tickets have been removed. `data/eval/cases.json` holds 47 cases with the notes
explaining why each one is in the set and what was got wrong about it;
`threads.json` holds 18 conversations for replay. The 14 notes in
`data/knowledge/notes/` are the second knowledge layer — things confirmed in
practice that the documentation does not say.

**No performance numbers are quoted here.** The eval needs a provider key, so
nothing in this README could be reproduced from the repository alone, and a
number you cannot check is worth nothing.

## Things worth knowing before reading the code

- **The scraper is not included.** The documentation pages are committed as
  markdown; the code that fetched them is left out of this repository.
- **Some strings are deliberately not in English.** `NÁVRH (SK)`,
  `NA ODOSLANIE`, `ZDROJ`, the gap marker `⚠️ Toto v docs nie je.` and the
  citation prefix `poznamky:` are protocol, not prose: the prompt and the checks
  are built on them, and translating them would change behaviour rather than
  wording. The same goes for the Slovak inside the prompt, which is addressed to
  the model. Everything else — code, comments, tests, script output — is
  English.
- **The proposal is always Slovak by design.** The helper reads Slovak; the
  customer's half is written in the customer's language and checked separately.

## Licence

None. That means all rights are reserved and this code is here to be read, not
reused.
