"""Evaluate the current rule checker on aligned CSV pairs; metrics are data-derived."""
import argparse, csv, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nlp.preprocessing import split_sentences
from nlp.error_detector import detect_errors
from nlp.pos_tagger import get_pos_tags
from nlp.correction import generate_correction

def main():
    p=argparse.ArgumentParser(); p.add_argument("csv",type=Path); a=p.parse_args()
    tp=fp=fn=exact=total=0
    with a.csv.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            src=row.get("incorrect",""); gold=row.get("correct",""); sents=split_sentences(src); tags=[get_pos_tags(s) for s in sents]
            found=detect_errors(sents,tags); predicted=bool(found); expected=src.strip()!=gold.strip()
            tp+=int(predicted and expected); fp+=int(predicted and not expected); fn+=int(not predicted and expected)
            exact+=int(generate_correction(src,found)["corrected_text"].strip()==gold.strip()); total+=1
    precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
    print(json.dumps({"examples":total,"precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0,"exact_match":exact/total if total else 0,"status":"Measured on supplied CSV; not corpus-level generalization."},indent=2))
if __name__=="__main__": main()
