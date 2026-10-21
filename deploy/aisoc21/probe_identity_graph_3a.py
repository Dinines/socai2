"""Exercise production account reads against only this batch's marked graph.

The sole mutation changes two explicitly named synthetic history properties.
It demonstrates that an Employee import cutoff cannot reconstruct a former
department/manager projection. No HTTP, ingestion, model, schema or shared
outage operation is performed. A checkpoint forbids blind operator replay.
"""
from pathlib import Path
import asyncio
import hashlib
import json
import os
import subprocess
import sys

R = Path('/opt/sting-aisoc-socai2')
B = '3a-identity-read-20261020'
E = R / ('evidence/' + B)
IMAGE = 'socai2-api:dispositions-3a-20261020'
IMAGE_ID = 'sha256:41bae3dde2fdccb230622f30af99b6ef807469c930cb7b6aed1baf860eb7cd3d'
OUTPUTS = ['graph-production-read.json', 'graph-history-mutation.json',
           'graph-query-failure.json', 'graph-material-after-read-probe.json']


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def value_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def save(directory, name, value):
    with (directory / name).open('x') as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')
    (directory / name).chmod(0o600)


async def container_probe():
    from copy import deepcopy
    from dataclasses import asdict
    from datetime import datetime
    from neo4j import AsyncGraphDatabase, WRITE_ACCESS
    from app.db import neo4j as graph_db
    from app.services import incident_context as production

    directory = Path('/evidence')
    fixture_path = directory / 'graph-fixtures.json'
    fixture = json.loads(fixture_path.read_text())
    assert fixture['batch'] == B and fixture['node_count'] == 27 and fixture['relationship_count'] == 22
    assert not any((directory / name).exists() for name in OUTPUTS)
    seeded = json.loads((directory / 'graph-material-seeded.json').read_text())
    tenant_a, tenant_b = fixture['tenants']['a'], fixture['tenants']['b']
    nodes = {node['alias']: node for node in fixture['nodes']}
    split = datetime.fromisoformat(fixture['split_at'])
    source = {name: file_sha(Path('/source') / name) for name in [
        'services/api/app/services/incident_context.py', 'services/api/app/db/neo4j.py',
        'services/api/app/api/v1/endpoints/graph.py']}
    query_sha = hashlib.sha256(production._IDENTITY_BY_ACCOUNT_CYPHER.encode()).hexdigest()
    assert graph_db._driver is None, 'General graph driver must remain disabled'

    async def snapshot():
        async with graph_db.get_identity_read_session() as session:
            async def rows(query):
                result = await session.run(query)
                return [dict(row) async for row in result]
            material = {
                'nodes': await rows('MATCH(n) RETURN elementId(n) AS element_id,labels(n) AS labels,properties(n) AS props ORDER BY n.id,element_id'),
                'relationships': await rows('MATCH(a)-[r]->(b) RETURN elementId(r) AS element_id,a.id AS origin,b.id AS target,type(r) AS type,properties(r) AS props ORDER BY origin,type,target,element_id'),
                'indexes': await rows('SHOW INDEXES YIELD name,type,entityType,labelsOrTypes,properties,state RETURN name,type,entityType,labelsOrTypes,properties,state ORDER BY name'),
                'constraints': await rows('SHOW CONSTRAINTS YIELD name,type,entityType,labelsOrTypes,properties RETURN name,type,entityType,labelsOrTypes,properties ORDER BY name'),
            }
        # Match the original seeded snapshot's driver/default-str projection.
        return json.loads(json.dumps(material, default=str))

    async def read(tenant, account, *, cutoff=None, limit=5, session=None):
        found = await production.read_identity_context_for_accounts(
            tenant, [account], limit=limit, as_of=cutoff, session=session)
        value = asdict(found)
        assert value['status'] in {'success', 'no_match'}, value['reason']
        assert value['without_timestamp'] == len(value['identities'])
        assert value['candidate_count'] == value['eligible_count'] + value['excluded_after_cutoff'] + value['excluded_unverifiable_import']
        assert value['eligible_count'] == len(value['identities']) + value['truncated_count']
        for row in value['identities']:
            assert row['account'].lower() == account
            projection = {'tenant_id': tenant, **{key: row[key] for key in production.IDENTITY_SOURCE_FIELDS}}
            assert value_sha(projection) == row['row_source_sha256']
        return value

    def one(value):
        assert value['status'] == 'success' and len(value['identities']) == 1
        return value['identities'][0]

    before = await snapshot()
    assert before == seeded
    assert len(before['nodes']) == 27 and len(before['relationships']) == 22
    assert len(before['indexes']) == 2 and not before['constraints']
    reads = {}
    for name, tenant, account, cutoff, limit in [
        ('model_a', tenant_a, fixture['model_account'], None, 5),
        ('model_b', tenant_b, fixture['model_account'], None, 5),
        ('cross_a', tenant_a, fixture['cross_account'], None, 5),
        ('cross_b', tenant_b, fixture['cross_account'], None, 5),
        ('unlinked_live', tenant_a, fixture['unlinked_account'], None, 5),
        ('unlinked_frozen', tenant_a, fixture['unlinked_account'], split, 5),
        ('multi', tenant_a, fixture['multi_account'], None, 5),
        ('cutoff_live', tenant_a, fixture['cutoff_account'], None, 2),
        ('cutoff_frozen', tenant_a, fixture['cutoff_account'], split, 1),
    ]:
        reads[name] = await read(tenant, account, cutoff=cutoff, limit=limit)
    for alias in ['a', 'b']:
        row = one(reads['model_' + alias])
        assert row['identity_id'] == nodes[alias + '-identity']['props']['id']
        assert row['employee_id'] == nodes[alias + '-employee']['props']['id']
        assert row['department_id'] == nodes[alias + '-department']['props']['id']
        assert row['manager_id'] == nodes[alias + '-manager']['props']['id']
        assert row['is_active'] is (alias == 'a')
        for key in ['identity_id', 'employee_id', 'department_id', 'manager_id']:
            assert row[key.replace('_id', '_id_kind')] == 'business_id'
    for name in ['cross_a', 'unlinked_live']:
        row = one(reads[name])
        assert row['employee_linked'] is False and row['employee_id'] is None
        assert row['department_id'] is None and row['manager_id'] is None
        assert row['employee'] is row['department'] is row['manager'] is None
        assert set(row['relationship_source'].values()) == {None}
    assert reads['cross_b']['status'] == 'no_match' and reads['cross_b']['candidate_count'] == 0
    assert reads['unlinked_frozen']['status'] == 'no_match'
    assert reads['unlinked_frozen']['excluded_unverifiable_import'] == reads['unlinked_frozen']['import_timestamp_missing'] == 1
    assert reads['multi']['candidate_count'] == len(reads['multi']['identities']) == 3
    assert [row['provider'] for row in reads['multi']['identities']] == ['synthetic-one', 'synthetic-one', 'synthetic-two']
    assert len({row['employee_id'] for row in reads['multi']['identities']}) == 3
    frozen, live = reads['cutoff_frozen'], reads['cutoff_live']
    for key, value in fixture['expected_frozen_cutoff'].items():
        assert frozen[key] == value, key
    assert one(frozen)['employee_id'] == nodes['a-cutoff-90-early']['props']['id']
    assert frozen['truncated_count'] == 0 and frozen['without_timestamp'] == 1
    assert live['candidate_count'] == live['eligible_count'] == 7 and live['truncated_count'] == 5
    assert live['excluded_after_cutoff'] == live['excluded_unverifiable_import'] == 0
    assert len(live['identities']) == live['without_timestamp'] == 2
    save(directory, 'graph-production-read.json', {
        'batch': B, 'actual_production_helper': 'read_identity_context_for_accounts',
        'actual_connection_helper': 'get_identity_read_session', 'source_sha256': source,
        'cypher_sha256': query_sha, 'graph_fixture_sha256': file_sha(fixture_path), 'reads': reads,
        'strict_tenant_nodes_and_mixed_global_labels_checked': True,
        'cutoff_before_order_and_limit_checked': True, 'counts_cover_all_requested_account_node_paths': True,
        'no_schema_or_general_driver_initialization': graph_db._driver is None,
        'actual_http_or_model_called': False, 'probe_uid': os.geteuid(),
        'synthetic_fixture_not_hr_or_authorization_quality': True,
    })

    # Two explicit current-property changes demonstrate the limit of an
    # Employee-only import cutoff. They are not a fake historical version.
    history_before = await read(tenant_a, fixture['history_account'], cutoff=split)
    original_row = one(history_before)
    assert original_row['department'] == 'Synthetic history department v1'
    assert original_row['manager'] == 'Synthetic history manager v1'
    changes = [
        {'alias': 'a-history-department', 'label': 'Department', 'property': 'name',
         'before': 'Synthetic history department v1', 'after': 'Synthetic history department v2'},
        {'alias': 'a-history-manager', 'label': 'Employee', 'property': 'display_name',
         'before': 'Synthetic history manager v1', 'after': 'Synthetic history manager v2'},
    ]
    config = graph_db._identity_read_config()
    async with AsyncGraphDatabase.driver(config['uri'], auth=(config['username'], config['password']),
                                        connection_timeout=5, max_transaction_retry_time=0) as driver:
        async with driver.session(database=config['database'], default_access_mode=WRITE_ACCESS) as session:
            transaction = await session.begin_transaction()
            try:
                for change in changes:
                    node_id = nodes[change['alias']]['props']['id']
                    assert node_id == B + '/' + change['alias']
                    # Label and property are closed literals from this list,
                    # never a caller-provided Cypher fragment.
                    query = ('MATCH(n:' + change['label'] + ' {id:$id,batch:$batch,tenant_id:$tenant}) '
                             'WHERE n.' + change['property'] + '=$before SET n.' + change['property'] + '=$after RETURN n.id AS id')
                    result = await transaction.run(query, id=node_id, batch=B, tenant=tenant_a,
                                                   before=change['before'], after=change['after'])
                    records = await result.data()
                    assert records == [{'id': node_id}]
                await transaction.commit()
            except BaseException:
                await transaction.rollback()
                raise
    history_after = await read(tenant_a, fixture['history_account'], cutoff=split)
    current_row = one(history_after)
    assert current_row['department'] == changes[0]['after'] and current_row['manager'] == changes[1]['after']
    assert current_row['imported_at'] == original_row['imported_at']
    assert current_row['row_source_sha256'] != original_row['row_source_sha256']
    assert history_before['without_timestamp'] == history_after['without_timestamp'] == 1
    after_history = await snapshot()
    expected_after = deepcopy(before)
    for change in changes:
        target = [row for row in expected_after['nodes'] if row['props']['id'] == nodes[change['alias']]['props']['id']]
        assert len(target) == 1 and target[0]['props'][change['property']] == change['before']
        target[0]['props'][change['property']] = change['after']
    assert after_history == expected_after, 'Unexpected graph property, relationship or schema change'
    save(directory, 'graph-history-mutation.json', {
        'batch': B, 'same_split_at': fixture['split_at'], 'before': history_before, 'after': history_after,
        'only_property_changes': [{**change, 'node_id': nodes[change['alias']]['props']['id']} for change in changes],
        'employee_import_stamp_unchanged': True, 'current_path_projection_changed': True,
        'whole_graph_before_sha256': value_sha(before), 'whole_graph_after_sha256': value_sha(after_history),
        'frozen_read_reconstructs_old_department_or_manager': False,
        'business_history_unknown_for_both_reads': True, 'database_enforced_read_only_role_claimed': False,
        'explicit_marked_synthetic_write_only': True, 'model_called': False,
    })

    class FaultProxy:
        def __init__(self, session):
            self.session, self.inject, self.failure = session, True, None

        async def run(self, cypher, **parameters):
            assert cypher == production._IDENTITY_BY_ACCOUNT_CYPHER
            if self.inject:
                try:
                    return await self.session.run('RETURN missing_variable')
                except Exception as exc:
                    self.failure = {'exception_type': type(exc).__name__, 'code': getattr(exc, 'code', None)}
                    raise
            return await self.session.run(cypher, **parameters)

    async with graph_db.get_identity_read_session() as session:
        proxy = FaultProxy(session)
        failed = await production.read_identity_context_for_accounts(tenant_a, [fixture['model_account']], session=proxy)
        assert failed.status == 'unavailable' and failed.reason == 'graph_query_failed' and not failed.identities
        assert proxy.failure is not None
        proxy.inject = False
        recovered = await read(tenant_a, fixture['model_account'], session=proxy)
        assert one(recovered)['identity_id'] == nodes['a-identity']['props']['id']
    save(directory, 'graph-query-failure.json', {
        'batch': B, 'source_sha256': source, 'production_cypher_sha256': query_sha,
        'injected_query': 'RETURN missing_variable', 'actual_neo4j_error': proxy.failure,
        'failed': asdict(failed), 'recovered': recovered,
        'same_production_dedicated_session_recovered': True,
        'query_substitution_only_in_probe_proxy': True,
        'http_or_shared_graph_outage_injected': False, 'api_http_503_propagation_claimed': False,
        'new_graph_objects_or_schema': False, 'model_called': False,
    })
    final = await snapshot()
    assert final == after_history == expected_after
    assert graph_db._driver is None
    assert source == {name: file_sha(Path('/source') / name) for name in source}
    save(directory, 'graph-material-after-read-probe.json', {
        'batch': B, 'material': final, 'material_sha256': value_sha(final),
        'seeded_material_sha256': value_sha(seeded), 'nodes': len(final['nodes']),
        'relationships': len(final['relationships']), 'indexes': len(final['indexes']),
        'constraints': len(final['constraints']), 'only_two_marked_history_properties_changed': True,
        'all_other_properties_nodes_relationships_and_schema_unchanged': True,
        'no_general_driver_initialized': True, 'source_unchanged_during_probe': True,
    })
    print(json.dumps({'production_reads': len(reads), 'history_reads': 2, 'query_failure_then_same_session_recovery': True,
                      'nodes': 27, 'relationships': 22, 'history_properties_changed': 2, 'model_calls': 0}))


def main():
    assert os.geteuid() == 0
    os.umask(0o077)
    checkpoint = E / 'graph-production-probe-started.json'
    assert not checkpoint.exists() and not any((E / name).exists() for name in OUTPUTS), 'Inspect probe/mutation checkpoints; never blindly rerun'
    assert (E / 'graph-fixtures.json').is_file() and (E / 'graph-material-seeded.json').is_file()
    assert json.loads(subprocess.check_output(['docker', 'image', 'inspect', IMAGE]))[0]['Id'] == IMAGE_ID
    config = R / 'private/identity-graph-3a'
    assert config.is_dir() and (config / 'config.json').is_file()
    save(E, checkpoint.name, {'batch': B, 'operator_sha256': file_sha(Path(__file__)),
                             'fixture_sha256': file_sha(E / 'graph-fixtures.json'), 'image': IMAGE_ID,
                             'source_readonly': True, 'config_readonly': True,
                             'possible_mutation': 'Only marked a-history-department.name and a-history-manager.display_name v1 to v2',
                             'no_blind_replay_after_checkpoint': True, 'new_ingress': 0, 'new_model_calls': 0})
    command = ['docker', 'run', '--rm', '--user', '0', '--network', 'socai2_default',
               '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'ENVIRONMENT=production',
               '-e', 'AISOC_DEV_AUTH_BYPASS=false', '-e', 'AISOC_DISABLE_NEO4J=true',
               '-e', 'DATABASE_URL=postgresql+asyncpg://unit:unit@127.0.0.1:1/unit',
               '-e', 'DATABASE_DSN=', '-e', 'PYTHONPATH=/source/services/api',
               '-e', 'AISOC_IDENTITY_GRAPH_CONFIG_FILE=/run/secrets/identity-graph/config.json',
               '-v', str(R / 'source') + ':/source:ro', '-v', str(config) + ':/run/secrets/identity-graph:ro',
               '-v', str(E) + ':/evidence', '-w', '/source/services/api', IMAGE_ID,
               'python', '/source/deploy/aisoc21/probe_identity_graph_3a.py', '--container']
    result = subprocess.run(command, text=True, capture_output=True)
    log = E / 'graph-production-probe-operator.log'
    with log.open('x') as stream:
        stream.write(result.stdout + result.stderr)
    log.chmod(0o600)
    assert result.returncode == 0, 'Inspect immutable probe log/checkpoints; no blind graph read/mutation replay'
    assert all((E / name).is_file() for name in OUTPUTS)
    print(result.stdout.strip())


if __name__ == '__main__':
    if sys.argv[1:] == ['--container']:
        asyncio.run(container_probe())
    else:
        assert not sys.argv[1:]
        main()
