"""POS and morphology features from spaCy, with a modest fallback for demos."""
import re
from .tokenizer import tokenize

PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "this", "that", "these", "those"}
DETERMINERS = {"a", "an", "the", "this", "that", "these", "those", "my", "your", "every", "each"}
PREPOSITIONS = {"to", "in", "on", "at", "of", "for", "with", "from", "by"}
VERBS = {"am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "go", "goes", "went", "play", "plays", "played", "like", "likes", "know", "knows", "depend", "depends", "interested", "good", "went"}


def _fallback_pos(word):
    w = word.lower()
    if re.fullmatch(r"[^\w']+", word): return "PUNCT"
    if w in PRONOUNS: return "PRON"
    if w in DETERMINERS: return "DET"
    if w in PREPOSITIONS: return "ADP"
    if w in VERBS or w.endswith(("ed", "ing")): return "VERB"
    if w.isdigit(): return "NUM"
    return "NOUN"


def get_pos_tags(sentence, nlp=None):
    """Return token, coarse/fine POS, lemma and available morphological features."""
    if nlp is not None:
        doc = nlp(sentence)
        # Model-less spaCy pipelines tokenize but do not assign POS; use the fallback then.
        if any(t.pos_ for t in doc if not t.is_punct):
            return [{"token": t.text, "pos": t.pos_, "tag": t.tag_, "lemma": t.lemma_ or t.text.lower(),
                     "morphology": str(t.morph) or "—", "idx": t.idx} for t in doc if not t.is_space]
    result = []
    for t in tokenize(sentence):
        word = t["text"]; pos = _fallback_pos(word)
        lemma = word.lower()
        if word.lower() in {"goes", "plays", "has", "does", "likes"}: lemma = {"goes":"go", "plays":"play", "has":"have", "does":"do", "likes":"like"}[word.lower()]
        result.append({"token": word, "pos": pos, "tag": pos, "lemma": lemma, "morphology": "—", "idx": t["idx"]})
    return result
