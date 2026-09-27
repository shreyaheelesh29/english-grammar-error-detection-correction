"""Apply exact character-span corrections from right to left."""


def generate_correction(original_text, errors):
    corrected = original_text
    usable = [e for e in errors if isinstance(e.get("start"), int) and isinstance(e.get("end"), int)]
    for error in sorted(usable, key=lambda e: e["start"], reverse=True):
        start, end = error["start"], error["end"]
        if 0 <= start <= end <= len(corrected):
            corrected = corrected[:start] + error["corrected"] + corrected[end:]
    return {"original_text": original_text, "corrected_text": corrected}
