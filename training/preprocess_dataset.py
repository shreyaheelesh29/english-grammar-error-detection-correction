"""Convert an aligned CSV (incorrect,correct) into leakage-aware JSONL splits.

Input may be any legally obtained corpus exported with those two column names.
Near-duplicate incorrect inputs are grouped by normalized text before splitting.
"""
import argparse, csv, hashlib, json, random, re
from pathlib import Path

def norm(s): return " ".join(re.findall(r"\w+", s.lower()))

def main():
    p=argparse.ArgumentParser(); p.add_argument("input", type=Path); p.add_argument("--out", type=Path, default=Path("data")); a=p.parse_args()
    groups={}
    with a.input.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            src=(row.get("incorrect") or row.get("source") or "").strip(); tgt=(row.get("correct") or row.get("target") or "").strip()
            if src and tgt: groups.setdefault(hashlib.sha1(norm(src).encode()).hexdigest(), []).append({"incorrect":src,"correct":tgt})
    keys=list(groups); random.Random(17).shuffle(keys); n=len(keys)
    cuts={"train":keys[:int(.8*n)],"validation":keys[int(.8*n):int(.9*n)],"test":keys[int(.9*n):]}
    for split, ids in cuts.items():
        out=a.out/split; out.mkdir(parents=True,exist_ok=True)
        with (out/"pairs.jsonl").open("w",encoding="utf-8") as f:
            for key in ids:
                for row in groups[key]: f.write(json.dumps(row,ensure_ascii=False)+"\n")
    stats={"unique_source_groups":n,"pairs":sum(map(len,groups.values())),"splits":{k:sum(len(groups[x]) for x in v) for k,v in cuts.items()},"sha1_grouped":True}
    (a.out/"statistics.json").write_text(json.dumps(stats,indent=2),encoding="utf-8")
    print(json.dumps(stats,indent=2))
if __name__=="__main__": main()
