import json

with open("results/baseline.json", encoding="utf-8") as f:
    report = json.load(f)

for r in report["results"]:
    t, p = r["truth"], r["pred"]
    if p is None:
        print(r["id"], "INVALID")
        continue
    cat_ok = t["category"] == p["category"]
    act_ok = t["action"] == p["action"]
    if not (cat_ok and act_ok):
        print(f'{r["id"]}: truth={t["category"]}/{t["action"]}  '
              f'pred={p["category"]}/{p["action"]}  conf={p["confidence"]}')