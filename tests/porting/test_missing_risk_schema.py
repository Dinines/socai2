"""Use with API or Fusion app path: both shared schemas preserve null vs zero."""
from uuid import uuid4
import pytest
try:
    from app.schemas.fusion_alert import RawAlert
except ModuleNotFoundError:
    from app.models.alert import RawAlert

@pytest.mark.parametrize('extra,expected',[({},None),({'risk_score':None},None),({'risk_score':0},0.0),({'risk_score':.8},.8)])
def test_wire_roundtrip_missing_null_zero_positive(extra,expected):
    a=RawAlert(tenant_id=uuid4(),source='test',title='Score contract',**extra)
    wire=a.model_dump(mode='json')
    assert wire['risk_score']==expected
    assert RawAlert.model_validate(wire).risk_score==expected

@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf')])
def test_nonfinite_risk_is_rejected(value):
    with pytest.raises(ValueError):RawAlert(tenant_id=uuid4(),source='test',title='Score contract',risk_score=value)
