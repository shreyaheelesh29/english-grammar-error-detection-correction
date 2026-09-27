"""Small, transparent grammar patterns. These are examples, not full English grammar."""
import re


def _error(sentence, match, corrected, kind, message):
    return {"original": match.group(0), "corrected": corrected, "error_type": kind,
            "message": message, "start": match.start(), "end": match.end()}


def detect_subject_verb(sentence):
    found = []
    # Controlled present-simple patterns; avoid trying to conjugate arbitrary verbs.
    forms = {"go": ("goes", "go"), "play": ("plays", "play"), "have": ("has", "have"), "do": ("does", "do"), "like": ("likes", "like")}
    for m in re.finditer(r"\b(I|you|he|she|it|we|they)\s+(goes|go|plays|play|has|have|does|do|likes|like)\b", sentence, re.I):
        subject, verb = m.group(1), m.group(2); s, v = subject.lower(), verb.lower()
        base = next((b for b, pair in forms.items() if v in pair), None)
        if not base: continue
        third = s in {"he", "she", "it"}
        expected = forms[base][0] if third else forms[base][1]
        if v != expected:
            start = m.start(2); end = m.end(2)
            corrected = expected.capitalize() if verb[0].isupper() else expected
            found.append({"original": verb, "corrected": corrected, "error_type": "Subject-Verb Agreement",
                          "message": f"The subject '{subject}' takes '{expected}' in this present-simple pattern.", "start": start, "end": end})
    return found


def detect_articles(sentence):
    out = []
    # Common silent-h words and consonant-sound examples only; pronunciation has exceptions.
    for m in re.finditer(r"\b(a|an)\s+([A-Za-z]+)", sentence, re.I):
        article, next_word = m.group(1), m.group(2); word = next_word.lower()
        vowel_sound = word.startswith(tuple("aeiou")) or word.startswith(("honest", "hour", "heir"))
        expected = "an" if vowel_sound else "a"
        if article.lower() != expected:
            new = expected.capitalize() if article[0].isupper() else expected
            out.append({"original": article, "corrected": new, "error_type": "Article Error",
                        "message": f"Use '{expected}' before this common { 'vowel' if vowel_sound else 'consonant' } sound.", "start": m.start(1), "end": m.end(1)})
    return out


def detect_number_agreement(sentence):
    out = []
    for m in re.finditer(r"\b(these|those|this|that)\s+(book|books|car|cars|student|students|apple|apples)\b", sentence, re.I):
        det, noun = m.group(1).lower(), m.group(2); plural_det = det in {"these", "those"}; plural_noun = noun.lower().endswith("s")
        if plural_det != plural_noun:
            expected = noun + "s" if plural_det else noun[:-1]
            out.append({"original": noun, "corrected": expected, "error_type": "Number Agreement",
                        "message": f"'{det}' requires a {'plural' if plural_det else 'singular'} noun here.", "start": m.start(2), "end": m.end(2)})
    # Demonstrative number can also require a matching form of be.
    for m in re.finditer(r"\b(this|that)\s+(book|books|car|cars|student|students|apple|apples)\s+(are)\b", sentence, re.I):
        verb = m.group(3)
        out.append({"original": verb, "corrected": "is", "error_type": "Number Agreement",
                    "message": f"The singular demonstrative '{m.group(1)}' takes 'is'.", "start": m.start(3), "end": m.end(3)})
    return out


def detect_tense(sentence):
    out = []
    m = re.search(r"\b(yesterday|last week|last month)\b.{0,30}?\b(I|you|he|she|it|we|they)\s+(go|goes)\b", sentence, re.I)
    if m:
        v = re.search(r"\b(go|goes)\b", sentence[m.start():m.end()], re.I)
        start = m.start() + v.start(); end = m.start() + v.end()
        out.append({"original": sentence[start:end], "corrected": "went", "error_type": "Tense Error",
                    "message": "The past-time expression indicates that 'go' should use its past form 'went'.", "start": start, "end": end})
    return out


def detect_prepositions(sentence):
    out = []
    rules = [(r"\bgood\s+in\b", "good at", "Common phrase: use 'good at' for a skill or subject."),
             (r"\binterested\s+on\b", "interested in", "The usual preposition after 'interested' is 'in'."),
             (r"\bdepend\s+of\b", "depend on", "The usual preposition after 'depend' is 'on'.")]
    for pattern, correction, message in rules:
        for m in re.finditer(pattern, sentence, re.I):
            replacement = correction.capitalize() if m.group(0)[0].isupper() else correction
            out.append({"original": m.group(0), "corrected": replacement, "error_type": "Preposition Error", "message": message, "start": m.start(), "end": m.end()})
    return out


def detect_double_negatives(sentence):
    out = []
    patterns = [r"\b(don't|do not|doesn't|does not|didn't|did not)\s+know\s+nothing\b"]
    for pattern in patterns:
        for m in re.finditer(pattern, sentence, re.I):
            original = m.group(0); replacement = re.sub(r"nothing$", "anything", original, flags=re.I)
            out.append({"original": original, "corrected": replacement, "error_type": "Possible Double Negative",
                        "message": "This supported pattern contains two negatives; use 'anything' after the negative verb.", "start": m.start(), "end": m.end()})
    return out


def run_rules(sentence, pos_tags=None):
    """Run each independent rule and return non-overlapping corrections."""
    candidates = (detect_subject_verb(sentence) + detect_articles(sentence) + detect_number_agreement(sentence)
                  + detect_tense(sentence) + detect_prepositions(sentence) + detect_double_negatives(sentence))
    # Remove overlapping spans, preferring the widest multiword correction (double negative/preposition).
    candidates.sort(key=lambda e: (e["start"], -(e["end"] - e["start"])))
    selected = []
    for item in candidates:
        if not selected or item["start"] >= selected[-1]["end"]:
            selected.append(item)
    return selected
