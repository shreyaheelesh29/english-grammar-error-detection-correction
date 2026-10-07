# Project Guide and Viva Preparation

## 1. What the project does

This is an English grammar error detection and correction **educational prototype**. A user enters English text. The app checks it with a local LanguageTool engine when that engine is available, shows suggested edits and explanations, and offers separate tabs for linguistic analysis. It has two interfaces: a public Streamlit app and a Flask web app/API.

The project is a hybrid system: a broad, prebuilt grammar checker is the primary checker; explicit local rules provide a limited fallback; smaller NLP demonstrations show how text can be analyzed in other ways. It does not train a large grammar-correction model, and it should not be presented as an automatic expert editor.

## 2. End-to-end processing

For a normal Streamlit check, the path is:

1. `streamlit_app.py` reads the submitted text, rejects empty or over-20,000-character input, and calls `analyze_text`.
2. `nlp/preprocessing.py` normalizes curly quotes and whitespace, then splits the text into sentences using spaCy boundaries where possible and a punctuation-based fallback otherwise.
3. `nlp/tokenizer.py` and `nlp/pos_tagger.py` provide tokens and POS information. A trained spaCy English model is used only if installed. Otherwise the app uses spaCy's blank English tokenizer plus simple word-list and suffix heuristics for POS tags.
4. `nlp/checking.py` calls `nlp/language_engine.py`. The primary path starts/reuses a local Java LanguageTool process, checks the complete document, and converts the engine matches into the project's finding format. If the engine is unavailable or fails, it calls `nlp/error_detector.py` and the explicit patterns in `nlp/grammar_rules.py`.
5. Findings carry character offsets and suggested replacement text. `nlp/correction.py` applies replacements from the end of the text toward the beginning so earlier offsets remain valid.
6. The app calculates a grammar score and document statistics, and builds POS summaries, n-gram scores, reference guesses, sentence-structure warnings, and optional style alternatives.
7. The UI shows the corrected text and findings. Separate tabs run the POS, document-insight, parser, and WordNet views.

The Flask interface follows the same shared checker through `app.py` and the same `nlp` modules. It also exposes JSON endpoints and stores Flask analyses in SQLite. The Streamlit app does not use that SQLite history.

## 3. Code map

| File | Responsibility |
|---|---|
| `streamlit_app.py` | Streamlit interface, input handling, result metrics, and analysis tabs. |
| `app.py` | Flask pages, `/check` endpoint, analysis history, parser endpoint, and WordNet endpoint. |
| `run.py` | Starts the Flask development app with debug mode off. |
| `nlp/preprocessing.py` | Quote/whitespace normalization and sentence splitting. |
| `nlp/tokenizer.py` | spaCy or regular-expression tokenization with character positions. |
| `nlp/pos_tagger.py` | spaCy POS/morphology output or a small heuristic fallback. |
| `nlp/language_engine.py` | Local LanguageTool lifecycle, match normalization, and fallback status. |
| `nlp/checking.py` | Shared document-level orchestration and sentence-index assignment. |
| `nlp/grammar_rules.py`, `nlp/error_detector.py` | Transparent hand-written fallback patterns and finding collection. |
| `nlp/correction.py` | Applies character-span corrections from right to left. |
| `nlp/analysis.py` | Length-normalized score, document statistics, and simple reference heuristic. |
| `nlp/ngram_model.py` | Unigram, bigram, and trigram counts and sequence scoring. |
| `nlp/sentence_structure.py` | Conservative dependent-clause and comma-splice warnings. |
| `nlp/cyk_parser.py` | CYK chart and one parse tree for a deliberately small grammar and lexicon. |
| `nlp/semantics.py` | NLTK WordNet senses and lexical relations. |
| `nlp/rewriter.py` | A few opt-in phrase-based style alternatives. |
| `training/preprocess_dataset.py` | Creates deterministic 80/10/10 JSONL splits from aligned CSV data, grouping identical normalized source texts first. |
| `training/evaluate.py` | Measures the fallback rule detector/corrector on an aligned CSV. |
| `training/train_ngram.py` | Instantiates the built-in demo n-gram model and prints its counts; it does not train a grammar correction model or serialize a new model. |
| `tests/test_project.py` | Unit tests for representative grammar rules, offsets, validation, correction, and parser behavior. |

## 4. Algorithms and concepts used

### Primary grammar engine

`language-tool-python` starts LanguageTool 6.7 locally on Java. LanguageTool compares the input against its installed language rules and returns candidate spans, messages, categories, and replacements. The project selects a replacement, normalizes the match fields, and preserves offsets into the original document. Text is not sent to a public grammar API by this implementation. The first use may need to download the LanguageTool files; after that the local process is reused.

### Rule-based fallback

The fallback applies explicit regular-expression patterns for a modest set of constructions such as common subject–verb agreement, tense, article, number, pronoun, and word-form errors. Some rules also use POS/dependency information if a trained spaCy parser is present. These rules are understandable and quick, but their vocabulary and grammar coverage are limited. The UI reports which engine was used.

### Tokenization, sentence segmentation, and POS

spaCy supplies token boundaries, offsets, sentence boundaries, POS tags, lemmas, morphology, and dependency links when a trained model is installed. The deployed app currently reports `spaCy tokenizer + rule-based POS fallback`, which means its English statistical parser/tagger is not installed there. In that mode, a small set of lexical lists and suffix checks guesses coarse POS categories; those guesses are useful for a demonstration, not robust linguistic annotation.

### Character offsets and correction

Each match identifies a start and end character position. The correction module sorts findings by descending start offset and replaces text from right to left. This prevents a later edit from shifting the offsets of an earlier edit. Overlapping LanguageTool findings are filtered to one deterministic non-overlapping suggestion; the rules fallback has its own rule-level behavior.

### Grammar score

The score starts at 100 and subtracts weighted penalties for reported findings. Penalties are divided by an estimated word count derived from text length, then the result is rounded and clamped to 0–100. It is a project-specific display metric, not a validated proficiency score or probability that the writing is correct.

### N-gram language model

`nlp/ngram_model.py` counts unigrams, bigrams, and trigrams, including start/end markers. It computes sequence likelihoods and perplexity with add-one (Laplace) smoothing; unseen tokens map to `<UNK>`. Its default data is the small curated examples CSV. The score indicates how familiar a sequence is to that tiny sample, not whether a sentence is grammatical. This model does not make the grammar corrections.

### CYK parser

The parser uses the small context-free grammar `S → NP VP`, `NP → DET N | PRON`, `VP → V NP | V PP`, and `PP → P NP`, plus a short fixed lexicon. CYK fills a triangular chart bottom-up: first assign lexical categories to words, then combine adjacent spans using grammar productions, retaining backpointers to build a parse tree. For a fixed grammar, the dynamic program takes cubic time in sentence length (with a production-dependent factor). A rejection means only that the sentence is outside this demo grammar; it does not mean the English sentence is incorrect.

### WordNet and reference analysis

The WordNet tab uses the bundled NLTK WordNet corpus to list up to two senses per selected word plus synonyms, antonyms, hypernyms, and hyponyms. It lists senses without resolving which meaning fits the surrounding sentence. Reference analysis is a nearest-prior-capitalized-name heuristic, not a full named-entity or coreference model.

### Dataset utilities and evaluation

The preprocessing script accepts aligned `incorrect,correct` (or `source,target`) CSV data, normalizes source text for grouping, then deterministically divides groups into 80% train, 10% validation, and 10% test splits. This reduces exact-source leakage; it does not detect semantic near-duplicates. The runtime's grammar rules are hand-written and do not train from those split files.

The current evaluation run on `dataset/grammar_dataset.csv` has 49 curated examples and reported precision **1.00**, recall **0.694**, F1 **0.819**, and exact-match correction **0.551**. `training/evaluate.py` measures the **fallback rules** on this supplied demo CSV, not the live LanguageTool engine, and the same examples are not a large independent held-out corpus. These figures are a small code-path check, not evidence of production accuracy or generalization.

## 5. Technology stack

- **Python**: application and NLP logic.
- **Streamlit**: public interactive demo interface.
- **Flask**: local web interface and JSON API.
- **LanguageTool 6.7 + `language-tool-python`**: primary local grammar/spelling/style rules.
- **Java 21**: runtime needed for the hosted LanguageTool engine.
- **spaCy**: tokenization and optional statistical English NLP model; the public deployment currently uses a tokenizer and heuristic POS fallback.
- **NLTK + WordNet 3.0**: dictionary senses and lexical relations.
- **SQLite**: persistent analysis history for the Flask application.
- **HTML, CSS, JavaScript**: Flask frontend.
- **Git/GitHub and Streamlit Community Cloud**: source hosting and public Streamlit deployment.

## 6. Who might use it, and why?

- **Students learning English** can paste a short passage, inspect suggested fixes, and read the explanation attached to a finding.
- **Teachers and tutors** can use it to demonstrate how agreement, tense, punctuation, POS labels, or simple syntax rules are represented in software.
- **NLP/computer-science students** can explore a transparent pipeline, inspect match offsets, compare a pretrained rules engine with explicit fallback rules, and view n-gram/CYK/WordNet examples.
- **Writers preparing short drafts** can use the LanguageTool pass as an extra proofreading aid, then review each suggestion themselves.

The value is immediate feedback plus inspectable explanations and small algorithm demonstrations in one app. It is a supplement to learning and proofreading, not a replacement for a teacher, editor, or authoritative language review.

## 7. Advantages

- The primary grammar check runs locally instead of transmitting submitted text to a public grammar API.
- Users can see the original span, suggested replacement, and explanation rather than receiving only a rewritten paragraph.
- The LanguageTool engine and fallback status are exposed, so a limited fallback is not silently presented as the main engine.
- The system combines practical grammar checking with inspectable educational examples of tokenization, POS tagging, n-grams, parsing, and lexical lookup.
- The fallback, input limit, corpus processing, and interface are small enough to run locally and explain in a student project presentation.

## 8. Limitations and risks to explain in a presentation

- **Not perfect:** grammar tools can miss errors and suggest changes that do not match a writer's intended meaning. Review every correction.
- **Fallback coverage is narrow:** if Java/LanguageTool cannot start, only the explicitly coded patterns run.
- **Reduced deployed POS quality:** the hosted app currently uses spaCy tokenization and heuristic POS tags rather than the trained `en_core_web_sm` model.
- **Small demonstration dataset:** 49 curated examples are not a representative learner corpus; measured results are not corpus-level or independent generalization results.
- **N-grams are not a grammar judge:** the tiny demo sample makes likelihood and perplexity illustrative only.
- **Parser coverage is tiny:** CYK accepts only strings supported by its short lexicon and grammar.
- **WordNet does not disambiguate context:** senses are listed, not selected with Lesk or another word-sense algorithm.
- **Reference links are simplistic:** capitalization and nearest-prior-name rules can produce incorrect antecedents.
- **Structure and style features are heuristic:** fragment/comma-splice checks and phrase rewrites cover limited patterns and may need human review.
- **No document upload or batch processing:** input is plain text with a 20,000-character limit.
- **History differs by interface:** Flask stores recent checks in local SQLite; Streamlit does not expose that persistent history.
- **Hosting constraints:** the public app can sleep on the free service, so allow time for a cold start. The first grammar check may also need to download LanguageTool.
- **Legal review:** check component licenses before redistributing a packaged copy, particularly `language-tool-python` (GPL-3.0-only) and bundled WordNet data.

## 9. Suggested live demonstration

1. Open the public Streamlit link in the repository README.
2. Use the prefilled example or enter `She go to college every day. They was happy.` and click **Check grammar**. Point out the corrected text, findings, and the displayed engine name.
3. Open **POS tags** and **Language insights** to show token labels and the summary/chart.
4. In **Syntax parser**, enter `She reads the book.` and submit it. Explain that acceptance is relative to the toy CFG.
5. In **WordNet**, enter `car` and submit it to show a dictionary definition and lexical relations.
6. State that the first grammar check after the hosted app wakes can be slower, and be ready to explain the fallback and data-set limits.

## 10. Short presentation summary

> “This project is a hybrid English grammar-checking and NLP teaching demo. It uses a local LanguageTool engine for its main grammar suggestions, with a transparent rule-based fallback. It also demonstrates POS tagging, simple document statistics, a smoothed n-gram model, CYK parsing with a small CFG, and WordNet lookup. Its key strength is inspectable feedback and locally processed text; its key limitation is narrow model and dataset coverage, so suggestions and educational submodules need human interpretation.”

