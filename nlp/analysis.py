"""Document-level summaries and deliberately simple reference resolution."""
import re
from collections import Counter


def grammar_score(text_length, sentence_count, errors):
    # Normalize by estimated document words to avoid unbounded penalties.
    words = max(1, round(text_length / 5.5))
    weights = {"Subject-Verb Agreement": 3.0, "Tense Error": 2.5, "Article Error": 1.5,
               "Number Agreement": 2.0, "Possible Double Negative": 2.5}
    penalty = sum(weights.get(e.get("error_type"), 1.5) for e in errors)
    return max(0, min(100, round(100 - 100 * penalty / (words + 20))))


def document_stats(text, tags):
    words = re.findall(r"\b[\w']+\b", text)
    return {"token_count": len(tags), "vocabulary_size": len({w.lower() for w in words}),
            "average_sentence_length": round(len(words) / max(1, len(re.findall(r"[.!?]+", text)) or 1), 2),
            "pos_distribution": dict(Counter(t.get("pos", "X") for t in tags)),
            "top_words": Counter(w.lower() for w in words).most_common(10)}


def resolve_references(text):
    """Nearest compatible explicit name/pronoun match; educational heuristic only."""
    tokens = re.findall(r"\b[A-Z][a-z]+\b|\b(?:he|she|they|him|her|them)\b", text)
    names = []
    links = []
    for token in tokens:
        if token[0].isupper() and token.lower() not in {"I".lower()}:
            names.append(token)
        elif token.lower() in {"he", "him", "she", "her", "they", "them"} and names:
            links.append({"pronoun": token, "antecedent": names[-1], "method": "nearest preceding named entity (heuristic)"})
    return {"links": links, "note": "Simplified educational heuristic; no full discourse or coreference model is used."}
