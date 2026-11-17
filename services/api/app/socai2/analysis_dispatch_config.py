"""Explicit internal dispatcher settings; HTTP workers never load a dispatcher."""
import re
from dataclasses import dataclass
from pathlib import Path

KINDS = ("case_investigation", "alert_triage", "incident_diagnosis", "knowledge_sync")


@dataclass(frozen=True)
class DispatchPolicy:
    namespace: str
    max_running_tasks: int
    poll_interval_seconds: float
    execution_timeout_seconds: float
    replenish_limit: int
    priorities: tuple[str, ...]
    receipt_directory: str
    lock_file: str

    def __post_init__(self):
        if not re.fullmatch(r"[a-zA-Z0-9:_-]+", self.namespace):
            raise ValueError("invalid dispatcher namespace")
        if any(type(v) is not int or v < 1 for v in (self.max_running_tasks, self.replenish_limit)):
            raise ValueError("invalid dispatcher capacity")
        if any(type(v) not in {int, float} or not 0 < v < float("inf")
               for v in (self.poll_interval_seconds, self.execution_timeout_seconds)):
            raise ValueError("invalid dispatcher interval")
        if len(self.priorities) != len(KINDS) or set(self.priorities) != set(KINDS):
            raise ValueError("invalid dispatcher priorities")
        if not all(Path(p).is_absolute() for p in (self.receipt_directory, self.lock_file)):
            raise ValueError("dispatcher paths must be absolute")
