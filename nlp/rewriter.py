"""Generate a few conservative, opt-in style rewrites for common transitions."""
import re


def generate_rewrites(text, goal="general"):
    """Return alternatives only when a known transition pattern is present.

    These are stylistic variants, not grammar corrections or model-generated paraphrases.
    """
    patterns = [
        (re.compile(r",?\s+and after that,?\s+", re.I), ", and afterward, ", "Clearer transition", "Replaces a wordy time phrase with a concise transition."),
        (re.compile(r",?\s+and after that,?\s+", re.I), ", then ", "More concise", "Uses a shorter sequence marker; review the resulting clause structure."),
    ]
    if goal == "casual":
        patterns.append((re.compile(r"\bstopped to get something to eat\b", re.I), "stopped to grab a bite to eat", "More conversational", "A casual word choice; keep it only if it matches your voice."))
    elif goal in {"academic", "business"}:
        patterns.append((re.compile(r"\bstopped to get something to eat\b", re.I), "stopped to have a meal", "More formal", "A more polished alternative; review it to make sure it preserves your meaning."))
    else:
        patterns.append((re.compile(r"\bstopped to get something to eat\b", re.I), "stopped for something to eat", "More natural", "A compact phrasing; review it to make sure it preserves your intended meaning."))
    proposals = []
    seen = {text}
    for pattern, replacement, label, reason in patterns:
        if not pattern.search(text):
            continue
        candidate = pattern.sub(replacement, text, count=1)
        # Tidy duplicated commas introduced by replacement templates.
        candidate = re.sub(r",\s*,", ",", candidate)
        if candidate not in seen:
            seen.add(candidate)
            proposals.append({"label": label, "text": candidate, "reason": reason})
    # An optional, conservative natural phrasing for the screenshot's coordinated sequence.
    natural = re.sub(r"\band after that,?\s+we\s+stopped to get\b", "and afterward, we stopped to get", text, flags=re.I)
    if natural != text and natural not in seen:
        proposals.append({"label": "More natural/casual", "text": natural,
                          "reason": "Uses 'afterward' to make the time relationship more direct."})
    return proposals[:3]
