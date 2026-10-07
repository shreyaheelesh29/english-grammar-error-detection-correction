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
    be_forms = {"am": {"i"}, "is": {"he", "she", "it"}, "are": {"you", "we", "they"},
                "was": {"i", "he", "she", "it"}, "were": {"you", "we", "they"}}
    for m in re.finditer(r"\b(I|you|he|she|it|we|they)\s+(am|is|are|was|were)\b", sentence, re.I):
        subject, verb = m.group(1), m.group(2)
        if subject.lower() not in be_forms[verb.lower()]:
            past = verb.lower() in {"was", "were"}
            expected = ("was" if subject.lower() in {"i", "he", "she", "it"} else "were") if past else ("am" if subject.lower() == "i" else "is" if subject.lower() in {"he", "she", "it"} else "are")
            found.append({"original": verb, "corrected": expected.capitalize() if verb[0].isupper() else expected,
                          "error_type": "Subject-Verb Agreement", "message": f"The subject '{subject}' requires '{expected}' in this form.",
                          "start": m.start(2), "end": m.end(2)})
    # Agreement follows the head noun in common singular "X of Y" phrases.
    for m in re.finditer(r"\b(the|a|this|that|my|your|his|her|our|their)?\s*(list|group|set|collection|series)\s+of\s+(?:(?:the|these|those|my|your|our|their)\s+)?([A-Za-z]+)\s+(are|were|have|do)\b", sentence, re.I):
        head, verb = m.group(2).lower(), m.group(4).lower()
        expected = {"are": "is", "were": "was", "have": "has", "do": "does"}[verb]
        original_verb = m.group(4)
        found.append({"original": original_verb, "corrected": expected.capitalize() if original_verb[0].isupper() else expected,
                      "error_type": "Subject-Verb Agreement", "message": f"The head noun '{head}' is singular here, so the verb should be '{expected}'.",
                      "start": m.start(4), "end": m.end(4)})
    return found


def detect_articles(sentence):
    out = []
    # Common silent-h words and consonant-sound examples only; pronunciation has exceptions.
    for m in re.finditer(r"\b(a|an)\s+([A-Za-z]+)", sentence, re.I):
        article, next_word = m.group(1), m.group(2); word = next_word.lower()
        consonant_sound = word.startswith(("uni", "use", "euro", "one", "once"))
        vowel_sound = (word.startswith(tuple("aeiou")) and not consonant_sound) or word.startswith(("honest", "hour", "heir", "honor"))
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
    # A singular count article cannot normally modify a regular plural noun.
    for m in re.finditer(r"\b(a|an)\s+([A-Za-z]+s)\b", sentence, re.I):
        noun = m.group(2)
        lower = noun.lower()
        irregular = {"children": "child", "people": "person", "men": "man", "women": "woman", "mice": "mouse"}
        singular_exceptions = {"news", "series", "species", "means", "business", "bus", "status", "crisis", "analysis", "thesis", "basis", "class", "glass", "dress", "address", "tennis"}
        if lower in irregular:
            singular = irregular[lower]
        elif lower.endswith("ies"):
            singular = noun[:-3] + "y"
        elif lower.endswith(("ches", "shes", "xes", "zes")):
            singular = noun[:-2]
        else:
            singular = noun[:-1]
        if lower not in singular_exceptions:
            starts_consonant_sound = singular.lower().startswith(("uni", "use", "euro", "one", "once"))
            silent_h = singular.lower().startswith(("honest", "hour", "heir", "honor"))
            expected_article = "a" if starts_consonant_sound else "an" if singular.lower()[0] in "aeiou" or silent_h else "a"
            if m.group(1)[0].isupper(): expected_article = expected_article.capitalize()
            out.append({"original": m.group(0), "corrected": f"{expected_article} {singular}", "error_type": "Article/Noun Number",
                        "message": f"This singular count-noun construction should be '{expected_article} {singular}'.",
                        "start": m.start(), "end": m.end()})
    # Count nouns after these collective heads are conventionally plural.
    irregular_plural = {"person": "people", "child": "children", "man": "men", "woman": "women", "mouse": "mice"}
    for m in re.finditer(r"\b(list|group|set|collection)\s+of\s+([A-Za-z]+)\b", sentence, re.I):
        noun = m.group(2); lower = noun.lower()
        mass_nouns = {"information", "furniture", "equipment", "advice", "research", "water", "music", "news"}
        already_plural = lower.endswith("s") or lower in {"people", "children", "men", "women", "mice", "data"}
        if not already_plural and lower not in mass_nouns:
            plural = irregular_plural.get(lower, noun + "s")
            out.append({"original": noun, "corrected": plural, "error_type": "Noun Number",
                        "message": f"A list or group normally contains plural count nouns; use '{plural}' here.",
                        "start": m.start(2), "end": m.end(2)})
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


def detect_capitalization_punctuation(sentence):
    out = []
    start = re.search(r"[A-Za-z]", sentence)
    if start and sentence[start.start()].islower():
        out.append({"original": sentence[start.start()], "corrected": sentence[start.start()].upper(), "error_type": "Capitalization",
                    "message": "Capitalize the first word of a sentence.", "start": start.start(), "end": start.start() + 1})
    # A terminal mark inside closing quotation marks/brackets is already valid.
    if sentence and not re.search(r"[.!?][\"'”’\])}]*\s*$", sentence):
        closing = re.search(r"[\"'”’\])}]+\s*$", sentence)
        insertion = closing.start() if closing else len(sentence)
        out.append({"original": "", "corrected": ".", "error_type": "Punctuation",
                    "message": "A complete sentence normally ends with punctuation.", "start": insertion, "end": insertion})
    for m in re.finditer(r"([!?])\1+", sentence):
        out.append({"original": m.group(0), "corrected": m.group(1), "error_type": "Punctuation",
                    "message": "Repeated punctuation is usually unnecessary in standard edited writing.", "start": m.start(), "end": m.end()})
    for m in re.finditer(r"\s+([,.;:!?])", sentence):
        out.append({"original": m.group(0), "corrected": m.group(1), "error_type": "Punctuation",
                    "message": "In standard typography, punctuation attaches to the preceding word.", "start": m.start(), "end": m.end()})
    for m in re.finditer(r"([,;:])(?=[A-Za-z])", sentence):
        out.append({"original": m.group(1), "corrected": m.group(1) + " ", "error_type": "Punctuation",
                    "message": "Add a space after this punctuation mark.", "start": m.start(), "end": m.end()})
    return out


def detect_common_confusions(sentence):
    out = []
    for pattern, replacement, message in [
        (r"\b(a lot|alot)\b", "a lot", "The standard spelling is two words: 'a lot'."),
        (r"\bdont\b", "don't", "Use an apostrophe in the contraction 'don't'."),
        (r"\bdoesnt\b", "doesn't", "Use an apostrophe in the contraction 'doesn't'."),
        (r"\bdidnt\b", "didn't", "Use an apostrophe in the contraction 'didn't'."),
    ]:
        for m in re.finditer(pattern, sentence, re.I):
            if replacement and m.group(0).lower() != replacement:
                out.append({"original":m.group(0),"corrected":replacement,"error_type":"Common Confusion","message":message,"start":m.start(),"end":m.end()})
    return out


def run_rules(sentence, pos_tags=None):
    """Run each independent rule and return non-overlapping corrections."""
    candidates = (detect_subject_verb(sentence) + detect_articles(sentence) + detect_number_agreement(sentence)
                  + detect_tense(sentence) + detect_prepositions(sentence) + detect_double_negatives(sentence)
                  + detect_capitalization_punctuation(sentence) + detect_common_confusions(sentence))
    # Remove overlapping spans, preferring the widest multiword correction (double negative/preposition).
    candidates.sort(key=lambda e: (e["start"], -(e["end"] - e["start"])))
    selected = []
    for item in candidates:
        if not selected or item["start"] >= selected[-1]["end"]:
            item["rule_match_strength"] = "strong" if item["error_type"] in {"Subject-Verb Agreement", "Number Agreement", "Tense Error"} else "moderate"
            item["suggestion"] = item["corrected"]
            item["explanation"] = item["message"]
            selected.append(item)
    return selected
