"""Shared grammar-check orchestration for the Flask and Streamlit interfaces."""

from .error_detector import detect_errors
from .language_engine import check_text as check_with_language_tool


def check_document(text, sentences, tags_by_sentence):
    """Check a document and return findings with document-relative offsets."""
    errors, engine = check_with_language_tool(text)
    if errors is None:
        errors = detect_errors(sentences, tags_by_sentence)
        cursor = 0
        for sentence_index, sentence in enumerate(sentences):
            offset = text.find(sentence, cursor)
            if offset < 0:
                offset = cursor
            cursor = offset + len(sentence)
            for error in errors:
                if error["sentence_index"] == sentence_index:
                    error["start"] += offset
                    error["end"] += offset
    else:
        # LanguageTool already provides document offsets; attach the sentence for
        # clients that display per-sentence findings.
        sentence_spans = []
        cursor = 0
        for sentence in sentences:
            offset = text.find(sentence, cursor)
            if offset < 0:
                offset = cursor
            sentence_spans.append((offset, offset + len(sentence)))
            cursor = offset + len(sentence)
        for error in errors:
            error["sentence_index"] = next(
                (index for index, (start, end) in enumerate(sentence_spans)
                 if start <= error["start"] < end),
                0,
            )
    return errors, engine
