"""Flask entry point for the educational grammar checker."""
from pathlib import Path
from flask import Flask, jsonify, render_template, request

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
    return jsonify({
        "original_text": clean, "corrected_text": corrected,
        "sentence_count": len(sentences),
        "word_count": sum(1 for t in tokenize(clean, NLP) if any(ch.isalnum() for ch in t["text"])),
        "error_count": len(errors), "errors": errors, "pos_tags": flattened_tags,
        "sentences": sentences,
        "nlp_mode": "spaCy en_core_web_sm" if NLP is not None and "tagger" in NLP.pipe_names else "spaCy tokenizer + rule-based POS fallback"
    })


if __name__ == "__main__":
    app.run(debug=True)
