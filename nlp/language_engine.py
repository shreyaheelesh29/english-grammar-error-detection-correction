"""Local LanguageTool adapter with a graceful rules-only fallback."""
from __future__ import annotations

import os
import threading
from pathlib import Path

_lock = threading.RLock()
_tool = None
_startup_error = None


def _local_tool():
    """Create one local Java-backed LanguageTool instance on first use."""
    global _tool, _startup_error
    if _tool is not None or _startup_error is not None:
        return _tool
    with _lock:
        if _tool is not None or _startup_error is not None:
            return _tool
        try:
            # Keep the optional engine download in this checkout's ignored data
            # directory so it works in restricted home-directory environments.
            project_data = Path(__file__).resolve().parent.parent / "data" / "language_tool"
            os.environ.setdefault("LTP_PATH", str(project_data))
            import language_tool_python
            _tool = language_tool_python.LanguageTool(
                "en-US",
                config={"maxTextLength": 20000, "cacheSize": 128, "pipelineCaching": True},
            )
        except Exception as exc:  # Java, package, download, or server startup can fail.
            _startup_error = exc
    return _tool


def _field(match, *names, default=None):
    """Read wrapper attributes as well as raw API dictionaries."""
    for name in names:
        if isinstance(match, dict):
            value = match.get(name)
        else:
            value = getattr(match, name, None)
        if value is not None:
            return value
    return default


def normalize_matches(matches, text):
    """Translate LanguageTool matches into the checker's offset-based format."""
    findings = []
    for match in matches:
        start = int(_field(match, "offset", default=-1))
        length = int(_field(match, "error_length", "errorLength", "length", default=0))
        if start < 0 or length <= 0 or start + length > len(text):
            continue
        replacements = _field(match, "replacements", default=()) or ()
        replacement = replacements[0] if replacements else None
        if isinstance(replacement, dict):
            replacement = replacement.get("value")
        replacement = getattr(replacement, "value", replacement)
        if replacement is None:
            continue
        replacement = str(replacement)
        original = text[start:start + length]
        if replacement == original:
            continue
        category = _field(match, "category")
        category = getattr(category, "name", category)
        rule_id = _field(match, "rule_id", "ruleId", default="")
        message = _field(match, "message", default="LanguageTool found a possible issue.")
        findings.append({
            "original": original,
            "corrected": replacement,
            "suggestion": replacement,
            "error_type": str(category or "Grammar Suggestion").replace("_", " ").title(),
            "message": str(message),
            "explanation": str(message),
            "start": start,
            "end": start + length,
            "rule_id": str(rule_id),
            "rule_match_strength": "moderate",
            "sentence_index": 0,
        })

    # Keep one deterministic suggestion when independent rules overlap the same text.
    findings.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
    selected = []
    for finding in findings:
        if not selected or finding["start"] >= selected[-1]["end"]:
            selected.append(finding)
    return selected


def check_text(text):
    """Return local LanguageTool findings, or None when only fallback rules are available."""
    if os.environ.get("GRAMMAR_ENGINE", "local").lower() == "rules":
        return None, "Basic pattern fallback (GRAMMAR_ENGINE=rules)"
    tool = _local_tool()
    if tool is None:
        return None, "Basic pattern fallback (local LanguageTool unavailable)"
    try:
        with _lock:
            matches = tool.check(text)
        return normalize_matches(matches, text), "LanguageTool local engine"
    except Exception:
        return None, "Basic pattern fallback (local LanguageTool error)"
