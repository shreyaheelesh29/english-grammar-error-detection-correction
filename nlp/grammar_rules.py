"""Small, transparent grammar patterns. These are examples, not full English grammar."""
import re


def _error(sentence, match, corrected, kind, message):
    return {"original": match.group(0), "corrected": corrected, "error_type": kind,
            "message": message, "start": match.start(), "end": match.end()}


def _third_person_singular(lemma):
    lower = lemma.lower()
    if lower in {"be", "have", "do", "go"}:
        return {"be": "is", "have": "has", "do": "does", "go": "goes"}[lower]
    if re.search(r"[^aeiou]y$", lower):
        return lemma[:-1] + "ies"
    if lower.endswith(("s", "x", "z", "ch", "sh", "o")):
        return lemma + "es"
    return lemma + "s"


def detect_subject_verb(sentence, pos_tags=None):
    found = []
    # Controlled present-simple patterns; avoid trying to conjugate arbitrary verbs.
    forms = {"go": ("goes", "go"), "play": ("plays", "play"), "have": ("has", "have"), "do": ("does", "do"), "like": ("likes", "like"),
             "dance": ("dances", "dance"), "walk": ("walks", "walk"), "run": ("runs", "run"), "work": ("works", "work"),
             "study": ("studies", "study"), "eat": ("eats", "eat"), "read": ("reads", "read"), "write": ("writes", "write"),
             "sing": ("sings", "sing"), "watch": ("watches", "watch"), "teach": ("teaches", "teach"), "pass": ("passes", "pass")}
    verb_forms = "|".join(sorted((form for pair in forms.values() for form in pair), key=len, reverse=True))
    for m in re.finditer(r"\b(I|you|he|she|it|we|they)\s+(" + verb_forms + r")\b", sentence, re.I):
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
    # With a trained spaCy parser, use the syntactic subject and verb features
    # instead of requiring a hard-coded verb pair.
    if pos_tags:
        by_index = {tag.get("token_i"): tag for tag in pos_tags if tag.get("token_i") is not None}
        for verb in pos_tags:
            if verb.get("pos") != "VERB" or verb.get("tag") not in {"VB", "VBP", "VBZ"}:
                continue
            verb_i = verb.get("token_i")
            if verb_i is None or verb.get("lemma", "").lower() in {"be", "have", "do"}:
                continue
            subject = next((tag for tag in pos_tags if tag.get("dep") in {"nsubj", "nsubjpass"} and tag.get("head_i") == verb_i), None)
            if not subject:
                continue
            subject_word = subject.get("token", "").lower()
            morphology = subject.get("morphology", "")
            features = set(re.findall(r"(?:Number|Person)=([A-Za-z]+)", morphology))
            third_singular = subject_word in {"he", "she", "it"} or ("Sing" in features and "3" in features)
            if subject.get("pos") in {"NOUN", "PROPN"} and "Plur" not in features and not subject_word.endswith("s"):
                third_singular = True
            if verb.get("tag") == "VBZ" and not third_singular:
                corrected = verb.get("lemma", "").lower()
            elif verb.get("tag") in {"VB", "VBP"} and third_singular:
                corrected = _third_person_singular(verb.get("lemma", ""))
            else:
                continue
            original = verb.get("token", "")
            start = verb.get("idx", -1)
            end = start + len(original)
            if start < 0 or any(item["start"] == start and item["end"] == end for item in found):
                continue
            if original.isupper():
                corrected = corrected.upper()
            elif original[0].isupper():
                corrected = corrected.capitalize()
            found.append({"original": original, "corrected": corrected, "error_type": "Subject-Verb Agreement",
                          "message": f"The parsed subject '{subject.get('token')}' and verb form appear to disagree; use '{corrected}'.",
                          "start": start, "end": end})
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
    # Existential "there" agrees with the noun phrase that follows it.
    for m in re.finditer(r"\bthere\s+(is|are|was|were)\s+(\d+|one|two|three|four|five|six|several|many)\b", sentence, re.I):
        quantity = m.group(2).lower()
        plural = quantity not in {"1", "one"}
        verb = m.group(1).lower()
        # If the same sentence has a clear past predicate, keep this existential
        # clause in that past narrative (e.g. "There is three dogs ... and we were...").
        past_context = verb in {"was", "were"} or bool(re.search(r"\b(?:yesterday|last\s+(?:night|week|month|year)|was|were|went|said|told|got|ate|bought)\b", sentence, re.I))
        expected = ("were" if plural else "was") if past_context else ("are" if plural else "is")
        if verb != expected:
            original = m.group(1)
            found.append({"original": original, "corrected": expected.capitalize() if original[0].isupper() else expected,
                          "error_type": "Subject-Verb Agreement", "message": f"With 'there', the verb agrees with the following quantity: use '{expected}'.",
                          "start": m.start(1), "end": m.end(1)})
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
    # Explicit quantities and "some" commonly require plural count nouns.
    for m in re.finditer(r"\b(\d+|one|two|three|four|five|six|several|many|some)\s+(dog|cat|book|car|student|apple|orange|friend|child|person|ticket|item)\b", sentence, re.I):
        quantity, noun = m.group(1).lower(), m.group(2)
        if quantity in {"1", "one"}:
            continue
        plural = irregular_plural.get(noun.lower(), noun + "s")
        out.append({"original": noun, "corrected": plural, "error_type": "Noun Number",
                    "message": f"'{quantity}' normally takes a plural count noun here: '{plural}'.",
                    "start": m.start(2), "end": m.end(2)})
    return out


def detect_tense(sentence):
    out = []
    # A time adverb alone cannot determine tense in every sentence, so this
    # deliberately handles common simple-past contexts and a controlled verb
    # list. It is broader than the original go-only rule, without pretending to
    # infer tense from unrestricted context.
    explicit_past_cue = re.search(
        r"\b(?:yesterday|last\s+(?:night|week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
        r"\d+\s+(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago|"
        r"(?:in|during)\s+(?:19\d{2}|20\d{2}))\b",
        sentence,
        re.I,
    )

    irregular = {
        "go": "went", "goes": "went", "say": "said", "says": "said",
        "am": "was", "is": "was", "are": "were",
        "have": "had", "has": "had", "do": "did", "does": "did",
        "get": "got", "gets": "got", "eat": "ate", "eats": "ate",
        "come": "came", "comes": "came", "see": "saw", "sees": "saw",
        "take": "took", "takes": "took", "make": "made", "makes": "made",
        "buy": "bought", "buys": "bought", "give": "gave", "gives": "gave",
        "run": "ran", "runs": "ran", "write": "wrote", "writes": "wrote",
        "speak": "spoke", "speaks": "spoke", "drive": "drove", "drives": "drove",
        "leave": "left", "leaves": "left", "meet": "met", "meets": "met",
        "find": "found", "finds": "found", "think": "thought", "thinks": "thought",
        "tell": "told", "tells": "told", "know": "knew", "knows": "knew",
        "pay": "paid", "pays": "paid",
        "feel": "felt", "feels": "felt", "keep": "kept", "keeps": "kept",
        "sleep": "slept", "sleeps": "slept", "stand": "stood", "stands": "stood",
        "sit": "sat", "sits": "sat", "bring": "brought", "brings": "brought",
        "build": "built", "builds": "built", "send": "sent", "sends": "sent",
        "spend": "spent", "spends": "spent", "hear": "heard", "hears": "heard",
        "wear": "wore", "wears": "wore", "teach": "taught", "teaches": "taught",
        "catch": "caught", "catches": "caught", "choose": "chose", "chooses": "chose",
        "fall": "fell", "falls": "fell", "grow": "grew", "grows": "grew",
        "begin": "began", "begins": "began", "break": "broke", "breaks": "broke",
        "drink": "drank", "drinks": "drank", "draw": "drew", "draws": "drew",
        "fly": "flew", "flies": "flew", "win": "won", "wins": "won",
        "lose": "lost", "loses": "lost", "understand": "understood", "understands": "understood",
    }
    regular = {
        "walk": "walked", "walks": "walked", "play": "played", "plays": "played",
        "work": "worked", "works": "worked", "open": "opened", "opens": "opened",
        "close": "closed", "closes": "closed", "stop": "stopped", "stops": "stopped",
        "study": "studied", "studies": "studied", "live": "lived", "lives": "lived",
        "visit": "visited", "visits": "visited", "use": "used", "uses": "used",
        "call": "called", "calls": "called", "help": "helped", "helps": "helped",
        "want": "wanted", "wants": "wanted", "need": "needed", "needs": "needed",
        "borrow": "borrowed", "borrows": "borrowed", "finish": "finished", "finishes": "finished",
        "start": "started", "starts": "started", "watch": "watched", "watches": "watched",
        "wash": "washed", "washes": "washed", "clean": "cleaned", "cleans": "cleaned",
        "cook": "cooked", "cooks": "cooked", "talk": "talked", "talks": "talked",
        "look": "looked", "looks": "looked", "move": "moved", "moves": "moved",
        "arrive": "arrived", "arrives": "arrived", "ask": "asked", "asks": "asked",
        "carry": "carried", "carries": "carried", "try": "tried", "tries": "tried",
        "enjoy": "enjoyed", "enjoys": "enjoyed", "dance": "danced", "dances": "danced",
    }
    present_forms = {**irregular, **regular}
    if explicit_past_cue:
        for m in re.finditer(r"\b(" + "|".join(sorted(present_forms, key=len, reverse=True)) + r")\b", sentence, re.I):
            # Preserve infinitives and verbs already governed by an auxiliary.
            prefix = sentence[max(0, m.start() - 18):m.start()]
            if re.search(r"\b(?:to|for|did|does|do|will|would|can|could|should|may|might|must)\s+$", prefix, re.I):
                continue
            original = m.group(1)
            corrected = present_forms[original.lower()]
            # Do not turn a present-perfect auxiliary into "had" while leaving
            # its participle behind (for example, "has finished").
            if original.lower() in {"have", "has"} and re.match(
                r"\s+(?:been|become|begun|broken|brought|built|bought|caught|chosen|come|done|driven|drunk|eaten|fallen|felt|flown|forgotten|found|given|gone|grown|heard|held|kept|known|left|lost|made|met|paid|read|run|said|seen|sent|shown|sung|sat|slept|spoken|spent|stood|taken|taught|thought|understood|worn|won|written|\w+ed)\b",
                sentence[m.end():],
                re.I,
            ):
                continue
            if original.lower() in {"am", "is", "are"}:
                subject = re.search(r"\b(I|you|he|she|it|we|they|[A-Za-z]+)\s+$", prefix, re.I)
                if subject:
                    subject_word = subject.group(1).lower()
                    corrected = "were" if subject_word in {"you", "we", "they"} or subject_word.endswith("s") else "was"
            if original.isupper():
                corrected = corrected.upper()
            elif original[0].isupper():
                corrected = corrected.capitalize()
            out.append({"original": original, "corrected": corrected, "error_type": "Tense Error",
                        "message": f"The past-time expression suggests using the past form '{corrected.lower()}'. Check that the surrounding context refers to a completed past event.",
                        "start": m.start(1), "end": m.end(1)})
    # A temporal "when ... get back" clause often inherits the past timeline
    # from its clause when that clause already contains a clear past predicate.
    past_context = re.search(r"\b(?:was|were|had|went|said|told|ate|bought|came|got|(?:should|could|would|might)\s+(?:have|of)\s+\w+(?:ed|en|t))\b", sentence, re.I)
    if past_context:
        for m in re.finditer(r"\bwhen\s+(?:I|you|he|she|it|we|they)\s+(get|gets)\s+back\b", sentence, re.I):
            original = m.group(1)
            out.append({"original": original, "corrected": "got", "error_type": "Tense Error",
                        "message": "This 'when' clause describes a return within an already past event; use 'got' here.",
                        "start": m.start(1), "end": m.end(1)})
    return out


def detect_verb_forms(sentence):
    out = []
    for m in re.finditer(r"\bfor\s+(buy)\b", sentence, re.I):
        out.append({"original": m.group(0), "corrected": "to " + m.group(1), "error_type": "Verb Form Error",
                    "message": "Use the infinitive 'to buy' to express the purpose of going to a store.",
                    "start": m.start(), "end": m.end()})
    for m in re.finditer(r"\b(should|could|would|might|must)\s+of\b", sentence, re.I):
        original = m.group(0)
        out.append({"original": original, "corrected": m.group(1) + " have", "error_type": "Verb Form Error",
                    "message": "After a modal verb, use 'have' in this perfect construction; 'of' is not the auxiliary.",
                    "start": m.start(), "end": m.end()})
    # In this common construction, move "very" before the -ed adjective.
    for m in re.finditer(r"\b(?:I|we|they|he|she|it)\s+(?:am|is|are|was|were)\s+(shocking|amazing|boring|exciting|surprising|confusing|frightening)\s+very much\b", sentence, re.I):
        adjective = m.group(1)
        corrected = adjective[:-3] + "ed" if adjective.lower().endswith("ing") else adjective
        out.append({"original": m.group(1) + " very much", "corrected": "very " + corrected,
                    "error_type": "Word Form Error", "message": "Use the -ed adjective for the person or group experiencing the feeling, and place 'very' before it.",
                    "start": m.start(1), "end": m.end()})
    # Experiencers are usually described with the -ed adjective ("we were shocked").
    for m in re.finditer(r"\b(I|we|they|he|she|it)\s+(?:am|is|are|was|were)\s+(shocking|amazing|boring|exciting|surprising|confusing|frightening)\b", sentence, re.I):
        adjective = m.group(2)
        corrected = adjective[:-3] + "ed" if adjective.lower().endswith("ing") else adjective
        out.append({"original": adjective, "corrected": corrected, "error_type": "Word Form Error",
                    "message": "Use the -ed adjective for the person or group experiencing this feeling.",
                    "start": m.start(2), "end": m.end(2)})
    for m in re.finditer(r"\b(running|run|runs|ran|walking|walk|walks|walked|driving|drive|drives|drove)\s+fastly\b", sentence, re.I):
        out.append({"original": "fastly", "corrected": "fast", "error_type": "Word Choice",
                    "message": "'Fast' is the standard adverb in this expression.", "start": m.end() - len("fastly"), "end": m.end()})
    return out


def detect_pronouns(sentence):
    out = []
    for m in re.finditer(r"\bme\s+and\s+my\s+friend\b", sentence, re.I):
        replacement = "my friend and I"
        if m.group(0)[0].isupper():
            replacement = replacement.capitalize()
        out.append({"original": m.group(0), "corrected": replacement, "error_type": "Pronoun Form",
                    "message": "Use the subject pronoun 'I' in this compound subject.",
                    "start": m.start(), "end": m.end()})
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
    candidates = (detect_subject_verb(sentence, pos_tags) + detect_articles(sentence) + detect_number_agreement(sentence)
                  + detect_tense(sentence) + detect_verb_forms(sentence) + detect_pronouns(sentence) + detect_prepositions(sentence) + detect_double_negatives(sentence)
                  + detect_capitalization_punctuation(sentence) + detect_common_confusions(sentence))
    # Remove overlapping spans, preferring the widest multiword correction (double negative/preposition).
    candidates.sort(key=lambda e: (
        e["start"],
        -(e["end"] - e["start"]),
        0 if e["error_type"] == "Tense Error" else 1,
    ))
    selected = []
    for item in candidates:
        if not selected or item["start"] >= selected[-1]["end"]:
            item["rule_match_strength"] = "strong" if item["error_type"] in {"Subject-Verb Agreement", "Number Agreement", "Tense Error"} else "moderate"
            item["suggestion"] = item["corrected"]
            item["explanation"] = item["message"]
            selected.append(item)
    return selected
