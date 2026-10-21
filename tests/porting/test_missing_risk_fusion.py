from uuid import uuid4
from app.models.alert import RawAlert,FusedAlert,FusionDecision
from app.services.entity_risk import EntityRiskEngine
from app.services.confidence import ConfidenceScorer

def alert(score):
    return RawAlert(tenant_id=uuid4(),source='test',title='Same signal',hostname='HOST',risk_score=score)

def test_unknown_rba_is_internal_unboosted_baseline_not_input_mutation():
    engine=EntityRiskEngine(None);a=alert(None);z=alert(0)
    assert engine._build_signals(a)[0].points==engine._build_signals(z)[0].points
    assert a.risk_score is None and z.risk_score==0

def test_confidence_distinguishes_unknown_explanation_with_same_numeric_baseline():
    values=[]
    for risk in [None,0]:
        a=alert(risk);f=FusedAlert(id=uuid4(),tenant_id=a.tenant_id,fusion_decision=FusionDecision.NEW_INCIDENT,alert=a)
        scored=ConfidenceScorer().score(f);factor=next(x for x in scored.confidence_rationale if x.factor=='upstream_risk');values.append((scored.confidence_score,factor))
    assert values[0][0]==values[1][0]
    assert 'not supplied' in values[0][1].value and values[1][1].value=='0.00'
