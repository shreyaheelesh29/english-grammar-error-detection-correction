"""spaCy-backed tokenization with a regex fallback."""
import re


def tokenize(sentence, nlp=None):
    if nlp is not None:
        return [{"text": t.text, "idx": t.idx, "is_punct": t.is_punct, "is_space": t.is_space}
                for t in nlp(sentence) if not t.is_space]
    return [{"text": m.group(), "idx": m.start(), "is_punct": bool(re.fullmatch(r"[^\w']+", m.group())), "is_space": False}
            for m in re.finditer(r"\w+(?:['’]\w+)?|[^\w\s]", sentence, re.UNICODE)]
