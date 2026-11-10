"""Read production page contracts against a frozen database snapshot; no model jobs."""
import argparse
import json
import shlex
import subprocess
from collections import Counter
from pathlib import Path
from uuid import UUID

from processing_workbench_source import detail_query
from production_case_probe import query, save
from verify_database_handoff import FK_SQL, audit, equivalent, request_plan

ROOT = Path(__file__).resolve().parents[2]
HTTP_READS = r'''
import concurrent.futures,json,sys,urllib.request,urllib.error
p=json.load(sys.stdin)
def get(spec):
 request=urllib.request.Request(p['base_url']+spec['path'],method='GET',
     headers={'Authorization':'Bearer '+p['key']})
 try:
  with urllib.request.urlopen(request,timeout=p['timeout']) as response:
   return {**spec,'status':response.status,'body':json.loads(response.read())}
 except urllib.error.HTTPError as error:
  raw=error.read().decode('utf-8',errors='replace')
  try:body=json.loads(raw)
  except ValueError:body={'unparsed_body':raw}
  return {**spec,'status':error.code,'body':body}
with concurrent.futures.ThreadPoolExecutor(max_workers=p['concurrency']) as pool:
 print(json.dumps(list(pool.map(get,p['plan'])),ensure_ascii=False))
'''


def fetch(runtime, plan, settings):
    t = runtime['transport']
    key = Path(runtime['target']['user_api_key_file'])
    if key.stat().st_mode & 0o077:
        raise ValueError('private_credential_file_required')
    payload = {'base_url': t['api_base_url'], 'timeout': t['http_timeout_seconds'],
               'concurrency': settings['concurrency'], 'plan': plan,
               'key': json.loads(key.read_text())[runtime['target']['user_api_key_json_path']]}
    result = subprocess.run([t['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UpdateHostKeys=no', '-o', f"ConnectTimeout={t['connect_timeout_seconds']}",
        t['ssh_target'], shlex.join([t['remote_python'], '-c', HTTP_READS])],
        input=json.dumps(payload), capture_output=True, text=True,
        timeout=settings['batch_timeout_seconds'], check=False)
    if result.returncode:
        raise RuntimeError('readonly_http_transport_failed')
    return json.loads(result.stdout)


def snapshot(runtime, case_id):
    sql = detail_query().replace('$3', 'NULL').replace('$2', "'" + str(UUID(case_id)) + "'")
    sql = sql.replace('$1', "'" + str(UUID(runtime['target']['tenant_id'])) + "'")
    # The related-alert contract spans the tenant, including alerts outside this
    # Case. Capture matching current objects in the same read-only snapshot.
    return query(runtime, """WITH captured(value) AS (""" + sql + """),
    keys AS MATERIALIZED (
      SELECT DISTINCT o.namespace,o.object_type,o.object_key
      FROM socai2.alert_objects o JOIN socai2.alerts a
        ON (a.tenant_id,a.id,a.latest_material_id)=(o.tenant_id,o.alert_id,o.material_id)
      WHERE a.id IN (SELECT (v->>'id')::uuid FROM captured,
        jsonb_array_elements(value->'data'->'alerts') v)
    ), related_objects AS MATERIALIZED (
      SELECT o.* FROM socai2.alert_objects o JOIN socai2.alerts a
        ON (a.tenant_id,a.id,a.latest_material_id)=(o.tenant_id,o.alert_id,o.material_id)
      WHERE EXISTS (SELECT FROM keys k WHERE
        (k.namespace,k.object_type,k.object_key)=(o.namespace,o.object_type,o.object_key))
    ) SELECT value || jsonb_build_object(
      'related_objects',(SELECT coalesce(jsonb_agg(to_jsonb(o) ORDER BY o.id),'[]') FROM related_objects o),
      'related_alerts',(SELECT coalesce(jsonb_agg(to_jsonb(a) ORDER BY a.id),'[]') FROM socai2.alerts a
        WHERE a.id IN (SELECT alert_id FROM related_objects))) FROM captured;""")


def extra_plan(data):
    case = data['cases'][0]['id']
    plan = [{'method': 'GET', 'path': f'/api/v1/socai2/cases/{case}/activities?limit=200',
             'kind': 'case_activities', 'expected_status': 200}]
    for a in data['artifacts']:
        if a['run_id'] is not None:
            continue
        subject = next((s for s in ('alert', 'incident', 'case') if a.get(s + '_id')), None)
        if subject:
            plan.append({'method': 'GET',
                'path': f"/api/v1/socai2/{subject}s/{a[subject + '_id']}/artifacts/{a['id']}",
                'kind': 'source_artifact', 'id': a['id'], 'expected_status': 200})
    return plan


def run(config_path, output):
    cfg = json.loads(config_path.read_text())
    runtime = json.loads((ROOT / cfg['run_config']).read_text())
    output.mkdir(parents=True, exist_ok=False)
    foreign_keys = query(runtime, FK_SQL)
    save(output / 'foreign-keys.json', foreign_keys)
    summaries = []
    for case_id in cfg['case_ids']:
        folder = output / str(UUID(case_id))
        folder.mkdir()
        before = snapshot(runtime, case_id)
        data = before['data']
        save(folder / 'snapshot-before.json', before)
        plan = request_plan(data, cfg) + extra_plan(data)
        save(folder / 'request-plan.json', plan)
        responses = fetch(runtime, plan, cfg['http'])
        save(folder / 'api-responses.json', responses)
        after = snapshot(runtime, case_id)
        save(folder / 'snapshot-after.json', after)
        # Base audit's historical Case-only expectation does not represent the
        # tenant-wide related-alert lookup; compare that section separately.
        base_responses = [{**r, 'kind': 'related_alerts'} if r.get('section') == 'related_alerts' else r
                          for r in responses]
        checks = audit(after['data'], data, foreign_keys, base_responses)
        checks.append({'name': 'related_snapshot_unchanged', 'passed':
            all(equivalent(before[k], after[k]) for k in ('related_alerts', 'related_objects'))})
        for response in responses:
            if response['status'] != 200:
                continue
            if response.get('section') == 'related_alerts':
                identity = response['id']
                members = {identity} if response['table'] == 'alerts' else {
                    r['alert_id'] for r in data['incident_alerts'] if r['incident_id'] == identity}
                objects = before['related_objects']
                keys = {(r['namespace'], r['object_type'], r['object_key'])
                        for r in objects if r['alert_id'] in members}
                ids = {r['alert_id'] for r in objects
                       if (r['namespace'], r['object_type'], r['object_key']) in keys} - members
                expected = [{k: v for k, v in r.items() if k not in ('tenant_id', 'source_identity_key')}
                            for r in before['related_alerts'] if r['id'] in ids]
                body = response['body']
                checks.extend([
                    {'name': response['path'] + '/tenant_wide_rows',
                     'passed': equivalent(body['items'], expected)},
                    {'name': response['path'] + '/total', 'passed': body['total'] == len(expected)},
                    {'name': response['path'] + '/not_truncated', 'passed': body['next_offset'] is None}])
            elif response['kind'] == 'source_artifact':
                expected = next(a for a in data['artifacts'] if a['id'] == response['id'])
                body = response['body']
                for key in ('content_json', 'content_text'):
                    if body['availability'] in ('available', 'retained_truncated'):
                        checks.append({'name': response['path'] + '/' + key,
                                       'passed': equivalent(body[key], expected[key])})
            elif response['kind'] == 'case_activities':
                body = response['body']
                checks.append({'name': response['path'] + '/deduplicated',
                    'passed': len({a['id'] for a in body['items']}) == len(body['items'])})
                expected = {a['id']: a for a in data['activities']}
                checks.append({'name': response['path'] + '/saved_activities_present',
                    'passed': set(expected) <= {a['id'] for a in body['items']}})
        save(folder / 'checks.json', checks)
        summary = {'case_id': case_id, 'requests': len(responses),
            'statuses': dict(Counter(str(r['status']) for r in responses)),
            'unexpected_http': [{k: r[k] for k in ('path', 'status', 'expected_status')}
                for r in responses if r['status'] != r['expected_status']],
            'checks': len(checks), 'failed_checks': [r for r in checks if not r['passed']],
            'database_unchanged': equivalent(data, after['data']),
            'table_counts': {t: len(rows) for t, rows in data.items()}}
        save(folder / 'summary.json', summary)
        summaries.append(summary)
        print(json.dumps({k: summary[k] for k in ('case_id', 'requests', 'statuses', 'checks', 'database_unchanged')})
              + ' failures=' + str(len(summary['failed_checks'])), flush=True)
    summary = {'batch': cfg['batch'], 'scope': cfg['scope'], 'real_model_calls': 0,
        'business_writes': 0, 'cases': summaries,
        'passed': all(not s['failed_checks'] and not s['unexpected_http'] and s['database_unchanged'] for s in summaries)}
    save(output / 'summary.json', summary)
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.config, args.output))
