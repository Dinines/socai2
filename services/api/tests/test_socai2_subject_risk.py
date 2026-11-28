"""Direct policy/legacy/frozen-view checks; persistence is checked on real PG."""
import json
from pathlib import Path

import pytest
from app.socai2.program_facts import incident_level
from app.socai2.subject_risk import incident_effective
from app.socai2.subject_risk_contracts import RiskPolicy
from pydantic import ValidationError

POLICY = Path(__file__).resolve().parents[3] / 'deploy/local-investigation/subject-risk.json'


def test_confirmed_mapping_and_configured_endpoints():
    value = RiskPolicy.model_validate_json(POLICY.read_text())
    assert value.priority_by_severity.model_dump() == {'info': 10, 'low': 30, 'medium': 50, 'high': 75, 'critical': 95}
    body = json.loads(POLICY.read_text())
    body['priority_by_severity'].update(info=0, critical=100)
    assert RiskPolicy.model_validate(body).priority_by_severity.info == 0


@pytest.mark.parametrize('value', [-1, 101, True, '75', 75.5])
def test_invalid_score_is_not_coerced(value):
    body = json.loads(POLICY.read_text())
    body['priority_by_severity']['high'] = value
    with pytest.raises(ValidationError):
        RiskPolicy.model_validate(body)


def test_persisted_level_does_not_follow_new_member_maximum():
    parent = {'severity': 'high', 'severity_source': 'member_max', 'risk_metadata': {'stored': True}, 'severity_override': None}
    assert incident_effective(parent, 'critical') == ('high', 'member_max')
    result = incident_level(parent, {'one': {'severity': 'critical'}}, ['one'])
    assert result['severity_auto'] == 'critical' and result['severity_effective'] == 'high'
    assert incident_effective({'severity_override': 'low'}, 'high') == ('low', 'manual_override')
    assert incident_effective({'severity_override': None}, None) == (None, None)
