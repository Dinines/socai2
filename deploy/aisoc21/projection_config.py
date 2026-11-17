"""Explicit projection process settings; private connection credentials stay in env files."""
import json
from pathlib import Path


def load_profile(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("explicit absolute projection profile required")
    value = json.loads(path.read_text())
    texts = {"topic", "group", "client_id", "bootstrap_servers", "environment"}
    paths = {"activation_file", "ready_file", "source_pythonpath", "analysis_policy_file"}
    numbers = {"poll_timeout_ms", "max_records", "request_timeout_ms", "max_partition_fetch_bytes",
        "connect_timeout_seconds", "command_timeout_seconds", "lock_timeout_ms", "source_prefetch", "health_max_age_seconds"}
    if set(value) != texts | paths | numbers:
        raise ValueError("invalid projection profile fields")
    if any(not isinstance(value[k], str) or not value[k].strip() for k in texts):
        raise ValueError("invalid projection transport")
    if any(not Path(value[k]).is_absolute() for k in paths):
        raise ValueError("absolute projection paths required")
    if any(type(value[k]) is not int or value[k] <= 0 for k in numbers):
        raise ValueError("invalid projection limit")
    return value
