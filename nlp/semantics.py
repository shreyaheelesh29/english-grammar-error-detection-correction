"""Optional WordNet lexical semantics, with a single actionable unavailable state."""
import re

INSTALL_COMMAND = "python -m nltk.downloader wordnet omw-1.4"
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "before", "being", "but", "by",
    "could", "did", "do", "does", "for", "from", "had", "has", "have", "he", "her", "hers",
    "him", "his", "i", "if", "in", "into", "is", "it", "its", "me", "my", "of", "on", "or",
    "our", "ours", "she", "that", "the", "their", "them", "there", "these", "they", "this", "those",
    "to", "us", "was", "we", "were", "will", "with", "you", "your", "after", "afterward", "again", "about", "also", "although", "always", "among",
    "before", "being", "every", "having", "just", "more",
    "other", "over", "some", "such", "than", "through", "under", "very", "went", "what", "when", "where",
    "which", "while", "would", "then", "ours", "ourselves",
}


def _sense_data(syn):
    return {
        "definition": syn.definition(),
        "synonyms": sorted({lemma.name().replace("_", " ") for lemma in syn.lemmas()}),
        "antonyms": sorted({ant.name().replace("_", " ") for lemma in syn.lemmas() for ant in lemma.antonyms()}),
        "hypernyms": sorted({name.replace("_", " ") for parent in syn.hypernyms() for name in parent.lemma_names()}),
        "hyponyms": sorted({name.replace("_", " ") for child in syn.hyponyms() for name in child.lemma_names()}),
    }


def analyze_words(text):
    if not isinstance(text, str) or not text.strip():
        return {"available": True, "words": [], "note": "Enter text containing a word to look up."}

    try:
        from nltk.corpus import wordnet as wn
        # Force lazy corpus loading here so a missing installation is detected once.
        wn.ensure_loaded()
    except (ImportError, LookupError):
        return {
            "available": False,
            "words": [],
            "note": "WordNet data is not installed, so lexical relations cannot be shown yet.",
            "install_command": INSTALL_COMMAND,
        }

    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text)
    words = []
    seen = set()
    for word in tokens:
        key = word.lower()
        if key in seen or key in STOPWORDS:
            continue
        seen.add(key)
        synsets = wn.synsets(key)[:2]
        words.append({"word": word, "senses": [_sense_data(syn) for syn in synsets]})
        if len(words) >= 8:
            break

    return {
        "available": True,
        "words": words,
        "note": "WordNet provides dictionary senses and lexical relations; senses are listed, not disambiguated from context.",
    }
