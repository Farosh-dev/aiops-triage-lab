from typing import Literal
from pydantic import BaseModel, Field

class Triage(BaseModel):
    category: Literal["cpu_high", "swap_high", "disk_full", "service_down", "false_alert"]
    severity: Literal["low", "medium", "high"]
    action: Literal["restart_service", "clear_tmp", "expand_fs", "escalate", "no_action"]
    confidence: float = Field(ge=0, le=1)