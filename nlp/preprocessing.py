"""Text cleanup and sentence segmentation."""
import re


def preprocess_text(text):
    """Normalize whitespace and Unicode while retaining punctuation."""
    if not isinstance(text, str):
        return ""
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text, nlp=None):
    """Use spaCy sentence boundaries when available, with a safe fallback."""
    text = preprocess_text(text)
    if not text:
        return []
    if nlp is not None:
        try:
            return [s.text.strip() for s in nlp(text).sents if s.text.strip()]
        except (ValueError, AttributeError):
            pass
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
