"""Read-only admission audit; no model, ingress, polling, commit or budget claim.

Run once on host21. Writes only a new evidence directory; does not deploy.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import os
import subprocess
import sys

R = Path('/opt/sting-aisoc-socai2')
S = R / 'source'
B = '3a-admission-review-20261020'
E = R / 'evidence' / B
RESUME = False
OLD = R / 'evidence/3a-triage-admission-20261020'
BUDGET = R / 'evidence/3a-triage-budget-20261020'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, data):
    if RESUME and (E / name).exists():
        assert json.loads((E / name).read_text()) == data, name
        return
    with (E / name).open('x') as f:
        json.dump(data, f, indent=2, default=str)
        f.write('\n')
    (E / name).chmod(0o600)


def inspect(name):
    return json.loads(subprocess.check_output(['docker', 'inspect', name]))[0]


def env(name):
    return dict(v.split('=', 1) for v in inspect(name)['Config']['Env'])


def container_json(code, payload=None, service='agents'):
    proc = subprocess.run(['docker', 'exec', '-i', 'socai2-' + service + '-1', 'python', '-c', code],
                          input=json.dumps(payload), text=True, capture_output=True)
    if proc.returncode:
        # No locals/env or exception bodies enter the public output.
        save('container-probe-failure.json', {'exit_code': proc.returncode,
             'stderr_sha256': hashlib.sha256(proc.stderr.encode()).hexdigest()})
        raise RuntimeError('Read-only container probe failed; inspect controlled evidence')
    return json.loads(proc.stdout.splitlines()[-1])


def main(mode='first'):
    global RESUME
    assert mode in {'first', 'resume-flags'}
    RESUME = mode == 'resume-flags'
    os.umask(0o077)
    if RESUME:
        assert (E / 'first-failure.json').is_file() and not (E / 'acceptance.json').exists()
    else:
        E.mkdir(mode=0o700, exist_ok=False)
    save('scope.json', {'batch': B, 'plan_sha256': sha(S / 'docs/operations/3a-admission-review-plan.md'),
                       'runtime_changes': 0, 'real_models': 0, 'new_messages': 0,
                       'offset_commits': 0, 'restarts': 0})
    from prepare_2a import snapshot
    from prepare_triage_request_3a import material, readers, SDK
    from prepare_identity_read_3a import TABLES
    from finish_model_triage_3a import METRICS

    admin = env('spirithub-postgres-1')['POSTGRES_USER']

    def pg(sql):
        # All calls, including helper SELECTs, are server-enforced read-only.
        proc = subprocess.run(['docker', 'exec', '-i', 'spirithub-postgres-1', 'psql',
                               '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
                               '-U', admin, '-d', 'aisoc'], input='BEGIN READ ONLY;\n' + sql + '\nROLLBACK;',
                              text=True, capture_output=True)
        if proc.returncode:
            raise RuntimeError('Read-only PG observation failed')
        return proc

    db = SimpleNamespace(pg=pg)
    receipt = json.loads((S / 'docs/operations/3a-triage-budget.json').read_text())
    old_receipt = json.loads((S / 'docs/operations/3a-triage-admission.json').read_text())
    old_hashes = {row['path']: row['sha256'] for row in old_receipt['raw_artifacts']}
    for name, digest in old_hashes.items():
        assert sha(OLD / name) == digest, name
    save('frozen-evidence.json', {'old_batch_raw_files_verified': len(old_hashes),
          'receipt_sha256': sha(S / 'docs/operations/3a-triage-admission.json'),
          'p01_inputs': {n: sha(OLD / n) for n in ['p01-sent-messages.json', 'p01-model-metadata.json',
                                                 'p01-worker-result.json', 'p01-stored-alert.json']}})

    def observation():
        tables = {t: [hashlib.sha256(row['material'].encode()).hexdigest() for row in material(db, t)]
                  for t in ['alerts'] + TABLES}
        budget = json.loads(pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM "
                               "(SELECT * FROM socai2_triage_budget_reservations ORDER BY run_id) t;").stdout)
        runs = json.loads(pg("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT r.id,r.tenant_id,r.status,"
                             "r.model_used,r.total_tokens,(SELECT json_agg(e.seq ORDER BY e.seq) FROM "
                             "investigation_events e WHERE e.run_id=r.id) AS event_seqs "
                             "FROM investigation_runs r JOIN socai2_triage_budget_reservations b ON b.run_id=r.id "
                             "ORDER BY r.id) t;").stdout)
        return {'environment': snapshot(), 'materials': tables, 'budget': budget, 'runs': runs,
                'readers': readers(db), 'policy_sha256': sha(R / 'private/triage-budget-3a/policy.json'),
                'migrations': int(pg('SELECT count(*) FROM aisoc_schema_migrations;').stdout.strip()),
                'gateway': json.loads(subprocess.check_output(['docker', 'exec', 'socai2-litellm-1',
                                                               'python', '-c', METRICS]))}

    before = observation()
    save('before.json', before)
    assert before['budget'] == json.loads((BUDGET / 'budget-after-restart.json').read_text())
    assert before['policy_sha256'] == receipt['postconditions']['budget_policy_sha256_final']
    assert before['gateway'] == receipt['postconditions']['gateway_before_after']
    for name, value in receipt['postconditions']['material_counts'].items():
        assert len(before['materials'][name]) == value['total'], name
    state = json.loads((R / 'private/app-triage-budget-3a.json').read_text())
    assert before['readers'] == state['reader_credentials']
    for n, digest in receipt['postconditions']['images'].items():
        item = inspect('socai2-' + n + '-1')
        assert item['Image'] == digest and item['State']['Health']['Status'] == 'healthy'

    runtime_code = '''import os,json,hashlib
from pathlib import Path
from app.workers import fused_alert_consumer as w
from app.context.organisation_memory import _credential
from app.llm.factory import make_chat_model
variables=['AISOC_ORG_MEMORY_KEYS_FILE','AISOC_TENANT_SKILLS_KEYS_FILE','AISOC_TRIAGE_KB_KEYS_FILE','AISOC_TRIAGE_DISPOSITIONS_KEYS_FILE','AISOC_TRIAGE_IDENTITY_KEYS_FILE']
tenants=json.load(__import__('sys').stdin)
print(json.dumps({'worker':w.worker_enabled(),'escalation':w._escalation_enabled(),'memory_writeback':w._memory_writeback_enabled(),'approvals':w._approvals_enabled(),'alert_graph':w.alert_trigger.deployment_enabled(),'uid':os.getuid(),'reader_maps_resolve':all(_credential(t,keys_file_env=v) for t in tenants for v in variables),'source':{'services/agents/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}}))'''
    runtime = container_json(runtime_code, [state['identities'][n]['tenant_id'] for n in ['a', 'b']])
    assert all(runtime[k] is False for k in ['worker', 'escalation', 'memory_writeback', 'alert_graph'])
    assert runtime['reader_maps_resolve'] and runtime['uid'] == 10001
    assert runtime['source'] == json.loads((BUDGET / 'tests-agents-final.json').read_text())['tested_runtime_source_sha256']
    api_source = json.loads(subprocess.check_output(['docker', 'exec', 'socai2-api-1', 'python', '-c',
        "from pathlib import Path;import hashlib,json;print(json.dumps({'services/api/app/'+str(p.relative_to('/app/app')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/app/app').rglob('*.py')}))"]))
    assert all(sha(S / p) == h for p, h in {**api_source, **runtime['source']}.items())
    ae, pe = env('socai2-agents-1'), env('socai2-api-1')
    runtime['approval_guard_explicitly_disabled'] = ae.get('AISOC_AGENT_RAISE_APPROVALS') == '0'
    runtime['approval_guard_missing_is_admission_blocker'] = runtime['approvals'] is True
    at = (ae.get('AISOC_API_SERVICE_TOKEN') or ae.get('AISOC_SERVICE_TOKEN') or '').strip()
    pt = (pe.get('AISOC_API_SERVICE_TOKEN') or pe.get('AISOC_SERVICE_TOKEN') or '').strip()
    runtime['tool_identity'] = {'agents_service_token_present': bool(at), 'api_service_token_present': bool(pt),
                                'nonempty_service_tokens_match': bool(at and pt and at == pt),
                                'legacy_agents_api_key_present': bool(ae.get('AISOC_AGENTS_API_KEY')),
                                'http_authorization_retested': False}
    runtime['api_source'] = api_source
    runtime['sdk'] = container_json(SDK)
    save('runtime.json', runtime)
    fe = env('socai2-fusion-1')
    save('kafka-configuration.json', {'agents_bootstrap_present': bool(ae.get('KAFKA_BOOTSTRAP_SERVERS')),
          'agents_security_protocol': ae.get('KAFKA_SECURITY_PROTOCOL', 'PLAINTEXT'),
          'fusion_bootstrap_present': bool(fe.get('KAFKA_BOOTSTRAP_SERVERS')),
          'fusion_security_protocol': fe.get('KAFKA_SECURITY_PROTOCOL', 'PLAINTEXT'),
          'offset_observer_service': 'fusion', 'resident_agents_config_changed': False})

    model = json.loads((OLD / 'p01-model-metadata.json').read_text())
    reply = json.loads(model['response_content'])
    stored = json.loads((OLD / 'p01-stored-alert.json').read_text())
    messages = json.loads((OLD / 'p01-sent-messages.json').read_text())
    gate_code = '''import json,sys
from types import SimpleNamespace
from app.confidence.groundedness import score_groundedness
from app.workers.fused_alert_consumer import FusedAlertTriageWorker
x=json.load(sys.stdin);r=score_groundedness(x['rationale'],json.dumps(x['messages']))
w=FusedAlertTriageWorker.__new__(FusedAlertTriageWorker);out={}
for verdict in ['true_positive','benign_true_positive']:
 s=SimpleNamespace(findings=[x['rationale']],confidence_basis=[],raw_alert=x['alert'],alert_summary='',groundedness=None)
 v,c=w._apply_groundedness_gate(s,verdict,0.92)
 out[verdict]={'verdict':v,'confidence':c,'indicator_score':s.groundedness}
print(json.dumps({'scorer':{'score':r.score,'grounded':r.grounded,'hallucinated':r.hallucinated},'worker_gate':out,'counterfactual_btp_is_not_a_model_sample':True}))'''
    gate = container_json(gate_code, {'rationale': reply['rationale'], 'alert': stored, 'messages': messages})
    assert gate['scorer']['score'] == 1.0 and gate['scorer']['grounded'] == gate['scorer']['hallucinated'] == []
    assert gate['worker_gate']['true_positive']['indicator_score'] is None
    assert gate['worker_gate']['benign_true_positive'] == {'verdict': 'benign_true_positive', 'confidence': .92, 'indicator_score': 1.0}
    save('p01-gate-reproduction.json', gate)

    offset_code = '''import asyncio,os,json
from aiokafka import AIOKafkaConsumer,TopicPartition
from app.core.kafka_security import kafka_client_kwargs
async def main():
 out={};security=kafka_client_kwargs();assert security['security_protocol']=='SSL'
 for alias in ['a_done','b_done','a_unknown','a_denied','b_denied','b_extra']:
  topic='socai2.test.3a-triage-budget-20261020.'+alias
  c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],group_id=topic+'.worker',enable_auto_commit=False,**security)
  await c.start();tp=TopicPartition(topic,0);c.assign([tp])
  try:out[alias]={'committed':await c.committed(tp),'end':(await c.end_offsets([tp]))[tp]}
  finally:await c.stop()
 print(json.dumps(out))
asyncio.run(main())'''
    offsets_before = container_json(offset_code, service='fusion')
    assert offsets_before == {n: {'committed': 0 if n == 'a_denied' else 1, 'end': 1}
                              for n in ['a_done', 'b_done', 'a_unknown', 'a_denied', 'b_denied', 'b_extra']}
    policy = json.loads((R / 'private/triage-budget-3a/policy.json').read_text())
    usage = []
    for tenant, limits in policy['tenants'].items():
        row = json.loads(pg("SELECT row_to_json(t) FROM (SELECT clock_timestamp() AS observed_at, count(*) "
             "FILTER (WHERE reserved_at > clock_timestamp() - " + str(limits['window_seconds']) + " * interval '1 second') AS calls,"
             "COALESCE(sum(charged_tokens) FILTER (WHERE reserved_at > clock_timestamp() - " + str(limits['window_seconds']) +
             " * interval '1 second'),0) AS reserved_units,count(*) FILTER (WHERE settled_at IS NULL) AS unsettled "
             "FROM socai2_triage_budget_reservations WHERE tenant_id='" + str(__import__('uuid').UUID(tenant)) + "') t;").stdout)
        usage.append({'tenant_id': tenant, 'limits': limits, 'usage': row,
                      'next_reservation_blocked_by_unsettled': row['unsettled'] + 1 > limits['max_unsettled']})
    save('budget-and-offsets.json', {'policy_sha256': before['policy_sha256'], 'usage': usage,
         'offsets': offsets_before, 'unknown_not_replayed_or_refunded': True,
         'no_natural_window_expiry_test': True})
    after = observation()
    assert before == after
    assert container_json(offset_code, service='fusion') == offsets_before
    assert all(sha(OLD / name) == digest for name, digest in old_hashes.items())
    save('after.json', after)
    save('acceptance.json', {'batch': B, 'read_only_pg_transactions': True,
          'before_after_equal': True, 'source_counts': {'agents': len(runtime['source']), 'api': len(api_source)},
          'frozen_raw_files_preserved': len(old_hashes), 'real_models': 0, 'new_messages': 0,
          'offset_commits': 0, 'restarts': 0, 'new_credentials': 0, 'runtime_changes': 0,
          'indicator_checks_cover_p01_time_authorization': False, 'worker_admission_accepted': False})
    print(json.dumps({'batch': B, 'read_only_audit_complete': True, 'real_models': 0,
                      'worker_admission_accepted': False}))


if __name__ == '__main__':
    main(*sys.argv[1:])
