# NLP-Based English Grammar Error Detection and Correction System

An explainable college-level NLP mini-project. The Flask application analyzes English text with spaCy preprocessing and a small, explicit rule engine. It demonstrates selected grammar patterns; it is not a comprehensive grammar checker.

## Problem statement and objective

Writers often miss common agreement, article, tense, and preposition errors. This project demonstrates how basic NLP analysis can support a grammar tool: segment text into sentences, tokenize it, assign part-of-speech and morphology information, apply readable patterns, explain findings, and make targeted corrections.

## Features

- Flask web interface with asynchronous `POST /check` requests.
- Sentence segmentation, tokenization, POS tags, lemmas, and morphology fields.
- Eight controlled rule families: subject–verb and pronoun/verb agreement, `I` agreement, articles, number agreement, selected past tense, selected prepositions, and a supported double-negative pattern.
- Explanations, correction suggestions, counts, and token analysis.
- Position-based correction so repeated words elsewhere are not changed accidentally.
- Small CSV of educational examples for demonstration and evaluation.
- No paid service, external API, or LLM.

## Technologies and NLP techniques

Python, Flask, spaCy, HTML, CSS, and vanilla JavaScript. spaCy supplies sentence boundaries, tokenization, POS labels, lemmas, and morphological features when `en_core_web_sm` is installed. `Number`, `Person`, `Tense`, and verb-form features may appear in each token's `morphology` field depending on the model and token. The rule engine is deliberately written as readable regular-expression patterns over text spans, supported by NLP preprocessing; it does not claim that the rules are learned from the CSV.

If the model is unavailable, the app still starts using spaCy's blank English tokenizer/sentencizer and a very small POS fallback. That fallback is less accurate and is identified in the response/UI. Download the trained model for the intended POS and morphology demonstration.

## System architecture

```text
Browser → Flask /check → whitespace normalization → sentence segmentation
        → spaCy tokenization / POS / lemma / morphology
        → controlled grammar rules → classified findings with spans
        → right-to-left span correction → JSON → results tables
```

## Project structure

```text
nlp-grammar-checker/
├── app.py
├── requirements.txt
├── nlp/
│   ├── preprocessing.py
│   ├── tokenizer.py
│   ├── pos_tagger.py
│   ├── grammar_rules.py
│   ├── error_detector.py
│   └── correction.py
├── dataset/grammar_dataset.csv
├── templates/index.html
├── static/style.css
├── static/script.js
└── README.md
```

## Installation and run

From this project directory:

```bash
python -m venv venv
# macOS / Linux
source venv/bin/activate
# Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python app.py
```

Open <http://127.0.0.1:5000>. If you skip the model download, the app starts in fallback mode. The Flask development server is for local student demonstrations.

## Example

Input: `She go to college every day.`

Expected correction: `She goes to college every day.` The output has one sentence, six words, and one Subject-Verb Agreement finding. The POS table shows token, POS, lemma, and morphology for each token.

Other examples:

| Input | Selected correction |
|---|---|
| `He is an good student.` | `He is a good student.` |
| `Yesterday I go home.` | `Yesterday I went home.` |
| `These book are interesting.` | `These books are interesting.` |
| `I don't know nothing.` | `I don't know anything.` |

## Grammar rules implemented

1. Present-simple agreement for a controlled verb list (`go`, `play`, `have`, `do`, `like`) and personal pronouns, including `I`.
2. `a`/`an` selection using common written vowel starts and a few silent-h examples (`honest`, `hour`, `heir`). It does not model pronunciation reliably for all words.
3. Singular/plural matching for a small demonstrative and noun list.
4. `go`/`goes` after selected past-time expressions becomes `went`.
5. Three fixed preposition patterns: `good in` → `good at`, `interested on` → `interested in`, and `depend of` → `depend on`.
6. A possible double-negative pattern for “(do/does/did) not know nothing”. It is a pattern warning, not semantic interpretation.

## Dataset and evaluation

`dataset/grammar_dataset.csv` is a small set of hand-written examples, not a comprehensive English grammar corpus. The current rule engine does not train on the CSV. The intended controlled evaluation includes at least these 15 cases: `She go to college.`, `He go to school.`, `They plays football.`, `I goes to college.`, `He have a book.`, `These book are interesting.`, `Yesterday I go to college.`, `He is an good student.`, `She is a honest girl.`, `I don't know nothing.`, `She goes to college every day.`, `They play football.`, `He has a book.`, `I went to college yesterday.`, and `She go. She go.` (the final case checks two repeated occurrences and sentence offsets).

For a reproducible controlled metric, label the 15 examples above as expected-error or expected-clean, and compare each predicted error span and corrected sentence with the expected labels/corrections. Precision = true positives / (true positives + false positives); recall = true positives / (true positives + false negatives); F1 = 2 × precision × recall / (precision + recall). Count a detection as correct only when its error type/span is expected; count a correction as correct only when the resulting sentence exactly matches the expected sentence. Report false positives as flagged errors in expected-clean examples. These hand-selected examples exercise the supported rules and do not estimate performance on general English.

## How the System Works (viva explanation)

1. **Input:** the browser sends the text to Flask as JSON.
2. **Sentence segmentation:** preprocessing separates sentence units so rule findings keep a sentence index.
3. **Tokenization:** spaCy splits words and punctuation while preserving token positions.
4. **POS tagging:** spaCy labels each token (such as `PRON`, `VERB`, `NOUN`). This helps inspect the grammatical role of words.
5. **Morphological analysis:** spaCy's model can expose features such as number, person, tense, and verb form; the app presents them for analysis. The simple rules only use a controlled subset of English forms.
6. **Grammar rule matching:** independent, readable rule functions search for supported patterns.
7. **Error detection and classification:** findings include the original span, replacement, category, explanation, and position.
8. **Correction:** exact spans are replaced from right to left, preventing earlier edits from shifting later positions.
9. **Output:** Flask returns JSON; JavaScript displays counts, corrected text, errors, and POS details without reloading.

Segmentation organizes the input; tokenization identifies units; POS and morphology expose linguistic information; rules find known patterns; classification makes results understandable; positioned correction changes only the intended text.

## Limitations

- The rule list and controlled vocabulary are intentionally small. Many valid or incorrect constructions are not recognized.
- Article choice is based on a few spelling patterns, not a pronunciation dictionary.
- The tense rule only handles selected `go` forms and past-time cues; it does not infer general tense or context.
- The fallback POS labels and morphology are approximate. Install `en_core_web_sm` for model-based analysis.
- The double-negative rule is a supported surface pattern and can miss context or dialect variation.
- There is no spelling checker, semantic model, or learned correction system.

## Future scope

Possible extensions include ML-based grammatical error detection, transformer correction, context-aware suggestions, stronger semantic analysis, broader grammar rules, additional languages, spell checking, highlighted edits, personalized writing suggestions, word-processor integration, and larger annotated datasets. These features are not implemented here.
