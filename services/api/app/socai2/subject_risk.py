"""Creation policy and persisted projections; GET never initializes risk."""
import json
import os
from pathlib import Path

from sqlalchemy import text

from .baseline_store import StoreError


def load_policy():
    try:
        path = Path(os.environ["SOCAI2_SUBJECT_RISK_CONFIG_FILE"])
        if not path.is_absolute():
            raise ValueError("absolute subject risk profile required")
        from .subject_risk_contracts import RiskPolicy
        policy = RiskPolicy.model_validate_json(path.read_text()).model_dump(mode="json")
    except (KeyError, OSError, ValueError):
        raise StoreError("subject_risk_configuration_invalid", 503) from None
    return policy


async def initialize(store, case_id, *, manual_level=None, actor_id=None):
    policy = load_policy()
    await store.db.execute(text("""SELECT socai2.initialize_subject_risk(
        :tenant,'case',:subject,CAST(:policy AS jsonb),:level,:actor)"""),
        {"tenant": store.tenant_id, "subject": case_id, "policy": json.dumps(policy),
         "level": manual_level, "actor": actor_id if manual_level is not None else None})


def incident_effective(row, automatic):
    if row.get("risk_metadata") is not None:
        return row["severity"], row["severity_source"]
    override = row.get("severity_override")
    return override or automatic, "manual_override" if override else "member_max" if automatic else None
