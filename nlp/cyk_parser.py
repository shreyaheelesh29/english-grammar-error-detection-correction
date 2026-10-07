"""Small CYK parser for a limited educational English CFG."""
import re

LEXICON = {"PRON": {"i", "you", "he", "she", "it", "we", "they"}, "DET": {"a", "an", "the", "this", "those"},
           "N": {"student", "book", "dog", "apples", "college", "school", "music"},
           "V": {"read", "reads", "like", "likes", "play", "plays", "go", "goes", "went"},
           "P": {"to", "in", "on", "at", "with"}}
RULES = {("S", ("NP", "VP")), ("NP", ("DET", "N")), ("VP", ("V", "NP")), ("VP", ("V", "PP")), ("PP", ("P", "NP"))}


def parse(text, nlp=None):
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", text)]
    if nlp:
        try: words = [t.text.lower() for t in nlp(text) if not t.is_punct and not t.is_space]
        except Exception: pass
    n = len(words); table = [[set() for _ in range(n + 1)] for _ in range(n)]
    back = {}
    for i, word in enumerate(words):
        for label, entries in LEXICON.items():
            if word in entries:
                table[i][i + 1].add(label); back[(i, i + 1, label)] = (word,)
        if word in {"he", "she", "it", "i", "you", "we", "they"}:
            table[i][i + 1].add("NP"); back[(i, i + 1, "NP")] = ("PRON",)
    for width in range(2, n + 1):
        for i in range(n - width + 1):
            j = i + width
            for k in range(i + 1, j):
                for lhs, (a, b) in RULES:
                    if a in table[i][k] and b in table[k][j]:
                        table[i][j].add(lhs); back[(i, j, lhs)] = (a, k, b)
    def tree(i, j, label):
        rule = back.get((i, j, label))
        if not rule: return {"label": label}
        if len(rule) == 1:
            child = rule[0]
            return {"label": label, "children": [tree(i, j, child)] if (i, j, child) in back else [{"label": child, "word": words[i]}]}
        a, k, b = rule
        return {"label": label, "children": [tree(i, k, a), tree(k, j, b)]}
    accepted = n > 0 and "S" in table[0][n]
    return {"accepted": accepted, "tokens": words, "cyk_table": [[sorted(table[i][j]) for j in range(i + 1, n + 1)] for i in range(n)],
            "parse_tree": tree(0, n, "S") if accepted else None,
            "grammar": ["S → NP VP", "NP → DET N | PRON", "VP → V NP | V PP", "PP → P NP"],
            "note": "The lexical grammar is intentionally small; rejection does not imply ungrammatical English."}
