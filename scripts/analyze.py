import json
from collections import Counter

with open("results/baseline.json", encoding="utf-8") as f:
    results = json.load(f)["results"]

for field in ["category", "action", "severity"]:
    truth = Counter(r["truth"][field] for r in results)
    pred = Counter(r["pred"][field] for r in results)
    print(f"\n{field}: label  truth  predicted")
    for label in sorted(set(truth) | set(pred)):
        print(f"  {label:16} {truth[label]:3}   {pred[label]:3}")

sev_ok = sum(r["truth"]["severity"] == r["pred"]["severity"] for r in results)
print("\nSeverity accuracy:", round(sev_ok / len(results), 3))