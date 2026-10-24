"""Controlled policy/config direct contracts, before HTTP implementation."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import UUID

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.investigation_v2.program_start_api import (ControlledManualTargetPolicy, StartAPIConfig, checked_budget,
    checked_start_token, POLICY_SCHEMA, TOKEN_ENV, DSN_ENV, CA_ENV, TOOL_URL_ENV, TOOL_TOKEN_ENV, BUDGET_ENV, POLICY_ENV, READ_TOKEN_ENV, _json)
from app.investigation_v2.scope import TenantPrincipal
from test_program_alert_projection_contract import current
from test_start_contract import policy
import test_evidence_view_contract as e

WRITE_TOKEN="test-only-internal-write-credential-not-live"
TOOL_TOKEN="test-only-start-tool-service-credential-not-live"
READ_TOKEN="test-only-compat-read-credential-not-live"

def policy_doc():
    return dict(schema=POLICY_SCHEMA,policy_ref="controlled-test-targets.v1",mode="isolated_manual_test",
        targets=[dict(tenant_id=str(e.TENANT),alert_id=str(e.ALERT),operational_isolation_ref="test-only-operational-receipt-not-proof")])

def environment():
    return {TOKEN_ENV:WRITE_TOKEN,DSN_ENV:"postgresql://test-only:test-only@localhost/test_only",TOOL_URL_ENV:"https://test-only.invalid/",
        TOOL_TOKEN_ENV:TOOL_TOKEN,BUDGET_ENV:json.dumps(policy().descriptor),POLICY_ENV:json.dumps(policy_doc()),READ_TOKEN_ENV:READ_TOKEN}

class StartAPIConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_concrete_policy_matches_only_server_configured_permitted_targets(self):
        target=ControlledManualTargetPolicy.from_document(policy_doc())
        kwargs=dict(current_principal=current(),tenant_id=e.TENANT,actor_id=UUID(int=55),alert_id=e.ALERT,policy_ref=target.policy_ref)
        result=await target.assess(**kwargs)
        self.assertIs(result['eligible'],True);self.assertEqual(result['target'],{'type':'alert','id':str(e.ALERT)})
        for change in ({'alert_id':UUID(int=99)},{'tenant_id':UUID(int=99)}, {'policy_ref':'unknown.v1'},
                       {'current_principal':TenantPrincipal()}):
            self.assertIs((await target.assess(**{**kwargs,**change}))['eligible'],False)

    async def test_policy_detaches_data_and_does_not_infer_actual_writer_exclusion(self):
        doc=policy_doc();target=ControlledManualTargetPolicy.from_document(doc);doc['targets'].clear()
        self.assertEqual(len(target.targets),1)
        self.assertEqual(target.targets[0].operational_isolation_ref,'test-only-operational-receipt-not-proof')
        self.assertFalse(hasattr(target,'legacy_writer_exclusion_verified'))

    async def test_policy_unknown_mode_fields_empty_duplicate_and_nil_identity_refuse(self):
        for mutate in (lambda d:d.update(mode='production'),lambda d:d.update(schema='future.v1'),lambda d:d.update(targets=[]),
                       lambda d:d.update(extra=True),lambda d:d['targets'].append(deepcopy(d['targets'][0])),
                       lambda d:d['targets'][0].update(alert_id=str(UUID(int=0))),
                       lambda d:d['targets'][0].update(tenant_id='*'),lambda d:d['targets'][0].update(operational_isolation_ref=''),
                       lambda d:d['targets'][0].update(source_flag=True)):
            doc=policy_doc();mutate(doc)
            with self.assertRaises(ValueError):ControlledManualTargetPolicy.from_document(doc)

    async def test_actor_must_be_nonnil_and_policy_does_not_take_text_as_control(self):
        target=ControlledManualTargetPolicy.from_document(policy_doc())
        for actor in (UUID(int=0),'not-a-uuid',True):
            with self.assertRaises(ValueError):
                await target.assess(current_principal=current(),tenant_id=e.TENANT,actor_id=actor,alert_id=e.ALERT,policy_ref=target.policy_ref)

    async def test_explicit_new_environment_and_secret_repr_are_bounded(self):
        with patch.dict(os.environ,environment(),clear=True):cfg=StartAPIConfig.from_environment(WRITE_TOKEN)
        self.assertEqual(cfg.tool_url,'https://test-only.invalid');self.assertEqual(cfg.budget,policy())
        for value in (WRITE_TOKEN,TOOL_TOKEN,'postgresql://'):
            self.assertNotIn(value,repr(cfg))

    async def test_only_old_environment_never_configures_new_writer(self):
        with patch.dict(os.environ,{'DATABASE_URL':'PRIVATE_DSN','AISOC_SERVICE_TOKEN':WRITE_TOKEN,'AISOC_INVESTIGATION_COMPAT_PG_DSN':'PRIVATE'},clear=True):
            with self.assertRaises(ValueError) as error:StartAPIConfig.from_environment(WRITE_TOKEN)
        self.assertNotIn('PRIVATE',str(error.exception))
        for key in (DSN_ENV,TOOL_URL_ENV,TOOL_TOKEN_ENV,BUDGET_ENV,POLICY_ENV):
            env=environment();env.pop(key)
            with patch.dict(os.environ,env,clear=True),self.assertRaises(ValueError):StartAPIConfig.from_environment(WRITE_TOKEN)

    async def test_write_credential_cannot_reuse_configured_read_or_tool_credential(self):
        for key in (TOOL_TOKEN_ENV,READ_TOKEN_ENV):
            env=environment();env[key]=WRITE_TOKEN
            with patch.dict(os.environ,env,clear=True),self.assertRaises(ValueError):StartAPIConfig.from_environment(WRITE_TOKEN)

    async def test_budget_has_exact_supported_schema_and_limits(self):
        self.assertEqual(checked_budget(policy().descriptor),policy())
        for change in ({'schema':'future.v1'},{'max_tool_calls':2},{'max_tokens':1},{'max_model_calls':True},
                       {'duration_seconds':0},{'extra':0}):
            with self.assertRaises(ValueError):checked_budget({**policy().descriptor,**change})

    async def test_duplicate_JSON_keys_nonfinite_and_oversize_config_refuse(self):
        for value in ('{"x":1,"x":2}','{"x":NaN}','x'*65537,'['*1200+']'*1200,None):
            with self.assertRaises(ValueError):_json(value)

    async def test_credential_and_tool_URL_validation_is_before_pool_creation(self):
        for token in ('short','x'*257,'密'*40,'x'*32+' ',None):
            with self.assertRaises(ValueError):checked_start_token(token)
        for url in ('file:///tmp/test','http://host:bad','http://user:secret@host','http://bad host','http://host/path','http://host?secret=bad'):
            env=environment();env[TOOL_URL_ENV]=url
            with patch.dict(os.environ,env,clear=True),self.assertRaises(ValueError):StartAPIConfig.from_environment(WRITE_TOKEN)

if __name__=='__main__':unittest.main()
