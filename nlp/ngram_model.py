"""Educational add-alpha unigram, bigram and trigram language model."""
from collections import Counter
import math
import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "dataset" / "grammar_dataset.csv"


class NGramModel:
    def __init__(self, sentences=()):
        self.uni, self.bi, self.tri = Counter(), Counter(), Counter()
        self.context2, self.context3 = Counter(), Counter()
        self.vocab = {"<UNK>"}
        for sentence in sentences:
            words = ["<s>", "<s>"] + self.words(sentence) + ["</s>"]
            self.vocab.update(words)
            self.uni.update(words)
            self.bi.update(zip(words, words[1:]))
            self.tri.update(zip(words, words[1:], words[2:]))
            self.context2.update(words[:-1])
            self.context3.update(zip(words[:-2], words[1:-1]))

    @staticmethod
    def words(text):
        return re.findall(r"[a-z]+(?:'[a-z]+)?|[0-9]+", text.lower())

    def score(self, words, n, smoothing=True):
        seq = ["<s>"] * (n - 1) + words + ["</s>"]
        V = max(1, len(self.vocab))
        logp, count = 0.0, 0
        for i in range(n - 1, len(seq)):
            target = seq[i] if seq[i] in self.vocab else "<UNK>"
            if n == 1:
                num, den = self.uni[target], sum(self.uni.values())
            elif n == 2:
                prev = seq[i - 1] if seq[i - 1] in self.vocab else "<UNK>"
                num, den = self.bi[(prev, target)], self.context2[prev]
            else:
                a = seq[i - 2] if seq[i - 2] in self.vocab else "<UNK>"
                b = seq[i - 1] if seq[i - 1] in self.vocab else "<UNK>"
                num, den = self.tri[(a, b, target)], self.context3[(a, b)]
            p = (num + 1) / (den + V) if smoothing else (num / den if den else 0.0)
            if p <= 0:
                return {"probability": 0.0, "perplexity": None}
            logp += math.log(p); count += 1
        return {"probability": round(math.exp(logp), 10), "perplexity": round(math.exp(-logp / max(count, 1)), 3)}

    def score_text(self, text):
        words = self.words(text)
        return {"unigram": self.score(words, 1), "bigram": self.score(words, 2), "trigram": self.score(words, 3),
                "vocabulary_size": len(self.vocab), "note": "Smoothed probabilities use add-one Laplace smoothing. Low likelihood is a sequence signal, not proof of a grammar error."}


def get_model():
    global _MODEL
    if _MODEL is None:
        # Train only from the supplied educational pairs; a licensed corpus can replace this input.
        import csv
        rows = []
        try:
            with CORPUS.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f): rows.extend([row.get("incorrect", ""), row.get("correct", "")])
        except OSError:
            pass
        _MODEL = NGramModel(rows)
    return _MODEL


_MODEL = None
