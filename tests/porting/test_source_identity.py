"""Same receiver contract is tested in the API and Fusion locked environments."""
import importlib,json,os
from pathlib import Path
from uuid import UUID,uuid4
import pytest
from pydantic import ValidationError
M=importlib.import_module(os.getenv('SOCAI2_MODEL_MODULE','app.models.alert'))

def alert(**changes):
    identity=UUID('de26c212-2c00-47c8-813f-dab42d082e22')
    return M.RawAlert(id=identity,source_alert_id=identity,identity_version='source-v1',tenant_id=UUID(int=1),source='test-edr',title='finding',hostname='test-host',**changes)

def test_same_features_different_upstream_ids_stay_independent():
    first=alert();other=first.model_copy(update={'id':uuid4(),'source_alert_id':uuid4()})
    assert first.correlation_key()==other.correlation_key()
    assert first.fingerprint()!=other.fingerprint() and first.deterministic_id()!=other.deterministic_id()

def test_content_or_canonicalisation_cannot_change_source_identity():
    first=alert();canonical=first.deterministic_id()
    changed=first.model_copy(update={'id':canonical,'title':'updated content','source_event_ids':['new-evidence']})
    assert changed.deterministic_id()==canonical
    roundtrip=M.RawAlert.model_validate_json(changed.model_dump_json())
    assert roundtrip.deterministic_id()==canonical

@pytest.mark.parametrize('changes',[{'tenant_id':UUID(int=2)},{'source':'other-edr'},{'connector_id':UUID(int=3)}])
def test_identity_namespace_includes_tenant_source_and_connector(changes):
    first=alert();other=first.model_copy(update=changes)
    assert first.deterministic_id()!=other.deterministic_id()

def test_source_version_requires_explicit_source_uuid():
    value=alert().model_dump();value['source_alert_id']=None
    with pytest.raises(ValidationError):M.RawAlert.model_validate(value)

def test_unknown_identity_version_is_refused():
    value=alert().model_dump();value['identity_version']='unknown-v99'
    with pytest.raises(ValidationError):M.RawAlert.model_validate(value)

def test_legacy_receipt_fingerprint_and_uuid_are_unchanged():
    data=json.loads((Path(__file__).parent/'fixtures/legacy-alert-2a.json').read_text())
    value=M.RawAlert.model_validate(data['input'])
    assert value.identity_version=='legacy-v1'
    assert value.fingerprint()==data['fingerprint'] and str(value.deterministic_id())==data['canonical_alert_id']
