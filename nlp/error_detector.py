"""Collect and classify the rule engine findings."""
from .grammar_rules import run_rules


def detect_errors(sentences, pos_by_sentence=None):
    errors = []
    for sentence_index, sentence in enumerate(sentences):
        tags = pos_by_sentence[sentence_index] if pos_by_sentence and sentence_index < len(pos_by_sentence) else None
        for item in run_rules(sentence, tags):
            item["sentence_index"] = sentence_index
            errors.append(item)
    return errors
