"""Inspect the built-in demo n-gram model and print its counts."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlp.ngram_model import get_model

if __name__ == "__main__":
    model=get_model()
    print(json.dumps({"vocabulary_size":len(model.vocab),"training_tokens":sum(model.uni.values()),"source":"dataset/grammar_dataset.csv"},indent=2))
