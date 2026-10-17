# How `show_errors.py` works

`scripts/show_errors.py` answers one question after a baseline run: **which incidents did the model get wrong, and how?** It prints one line per incident where the category, the action, or both were wrong. It does not call the model.

## Run it

```powershell
cd C:\VsCode\aiops-triage-lab
C:\VsCode\.venv\Scripts\python.exe scripts/show_errors.py
```

Run `scripts/run_baseline.py` first (see [run_baseline_flow.md](run_baseline_flow.md)). Without `results/baseline.json` the script fails with `FileNotFoundError`. It reads that file by relative path, so run it from the repo root.

## Flow

```
results/baseline.json ──► show_errors.py ──► console only (nothing is written)
  report["results"]          for each row:
  (one record per              pred is None?          → print "<id> INVALID"
   incident)                   category AND action ok? → print nothing
                               otherwise              → print one line
```

It uses only `report["results"]`, the per-row records that `run_baseline.py` wrote. The summary fields such as `category_accuracy` are ignored.

## Worked example: `inc-017`

### 1. The record it reads

This is one entry of `results` in `baseline.json`. `truth` came from the dataset and `pred` came from the model.

```json
{
  "id": "inc-017",
  "truth": {"category": "swap_high", "severity": "medium", "action": "escalate",
            "rationale": "caused by config change; restart won't undo it, owner must revert"},
  "pred":  {"category": "swap_high", "severity": "low", "action": "clear_tmp", "confidence": 0.8},
  "tries": 1
}
```

### 2. The two checks

```python
cat_ok = t["category"] == p["category"]   # swap_high == swap_high  → True
act_ok = t["action"]   == p["action"]     # escalate  == clear_tmp  → False
```

Only a row where **both** are true is skipped. Here the action is wrong, so the row is printed.

### 3. The printed line

```
inc-017: truth=swap_high/escalate  pred=swap_high/clear_tmp  conf=0.8
```

Format: `<id>: truth=<category>/<action>  pred=<category>/<action>  conf=<model confidence>`.

## Reading the output

The current run prints 22 lines, so 22 of the 30 incidents have at least one wrong field and 8 are fully correct.

| What the line looks like | Meaning | Example |
|---|---|---|
| Same category on both sides, different action | The model understood the problem but chose the wrong fix | `inc-017: truth=swap_high/escalate  pred=swap_high/clear_tmp  conf=0.8` |
| Different category and different action | The model misread the incident | `inc-013: truth=false_alert/no_action  pred=service_down/restart_service  conf=0.8` |
| Different category, same action | Wrong diagnosis, right outcome by luck | `inc-014: truth=false_alert/no_action  pred=cpu_high/no_action  conf=0.2` |
| `<id> INVALID` | All 3 attempts failed schema validation, so there is no prediction | none in the current run |

## Limits to be aware of

- **Severity is ignored.** A row whose only mistake is severity is not printed. Use `analyze.py` for severity (see [analyze_flow.md](analyze_flow.md)).
- **No counts.** There is no summary line. Count by eye, or pipe the output: `python scripts/show_errors.py | Measure-Object -Line`.
- **Incident text is not shown.** To see why the model erred, look up the `id` in `data/incidents_v0.jsonl`.
- **`conf` is a weak signal.** The model mostly answers 0.2 or 0.8 whether right or wrong, so a high value does not mean the answer is reliable.
