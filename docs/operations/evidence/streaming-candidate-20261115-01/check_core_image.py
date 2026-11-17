"""Check the frozen image's current contracts and actual factory without executing tasks."""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

config = json.load(sys.stdin)
os.environ["SOCAI2_INVESTIGATION_POLICY"] = config["executor"]["investigation_policy_file"]

from app.socai2.analysis_case_executor import executors
from app.socai2.analysis_dispatch_runtime import validate_executors
from app.socai2.runtime_policy import active_policy


def no_database(*args, **kwargs):
    raise AssertionError("image_check_must_not_access_database")


with tempfile.TemporaryDirectory() as directory:
    allocation = Path(directory) / "case-allocation.json"
    allocation.write_text(json.dumps(config["allocation"]))
    os.environ["SOCAI2_CASE_ALLOCATION_CONFIG_FILE"] = str(allocation)
    policy = active_policy().require_execution_profiles()
    assert policy.sha256 == config["expected_policy_sha256"]
    handlers = executors(config["executor"], SimpleNamespace(sessions=no_database))
    validate_executors(handlers)
    print(json.dumps({"state": "passed", "handlers": sorted(handlers),
        "profile_versions": {name: getattr(policy, name).version
                             for name in ("alert_io", "incident_io", "case_io")},
        "policy_sha256": policy.sha256,
        "output_budgets": dict(policy.model.output_tokens),
        "network": "none", "database_calls": 0, "model_calls": 0,
        "tasks_executed": 0}))
