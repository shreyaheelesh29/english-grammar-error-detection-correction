# English Grammar Error Detection and Correction Using Local LanguageTool

A local Flask and Streamlit NLP application. Both interfaces use a shared local LanguageTool engine for broad grammar, spelling, and style checks without sending writing to a public API. The app retains a small pattern-based fallback for offline or first-run setup failures, plus POS analysis, n-gram scoring, a limited CYK parser, optional WordNet lookup, and reference resolution. The fallback is labeled as limited; it is not equivalent to the primary engine.

[![Open the Streamlit app](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://english-grammar-error-detection-correction-hy5txg9vzpf4xrdkqkv.streamlit.app/)

## Implemented

- Flask interface with responsive dashboard, sample input, grammar score, error explanations, POS table, n-gram results, reference links, and parse view.
- Streamlit interface in `streamlit_app.py` using the same shared grammar engine, with corrections, POS tags, language insights, a CYK parser demonstration, and optional WordNet lookup.
- Reusable tokenization, sentence segmentation, POS tagging and fallback, lemmatization where spaCy model exists, and morphology output.
- Local LanguageTool checks grammar, spelling, punctuation, and style, and returns replacement spans and explanations. A singleton local Java server is reused for checks. The first check may download the engine; subsequent checks run locally.
- If LanguageTool cannot start, the app falls back to the project's small explicit rule set. The UI identifies which engine handled each check so fallback output is not mistaken for broad grammar coverage.
- Sentence-structure checks flag likely dependent-clause fragments and comma splices for review. They use conservative surface patterns and do not automatically rewrite clauses.
- Optional style rewrites suggest alternate transitions for the phrase “and after that” and a small set of nearby constructions. They are explicitly separated from grammar corrections and must be applied by the user.
- Structured findings include character offsets, original/corrected span, category, explanation, and qualitative `rule_match_strength` (`strong`/`moderate`). It is not a calibrated probability.
- Laplace-smoothed unigram, bigram and trigram models, unknown-token mapping, sentence probability and perplexity. The supplied demo CSV is the tiny training source by default; its scores are demonstration-only. Low likelihood is not itself a grammar error.
- CYK parser with a small CFG: `S → NP VP`, `NP → DET N | PRON`, `VP → V NP | V PP`, `PP → P NP`. Rejection means outside this grammar, not ungrammatical English.
- WordNet 3.0 lexical relations through NLTK. The corpus and its license are bundled under `nltk_data/`, so the Streamlit deployment has offline lookup data available.
- SQLite analysis history, limited to recent 30 entries in the history API.
- Aligned-corpus preprocessing script groups identical normalized source sentences before a deterministic 80/10/10 split. Evaluation script reports metrics computed on the input CSV; no corpus-level scores are claimed here.
- 49 curated demonstration pairs in `dataset/grammar_dataset.csv`. These are examples, not a large-scale GEC corpus and not training evidence for grammar rules.

## Install and run

Python 3.10+ and Java 17+ are recommended. The first LanguageTool check needs internet access to download the local engine; the submitted writing is then checked by the local Java process. Streamlit Community Cloud installs Java 21 from `packages.txt`. From this directory:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python run.py
```

Open <http://127.0.0.1:5000>. `python app.py` also starts the Flask development server. The LanguageTool wrapper launches and reuses a local Java server. Without `en_core_web_sm`, tokenization and sentence segmentation use spaCy blank English, with a small rule-based POS fallback; POS and morphology quality is reduced. If Java or the local LanguageTool download is unavailable, the app reports that it is using limited pattern checks.

### Run the Streamlit interface

With the same virtual environment and dependencies installed, run:

```bash
streamlit run streamlit_app.py
```

### Deploy to Streamlit Community Cloud

Push this repository to a GitHub repository you administer, then create an app at <https://share.streamlit.io/> using the repository, branch, and `streamlit_app.py` as the entrypoint. The repository root `requirements.txt` contains the app dependencies. Community Cloud deploys the app to a public `streamlit.app` URL by default; set access controls in the app settings if needed.

WordNet 3.0 is bundled under `nltk_data/corpora/wordnet.zip`, with its license alongside the archive. The apps add this repository data directory to NLTK automatically. If you run the analysis modules outside this project checkout, install the corpus in that environment with:

```bash
python -m nltk.downloader wordnet omw-1.4
```

## Dataset setup and preprocessing

The included examples do not satisfy the scale or provenance of an academic corpus. Obtain BEA-2019/W&amp;I+LOCNESS, NUCLE, FCE, JFLEG, or another corpus only through its official access and licensing terms. The project does not bundle or automatically download restricted corpora. Export aligned examples as UTF-8 CSV with `incorrect,correct` columns; `source,target` are also accepted.

```bash
python training/preprocess_dataset.py path/to/aligned.csv --out data
```

This writes `data/train/pairs.jsonl`, `data/validation/pairs.jsonl`, `data/test/pairs.jsonl`, and `data/statistics.json`. Normalized identical source strings are grouped before splitting to reduce exact-duplicate leakage. Near-duplicate semantic detection is not implemented. Raw corpora should be kept under `data/raw/` only when their license permits.

The project structure keeps corpus staging separate:

```text
data/raw/ data/processed/ data/train/ data/validation/ data/test/
```

`language-tool-python` is GPL-3.0-only; review its terms before distributing a packaged copy. The LanguageTool core is LGPL-2.1-or-later. The local engine download is cached in the ignored `data/language_tool/` directory. If it cannot download or start, the app labels the result as a limited fallback instead of presenting it as a full grammar check.

## Evaluate / inspect model counts

```bash
python training/evaluate.py dataset/grammar_dataset.csv
python training/train_ngram.py
```

Evaluation uses detection presence and exact corrected-sentence match against aligned CSV examples. It prints precision, recall, F1 and exact match from the supplied data. Run it on a held-out corpus split for meaningful results. There are no baseline/hybrid corpus results in the repository because no large licensed corpus has been supplied. The n-gram counts are currently built in memory from the demo pairs at app startup and reused for the process lifetime.

## API

- `POST /check` with `{"text":"She go to college."}`: findings, corrected text, statistics, score, POS, n-grams and reference heuristic.
- `POST /api/parse` with `{"text":"She reads the book."}`: grammar, CYK chart and parse tree if accepted.
- `POST /api/semantics` with `{"text":"car"}`: WordNet senses/relations when data is installed.
- `GET /api/history`: latest 30 saved analyses.

Input is limited to 20,000 characters. This version does not accept uploaded documents. The filesystem-backed SQLite history is created at `data/history.sqlite3`.

## Viva notes: NLP concepts

- **Tokenization and segmentation:** identify word/punctuation units and sentence boundaries before local rules operate. Character offsets connect findings to source text.
- **POS and morphology:** labels such as PRON, VERB and NOUN describe grammatical roles. A trained spaCy pipeline supplies statistical tags and features; the fallback uses small lexical/suffix heuristics. Inflection features help explain agreement, but the current rules are deliberately narrower than the full feature set.
- **Rule-based analysis:** explicit patterns detect a known construction, attach its span and explanation, then corrections are applied from right to left so earlier offsets stay valid.
- **HMM:** spaCy's trained tagger is a statistical sequence tagger; this code does not separately implement/train an HMM. An independent educational HMM tagger is future work, rather than a claim about spaCy internals.
- **N-grams:** unigram/bigram/trigram likelihoods estimate token sequence likelihood. Laplace add-one smoothing assigns nonzero mass to unseen events; `<UNK>` maps out-of-vocabulary words. Perplexity is the inverse geometric mean likelihood and indicates surprise under this small model, not grammaticality.
- **Syntax and CYK:** a CFG defines productions; CYK is a bottom-up dynamic program for CNF-style binary productions. The chart and one backpointer-derived tree are exposed for the project's limited lexicon. General English parsing is out of scope.
- **Semantics and Lesk:** WordNet endpoint demonstrates lexical definitions and relations. Context-based Lesk word-sense disambiguation is not implemented yet; WordNet senses are listed, not selected using Lesk.
- **Reference analysis:** a nearest preceding capitalized name heuristic links selected pronouns; it does not enforce robust gender/number/person constraints and is not full coreference resolution.
- **Hybrid approach:** deterministic rules explain findings; POS/morphology and n-gram values support inspection. A model is not asked to make opaque corrections, preserving local operation and explainability.

## Limitations and future scope

The current rules and vocabulary are small and can produce misses or false positives; the score is a length-normalized weighted rule penalty, not a validated proficiency measure. The n-gram model uses demo data unless adapted to an authorized corpus. Uploads, a true trained HMM module, Lesk WSD, broad error rules, baselines, calibrated confidence, document-level export, charts, and near-duplicate detection are not implemented. Possible extensions: neural GEC, transformer correction, multilingual/Indian language support, speech/OCR input, browser extension, personalized tutor, domain models, richer semantics, and discourse/coreference models.
