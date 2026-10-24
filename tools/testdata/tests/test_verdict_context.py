"""Use a separate Agents interpreter so the API's app package cannot collide."""
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
PREAMBLE = r'''
import asyncio, copy, inspect, json, socket, sys
from datetime import UTC, datetime
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'tools/testdata'))
import verdict_context as adapter
assert 'app' not in sys.modules, 'adapter import must remain lazy'
sys.path.insert(0, str(Path(sys.argv[1]) / 'services/agents'))
from app.replay.shadow import ContextSnapshot, FrozenTriageContextReader
from app.context import dispositions, identity, knowledge_base, organisation_memory, tenant_skills
from app.workers.triage_persistence import CONTEXT_FREEZE_KINDS, CUTOFF
split = datetime(2026, 10, 23, tzinfo=UTC)
snapshot = ContextSnapshot(split_at=split,
    statements=({'statement':'An existing supplied statement'},),
    priors={'signature':{'disposition':'needs_review','confidence':0.4}},
    skills=({'skill_id':'kept','body':{'guidance':'supplied only'}},))
original = copy.deepcopy(snapshot)
reader = adapter.make_context_reader(snapshot)
assert isinstance(reader, FrozenTriageContextReader)

def denied(*args, **kwargs):
    raise AssertionError('network or live context source forbidden')
async def async_denied(*args, **kwargs):
    raise AssertionError('network or live context source forbidden')
socket.create_connection = denied
socket.socket.connect = denied
import httpx
httpx.AsyncClient.request = async_denied
httpx.Client.request = denied
knowledge_base.fetch_runbooks = async_denied
dispositions.fetch_recent_dispositions = async_denied
identity.fetch_identity_context = async_denied
organisation_memory.fetch_organisation_memory = async_denied
tenant_skills.fetch_tenant_skills = async_denied
'''


def run(code):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-c", PREAMBLE + code, str(ROOT)],
                            text=True, capture_output=True, env=env, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_original_interfaces_and_types_have_explicit_disabled_provenance_without_network():
    result = run(r'''
assert {name for name, kind in CONTEXT_FREEZE_KINDS.items() if kind == CUTOFF} == {
    'retrieve_runbooks', 'recent_dispositions', 'fetch_identity_context'}
for name, kind in CONTEXT_FREEZE_KINDS.items():
    old = inspect.signature(getattr(FrozenTriageContextReader, name)).parameters
    new = inspect.signature(getattr(type(reader), name)).parameters
    assert [(n,p.kind,p.default) for n,p in old.items()] == [(n,p.kind,p.default) for n,p in new.items()]
async def main():
    rows = [await reader.retrieve_runbooks('tenant', query='powershell'),
            await reader.recent_dispositions('tenant', rule_id='rule', entities=['host']),
            await reader.fetch_identity_context('tenant', accounts=['account'])]
    assert [type(r) for r in rows] == [knowledge_base.RunbookRetrieval, dispositions.RecentDispositions, identity.IdentityContext]
    for row, module in zip(rows, (knowledge_base, dispositions, identity)):
        facts = row.as_read()
        assert not row
        assert facts['status'] == 'disabled'
        assert facts['reason'] == adapter.EXCLUDED_REASON
        assert facts['source'] == adapter.SOURCE
        assert facts['http_status'] is None and facts['as_of'] is None
        assert facts['requested_as_of'] == split.isoformat()
        assert facts['cache']['freshness'] == 'not_available'
        text = module.render_read_status(facts)
        assert 'disabled' in text and 'not queried' in text and 'does not establish' in text
    assert snapshot == original
    print(json.dumps({'statuses':[row.as_read()['status'] for row in rows]}))
asyncio.run(main())
''')
    assert result["statuses"] == ["disabled"] * 3


def test_snapshot_memory_skills_priors_keep_original_behavior_and_input_is_not_modified():
    assert run(r'''
base = FrozenTriageContextReader(copy.deepcopy(original))
async def main():
    for name, args in [('fetch_statements', ('tenant',)), ('fetch_organisation_memory', ('tenant',)),
                       ('fetch_skills', ('tenant',)), ('fetch_tenant_skills', ('tenant',)),
                       ('lookup_prior', ('tenant','signature'))]:
        assert getattr(type(reader), name) is getattr(FrozenTriageContextReader, name)
        assert await getattr(reader, name)(*args) == await getattr(base, name)(*args)
    # A caller editing its input snapshot after construction cannot modify the reader.
    snapshot.skills[0]['body']['guidance'] = 'caller mutation'
    assert (await reader.fetch_skills('tenant'))[0]['body']['guidance'] == 'supplied only'
    returned = await reader.fetch_statements('tenant')
    returned[0]['statement'] = 'mutated returned projection'
    assert (await reader.fetch_statements('tenant'))[0]['statement'] == original.statements[0]['statement']
    assert reader.snapshot == original
    print(json.dumps({'snapshot_preserved': True}))
asyncio.run(main())
''')["snapshot_preserved"]


def test_each_disabled_read_and_method_note_are_fresh_and_do_not_claim_zero_matches():
    assert run(r'''
async def main():
    first = await reader.retrieve_runbooks('tenant', query='q')
    first.read['status'] = 'success'
    first.read['runbooks'].append({'content':'mutated'})
    second = await reader.retrieve_runbooks('tenant', query='q')
    assert second.as_read()['status'] == 'disabled' and not second.runbooks
    note = reader.as_method_note()
    assert note['external_context']['runbooks']['requested_by_triage'] == 2
    for source in note['external_context'].values():
        assert source['source_queried'] is False
        assert source['received_count'] is None and source['matched_count'] is None
        assert source['cutoff_applied'] is False
    assert 'runbooks_frozen' not in note
    note['external_context']['runbooks']['status'] = 'success'
    assert reader.as_method_note()['external_context']['runbooks']['status'] == 'excluded'
    assert snapshot == original
    print(json.dumps({'fresh': True}))
asyncio.run(main())
''')["fresh"]
