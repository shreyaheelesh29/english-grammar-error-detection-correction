"""Shared grammar-check orchestration for the Flask and Streamlit interfaces."""

from .error_detector import detect_errors
from .language_engine import check_text as check_with_language_tool


def check_document(text, sentences, tags_by_sentence):
    """Check a document and return findings with document-relative offsets."""
    errors, engine = check_with_language_tool(text)
    sentence_spans = []
    cursor = 0
    for sentence in sentences:
        offset = text.find(sentence, cursor)
        if offset < 0:
            offset = cursor
        sentence_spans.append((offset, offset + len(sentence)))
        cursor = offset + len(sentence)

    if errors is None:
        errors = detect_errors(sentences, tags_by_sentence)
        for error in errors:
            offset = sentence_spans[error["sentence_index"]][0]
            error["start"] += offset
            error["end"] += offset
    else:
        # LanguageTool already provides document offsets; attach the sentence for
        # clients that display per-sentence findings.
        for error in errors:
            error["sentence_index"] = next(
                (index for index, (start, end) in enumerate(sentence_spans)
                 if start <= error["start"] < end),
                0,
            )

        # LanguageTool can suggest the wrong tense when a sentence has an
        # explicit past-time cue (for example, "goes" for "yesterday"). Add
        # the local, high-confidence past-cue rules and prefer them when they
        # address the same verb span.
        tense_rules = [
            error
            for error in detect_errors(sentences, tags_by_sentence)
            if error.get("error_type") == "Tense Error"
        ]
        for error in tense_rules:
            sentence_index = error["sentence_index"]
            offset = sentence_spans[sentence_index][0]
            error["start"] += offset
            error["end"] += offset
            overlapping = [
                index for index, existing in enumerate(errors)
                if error["start"] < existing["end"] and error["end"] > existing["start"]
            ]
            if overlapping:
                for index in reversed(overlapping):
                    errors.pop(index)
            errors.append(error)
        if tense_rules:
            engine = f"{engine} + explicit past-time rules"
        errors.sort(key=lambda error: (error["start"], error["end"]))
    return errors, engine
