# How `run_baseline.py` works

`scripts/run_baseline.py` measures how well a local LLM (`llama3.2`, served by Ollama) triages the synthetic incidents in `data/incidents_v0.jsonl`. It reads each incident, asks the model for a category, severity and action, compares the answer with the hand-written label, and writes a scored report.

## Run it

Run from the repo root, as a module. The script imports `src.triage`, so running `python scripts/run_baseline.py` directly fails with `ModuleNotFoundError: No module named 'src'`.

```powershell
cd C:\VsCode\aiops-triage-lab
C:\VsCode\.venv\Scripts\python.exe scripts/check_data.py        # optional: validate the labels first
C:\VsCode\.venv\Scripts\python.exe -m scripts.run_baseline
```

Needs the Ollama app running with the model pulled (`ollama pull llama3.2`), and the `ollama` and `pydantic` Python packages (both are in the shared venv).

## The files involved

| File | Role |
|---|---|
| `data/incidents_v0.jsonl` | Input: one incident per line, with the model's inputs and the hidden answer (`truth`) |
| `src/triage.py` | Builds the prompt, calls Ollama, validates and retries |
| `src/schema.py` | `Triage` model: the only answer shape the model may return |
| `scripts/run_baseline.py` | Loops over incidents, scores, writes the report |
| `results/baseline.json` | Output (created on first run) |

## End-to-end flow

```
incidents_v0.jsonl ──► run_baseline.py ──► triage(row) ──► Ollama (llama3.2)
   (30 rows)             for each row         │                  │
                                              │  JSON reply      │
                                              ◄──────────────────┘
                                   validate against Triage schema
                                     ├─ valid   → return (prediction, attempt number)
                                     └─ invalid → retry, up to 3 attempts, then (None, 3)
                                              │
                         compare prediction with row["truth"]
                                              │
                                  results/baseline.json + printed summary
```

## Worked example: `inc-009`

This is one of the deliberately messy rows. The alert text is vague, and disk usage is only 41%, but the real problem is inode exhaustion.

### 1. One line of the input file

```json
{
  "id": "inc-009",
  "host": "app-09",
  "alert_text": "No space left on device",
  "metrics": {"cpu": 24, "swap": 4, "disk": 41},
  "log_excerpt": "write failed: No space left on device (inodes exhausted); 4.2M zero-byte session files in /tmp/sessions",
  "truth": {
    "category": "disk_full",
    "severity": "high",
    "action": "clear_tmp",
    "rationale": "inode exhaustion with byte usage low; stale temp session files are safe to delete"
  }
}
```

The row has two halves:

- **What the model sees:** `host`, `alert_text`, `metrics`, `log_excerpt`.
- **What the model never sees:** `truth`, which is the answer key used only for scoring. `id` is used only for bookkeeping.

### 2. Load (`run_baseline.py`, lines 6-7)

Every line is parsed with `json.loads` into a dict, giving a list `rows`.

### 3. Build the prompt (`src/triage.py`, `build_prompt`)

Only the four input fields are used. The model gets two messages.

System message (the same for every incident):

```
You are an SRE triage assistant.
Read the incident and reply with JSON only.
Categories: cpu_high, swap_high, disk_full, service_down, false_alert.
Severity: low, medium, high.
Actions: restart_service, clear_tmp, expand_fs, escalate, no_action.
Confidence is a number from 0 to 1.
```

User message (built from this row):

```
Host: app-09
Alert: No space left on device
Metrics: {"cpu": 24, "swap": 4, "disk": 41}
Log: write failed: No space left on device (inodes exhausted); 4.2M zero-byte session files in /tmp/sessions
```

### 4. Call the model with a forced output shape

`ollama.chat(...)` is called with `format=Triage.model_json_schema()`. That asks Ollama to constrain the reply to JSON matching `src/schema.py`:

```python
class Triage(BaseModel):
    category:   Literal["cpu_high", "swap_high", "disk_full", "service_down", "false_alert"]
    severity:   Literal["low", "medium", "high"]
    action:     Literal["restart_service", "clear_tmp", "expand_fs", "escalate", "no_action"]
    confidence: float  # 0 to 1
```

Attempt 1 uses `temperature=0` so the answer is as repeatable as possible. Retries use `temperature=0.3`.

### 5. Validate and retry

The reply text goes through `Triage.model_validate_json`.

- **Valid:** `triage()` returns `(Triage object, attempt number)`.
- **Invalid** (bad JSON, unknown label, confidence outside 0-1): it tries again with the same messages, up to 3 attempts. If all fail it returns `(None, 3)`, and the row is reported as `INVALID`.

An illustrative valid reply (the actual output varies by run):

```json
{"category": "disk_full", "severity": "high", "action": "clear_tmp", "confidence": 0.8}
```

### 6. Record the result (`run_baseline.py`, lines 12-18)

```json
{
  "id": "inc-009",
  "truth": {"category": "disk_full", "severity": "high", "action": "clear_tmp", "rationale": "..."},
  "pred":  {"category": "disk_full", "severity": "high", "action": "clear_tmp", "confidence": 0.8},
  "tries": 1
}
```

The console prints `inc-009 -> disk_full (tries=1)`.

### 7. Score this row

| Check | Truth | Prediction | Counts as |
|---|---|---|---|
| category | `disk_full` | `disk_full` | correct |
| action | `clear_tmp` | `clear_tmp` | correct |
| severity | `high` | `high` | not scored |

If the model had answered `false_alert` instead (because disk is only 41%), the category would be wrong, and `confusion` would gain `disk_full -> false_alert`.

## How the final report is computed

After the loop, over all `n` incidents:

| Field in `results/baseline.json` | Meaning |
|---|---|
| `model`, `n_incidents` | Which model, how many rows |
| `invalid_outputs` | Rows where all 3 attempts failed validation |
| `needed_retry` | Rows that needed more than one attempt |
| `category_accuracy` | Correct categories / `n` |
| `action_accuracy` | Correct actions / `n` |
| `per_category_accuracy` | Category accuracy within each *true* category |
| `confusion` | Counts of `true -> predicted` category, valid rows only |
| `results` | The per-row records from step 6 |

Things worth knowing when reading the numbers:

- **Invalid outputs count as wrong.** The accuracy denominator is `n`, not the number of valid rows, so an `INVALID` row lowers both accuracies.
- **Severity is not scored.** The model predicts it and it is saved in the report, but no metric uses it.
- **`truth.rationale` is not used by the code.** It is documentation for whoever reviews the labels.
- **`confusion` skips invalid rows.** They appear only in `invalid_outputs`.
- **With 30 rows, each row is worth about 3.3 points** of accuracy, so small differences between runs or models are noise.
