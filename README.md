# aiops-triage-lab
An AI agent that reads an incident (alert + metrics + logs),
classifies it, suggests a safe fix, and asks a human to approve.
Data is 100% synthetic. No client or company data is used.

## Scope (v0)
- Categories: cpu_high, swap_high, disk_full, service_down, false_alert
- Actions: restart_service, clear_tmp, expand_fs, escalate, no_action
- Out of scope: real systems, real credentials