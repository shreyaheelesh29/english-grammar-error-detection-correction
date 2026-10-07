"""Conservative sentence-structure diagnostics with reviewable suggestions."""
import re

DEPENDENT_STARTERS = ("because", "although", "though", "when", "while", "if", "unless", "since", "whereas")
SUBJECT = r"(?:I|you|he|she|it|we|they|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
FINITE = r"(?:am|is|are|was|were|has|have|had|do|does|did|can|could|will|would|should|must|went|goes|go|stopped|ate|played|works|worked|said|says|left|arrived|stayed|reads|read|likes|liked)"


def analyze_structure(sentences):
    issues = []
    for index, sentence in enumerate(sentences):
        stripped = sentence.strip().strip('"“”\'()[]{} ')
        first = stripped.split(maxsplit=1)[0].lower().strip(",;:") if stripped else ""
        if first in DEPENDENT_STARTERS and not re.search(r",\s*\w", stripped):
            issues.append({"sentence_index": index, "original": sentence,
                           "type": "Possible sentence fragment", "severity": "review",
                           "explanation": f"A clause beginning with '{first}' often depends on a main clause. This may be intentional in context.",
                           "suggestion": "Connect it to a main clause or rewrite it as a complete sentence."})
        # Surface heuristic: comma followed by an explicit subject + finite verb, without a coordinator.
        for m in re.finditer(rf",\s+({SUBJECT})\s+({FINITE})\b", sentence, re.I):
            left = sentence[:m.start()].strip()
            if re.search(rf"\b{FINITE}\b", left, re.I) and not re.search(r",\s*(?:and|but|or|so|yet|for|nor)\b", sentence[:m.start() + 1], re.I):
                issues.append({"sentence_index": index, "original": sentence,
                               "type": "Possible comma splice", "severity": "review",
                               "explanation": "The comma appears to join two independent clauses. The pattern is heuristic; check the clause boundary.",
                               "suggestion": "Use a period, semicolon, or a comma plus a coordinating conjunction."})
                break
    return issues
