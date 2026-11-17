"""Restore only this step's model-boundary edits in memory to classify old fixture failures."""
from pathlib import Path
import pytest
from app.socai2 import incident_diagnosis_contract, incident_model_boundary
for module in (incident_diagnosis_contract, incident_model_boundary):
    source=Path(module.__file__).read_text().replace('source.get("input_selection", {}).get("limit", 200)', '200')
    if module is incident_diagnosis_contract:
        source=source.replace('alert_ids: list[UUID] = Field(min_length=1)', 'alert_ids: list[UUID] = Field(min_length=1, max_length=200)')
        source=source.replace('members: list[Member] = Field(min_length=1)', 'members: list[Member] = Field(min_length=1, max_length=200)')
    exec(compile(source, '<before-step4-'+module.__name__+'>', 'exec'), module.__dict__)
raise SystemExit(pytest.main(['-q','services/api/tests/test_socai2_incident_alias_namespace.py','--tb=short']))
