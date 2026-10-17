import json
import ollama
from pydantic import ValidationError
from src.schema import Triage

MODEL = "llama3.2"

SYSTEM = """You are an SRE triage assistant.
Read the incident and reply with JSON only.
Categories: cpu_high, swap_high, disk_full, service_down, false_alert.
Severity: low, medium, high.
Actions: restart_service, clear_tmp, expand_fs, escalate, no_action.
Confidence is a number from 0 to 1."""

def build_prompt(incident):
    return (
        f"Host: {incident['host']}\n"
        f"Alert: {incident['alert_text']}\n"
        f"Metrics: {json.dumps(incident['metrics'])}\n"
        f"Log: {incident['log_excerpt']}"
    )

def triage(incident, max_tries=3):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": build_prompt(incident)},
    ]
    for attempt in range(1, max_tries + 1):
        resp = ollama.chat(
            model=MODEL,
            messages=messages,
            format=Triage.model_json_schema(),
            options={"temperature": 0 if attempt == 1 else 0.3},
        )
        try:
            return Triage.model_validate_json(resp.message.content), attempt
        except ValidationError:
            continue
    return None, max_tries