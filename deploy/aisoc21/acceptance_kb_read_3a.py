"""Checkpointed 3A-06 real KB reads and one bounded Fusion/model run.

The six KB rows are synthetic read fixtures. Direct production-SQL/SAVEPOINT
checks are not an HTTP/database outage claim. Accepted ingress and a started
model call are never replayed by this script. Re-run only a read-only mode
under a separately reviewed checkpoint when an outcome needs investigation.
"""
from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, '/app')
import httpx
from aiokafka import AIOKafkaConsumer, TopicPartition
from app.agents.auto_triage_agent import _build_alert_context
from app.context import knowledge_base as kb
from app.context import organisation_memory as memory
from app.context import tenant_skills as skills
from app.core.kafka_security import kafka_client_kwargs
from app.investigator import ledger
from app.workers.fused_alert_consumer import FusedAlertTriageWorker, build_state, worker_enabled

E = Path('/evidence')
B = '3a-kb-read-20261020'
CONTEXT_PATH = '/api/v1/kb/runbooks/for-triage'
API_SOURCE = Path('/api-knowledge-base.py')


def save(name, value):
    with (E / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
    (E / name).chmod(0o600)


def decoded(value):
    return json.loads(value) if isinstance(value, str) else value


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def instant(value):
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def document_ids(value):
    return {str(row['doc_id']) for row in value['chunks']}


def adopted_ids(value):
    return {str(row['doc_id']) for row in value['runbooks']}


def prompt_messages(content):
    """A ledger prompt is JSON messages, so compare their decoded content."""
    value = json.loads(content)
    assert isinstance(value, list) and value
    return [str(message['content']) for message in value]


def decoded_kb_body(block):
    """The data inside the nonce fence is a JSON string, not raw prose."""
    matches = re.findall(r'<UNTRUSTED_DATA source="knowledge_base">\n(.*?)\n</UNTRUSTED_DATA>', block, re.DOTALL)
    assert len(matches) == 1
    body = json.loads(matches[0])
    assert isinstance(body, str) and body
    return body


def production_sql():
    """Load only the literal SQL/kinds and its pure formatter, no API import."""
    text = API_SOURCE.read_text()
    tree = ast.parse(text, filename=str(API_SOURCE))
    values = {}
    formatter = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {'_TRIAGE_RETRIEVAL_SQL', '_TRIAGE_DOC_KINDS'}:
                    values[target.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in {'_TRIAGE_RETRIEVAL_SQL', '_TRIAGE_DOC_KINDS'}:
                values[node.target.id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef) and node.name == 'triage_retrieval_sql':
            assert not node.decorator_list
            formatter = node
    assert formatter is not None and isinstance(values['_TRIAGE_RETRIEVAL_SQL'], str)
    assert values['_TRIAGE_DOC_KINDS'] == ('runbook', 'playbook', 'sop')
    # The trusted formatter must remain pure: no imports, awaits, callbacks,
    # attributes other than str.format or names outside its literal namespace.
    allowed_names = {'cutoff', '_TRIAGE_RETRIEVAL_SQL', 'str', 'bool'}
    assert all(node.id in allowed_names for node in ast.walk(formatter) if isinstance(node, ast.Name))
    assert all(isinstance(node.func, ast.Attribute) and node.func.attr == 'format'
               for node in ast.walk(formatter) if isinstance(node, ast.Call))
    assert not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.Await))
                   for node in ast.walk(formatter))
    namespace = {'__builtins__': {}, 'str': str, 'bool': bool, **values}
    module = ast.fix_missing_locations(ast.Module(body=[formatter], type_ignores=[]))
    exec(compile(module, str(API_SOURCE), 'exec'), namespace)
    return namespace['triage_retrieval_sql'], list(values['_TRIAGE_DOC_KINDS']), sha(text)


def positional(sql, values):
    """Convert the production statement's named binds, retaining SQL casts."""
    names = []
    def bind(match):
        name = match.group(1)
        assert name in values, name
        if name not in names:
            names.append(name)
        return '$' + str(names.index(name) + 1)
    query = re.sub(r'(?<!:):([a-z_][a-z_0-9]*)', bind, sql)
    return query, [values[name] for name in names]


async def main(mode):
    assert mode in {'before', 'after', 'verify', 'restart', 'resume-model', 'resume-model-v2'}
    resume_checkpoints = [
        'after-started.json', 'after-http-checks.json', 'read-matrix.json',
        'production-sql-savepoint.json', 'ledger-failure-acceptance.json',
        'model-sending.json', 'model-ack.json', 'model-stored-alert.json',
        'model-fused-envelope.json', 'fused-read-starts.json',
        'fixture_mutation_before_model.json', 'model-prompt-budget-preflight.json',
    ]
    if mode == 'resume-model':
        assert all((E / name).is_file() for name in resume_checkpoints), 'Incomplete pre-model checkpoint'
        assert not any((E / name).exists() for name in [
            'model-call-started.json', 'model-sent-messages.json', 'model-metadata.json',
            'model-before-persist.json', 'model-worker-result.json', 'after-acceptance.json',
            'fixture_compaction_before_model.json', 'budget-preflight-resumed.json',
        ]), 'A model or earlier resume may have started; inspect, never replay'
    if mode == 'resume-model-v2':
        required = resume_checkpoints + [
            'resume-model-started.json', 'resume-model-http-checks.json',
            'resume-fused-coordinate.json', 'fixture_compaction_before_model.json',
            'budget-preflight-resumed.json',
        ]
        assert all((E / name).is_file() for name in required), 'Incomplete first-resume checkpoint'
        assert not any((E / name).exists() for name in [
            'model-call-started.json', 'model-sent-messages.json', 'model-metadata.json',
            'model-before-persist.json', 'model-worker-result.json', 'after-acceptance.json',
            'budget-preflight-v2.json', 'resume-v2-preconditions.json',
        ]), 'A model or v2 resume may have started; inspect, never replay'
    save(mode + '-started.json', {'at': datetime.now(timezone.utc), 'resident_worker_enabled': worker_enabled()})
    assert not worker_enabled()
    state = json.loads(Path('/private/state.json').read_text())
    assert state['batch'] == B
    ids, documents = state['identities'], state['documents']
    tenant_a, tenant_b = ids['a']['tenant_id'], ids['b']['tenant_id']
    query = state['query']
    split = instant(state['split_at'])
    checks = []
    resume_prior_check_count = 0
    async with httpx.AsyncClient(base_url='http://api:8000', trust_env=False, timeout=25) as client:
        async def req(method, path, identity='a', *, params=None, body=None, status=200, headers=None):
            auth = {'Authorization': 'Bearer ' + ids[identity]['key']} if identity else {}
            response = await client.request(method, path, params=params, headers=auth if headers is None else headers, json=body)
            checks.append({'method': method, 'path': path, 'params': params, 'identity': identity,
                           'status': response.status_code, 'expected': status})
            log = E / (mode + '-http-checks.json')
            log.write_text(json.dumps(checks[resume_prior_check_count:], indent=2, default=str)); log.chmod(0o600)
            assert response.status_code == status, (response.status_code, response.text[:150])
            return response.json() if response.content else None

        def parameters(tenant, *, q=query, cutoff=None):
            value = {'tenant_id': tenant, 'q': q, 'limit': 3}
            if cutoff is not None:
                value['as_of'] = cutoff.isoformat()
            return value

        async def complete_model_tail(fused, coordinate, alert, probe_run_id, actual_query, mutations, *, resume_info=None):
            from app.agents import auto_triage_agent as agent_module
            memory.clear_cache(); skills.clear_cache(); kb.clear_cache()
            original_invoke = agent_module.safe_ainvoke
            async def observe(llm, messages, *args, **kwargs):
                save('model-sent-messages.json', [{'role': message.type, 'content': message.content} for message in messages])
                response = await original_invoke(llm, messages, *args, **kwargs)
                metadata = response.response_metadata or {}; headers = metadata.get('headers', {}) or {}
                save('model-metadata.json', {'usage_metadata': response.usage_metadata,
                                             'finish_reason': metadata.get('finish_reason'),
                                             'route': headers.get('x-litellm-model-api-base'), 'model': metadata.get('model_name'),
                                             'response_content': response.content})
                return response
            class ObservedWorker(FusedAlertTriageWorker):
                async def _record(self, investigation, **kwargs):
                    actual = {key: asdict(value) if is_dataclass(value) else value for key, value in kwargs.items() if key != 'writer'}
                    save('model-before-persist.json', {'run_id': str(investigation.run_id), 'raw_alert': investigation.raw_alert,
                                                       'knowledge_base_read': investigation.knowledge_base_read,
                                                       'knowledge_base': investigation.knowledge_base,
                                                       'tenant_skill_read': investigation.tenant_skill_read,
                                                       'organisation_memory_read': investigation.organisation_memory_read,
                                                       'exchanges': investigation.llm_exchanges, 'verdict': investigation.verdict,
                                                       'tokens': kwargs.get('tokens', 0), 'tier': kwargs['tier'],
                                                       'findings': investigation.findings, 'model_used': investigation.model_used,
                                                       'actual_kwargs': actual, 'writer_class': type(kwargs['writer']).__name__})
                    await super()._record(investigation, **kwargs)
            agent_module.safe_ainvoke = observe
            try:
                save('model-call-started.json', {'coordinate': coordinate, 'source': 'actual Fusion envelope',
                                                'no_replay_after_this_checkpoint': True})
                result = await ObservedWorker(bootstrap_servers='').triage(fused)
            finally: agent_module.safe_ainvoke = original_invoke
            save('model-worker-result.json', result)
            assert result['shadow'] and result['tier'] == 'llm'
            assert not result['response_dispatched'] and not result['approvals_raised'] and result['source_writeback'] is None
            pre = json.loads((E / 'model-before-persist.json').read_text())
            adopted, org_read, skill_read = pre['knowledge_base_read'], pre['organisation_memory_read'], pre['tenant_skill_read']
            messages = json.loads((E / 'model-sent-messages.json').read_text())
            contents = [str(message['content']) for message in messages]
            assert adopted['status'] == 'success' and adopted['cache']['source'] == 'network'
            assert adopted['query'] == actual_query and documents['a_runbook']['id'] in adopted_ids(adopted)
            assert adopted['prompt_block'] and sha(adopted['prompt_block']) == adopted['prompt_sha256']
            assert any(adopted['prompt_block'] in content for content in contents)
            assert org_read['status'] == 'success' and 'ORG-MEMORY-A-VALID' in org_read['prompt_block']
            assert any(org_read['prompt_block'] in content for content in contents)
            assert skill_read['status'] == 'success' and skill_read['selection']['ref'] == 'skill-a-rule@v3'
            assert any(skill_read['prompt_block'] in content for content in contents)
            assert adopted['adopted_count'] == len(adopted['runbooks']) == len(adopted['citations'])
            available = {row['marker'].upper() for row in adopted['runbooks']}
            metadata = json.loads((E / 'model-metadata.json').read_text())
            response_value = agent_module._parse_llm_response(str(metadata['response_content']))
            rationale = response_value['rationale']
            actual_cited = sorted({marker.upper() for marker in re.findall(r'\[(KB\d{1,3})\]', rationale, re.IGNORECASE)})
            assert adopted['model_citations'] == actual_cited
            assert adopted['unresolvable_citations'] == sorted(set(actual_cited) - available)
            literal_kb_body = decoded_kb_body(adopted['prompt_block'])
            for row in adopted['runbooks']:
                assert row['doc_id'] not in {documents['b_runbook']['id'], documents['a_policy']['id'], documents['a_wiki']['id']}
                assert row['content_sha256'] == sha(row['content'])
                assert row['content'] in literal_kb_body and '[' + row['marker'] + ']' in literal_kb_body
            assert pre['exchanges'] and not pre['exchanges'][0]['prompt_truncated']
            assert not pre['exchanges'][0]['response_truncated']
            save('model-citation-observation.json', {'actual_model_citations': actual_cited,
                                                    'provided_markers': sorted(available),
                                                    'unresolvable_citations': adopted['unresolvable_citations'],
                                                    'model_cited_any_provided_marker': bool(set(actual_cited) & available),
                                                    'rationale': rationale, 'verdict': result['verdict'],
                                                    'no_required_verdict_or_citation_success': True,
                                                    'citation_correctness_or_retrieval_quality_not_claimed': True,
                                                    'second_model_call': False})
            save('after-acceptance.json', {'alerts': {'model': alert}, 'result': result,
                                          'probe_run_id': str(probe_run_id), 'checks': checks,
                                          'fused_coordinate': coordinate, 'fused_consumer_group': None,
                                          'fused_reader_commits': False, 'submitted_alerts': 1, 'model_calls': 1,
                                          'failure_prompt_was_projection_only': True,
                                          'actual_model_kb_read': adopted, 'actual_model_memory_read': org_read,
                                          'actual_model_skill_read': skill_read, 'actual_query': actual_query,
                                          'actual_model_citations': actual_cited,
                                          'unresolvable_citations': adopted['unresolvable_citations'],
                                          'synthetic_kb_rows_expected': 6, 'fixture_mutations': mutations,
                                          'cutoff_validated_before_synthetic_query_term_adaptation': True,
                                          'synthetic_read_fixtures_not_real_sop_or_quality_acceptance': True,
                                          **({'resume': resume_info} if resume_info else {})})

        try:
            if mode == 'resume-model-v2':
                # The first compaction is frozen. This continuation only
                # rereads its rows and original broker record after a bounded
                # runtime boundary-note fix has passed its own locked tests.
                original_checks = json.loads((E / 'after-http-checks.json').read_text())
                first_resume_checks = json.loads((E / 'resume-model-http-checks.json').read_text())
                checks.extend([*original_checks, *first_resume_checks])
                resume_prior_check_count = len(checks)
                ack = json.loads((E / 'model-ack.json').read_text())
                alert = json.loads((E / 'model-stored-alert.json').read_text())
                fused = json.loads((E / 'model-fused-envelope.json').read_text())
                first_mutations = json.loads((E / 'fixture_mutation_before_model.json').read_text())
                compacted = json.loads((E / 'fixture_compaction_before_model.json').read_text())
                first_budget = json.loads((E / 'model-prompt-budget-preflight.json').read_text())
                compact_budget = json.loads((E / 'budget-preflight-resumed.json').read_text())
                first_coordinate = json.loads((E / 'resume-fused-coordinate.json').read_text())['coordinate']
                fault = json.loads((E / 'ledger-failure-acceptance.json').read_text())
                probe_run_id = uuid.UUID(fault['probe_run_id'])
                assert compact_budget['literal_chars'] > compact_budget['literal_limit'] == 8000
                assert not compact_budget['model_invoked'] and not compact_budget['new_run_persisted']
                assert alert['id'] == ack['canonical_alert_id'] == str(fused['alert_row_id']) and fused['tenant_id'] == tenant_a
                actual_state = build_state(fused); assert actual_state is not None
                actual_query = kb.query_for(actual_state.alert_summary or '', actual_state.raw_alert)
                assert actual_query == first_mutations['actual_query'] == compacted['actual_query']
                assert actual_state.alert_summary == first_mutations['actual_alert_summary']
                assert {row['alias'] for row in compacted['mutations']} == {'a_runbook', 'b_runbook'}
                pool = await ledger.get_pool(); assert pool is not None
                async def scoped(tenant, operation):
                    async with pool.acquire() as connection:
                        async with connection.transaction():
                            await ledger._set_rls_context(connection, uuid.UUID(tenant))
                            return await operation(connection)
                async def verify_model_absent(connection):
                    found = dict(await connection.fetchrow(
                        'SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1) runs,'
                        '(SELECT count(*) FROM investigation_events WHERE run_id=$1) events,'
                        '(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1) artifacts,'
                        '(SELECT count(*) FROM aisoc_run_costs WHERE run_id=$1::text) costs', actual_state.run_id))
                    assert found == {'runs': 0, 'events': 0, 'artifacts': 0, 'costs': 0}
                    probe = dict(await connection.fetchrow(
                        'SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1) runs,'
                        '(SELECT count(*) FROM investigation_events WHERE run_id=$1) events,'
                        '(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1) artifacts', probe_run_id))
                    assert probe == {'runs': 1, 'events': 1, 'artifacts': 1}
                    return {'model_run_id': str(actual_state.run_id), 'model_rows_before_resume': found,
                            'existing_probe_run_id': str(probe_run_id), 'existing_probe_counts': probe}
                empty_model = await scoped(tenant_a, verify_model_absent)
                current_rows = []
                for mutation in compacted['mutations']:
                    expected = mutation['after']; tenant = str(expected['tenant_id'])
                    alias = mutation['alias']
                    assert str(expected['id']) == documents[alias]['id']
                    async def read_row(connection, expected=expected, tenant=tenant):
                        row = dict(await connection.fetchrow(
                            'SELECT id,tenant_id,title,content,created_at,updated_at FROM aisoc_kb_documents WHERE id=$1 AND tenant_id=$2',
                            uuid.UUID(str(expected['id'])), uuid.UUID(tenant)))
                        assert str(row['id']) == str(expected['id']) and str(row['tenant_id']) == tenant
                        assert row['title'] == expected['title'] and row['content'] == expected['content']
                        assert row['created_at'] == instant(expected['created_at']) and row['updated_at'] == instant(expected['updated_at'])
                        return row
                    current_rows.append(await scoped(tenant, read_row))

                topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
                starts = json.loads((E / 'fused-read-starts.json').read_text())
                consumer = AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                            **kafka_client_kwargs(), enable_auto_commit=False, group_id=None)
                await consumer.start()
                try:
                    assigned = [TopicPartition(topic, row['partition']) for row in starts]
                    consumer.assign(assigned)
                    bounds = await consumer.end_offsets(assigned)
                    for row in starts: consumer.seek(TopicPartition(topic, row['partition']), row['offset'])
                    matches = []
                    for _ in range(100):
                        records = await consumer.getmany(timeout_ms=200, max_records=100)
                        for partition, messages in records.items():
                            for message in messages:
                                if message.offset >= bounds[partition]: continue
                                value = json.loads(message.value)
                                if str(value.get('alert_row_id')) == ack['canonical_alert_id']:
                                    assert value == fused
                                    matches.append({'topic': topic, 'partition': message.partition, 'offset': message.offset,
                                                    'sha256': hashlib.sha256(message.value).hexdigest()})
                        positions = {partition: await consumer.position(partition) for partition in bounds}
                        if all(positions[partition] >= bound for partition, bound in bounds.items()): break
                    assert len(matches) == 1 and matches[0] == first_coordinate
                    coordinate = matches[0]
                finally:
                    with contextlib.suppress(asyncio.CancelledError): await consumer.stop()
                save('resume-v2-fused-coordinate.json', {'coordinate': coordinate, 'same_as_first_resume': True,
                                                        'exact_saved_envelope_reobserved': True, 'consumer_group': None,
                                                        'commits': False, 'new_messages_sent': 0})
                a_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, q=actual_query))
                b_http = await req('GET', CONTEXT_PATH, 'reader_b', params=parameters(tenant_b, q=actual_query))
                assert documents['a_runbook']['id'] in document_ids(a_http)
                assert document_ids(b_http) == {documents['b_runbook']['id']}
                assert documents['b_runbook']['id'] not in document_ids(a_http)
                from app.agents import auto_triage_agent as agent_module
                memory.clear_cache(); skills.clear_cache(); kb.clear_cache()
                budget_state = build_state(fused); assert budget_state is not None
                budget_state.organisation_memory_read = await memory.fetch_organisation_memory(tenant_a)
                budget_state.organisation_memory = list(budget_state.organisation_memory_read['statements'])
                budget_worker = FusedAlertTriageWorker(bootstrap_servers='')
                await budget_worker._attach_tenant_skill(budget_state)
                await budget_worker._attach_runbooks(budget_state)
                await budget_worker._attach_recent_dispositions(budget_state)
                await budget_worker._attach_identity_context(budget_state)
                nonce = agent_module.make_nonce()
                context = _build_alert_context(budget_state, nonce=nonce)
                system = agent_module.prompt_text('triage.system') + '\n\n' + agent_module.system_rule(nonce)
                prompt = json.dumps([{'role': 'system', 'content': system}, {'role': 'user', 'content': context}], sort_keys=True, default=str)
                budget = {'literal_limit': 8000, 'original_literal_chars': first_budget['literal_chars'],
                          'first_resumed_literal_chars': compact_budget['literal_chars'], 'literal_chars': len(prompt),
                          'prompt_sha256': sha(prompt), 'kb_read': budget_state.knowledge_base_read,
                          'org_block_chars': len(budget_state.organisation_memory_read['prompt_block']),
                          'skill_block_chars': len(budget_state.tenant_skill_read['prompt_block']),
                          'kb_block_chars': len(budget_state.knowledge_base_read['prompt_block']),
                          'boundary_note_sha256': sha(kb.BOUNDARY_NOTE), 'boundary_note_chars': len(kb.BOUNDARY_NOTE),
                          'model_invoked': False, 'new_run_persisted': False, 'new_ingress': 0,
                          'fixture_mutated': False, 'existing_probe_reexecuted': False,
                          'original_query_and_fused_envelope_unchanged': True}
                save('budget-preflight-v2.json', budget)
                assert len(prompt) <= 8000, 'Boundary-note fix still exceeds cap; stop before model'
                required = resume_checkpoints + ['resume-model-started.json', 'resume-model-http-checks.json',
                                                'resume-fused-coordinate.json', 'fixture_compaction_before_model.json',
                                                'budget-preflight-resumed.json']
                resume_info = {'mode': mode, 'reason': 'Two pre-model budget stops; compacted fixtures retained, equivalent shorter runtime boundary note',
                               'original_budget_chars': first_budget['literal_chars'],
                               'first_resumed_budget_chars': compact_budget['literal_chars'], 'resumed_budget_chars': len(prompt),
                               'checkpoint_sha256': {name: hashlib.sha256((E / name).read_bytes()).hexdigest() for name in required},
                               'model_ledger_absent_before_resume': empty_model, 'coordinate_recovered_read_only': coordinate,
                               'compacted_rows_unchanged': current_rows, 'fixture_mutated': False,
                               'a_actual_query_http': a_http, 'b_actual_query_http': b_http,
                               'original_after_http_check_count': len(original_checks),
                               'first_resume_http_check_count': len(first_resume_checks),
                               'prior_http_check_count': resume_prior_check_count,
                               'resume_http_check_count': len(checks) - resume_prior_check_count,
                               'new_ingress': 0, 'new_restarts': 0, 'pg_fault_probe_reexecuted': False,
                               'same_saved_alert_fused_query_probe_used': True,
                               'fixture_compaction_evidence': 'fixture_compaction_before_model.json'}
                save('resume-v2-preconditions.json', resume_info)
                mutations = [*first_mutations['mutations'], *compacted['mutations']]
                await complete_model_tail(fused, coordinate, alert, probe_run_id, actual_query, mutations, resume_info=resume_info)
                return

            if mode == 'resume-model':
                # Continue the one accepted alert after a *pre-model* budget
                # failure. No ingress, PG fault, key mutation or restart here.
                checks.extend(json.loads((E / 'after-http-checks.json').read_text()))
                resume_prior_check_count = len(checks)
                ack = json.loads((E / 'model-ack.json').read_text())
                alert = json.loads((E / 'model-stored-alert.json').read_text())
                fused = json.loads((E / 'model-fused-envelope.json').read_text())
                mutation_checkpoint = json.loads((E / 'fixture_mutation_before_model.json').read_text())
                previous_budget = json.loads((E / 'model-prompt-budget-preflight.json').read_text())
                fault_checkpoint = json.loads((E / 'ledger-failure-acceptance.json').read_text())
                probe_run_id = uuid.UUID(fault_checkpoint['probe_run_id'])
                assert fault_checkpoint['rolled_back']['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
                assert fault_checkpoint['recovered']['counts'] == {'runs': 1, 'events': 1, 'artifacts': 1}
                assert previous_budget['literal_chars'] > previous_budget['literal_limit'] == 8000
                assert not previous_budget['model_invoked'] and not previous_budget['new_run_persisted']
                assert alert['id'] == ack['canonical_alert_id'] == str(fused['alert_row_id'])
                assert fused['tenant_id'] == tenant_a
                actual_state = build_state(fused); assert actual_state is not None
                actual_query = kb.query_for(actual_state.alert_summary or '', actual_state.raw_alert)
                assert actual_query == mutation_checkpoint['actual_query']
                assert actual_state.alert_summary == mutation_checkpoint['actual_alert_summary']
                pool = await ledger.get_pool(); assert pool is not None
                async def scoped(tenant, operation):
                    async with pool.acquire() as connection:
                        async with connection.transaction():
                            await ledger._set_rls_context(connection, uuid.UUID(tenant))
                            return await operation(connection)
                async def verify_no_model_run(connection):
                    model_run_id = actual_state.run_id
                    found = dict(await connection.fetchrow(
                        'SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1) runs,'
                        '(SELECT count(*) FROM investigation_events WHERE run_id=$1) events,'
                        '(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1) artifacts,'
                        '(SELECT count(*) FROM aisoc_run_costs WHERE run_id=$1::text) costs', model_run_id))
                    assert found == {'runs': 0, 'events': 0, 'artifacts': 0, 'costs': 0}
                    probe = dict(await connection.fetchrow(
                        'SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1) runs,'
                        '(SELECT count(*) FROM investigation_events WHERE run_id=$1) events,'
                        '(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1) artifacts', probe_run_id))
                    assert probe == {'runs': 1, 'events': 1, 'artifacts': 1}
                    return {'model_run_id': str(model_run_id), 'model_rows_before_resume': found,
                            'existing_probe_run_id': str(probe_run_id), 'existing_probe_counts': probe}
                empty_model = await scoped(tenant_a, verify_no_model_run)

                # Recover the broker coordinate without a group or commit.
                # Read only the bounded offsets that now exist, and demand
                # exact equality with the previously captured Fusion value.
                topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
                starts = json.loads((E / 'fused-read-starts.json').read_text())
                consumer = AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                            **kafka_client_kwargs(), enable_auto_commit=False, group_id=None)
                await consumer.start()
                try:
                    assigned = [TopicPartition(topic, row['partition']) for row in starts]
                    consumer.assign(assigned)
                    bounds = await consumer.end_offsets(assigned)
                    for row in starts: consumer.seek(TopicPartition(topic, row['partition']), row['offset'])
                    matches = []
                    for _ in range(100):
                        records = await consumer.getmany(timeout_ms=200, max_records=100)
                        for partition, messages in records.items():
                            for message in messages:
                                if message.offset >= bounds[partition]: continue
                                value = json.loads(message.value)
                                if str(value.get('alert_row_id')) == ack['canonical_alert_id']:
                                    assert value == fused, 'Broker value differs from frozen pre-model envelope'
                                    matches.append({'topic': topic, 'partition': message.partition, 'offset': message.offset,
                                                    'sha256': hashlib.sha256(message.value).hexdigest()})
                        positions = {partition: await consumer.position(partition) for partition in bounds}
                        if all(positions[partition] >= bound for partition, bound in bounds.items()): break
                    assert len(matches) == 1, 'Missing/duplicate bounded original Fusion record; do not re-ingress'
                    coordinate = matches[0]
                finally:
                    with contextlib.suppress(asyncio.CancelledError): await consumer.stop()
                save('resume-fused-coordinate.json', {'coordinate': coordinate, 'original_saved_starts': starts,
                                                     'bounded_ends': [{'partition': part.partition, 'offset': offset} for part, offset in bounds.items()],
                                                     'saved_fused_file_sha256': hashlib.sha256((E / 'model-fused-envelope.json').read_bytes()).hexdigest(),
                                                     'exact_saved_envelope_reobserved': True,
                                                     'consumer_group': None, 'commits': False, 'new_messages_sent': 0})

                # Only the newly seeded A/B runbooks may be shortened. Derive
                # English FTS lexemes with the actual PG configuration, then
                # remove a redundant lexeme only if that same PG query still
                # matches the whole candidate body. At most one trial/lexeme.
                save('fixture-compaction-started.json', {'actual_query': actual_query,
                                                        'only_new_document_ids': [documents[alias]['id'] for alias in ['a_runbook', 'b_runbook']],
                                                        'original_literal_chars': previous_budget['literal_chars'],
                                                        'model_calls': 0, 'new_ingress': 0})
                sop = 'Synthetic SOP: Verify current auth/process/job proof.\nTest terms: '
                async def compact(connection, alias, tenant, title):
                    document = documents[alias]
                    old = dict(await connection.fetchrow(
                        'SELECT id,tenant_id,title,content,created_at,updated_at FROM aisoc_kb_documents WHERE id=$1 AND tenant_id=$2',
                        uuid.UUID(document['id']), uuid.UUID(tenant)))
                    prior_mutations = [row for row in mutation_checkpoint['mutations'] if row['alias'] == alias]
                    expected_content = prior_mutations[-1]['after']['content'] if prior_mutations else document['content']
                    assert old['content'] == expected_content and old['title'] == document['title']
                    lexemes = list(await connection.fetchval("SELECT tsvector_to_array(to_tsvector('english',$1))", actual_query))
                    assert 0 < len(lexemes) <= 38 and len(lexemes) == len(set(lexemes))
                    remaining = list(lexemes); trials = []
                    def body(terms): return sop + ' '.join(terms)
                    assert await connection.fetchval("SELECT to_tsvector('english',$1) @@ plainto_tsquery('english',$2)", body(remaining), actual_query)
                    for lexeme in sorted(lexemes, key=lambda value: (-len(value), value)):
                        candidate = [value for value in remaining if value != lexeme]
                        matches_query = bool(await connection.fetchval(
                            "SELECT to_tsvector('english',$1) @@ plainto_tsquery('english',$2)", body(candidate), actual_query))
                        trials.append({'removed_lexeme': lexeme, 'candidate_still_matches': matches_query,
                                       'removed': matches_query, 'candidate_content_chars': len(body(candidate))})
                        if matches_query: remaining = candidate
                    content = body(remaining)
                    assert len(content) < len(old['content'])
                    result = await connection.execute(
                        'UPDATE aisoc_kb_documents SET title=$1,content=$2,updated_at=now() WHERE id=$3 AND tenant_id=$4 AND title=$5 AND content=$6',
                        title, content, uuid.UUID(document['id']), uuid.UUID(tenant), old['title'], old['content'])
                    assert result == 'UPDATE 1'
                    current = dict(await connection.fetchrow(
                        'SELECT id,tenant_id,title,content,created_at,updated_at FROM aisoc_kb_documents WHERE id=$1 AND tenant_id=$2',
                        uuid.UUID(document['id']), uuid.UUID(tenant)))
                    assert current['created_at'] == old['created_at'] and current['updated_at'] > split
                    return {'alias': alias, 'before': old, 'after': current,
                            'old_content_sha256': sha(old['content']), 'new_content_sha256': sha(content),
                            'old_title_sha256': sha(old['title']), 'new_title_sha256': sha(title),
                            'original_unique_lexemes': lexemes, 'retained_lexemes': remaining,
                            'lexeme_removal_trials': trials, 'trial_count': len(trials), 'trial_limit': 38,
                            'reason': 'New synthetic read fixture exceeds literal prompt budget; shorten title and remove only FTS-redundant terms',
                            'new_text_not_claimed_to_exist_at_split': True, 'original_query_unchanged': True}
                compactions = []
                for name, alias in [('a', 'a_runbook'), ('b', 'b_runbook')]:
                    async def operation(connection, alias=alias, name=name):
                        return await compact(connection, alias, ids[name]['tenant_id'], name.upper())
                    compactions.append(await scoped(ids[name]['tenant_id'], operation))
                kb.clear_cache()
                a_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, q=actual_query))
                b_http = await req('GET', CONTEXT_PATH, 'reader_b', params=parameters(tenant_b, q=actual_query))
                assert documents['a_runbook']['id'] in document_ids(a_http)
                assert document_ids(b_http) == {documents['b_runbook']['id']}
                assert documents['b_runbook']['id'] not in document_ids(a_http)
                compact_read = (await kb.fetch_runbooks(tenant_a, query=actual_query)).as_read()
                assert compact_read['status'] == 'success' and documents['a_runbook']['id'] in adopted_ids(compact_read)
                save('fixture_compaction_before_model.json', {'actual_query': actual_query, 'mutations': compactions,
                                                             'a_actual_query_http': a_http, 'b_actual_query_http': b_http,
                                                             'a_actual_query_read': compact_read,
                                                             'cutoff_acceptance_completed_before_mutation': True,
                                                             'only_new_synthetic_a_b_runbooks_mutated': True,
                                                             'original_query_and_fused_envelope_unchanged': True,
                                                             'synthetic_structure_test_not_real_sop_or_retrieval_quality': True,
                                                             'new_alerts': 0, 'new_model_calls': 0})

                from app.agents import auto_triage_agent as agent_module
                memory.clear_cache(); skills.clear_cache(); kb.clear_cache()
                budget_state = build_state(fused); assert budget_state is not None
                budget_state.organisation_memory_read = await memory.fetch_organisation_memory(tenant_a)
                budget_state.organisation_memory = list(budget_state.organisation_memory_read['statements'])
                budget_worker = FusedAlertTriageWorker(bootstrap_servers='')
                await budget_worker._attach_tenant_skill(budget_state)
                await budget_worker._attach_runbooks(budget_state)
                await budget_worker._attach_recent_dispositions(budget_state)
                await budget_worker._attach_identity_context(budget_state)
                nonce = agent_module.make_nonce()
                context = _build_alert_context(budget_state, nonce=nonce)
                system = agent_module.prompt_text('triage.system') + '\n\n' + agent_module.system_rule(nonce)
                prompt = json.dumps([{'role': 'system', 'content': system}, {'role': 'user', 'content': context}], sort_keys=True, default=str)
                budget = {'literal_limit': 8000, 'original_literal_chars': previous_budget['literal_chars'],
                          'literal_chars': len(prompt), 'prompt_sha256': sha(prompt),
                          'kb_read': budget_state.knowledge_base_read,
                          'org_block_chars': len(budget_state.organisation_memory_read['prompt_block']),
                          'skill_block_chars': len(budget_state.tenant_skill_read['prompt_block']),
                          'kb_block_chars': len(budget_state.knowledge_base_read['prompt_block']),
                          'model_invoked': False, 'new_run_persisted': False,
                          'new_ingress': 0, 'existing_probe_reexecuted': False,
                          'original_query_and_fused_envelope_unchanged': True}
                save('budget-preflight-resumed.json', budget)
                assert len(prompt) <= 8000, 'Compacted fixture still exceeds cap; stop before model and inspect'
                resume_info = {'mode': mode, 'reason': 'Previous attempt stopped before any model at literal budget check',
                               'original_budget_chars': previous_budget['literal_chars'], 'resumed_budget_chars': len(prompt),
                               'checkpoint_sha256': {name: hashlib.sha256((E / name).read_bytes()).hexdigest() for name in resume_checkpoints},
                               'model_ledger_absent_before_resume': empty_model,
                               'coordinate_recovered_read_only': coordinate, 'new_ingress': 0,
                               'new_restarts': 0, 'pg_fault_probe_reexecuted': False,
                               'prior_http_check_count': resume_prior_check_count,
                               'resume_http_check_count': len(checks) - resume_prior_check_count,
                               'same_saved_alert_fused_query_probe_used': True,
                               'fixture_compaction_evidence': 'fixture_compaction_before_model.json'}
                save('resume-model-preconditions.json', resume_info)
                mutations = [*mutation_checkpoint['mutations'], *compactions]
                await complete_model_tail(fused, coordinate, alert, probe_run_id, actual_query, mutations, resume_info=resume_info)
                return

            if mode == 'before':
                token = os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '').strip()
                assert token, 'Existing token is used only to reproduce the refused old header'
                await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a), status=401)
                await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                          headers={'X-AiSOC-Service-Token': token})
                kb.clear_cache()
                old = await kb.fetch_runbooks(tenant_a, query=query)
                assert not old.runbooks
                save('before-acceptance.json', {'checks': checks, 'old_bearer_actual_http_status': 401,
                                              'old_shared_header_actual_http_status': 401,
                                              'old_reader_state': old.as_state(),
                                              'model_invoked': False, 'new_alerts_submitted': 0})
                return

            if mode in {'verify', 'restart'}:
                previous = json.loads((E / 'after-acceptance.json').read_text())
                model_id, probe_id = previous['result']['run_id'], previous['probe_run_id']
                async def read_run(run_id, event_count, artifact_count):
                    base = '/api/v1/investigations/' + run_id
                    run = await req('GET', base)
                    events = await req('GET', base + '/events')
                    artifacts = await req('GET', base + '/artifacts')
                    assert run['status'] == 'completed' and run['event_count'] == event_count
                    assert len(events['items']) == event_count and len(artifacts) == artifact_count
                    details = [await req('GET', base + '/artifacts/' + item['id']) for item in artifacts]
                    verdicts = [item for item in events['items'] if item['kind'] == 'triage_verdict']
                    receipts = [item for item in details if item['kind'] == 'knowledge_base_read']
                    assert len(verdicts) == len(receipts) == 1
                    receipt = json.loads(receipts[0]['content'])
                    assert receipt == verdicts[0]['payload']['knowledge_base_read']
                    for artifact in details:
                        blob = artifact['content'].encode()
                        assert artifact['event_id'] == verdicts[0]['id']
                        assert hashlib.sha256(blob).hexdigest() == artifact['sha256']
                        assert len(blob) == artifact['size_bytes']
                    return run, events, artifacts, details, receipt

                run, events, artifacts, details, adopted = await read_run(model_id, 2, 5)
                probe_run, probe_events, probe_artifacts, probe_details, failed = await read_run(probe_id, 1, 1)
                pre = json.loads((E / 'model-before-persist.json').read_text())
                assert adopted == pre['knowledge_base_read']
                assert adopted['status'] == 'success' and adopted['adopted_count'] >= 1
                assert sha(adopted['prompt_block']) == adopted['prompt_sha256']
                prompts = prompt_messages(next(item['content'] for item in details if item['kind'] == 'llm_prompt'))
                assert any(adopted['prompt_block'] in content for content in prompts)
                verdict = next(item for item in events['items'] if item['kind'] == 'triage_verdict')
                for kind in ['organisation_memory_read', 'tenant_skill_read']:
                    artifact = next(item for item in details if item['kind'] == kind)
                    assert json.loads(artifact['content']) == verdict['payload'][kind] == pre[kind]
                assert pre['tenant_skill_read']['selection']['ref'] == 'skill-a-rule@v3'
                assert failed == json.loads((E / 'actual-auth-failure-read.json').read_text())
                assert failed['status'] == 'unavailable' and failed['reason'] == 'auth_failed'
                assert not failed['runbooks'] and not failed['prompt_block'] and probe_run['total_tokens'] == 0
                assert {item['kind'] for item in artifacts} == {'llm_prompt', 'llm_response', 'organisation_memory_read', 'tenant_skill_read', 'knowledge_base_read'}
                current = await req('GET', '/api/v1/alerts/' + previous['alerts']['model']['id'])
                for key in ['raw_event', 'severity', 'status', 'disposition', 'resolved_at', 'priority']:
                    assert current.get(key) == previous['alerts']['model'].get(key), key
                result = {'run': run, 'events': events, 'artifacts': artifacts, 'artifact_details': details,
                          'probe_run': probe_run, 'probe_events': probe_events, 'probe_artifacts': probe_artifacts,
                          'probe_artifact_details': probe_details, 'checks': checks,
                          'actual_model_citations': adopted['model_citations'],
                          'unresolvable_citations': adopted['unresolvable_citations'],
                          'manual_alert_state_preserved': True, 'model_invoked': False, 'new_alerts_submitted': 0}
                if mode == 'verify':
                    await req('GET', '/api/v1/investigations/' + model_id, 'b', status=404)
                    await req('GET', '/api/v1/investigations/' + model_id, 'denied', status=403)
                    await req('GET', '/api/v1/investigations/' + model_id, None, status=401)
                    await req('GET', '/api/v1/investigations/' + probe_id, 'b', status=404)
                else:
                    earlier = json.loads((E / 'verify-acceptance.json').read_text())
                    for key in ['run', 'events', 'artifacts', 'artifact_details', 'probe_run', 'probe_events', 'probe_artifacts', 'probe_artifact_details']:
                        assert result[key] == earlier[key], key
                save(mode + '-acceptance.json', result)
                return

            # Real HTTP authentication, non-empty A/B isolation, kind filters.
            initial_a = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a))
            initial_b = await req('GET', CONTEXT_PATH, 'reader_b', params=parameters(tenant_b))
            expected_a = {documents[alias]['id'] for alias in ['a_runbook', 'a_updated_after', 'a_created_after']}
            assert initial_a['tenant_id'] == tenant_a and initial_b['tenant_id'] == tenant_b
            assert document_ids(initial_a) == expected_a and document_ids(initial_b) == {documents['b_runbook']['id']}
            assert all(row['doc_kind'] in {'runbook', 'playbook', 'sop'} for row in initial_a['chunks'])
            inferred = await req('GET', CONTEXT_PATH, 'reader_a', params={'q': query, 'limit': 3})
            assert inferred == initial_a
            await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_b), status=403)
            await req('GET', CONTEXT_PATH, 'denied', params=parameters(tenant_a), status=403)
            await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401)
            await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                      headers={'Authorization': 'Bearer invalid-acceptance-credential'})
            await req('GET', CONTEXT_PATH, None, params=parameters(tenant_a), status=401,
                      headers={'X-AiSOC-Service-Token': os.environ.get('AISOC_AGENTS_SERVICE_TOKEN', '')})
            fixture = json.loads(Path('/fixture.json').read_text())
            base_alert = fixture['alert']
            forbidden = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/forbidden-ingress')),
                         'source': 'socai2-' + B, 'source_event_ids': [B + '-forbidden'],
                         'event_time': datetime.now(timezone.utc).isoformat()}
            await req('POST', '/api/v1/alert-ingress', 'reader_a', body=forbidden, status=403)
            await req('POST', '/api/v1/kb/ingest', 'reader_a', status=403,
                      body={'title': 'Forbidden probe document', 'content': 'A structurally valid synthetic document.', 'doc_kind': 'runbook'})
            await req('DELETE', '/api/v1/kb/documents/' + documents['a_runbook']['id'], 'reader_a', status=403)
            frozen_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, cutoff=split))
            assert document_ids(frozen_http) == {documents['a_runbook']['id']}
            assert frozen_http['excluded_after_cutoff'] == frozen_http['excluded_after_update'] == 1
            assert frozen_http['excluded_after_cutoff_total'] == 2 and frozen_http['without_timestamp'] == 0
            all_excluded = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, cutoff=split - timedelta(days=2)))
            assert all_excluded['chunks'] == [] and all_excluded['excluded_after_cutoff_total'] == 3
            no_match_http = await req('GET', CONTEXT_PATH, 'reader_a', params=parameters(tenant_a, q='unmatchable-socai2-kb-probe-938817'))
            assert no_match_http['chunks'] == []
            preview = await req('GET', '/api/v1/kb/documents/' + documents['a_runbook']['id'])
            assert len(preview['content_preview']) <= 200

            kb.clear_cache()
            live_a = await kb.fetch_runbooks(tenant_a, query=query)
            cached_a = await kb.fetch_runbooks(tenant_a, query=query)
            live_b = await kb.fetch_runbooks(tenant_b, query=query)
            read_a, read_cached, read_b = live_a.as_read(), cached_a.as_read(), live_b.as_read()
            assert read_a['status'] == read_b['status'] == 'success'
            assert read_a['cache']['source'] == 'network' and read_cached['cache']['source'] == 'memory'
            assert adopted_ids(read_a) == expected_a and adopted_ids(read_b) == {documents['b_runbook']['id']}
            no_match = (await kb.fetch_runbooks(tenant_a, query='unmatchable-socai2-kb-probe-938817')).as_read()
            empty_query = (await kb.fetch_runbooks(tenant_a, query='')).as_read()
            assert no_match['status'] == 'no_match' and not no_match['runbooks']
            assert empty_query['status'] == 'not_requested' and not empty_query['runbooks']
            original_enabled = os.environ.get('AISOC_TRIAGE_KB_ENABLED')
            try:
                os.environ['AISOC_TRIAGE_KB_ENABLED'] = '0'
                disabled = (await kb.fetch_runbooks(tenant_a, query=query)).as_read()
                assert disabled['status'] == 'disabled' and not disabled['runbooks']
            finally:
                if original_enabled is None: os.environ.pop('AISOC_TRIAGE_KB_ENABLED', None)
                else: os.environ['AISOC_TRIAGE_KB_ENABLED'] = original_enabled
            original_keys_file = os.environ['AISOC_TRIAGE_KB_KEYS_FILE']
            with tempfile.TemporaryDirectory(prefix='kb-read-probe-') as temporary:
                path = Path(temporary) / 'keys.json'
                with path.open('x') as stream: json.dump({}, stream)
                path.chmod(0o600)
                try:
                    os.environ['AISOC_TRIAGE_KB_KEYS_FILE'] = str(path)
                    missing = (await kb.fetch_runbooks(tenant_a, query=query)).as_read()
                    assert missing['status'] == 'unavailable' and missing['reason'] == 'not_configured' and not missing['runbooks']
                    path.write_text(json.dumps({tenant_a: ids['reader_b']['key']}))
                    wrong_identity = (await kb.fetch_runbooks(tenant_a, query=query)).as_read()
                    assert wrong_identity['status'] == 'unavailable' and wrong_identity['reason'] == 'auth_failed'
                    assert wrong_identity['http_status'] == 403 and not wrong_identity['runbooks']
                finally:
                    os.environ['AISOC_TRIAGE_KB_KEYS_FILE'] = original_keys_file

            pool = await ledger.get_pool()
            assert pool is not None
            async def scoped(tenant, operation):
                async with pool.acquire() as connection:
                    async with connection.transaction():
                        await ledger._set_rls_context(connection, uuid.UUID(tenant))
                        return await operation(connection)
            async def reader_active(active):
                async def update(connection):
                    result = await connection.execute('UPDATE api_keys SET is_active=$1 WHERE id=$2 AND tenant_id=$3',
                                                      active, uuid.UUID(ids['reader_a']['key_id']), uuid.UUID(tenant_a))
                    assert result == 'UPDATE 1'
                await scoped(tenant_a, update)
            def probe_envelope(label):
                return {'tenant_id': tenant_a, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/selection/' + label)),
                        'alert': {**base_alert, 'source': 'socai2-' + B}}
            async def attach(envelope):
                investigation = build_state(envelope)
                assert investigation is not None
                await FusedAlertTriageWorker(bootstrap_servers='')._attach_runbooks(investigation)
                return investigation

            original_ttl = kb._CACHE_TTL_S
            try:
                await reader_active(False)
                cached_after_server_revoke = (await kb.fetch_runbooks(tenant_a, query=query)).as_read()
                assert cached_after_server_revoke['status'] == 'success' and cached_after_server_revoke['cache']['source'] == 'memory'
                kb._CACHE_TTL_S = 0
                revoked_refresh = (await kb.fetch_runbooks(tenant_a, query=query)).as_read()
                assert revoked_refresh['status'] == 'unavailable' and revoked_refresh['reason'] == 'auth_failed'
                assert revoked_refresh['http_status'] == 401 and not revoked_refresh['runbooks']
                assert revoked_refresh['cache']['freshness'] == 'expired'
                projection = await attach(probe_envelope('failure'))
                failed_prompt = _build_alert_context(projection, nonce='probe-only')
                auth_failure = deepcopy(projection.knowledge_base_read)
                assert auth_failure['status'] == 'unavailable' and auth_failure['reason'] == 'auth_failed'
                assert not auth_failure['runbooks'] and not auth_failure['prompt_block']
                assert 'status=unavailable' in failed_prompt and 'auth_failed' in failed_prompt
                assert 'KB-A-RUNBOOK' not in failed_prompt
                save('actual-auth-failure-read.json', auth_failure)
                save('failure-prompt-projection.json', {'model_invoked': False, 'probe_only': True,
                                                       'read': auth_failure, 'context': failed_prompt,
                                                       'does_not_claim_model_saw_failure': True})
            finally:
                await reader_active(True)
                kb._CACHE_TTL_S = original_ttl
            kb.clear_cache()
            recovered = (await kb.fetch_runbooks(tenant_a, query=query)).as_read()
            assert recovered['status'] == 'success' and recovered['cache']['source'] == 'network'
            original_url, original_timeout = kb._API_URL, kb._TIMEOUT_S
            try:
                kb._API_URL, kb._TIMEOUT_S = 'http://127.0.0.1:1', .5
                transport = (await kb.fetch_runbooks(tenant_a, query=query)).as_read()
                assert transport['status'] == 'unavailable' and transport['reason'] == 'transport_error' and not transport['runbooks']
            finally:
                kb._API_URL, kb._TIMEOUT_S = original_url, original_timeout

            # Frozen port calls the real HTTP reader at split; it may not use now.
            from app.replay.shadow import ContextSnapshot, FrozenTriageContextReader
            frozen_reader = FrozenTriageContextReader(ContextSnapshot(split_at=split))
            frozen_result = await frozen_reader.retrieve_runbooks(tenant_a, query=query)
            frozen_read = frozen_result.as_read()
            assert frozen_read['status'] == 'success'
            assert adopted_ids(frozen_read) == {documents['a_runbook']['id']}
            assert instant(frozen_read['as_of']) == instant(frozen_read['requested_as_of']) == split
            assert frozen_read['excluded_after_cutoff_total'] == 2 and frozen_read['excluded_after_update'] == 1
            frozen_note = frozen_reader.as_method_note()
            assert frozen_note['runbooks_frozen'] == 1 and frozen_note['runbooks_dropped_after_split'] == 2
            save('read-matrix.json', {'a_network': read_a, 'a_cached': read_cached, 'b_network': read_b,
                                      'no_match': no_match, 'empty_query': empty_query, 'disabled': disabled,
                                      'not_configured': missing, 'wrong_identity': wrong_identity,
                                      'default_cache_after_server_revocation': cached_after_server_revoke,
                                      'forced_ttl_zero_revoked_refresh': revoked_refresh,
                                      'actual_revoked_key_worker': auth_failure, 'recovery': recovered,
                                      'transport_failure': transport, 'frozen': frozen_read, 'frozen_method_note': frozen_note,
                                      'frozen_http': frozen_http, 'all_excluded_http': all_excluded,
                                      'no_match_http': no_match_http, 'document_preview': preview,
                                      'missing_time_boundary_unit_only_due_not_null_schema': state['no_timestamp_fixture'],
                                      'unhonoured_echo_rejection_covered_in_unit_not_fake_live_service': True,
                                      'controls_probe_process_only': True, 'model_calls': 0})

            formatter, kinds, api_source_hash = production_sql()
            params = {'q': query, 'tenant_id': uuid.UUID(tenant_a), 'kinds': kinds, 'limit': 3, 'as_of': split}
            direct_sql, arguments = positional(formatter(cutoff=True), params)
            async def savepoint_probe(connection):
                pid = await connection.fetchval('SELECT pg_backend_pid()')
                before = [dict(row) for row in await connection.fetch(direct_sql, *arguments)]
                try:
                    async with connection.transaction():
                        await connection.execute('SELECT 1/0')
                except Exception as error:
                    assert type(error).__name__ == 'DivisionByZeroError'
                    failure = {'exception': type(error).__name__, 'operation': 'SELECT 1/0', 'savepoint_rolled_back': True}
                else: raise AssertionError('Real PostgreSQL error expected')
                after = [dict(row) for row in await connection.fetch(direct_sql, *arguments)]
                assert before == after and await connection.fetchval('SELECT pg_backend_pid()') == pid
                assert {str(row['id']) for row in after if row['id'] is not None} == {documents['a_runbook']['id']}
                assert after[0]['excluded_after_cutoff_total'] == 2 and after[0]['excluded_after_update'] == 1
                return {'source_sha256': api_source_hash, 'sql_sha256': sha(formatter(cutoff=True)),
                        'source': str(API_SOURCE), 'production_formatter_and_statement_used': True,
                        'backend_pid': pid, 'failure': failure, 'before': before, 'after': after,
                        'same_session_recovered': True, 'http_or_shared_database_outage_injected': False,
                        'api_http_503_or_outage_propagation_claimed': False}
            save('production-sql-savepoint.json', await scoped(tenant_a, savepoint_probe))

            # Actual PG failure at the newly added artifact, same transaction.
            probe_run_id = uuid.uuid5(uuid.NAMESPACE_URL, B + '/ledger-failure-probe')
            probe_kwargs = {'run_id': probe_run_id, 'alert_id': None, 'tenant_ref': tenant_a,
                            'alert_summary': 'Probe-only KB read transaction recovery',
                            'raw_alert': {'batch': B, 'probe_only': True}, 'tier': 'probe_only',
                            'verdict': 'needs_review', 'confidence': 0.0,
                            'rationale': 'Probe-only transaction test; no model verdict or alert mutation.',
                            'shadow': True, 'knowledge_base_read': auth_failure}
            async def probe_rows():
                async def read(connection):
                    counts = dict(await connection.fetchrow('SELECT (SELECT count(*) FROM investigation_runs WHERE id=$1) runs,(SELECT count(*) FROM investigation_events WHERE run_id=$1) events,(SELECT count(*) FROM investigation_artifacts WHERE run_id=$1) artifacts', probe_run_id))
                    events = [dict(row) for row in await connection.fetch('SELECT seq,kind,payload FROM investigation_events WHERE run_id=$1 ORDER BY seq', probe_run_id)]
                    artifacts = [dict(row) for row in await connection.fetch('SELECT id,kind,content,sha256,event_id FROM investigation_artifacts WHERE run_id=$1 ORDER BY created_at,id', probe_run_id)]
                    return {'counts': counts, 'events': events, 'artifacts': artifacts}
                return await scoped(tenant_a, read)
            assert (await probe_rows())['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
            original_get_pool = ledger.get_pool
            fault_hits = []
            class FaultConnection:
                def __init__(self, connection): self.connection = connection
                def __getattr__(self, name): return getattr(self.connection, name)
                async def execute(self, sql, *args):
                    if 'INSERT INTO investigation_artifacts' in sql and len(args) > 4 and args[4] == 'knowledge_base_read':
                        fault_hits.append('knowledge_base_read INSERT -> actual SELECT 1/0')
                        return await self.connection.execute('SELECT 1/0')
                    return await self.connection.execute(sql, *args)
            class FaultAcquire:
                async def __aenter__(self):
                    self.acquisition = pool.acquire()
                    return FaultConnection(await self.acquisition.__aenter__())
                async def __aexit__(self, *args): return await self.acquisition.__aexit__(*args)
            class FaultPool:
                def acquire(self): return FaultAcquire()
            async def failing_pool(): return FaultPool()
            save('ledger-fault-started.json', {'run_id': str(probe_run_id), 'probe_only': True,
                                              'fault': 'actual SELECT 1/0 at knowledge base artifact insert'})
            ledger.get_pool = failing_pool
            try:
                try: await ledger.persist_auto_triage(**probe_kwargs)
                except ledger.LedgerPersistError as error:
                    failure = {'exception': type(error).__name__, 'cause': type(error.__cause__).__name__}
                else: raise AssertionError('Actual PG error was swallowed')
            finally: ledger.get_pool = original_get_pool
            assert fault_hits and failure['cause'] == 'DivisionByZeroError'
            rolled_back = await probe_rows()
            assert rolled_back['counts'] == {'runs': 0, 'events': 0, 'artifacts': 0}
            assert await ledger.persist_auto_triage(**probe_kwargs)
            first_probe = await probe_rows()
            assert first_probe['counts'] == {'runs': 1, 'events': 1, 'artifacts': 1}
            assert decoded(first_probe['events'][0]['payload'])['knowledge_base_read'] == auth_failure
            assert first_probe['artifacts'][0]['kind'] == 'knowledge_base_read'
            assert json.loads(first_probe['artifacts'][0]['content']) == auth_failure
            assert await ledger.persist_auto_triage(**probe_kwargs)
            repeated_probe = await probe_rows()
            assert repeated_probe == first_probe
            save('ledger-failure-acceptance.json', {'probe_run_id': str(probe_run_id), 'probe_only': True,
                                                   'model_invoked': False, 'failure': failure, 'fault_hits': fault_hits,
                                                   'rolled_back': rolled_back, 'recovered': first_probe,
                                                   'same_run_retry': repeated_probe, 'cost_rows_expected': 0,
                                                   'actual_failed_read_persisted': True})

            # Observe exactly the accepted alert's production Fusion envelope.
            topic = os.environ['KAFKA_TOPIC_ALERTS_FUSED']
            consumer = AIOKafkaConsumer(topic, bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],
                                        **kafka_client_kwargs(), enable_auto_commit=False, group_id=None)
            await consumer.start()
            try:
                partitions = sorted(consumer.partitions_for_topic(topic) or [])
                assert partitions
                assigned = [TopicPartition(topic, partition) for partition in partitions]
                consumer.unsubscribe(); consumer.assign(assigned)
                starts = await consumer.end_offsets(assigned)
                for partition, offset in starts.items(): consumer.seek(partition, offset)
                save('fused-read-starts.json', [{'partition': partition.partition, 'offset': offset} for partition, offset in starts.items()])
                body = {**base_alert, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/model-alert')),
                        'source': 'socai2-' + B, 'source_event_ids': [str(uuid.uuid5(uuid.NAMESPACE_URL, B + '/model-event'))],
                        'event_time': datetime.now(timezone.utc).isoformat(), 'tags': [B]}
                save('model-sending.json', body)
                ack = await req('POST', '/api/v1/alert-ingress', body=body, status=202)
                save('model-ack.json', ack)
                for _ in range(80):
                    response = await client.get('/api/v1/alerts/' + ack['canonical_alert_id'], headers={'Authorization': 'Bearer ' + ids['a']['key']})
                    if response.status_code == 200: break
                    assert response.status_code == 404
                    await asyncio.sleep(.25)
                else: raise AssertionError('Accepted ingress outcome unknown; inspect, never resubmit')
                alert = response.json(); save('model-stored-alert.json', alert)
                fused = coordinate = None
                for _ in range(100):
                    records = await consumer.getmany(timeout_ms=200, max_records=50)
                    for _, messages in records.items():
                        for message in messages:
                            candidate = json.loads(message.value)
                            if str(candidate.get('alert_row_id')) == ack['canonical_alert_id']:
                                assert fused is None, 'Unexpected second delivery in bounded probe'
                                assert candidate['tenant_id'] == tenant_a
                                fused = candidate
                                coordinate = {'topic': topic, 'partition': message.partition, 'offset': message.offset,
                                              'sha256': hashlib.sha256(message.value).hexdigest()}
                    if fused is not None: break
                assert fused is not None, 'Missing fused result; do not resubmit'
                save('model-fused-envelope.json', fused)
            finally:
                with contextlib.suppress(asyncio.CancelledError): await consumer.stop()

            # AND-based FTS includes the actual Fusion narrative in query_for.
            # Adapt only new synthetic A/B rows if necessary, before the sole
            # model call and after all historical-cutoff assertions above.
            actual_state = build_state(fused); assert actual_state is not None
            actual_query = kb.query_for(actual_state.alert_summary or '', actual_state.raw_alert)
            assert actual_query
            query_before = {}; mutations = []
            for name, alias in [('a', 'a_runbook'), ('b', 'b_runbook')]:
                tenant = ids[name]['tenant_id']
                found = await req('GET', CONTEXT_PATH, 'reader_' + name, params=parameters(tenant, q=actual_query))
                query_before[name] = found
                if documents[alias]['id'] in document_ids(found): continue
                async def add_terms(connection, alias=alias, tenant=tenant):
                    doc = documents[alias]
                    old = dict(await connection.fetchrow('SELECT id,tenant_id,content,created_at,updated_at FROM aisoc_kb_documents WHERE id=$1 AND tenant_id=$2', uuid.UUID(doc['id']), uuid.UUID(tenant)))
                    assert old['content'] == doc['content'] and str(old['tenant_id']) == tenant
                    content = old['content'] + '\n\nTest retrieval terms (synthetic, not policy): ' + actual_query
                    result = await connection.execute('UPDATE aisoc_kb_documents SET content=$1,updated_at=now() WHERE id=$2 AND tenant_id=$3 AND content=$4', content, uuid.UUID(doc['id']), uuid.UUID(tenant), old['content'])
                    assert result == 'UPDATE 1'
                    current = dict(await connection.fetchrow('SELECT id,tenant_id,content,created_at,updated_at FROM aisoc_kb_documents WHERE id=$1 AND tenant_id=$2', uuid.UUID(doc['id']), uuid.UUID(tenant)))
                    assert current['created_at'] == old['created_at'] and current['updated_at'] > split
                    return {'alias': alias, 'before': old, 'after': current, 'old_content_sha256': sha(old['content']),
                            'new_content_sha256': sha(content), 'reason': 'Actual production query_for includes Fusion narrative; exact AND terms were absent',
                            'new_text_not_claimed_to_exist_at_split': True}
                mutations.append(await scoped(tenant, add_terms))
            kb.clear_cache()
            model_read_preflight = (await kb.fetch_runbooks(tenant_a, query=actual_query)).as_read()
            b_actual = (await kb.fetch_runbooks(tenant_b, query=actual_query)).as_read()
            assert model_read_preflight['status'] == b_actual['status'] == 'success'
            assert documents['a_runbook']['id'] in adopted_ids(model_read_preflight)
            assert adopted_ids(b_actual) == {documents['b_runbook']['id']}
            assert documents['b_runbook']['id'] not in adopted_ids(model_read_preflight)
            save('fixture_mutation_before_model.json', {'actual_query': actual_query, 'actual_alert_summary': actual_state.alert_summary,
                                                       'query_before': query_before, 'mutations': mutations,
                                                       'mutation_performed': bool(mutations), 'a_actual_query_read': model_read_preflight,
                                                       'b_actual_query_read': b_actual, 'cutoff_acceptance_completed_before_mutation': True,
                                                       'only_new_synthetic_a_b_runbooks_mutated': True,
                                                       'original_query_and_fused_envelope_unchanged': True, 'model_calls': 0,
                                                       'synthetic_structure_test_not_real_sop_or_retrieval_quality': True})

            # Check the exact ledger serialization budget before entering the
            # worker/model call. A failure here cannot trigger an LLM fallback
            # verdict or consume the one model call merely to discover a cap.
            from app.agents import auto_triage_agent as agent_module
            budget_state = build_state(fused); assert budget_state is not None
            budget_state.organisation_memory_read = await memory.fetch_organisation_memory(tenant_a)
            budget_state.organisation_memory = list(budget_state.organisation_memory_read['statements'])
            budget_worker = FusedAlertTriageWorker(bootstrap_servers='')
            await budget_worker._attach_tenant_skill(budget_state)
            await budget_worker._attach_runbooks(budget_state)
            await budget_worker._attach_recent_dispositions(budget_state)
            await budget_worker._attach_identity_context(budget_state)
            nonce = agent_module.make_nonce()
            preflight_context = _build_alert_context(budget_state, nonce=nonce)
            preflight_system = agent_module.prompt_text('triage.system') + '\n\n' + agent_module.system_rule(nonce)
            preflight_prompt = json.dumps([{'role': 'system', 'content': preflight_system},
                                          {'role': 'user', 'content': preflight_context}], sort_keys=True, default=str)
            save('model-prompt-budget-preflight.json', {'literal_limit': 8000,
                                                       'literal_chars': len(preflight_prompt),
                                                       'prompt_sha256': sha(preflight_prompt),
                                                       'kb_read': budget_state.knowledge_base_read,
                                                       'org_block_chars': len(budget_state.organisation_memory_read['prompt_block']),
                                                       'skill_block_chars': len(budget_state.tenant_skill_read['prompt_block']),
                                                       'kb_block_chars': len(budget_state.knowledge_base_read['prompt_block']),
                                                       'model_invoked': False, 'new_run_persisted': False})
            assert len(preflight_prompt) <= 8000, 'Literal prompt would be truncated; inspect new synthetic fixture before any model call'
            await complete_model_tail(fused, coordinate, alert, probe_run_id, actual_query, mutations)
        finally:
            await ledger.close_pool()


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
