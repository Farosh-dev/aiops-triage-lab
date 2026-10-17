import json
import os
from collections import Counter, defaultdict
from src.triage import triage, MODEL

with open("data/incidents_v0.jsonl", encoding="utf-8") as f:
    rows = [json.loads(line) for line in f]

results = []
for row in rows:
    pred, tries = triage(row)
    results.append({
        "id": row["id"],
        "truth": row["truth"],
        "pred": pred.model_dump() if pred else None,
        "tries": tries,
    })
    print(row["id"], "->", pred.category if pred else "INVALID", f"(tries={tries})")

n = len(rows)
valid = [r for r in results if r["pred"]]

cat_correct = sum(r["pred"]["category"] == r["truth"]["category"] for r in valid)
act_correct = sum(r["pred"]["action"] == r["truth"]["action"] for r in valid)

per_cat = defaultdict(list)
for r in results:
    ok = bool(r["pred"]) and r["pred"]["category"] == r["truth"]["category"]
    per_cat[r["truth"]["category"]].append(ok)

confusion = Counter(
    f'{r["truth"]["category"]} -> {r["pred"]["category"]}' for r in valid
)

report = {
    "model": MODEL,
    "n_incidents": n,
    "invalid_outputs": n - len(valid),
    "needed_retry": sum(r["tries"] > 1 for r in results),
    "category_accuracy": round(cat_correct / n, 3),
    "action_accuracy": round(act_correct / n, 3),
    "per_category_accuracy": {k: round(sum(v) / len(v), 3) for k, v in per_cat.items()},
    "confusion": dict(confusion),
    "results": results,
}

os.makedirs("results", exist_ok=True)
with open("results/baseline.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("\nCategory accuracy:", report["category_accuracy"])
print("Action accuracy:", report["action_accuracy"])
print("Per category:", report["per_category_accuracy"])