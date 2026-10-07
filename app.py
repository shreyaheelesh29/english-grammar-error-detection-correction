"""Flask entry point for the educational grammar checker."""
from pathlib import Path
from flask import Flask, jsonify, render_template, request
import sqlite3
from datetime import datetime, timezone

from nlp.preprocessing import preprocess_text, split_sentences
from nlp.tokenizer import tokenize
from nlp.pos_tagger import get_pos_tags
from nlp.error_detector import detect_errors
from nlp.correction import generate_correction

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent


def load_nlp():
    """Prefer the trained spaCy English pipeline; continue with transparent fallback if absent."""
    try:
        import spacy
        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            # Keep local demos usable before downloading the model. This pipeline tokenizes and segments;
            # POS output then uses the simple documented fallback in pos_tagger.py.
            nlp = spacy.blank("en")
            nlp.add_pipe("sentencizer")
            return nlp
    except ImportError:
        return None


NLP = load_nlp()
MAX_TEXT_CHARS = 20000
DB_PATH = ROOT / "data" / "history.sqlite3"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS analyses (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, original TEXT NOT NULL, corrected TEXT NOT NULL, score INTEGER NOT NULL, error_count INTEGER NOT NULL)")


init_db()


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/check")
def check():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
        return jsonify({"error": "Send a JSON object with a text string."}), 400
    clean = preprocess_text(payload["text"])
    if not clean:
        return jsonify({"error": "Please enter some text to check."}), 400
    if len(clean) > MAX_TEXT_CHARS:
        return jsonify({"error": f"Text is too long. The limit is {MAX_TEXT_CHARS:,} characters."}), 413

    sentences = split_sentences(clean, NLP)
    tags_by_sentence = [get_pos_tags(sentence, NLP) for sentence in sentences]
    errors = detect_errors(sentences, tags_by_sentence)
    # Rule offsets are sentence-local; convert them to positions in the complete normalized input.
    cursor = 0
    for i, sentence in enumerate(sentences):
        offset = clean.find(sentence, cursor)
        if offset < 0:
            offset = cursor
        cursor = offset + len(sentence)
        for error in errors:
            if error["sentence_index"] == i:
                error["start"] += offset
                error["end"] += offset
    corrected = generate_correction(clean, errors)["corrected_text"]

    flattened_tags = []
    for sentence_index, tags in enumerate(tags_by_sentence):
        for tag in tags:
            flattened_tags.append({**tag, "sentence_index": sentence_index})
    # Keep API fields readable for students; internal offsets support precise correction.
    from nlp.ngram_model import get_model
    from nlp.analysis import document_stats, grammar_score, resolve_references
    from nlp.sentence_structure import analyze_structure
    from nlp.rewriter import generate_rewrites
    score = grammar_score(len(clean), len(sentences), errors)
    stats = document_stats(clean, flattened_tags)
    model = get_model()
    ngrams = model.score_text(clean)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO analyses(created_at, original, corrected, score, error_count) VALUES (?, ?, ?, ?, ?)",
                   (datetime.now(timezone.utc).isoformat(), clean, corrected, score, len(errors)))
    goal = payload.get("goal", "general")
    if goal not in {"general", "academic", "business", "casual"}:
        goal = "general"
    return jsonify({
        "original_text": clean, "corrected_text": corrected,
        "sentence_count": len(sentences),
        "word_count": sum(1 for t in tokenize(clean, NLP) if any(ch.isalnum() for ch in t["text"])),
        "error_count": len(errors), "errors": errors, "pos_tags": flattened_tags,
        "sentences": sentences,
        "grammar_score": score,
        "score_label": "Very Good" if score >= 90 else "Good" if score >= 80 else "Needs Improvement" if score >= 65 else "Major Corrections Needed",
        "stats": stats,
        "ngram": ngrams,
        "references": resolve_references(clean),
        "pos_distribution": stats["pos_distribution"],
        "structure_issues": analyze_structure(sentences),
        "writing_alternatives": generate_rewrites(clean, goal),
        "nlp_mode": "spaCy en_core_web_sm" if NLP is not None and "tagger" in NLP.pipe_names else "spaCy tokenizer + rule-based POS fallback"
    })


@app.get("/api/history")
def history():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT 30").fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/parse")
def parse_sentence():
    from nlp.cyk_parser import parse
    payload = request.get_json(silent=True) or {}
    text = preprocess_text(payload.get("text", ""))
    if not text:
        return jsonify({"error": "Enter a sentence to parse."}), 400
    return jsonify(parse(text, NLP))


@app.post("/api/semantics")
def semantics():
    from nlp.semantics import analyze_words
    payload = request.get_json(silent=True) or {}
    return jsonify(analyze_words(payload.get("text", "")))


if __name__ == "__main__":
    app.run(debug=True)
