import json

CATS = {"cpu_high","swap_high","disk_full","service_down","false_alert"}
ACTS = {"restart_service","clear_tmp","expand_fs","escalate","no_action"}

with open("data/incidents_v0.jsonl") as f:
    for n, line in enumerate(f, 1):
        row = json.loads(line)
        assert row["truth"]["category"] in CATS, f"line {n}: bad category"
        assert row["truth"]["action"] in ACTS, f"line {n}: bad action"
print("OK: all rows valid")