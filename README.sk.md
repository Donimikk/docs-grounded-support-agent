# docs-grounded-support-agent

Asistent podpory pre discordovú komunitu produktu, ktorý odpovedá **iba
z dokumentácie produktu** — a keď v nej odpoveď nie je, povie to nahlas.

Vznikol pre [Fyndit](https://www.fyndit.app), monitorovacieho bota na Vinted,
ktorého podpora beží v discordových ticketoch. Človek zostáva v slučke: nástroj
napíše návrh, helper si ho prečíta a rozhodne, čo sa odošle.

*English version: [README.md](README.md).*

---

## Čo rieši

Odpovede podpory sa písali z hlavy. Je to rýchle a dosť často to nesedí:
dokumentácia hovorí o dočasnom obmedzení asi na 24 hodín, človek pod tlakom
napíše „dostal si ban". Opačné zlyhanie je horšie — sebavedome vymyslená odpoveď
na otázku, ktorú dokumentácia nikdy nepokrývala.

Nástroj preto robí tri veci:

1. **Navrhne odpoveď striktne z korpusu.** Do promptu ide celá dokumentácia;
   nie je tu vyhľadávací krok, na ktorý by sa dalo zviezť pri netrafení.
2. **Medzeru označí namiesto toho, aby ju zaplnil.** Keď odpoveď v korpuse nie
   je, model to musí povedať a ticket posunúť ďalej, nie si domyslieť
   vierohodné áno či nie. To, že niečo v dokumentácii chýba, nie je dôkaz, že sa
   to nedá — táto chyba má v eval sade vlastný prípad.
3. **Skontroluje odpoveď skôr, než ju niekto odošle.** Deterministické kontroly
   chytia uniknutú internú značku, vymyslený kanál alebo odkaz na video,
   otázku vrátenú zákazníkovi a odpoveď v zlom jazyku.

Odpoveď má dve časti: slovenský **NÁVRH** pre helpera, ktorý nesie interné
poznámky aj značku medzery, a **NA ODOSLANIE** v jazyku zákazníka, kde nesmie
byť nič interné. Tretia sekcia, **ZDROJ**, cituje stránku alebo poznámku, z
ktorej odpoveď vyšla.

## Architektúra

HTTP vrstva je zámerne tenká, aby ten istý pipeline mohol neskôr volať aj
discordový bot bez toho, aby chodil cez ňu.

| Modul | Čo robí |
| --- | --- |
| `api.py` | FastAPI appka: `/ask`, `/health`, `/history`, stránka chránená heslom |
| `pipeline.py` | Dvojkrokový tok nad vláknom: najprv preklad, potom odpoveď |
| `prompt.py` | Skladá systémový prompt zo šablóny a načítaného korpusu |
| `docs.py` | Načíta stránky dokumentácie. Celé stránky, žiadne delenie, žiadne embeddingy |
| `knowledge.py` | Druhá vrstva: čo vieme z praxe, ale dokumentácia to nehovorí |
| `videos.py` | Tutoriálové videá — mapa „téma → odkaz", aby si model URL nevymyslel |
| `language.py` | Zisťuje jazyk zákazníka; radšej nevráti nič, než aby hádal |
| `checks.py` | Deterministické kontroly návrhu — prvá vrstva hodnotenia |
| `evaluation.py` | Porovná návrh s očakávaním — druhá vrstva |
| `llm.py`, `providers.py` | Jedna trieda na poskytovateľa za protokolom s jedinou metódou |
| `history.py` | Čo sa už odpovedalo, uložené ako JSON na disku |
| `prompt_store.py` | Obsahovo adresovaný sklad zložených promptov, aby sa skóre dalo dohľadať |
| `discord.py` | Premieňa discordové vlákno na správy, s ktorými pipeline pracuje |

Dve rozhodnutia stojí za to pomenovať, lebo práve na ne sa ľudia pýtajú:

- **Žiadna vektorová databáza.** Korpus sa celý zmestí do promptu. Vyhľadávacia
  vrstva by pridala súčasť, ktorá vie zlyhať potichu a dá sa na ňu zviezť každé
  netrafenie. Keď korpus prerastie kontextové okno, zmení sa to; dovtedy je to
  závislosť, ktorá nič nekupuje.
- **Žiadna pamäť medzi volaniami.** Celé vlákno sa posiela zakaždým. To, čo
  vyzerá ako pamätajúci si model, je znova poslaná história — pipeline to teda
  robí priznane, namiesto aby predstieral, že si niečo drží.

## Ako funguje meranie

Kvôli tejto časti existuje zvyšok repa.

- **`scripts/run_eval.py`** prežene eval sadu modelom a vypíše tabuľku. Každý
  beh uloží celé odpovede modelu, odtlačok zloženého promptu a odtlačok
  zdrojových súborov, ktoré nesú správanie — takže sa dva behy dajú porovnať a
  rozdiel priradiť.
- **`scripts/rescore.py`** prepočíta uložený beh podľa aktuálnych očakávaní,
  **bez toho, aby model volal znova**. Chybne označený prípad sa stáva
  častejšie než chybujúci model a nie je dôvod platiť za tie isté odpovede
  dvakrát.
- **`scripts/replay_thread.py`** prehrá skutočné vlákno po jednej správe. Eval
  sada sa pýta „je táto odpoveď správna"; toto sa pýta, či si bot všimol, čo už
  bolo povedané. Celé vlákno naraz nikdy nevidí.
- **`--repeat`** pustí ten istý prípad viackrát, lebo prípad, ktorý prejde tri
  razy z piatich, je iný nález než ten, ktorý padá vždy.

Eval sada nemeria v prvom rade správnosť. Meria, či model prizná, že nevie.

Každý prípad s `expects: gap` musí mať pole `verified_absent` s konkrétnym
hľadaním, ktoré dokazuje, že odpoveď v korpuse naozaj chýba — pravidlo vzniklo
preto, že tri z prvých piatich „medzier" odpoveď mali, len v súbore, ktorý nikto
neprehľadal. Väčšina raných „zlyhaní" modelu boli chyby v eval sade a poznámky
pri prípadoch hovoria, ktoré to boli.

## Testy konzistencie

`tests/test_consistency.py` viaže kód na obsah, čo je časť, ktorá hnije
najtichšie:

- každý kanál z `ALLOWED_CHANNELS` je aj v prompte,
- každé slovo z `must_mention` sa naozaj dá nájsť v korpuse, takže prípad
  nemôže žiadať formuláciu, ktorá neexistuje,
- každý `gap` prípad je stále medzerou — pridaná poznámka vie potichu spraviť
  z medzery odpoveď a začať trestať model za to, že má pravdu,
- videá sa naozaj dostanú do zloženého promptu.

## Ako to spustiť

```bash
python -m venv .venv
.venv/Scripts/activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # doplň kľúč jedného poskytovateľa, API_KEY, APP_PASSWORD
uvicorn fyndit_helper.api:app --reload --app-dir src
```

Potom otvor <http://127.0.0.1:8000>. `/ask` potrebuje `API_KEY`; bez neho appka
nabehne, ale zámerne vracia 503, aby verejná URL nemohla míňať kredit
u poskytovateľa.

Testy nepotrebujú kľúč ani sieť:

```bash
pytest -q
```

Zapojení sú piati poskytovatelia (Mistral, Gemini, OpenAI, OpenRouter a jedna
brána kompatibilná s OpenAI); ktorý beží, je jeden riadok v `.env`.
`python scripts/list_models.py` vypíše modely, ku ktorým kľúč naozaj má prístup.

## O dátach v tomto repe

**Dokumentácia je skutočná.** `data/docs/en/` obsahuje 38 stránok vlastnej
verejnej dokumentácie Fynditu — tie isté stránky, čo sú zverejnené na
<https://www.fyndit.app/docs>, plus právne stránky webu. Z právnych stránok sú
odstránené identifikačné údaje prevádzkovateľa; inak sa na nich nič nemenilo,
aby sa správanie dalo čítať oproti korpusu, ktorý naozaj existuje.

**Eval dáta pochádzajú zo skutočných ticketov a sú odosobnené.** Prezývky
zákazníkov, mená ľudí aj dátumy, ktoré by ukazovali späť na konkrétne tickety,
sú odstránené. `data/eval/cases.json` má 47 prípadov aj s poznámkami, prečo je
každý v sade a čo sa pri ňom pomýlilo; `threads.json` má 18 konverzácií na
prehrávanie. 14 poznámok v `data/knowledge/notes/` je druhá vrstva znalostí —
veci overené praxou, ktoré dokumentácia nehovorí.

**Nie sú tu žiadne čísla o výkone.** Eval potrebuje kľúč poskytovateľa, takže
nič z tohto README by sa nedalo zopakovať zo samotného repa — a číslo, ktoré si
nevieš overiť, nemá cenu.

## Čo sa oplatí vedieť pred čítaním kódu

- **Scraper tu nie je.** Stránky dokumentácie sú zacommitované ako markdown;
  kód, ktorý ich stiahol, v tomto repe nie je.
- **Niektoré reťazce zámerne nie sú po anglicky.** `NÁVRH (SK)`,
  `NA ODOSLANIE`, `ZDROJ`, značka medzery `⚠️ Toto v docs nie je.` a citačný
  prefix `poznamky:` nie sú text, ale protokol: stojí na nich prompt aj
  kontroly a preklad by zmenil správanie, nie formuláciu. To isté platí pre
  slovenčinu v prompte, ktorá je určená modelu. Všetko ostatné — kód, komentáre,
  testy, výpis skriptov — je po anglicky.
- **Návrh je po slovensky zámerne.** Helper číta po slovensky; zákazníkova
  polovica sa píše v jeho jazyku a kontroluje sa zvlášť.

## Licencia

Žiadna. To znamená, že všetky práva sú vyhradené a tento kód je tu na čítanie,
nie na použitie.
