# How `analyze.py` works

`scripts/analyze.py` answers: **does the model's overall pattern of answers match the labels?** For category, action and severity, it prints how often each label appears in the truth versus in the model's predictions. It then prints severity accuracy, which `run_baseline.py` does not compute. It does not call the model.

## Run it

```powershell
cd C:\VsCode\aiops-triage-lab
C:\VsCode\.venv\Scripts\python.exe scripts/analyze.py
```

Run `scripts/run_baseline.py` first (see [run_baseline_flow.md](run_baseline_flow.md)). The script reads `results/baseline.json` by relative path, so run it from the repo root.

## Flow

```
results/baseline.json ──► analyze.py ──► console only (nothing is written)
  report["results"]        for field in [category, action, severity]:
                             truth = count of each label in r["truth"][field]
                             pred  = count of each label in r["pred"][field]
                             print one row per label: truth count, predicted count
                           then: severity accuracy = matches / number of rows
```

## Worked example: the `action` table

### 1. Two of the records it reads

```json
{"id": "inc-017",
 "truth": {"category": "swap_high", "severity": "medium", "action": "escalate"},
 "pred":  {"category": "swap_high", "severity": "low",    "action": "clear_tmp", "confidence": 0.8}}
{"id": "inc-014",
 "truth": {"category": "false_alert", "severity": "low", "action": "no_action"},
 "pred":  {"category": "cpu_high",    "severity": "low", "action": "no_action", "confidence": 0.2}}
```

### 2. Counting

For `field = "action"` it builds two counters over all 30 records:

- `truth`: `inc-017` adds one to `escalate`, `inc-014` adds one to `no_action`, and so on.
- `pred`: `inc-017` adds one to `clear_tmp`, `inc-014` adds one to `no_action`, and so on.

Then it prints every label found in either counter. A label the model never used shows `0` in the predicted column.

### 3. The printed table (current run)

```
action: label  truth  predicted
  clear_tmp          3    13
  escalate           9     0
  expand_fs          2     0
  no_action          6     8
  restart_service   10     9
```

Reading it:

- **`clear_tmp`: 3 true, 13 predicted.** The model uses `clear_tmp` more than four times as often as it should.
- **`escalate`: 9 true, 0 predicted.** It never escalates. Every row that needed a human got a different action.
- **`expand_fs`: 2 true, 0 predicted.** It never proposes growing a volume.
- **`no_action` and `restart_service`** are close to the truth counts, but close counts do not mean correct rows.

## The other two tables

Category (6 of each label in the truth, since the dataset is balanced):

```
category: label  truth  predicted
  cpu_high           6    10
  disk_full          6     7
  false_alert        6     0
  service_down       6     8
  swap_high          6     5
```

The model never predicts `false_alert`. It labels those rows as real problems, mostly `cpu_high` and `service_down`.

Severity:

```
severity: label  truth  predicted
  high              14     1
  low                6    18
  medium            10    11

Severity accuracy: 0.3
```

The model says `high` once and `low` 18 times, so it badly underrates how serious incidents are. This is the only place severity is scored.

## How to interpret these tables

- **The tables show bias, not correctness.** They compare totals. A label with matching counts can still be assigned to the wrong rows. For per-row mistakes, use `show_errors.py` (see [show_errors_flow.md](show_errors_flow.md)).
- **Where to look first:** large gaps between truth and predicted point at the model's blind spots. Here those are `escalate`, `false_alert`, and high severity.
- **Severity accuracy** is `rows where truth severity == predicted severity` divided by the number of rows.

## Known limitation

If any row is `INVALID` (its `pred` is `null` in `baseline.json`), the script crashes with a `TypeError` when it reaches that row, because it indexes `r["pred"][field]` without checking. The current run has no invalid rows, so it works. Unlike `show_errors.py`, it does not skip them.
