"""Select a saved, locally terminal I delivery and freeze its Case business view.

No parser/model is run here. All mutable pointers and source bodies are read by
C1's one statement; the stored receipt is checked against its saved originals.
"""
import copy
from collections import Counter

from pydantic import ValidationError

from .incident_inputs import SELECTION_VERSION
from .stage_inputs import VERSION, incident_source_sql

MATERIAL_VERSION = "socai2.case-incident-material.v1"


def source_sql():
    current = incident_source_sql(selection_limit="CAST(f.content_json->'input_selection'->>'limit' AS integer)")
    # SOURCE_SQL has its own `incidents i`; using i.id there would select every
    # tenant incident. Bind the outer task's subject through a distinct alias.
    current = current.replace(":kind", "'incident_diagnosis'").replace(":id", "case_material_task.subject_id").replace(":version", "'" + VERSION + "'")
    # Select only one immutable answer; never merge units from different Runs.
    return f"""(SELECT jsonb_build_object('task',to_jsonb(case_material_task),'attempt',to_jsonb(a),
      'run',to_jsonb(r),'input',to_jsonb(f),'receipt',to_jsonb(d),
      'diagnosis',(SELECT to_jsonb(j) FROM socai2.incident_diagnoses j
        WHERE j.tenant_id=r.tenant_id AND j.incident_id=i.id AND j.source_run_id=r.id LIMIT 1),
      'response',(SELECT to_jsonb(m) FROM socai2.artifacts m
        WHERE m.tenant_id=r.tenant_id AND m.incident_id=i.id AND m.run_id=r.id
          AND m.kind='model_response' AND m.content_json ? 'received_analysis'
          AND m.content_json->'citation_review'->>'original_response_artifact_id' IN
            (SELECT o->>'artifact_id' FROM jsonb_array_elements(d.content_json->'originals') o WHERE o->>'kind'='response')
        ORDER BY m.captured_at DESC,m.id DESC LIMIT 1),
      'originals',(SELECT jsonb_agg(to_jsonb(o) ORDER BY o.id) FROM socai2.artifacts o
        WHERE o.tenant_id=r.tenant_id AND o.incident_id=i.id AND o.run_id=r.id
          AND o.id::text IN (SELECT x->>'artifact_id' FROM jsonb_array_elements(d.content_json->'originals') x)))
      FROM socai2.analysis_attempts a
      JOIN socai2.analysis_tasks case_material_task ON case_material_task.tenant_id=a.tenant_id AND case_material_task.id=a.task_id
        AND case_material_task.subject_type='incident' AND case_material_task.subject_id=i.id AND case_material_task.kind='incident_diagnosis'
      JOIN socai2.runs r ON r.tenant_id=a.tenant_id AND r.id=a.run_id
        AND r.incident_id=i.id AND r.kind='incident_diagnosis'
      JOIN socai2.artifacts f ON f.tenant_id=r.tenant_id AND f.id=r.input_artifact_id
        AND f.id=a.input_artifact_id AND f.run_id=r.id AND f.incident_id=i.id AND f.kind='input_snapshot'
      JOIN socai2.artifacts d ON d.tenant_id=r.tenant_id AND d.run_id=r.id AND d.incident_id=i.id
        AND d.schema_version='socai2.stage-delivery.v1' AND d.kind='source_snapshot'
        AND d.content_json->>'stage'='I'
      WHERE a.tenant_id=:tenant AND a.subject_type='incident' AND a.subject_id=i.id
        AND a.kind='incident_diagnosis' AND a.local_state='ended' AND a.local_ended_at IS NOT NULL
        AND case_material_task.state IN ('completed','failed') AND case_material_task.ended_at IS NOT NULL
        AND r.state IN ('completed','failed','unknown')
        AND NOT EXISTS (SELECT 1 FROM socai2.analysis_attempts newer
          WHERE newer.tenant_id=a.tenant_id AND newer.task_id=a.task_id AND newer.attempt_no>a.attempt_no)
        AND NOT EXISTS (SELECT 1 FROM socai2.analysis_tasks active
          WHERE active.tenant_id=a.tenant_id AND active.subject_type='incident' AND active.subject_id=i.id
            AND active.kind='incident_diagnosis' AND (active.state='running' OR
              (active.state='waiting' AND active.started_at IS NOT NULL AND active.next_retry_at IS NOT NULL)))
        AND f.content_json->>'selection_version'='{SELECTION_VERSION}'
        AND f.content_json->'change_view'=(({current})->'change_view')
      ORDER BY (d.content_json->'use'->>'conclusion_available'='true') DESC,
        (d.content_json->'delivery'->>'state'<>'none') DESC,a.local_ended_at DESC,a.id DESC,d.id DESC LIMIT 1)"""


def checked_artifact(row, tenant, incident, run):
    from .baseline_store import digest, encoded
    if (not row or str(row['tenant_id']) != tenant or str(row['incident_id']) != incident or str(row['run_id']) != run
            or row['material_state'] != 'complete' or row.get('blob_ref') is not None
            or row['sha256'] != digest(row['content_json']) or row['size_bytes'] != len(encoded(row['content_json']))):
        raise ValueError('incident_material_source_invalid')
    return row['content_json']


def identity(row):
    return {key: copy.deepcopy(row[key]) for key in ('id', 'sha256', 'size_bytes', 'kind', 'schema_version')}


def semantic_ref(resolved, source, input_id, source_map):
    from .baseline_store import digest
    ref = resolved['ref']
    path = ref.get('source_path')
    body = None
    if ref['type'] == 'artifact' and str(ref['id']) == input_id:
        body = source
    elif ref['type'] == 'alert_material':
        body = next((m['material'] for m in source['members'] if m.get('material')
                     and m['material']['id'] == str(ref['id'])), None)
    elif ref['type'] == 'artifact':
        body = next((q['content_json'] for rows in source.get('triage_queries', {}).values()
                     for q in rows if q['id'] == str(ref['id'])), None)
    value_hash = None
    if body is not None and path:
        value = body
        try:
            for part in path[2:].split('.'):
                value = value[int(part)] if isinstance(value, list) else value[part]
            if body is source and path == '$.parent':
                value = {k: value.get(k) for k in ('title', 'description', 'category', 'severity')}
            elif body is source and path.endswith('.alert'):
                value = {k: value.get(k) for k in ('title', 'description', 'category', 'severity', 'event_time')}
            elif body is source and path.endswith(('.triage', '.feedback')):
                from .case_update_inputs import assessment
                value = assessment(value)
                for recommendation in value['recommendations']:
                    recommendation.pop('source_refs', None)
            value_hash = digest(value)
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    if value_hash is None:
        # The request already saved the exact projected business value's hash.
        # Do not use the referenced artifact's hash (which includes its ledger).
        value_hash = source_map.get(resolved['source_id'], {}).get('visible_value_sha256')
    if body is source and path:
        parts = path.split('.')
        if len(parts) > 3 and parts[1] == 'members' and parts[2].isdigit():
            parts[2] = source['members'][int(parts[2])]['alert']['id']
            path = '.'.join(parts)
    return {'type': ref['type'], 'role': ref['role'], 'alert_ids': sorted(resolved['alert_ids']),
            'source_path': path, 'row_keys': ref.get('row_keys', []), 'external': ref.get('external'),
            'business_value_sha256': value_hash}


def project(receipt, analysis, source, input_id, source_map):
    """Project only the already saved normalized units; keep prose unchanged."""
    from .baseline_store import encoded
    counters, units, semantic = Counter(), [], []
    selected = source['input_selection']['selected_alert_ids']
    allowed = set(receipt['use']['material_paths'])
    for raw in receipt['retained_units']:
        path = raw['path']
        if path not in allowed:
            continue
        if raw['kind'] == 'empty_array':
            semantic.append({'kind': path[2:], 'value': []})
            continue
        field = path[2:].split('[', 1)[0]
        if field.startswith('diagnosis.'):
            name = field.split('.')[1]
            value = copy.deepcopy(analysis['diagnosis'][name])
            if name == 'source_ids':
                continue
            owners = selected if receipt['use']['conclusion_available'] else []
            kind = 'incident'
        else:
            value = copy.deepcopy(analysis[field][counters[field]])
            counters[field] += 1
            owners = [value['alert_id']] if field == 'members' else value['alert_ids']
            if not set(owners) <= set(selected):
                raise ValueError('incident_material_unit_scope_invalid')
            value = {k: v for k, v in value.items() if k not in {'alert_id', 'alert_ids', 'source_ids', 'id'}}
            kind = 'question' if field == 'open_questions' else 'finding'
        scope = {'alert_ids': sorted(owners)}
        refs = [r['ref'] for r in raw['resolved_refs']]
        units.append({'path': path, 'kind': kind, 'value': value, 'scope': scope, 'source_refs': refs})
        semantic.append({'kind': field, 'value': value, 'scope': scope,
            'sources': sorted([semantic_ref(r, source, input_id, source_map) for r in raw['resolved_refs']], key=encoded)})
    return units, sorted(semantic, key=encoded)


def freeze(incident_id, candidate, case_members):
    """Invalid/missing sources are gaps, never a fallback to a mutable pointer."""
    from .baseline_store import digest
    from .stage_delivery import validate_sources
    if not candidate:
        return None, ['incident_terminal_material_unavailable']
    try:
        a, t, r = (candidate[k] for k in ('attempt', 'task', 'run'))
        tenant, iid, rid = str(r['tenant_id']), str(incident_id), str(r['id'])
        if (a['local_state'] != 'ended' or not a['local_ended_at'] or t['state'] not in {'completed', 'failed'}
                or not t['ended_at'] or t.get('next_retry_at') is not None
                or r['state'] not in {'completed', 'failed', 'unknown'}
                or str(a['tenant_id']) != tenant or str(t['tenant_id']) != tenant
                or str(a['run_id']) != rid or str(a['task_id']) != str(t['id'])
                or a['subject_type'] != 'incident' or t['subject_type'] != 'incident'
                or str(a['subject_id']) != iid or str(t['subject_id']) != iid
                or a['kind'] != 'incident_diagnosis' or t['kind'] != 'incident_diagnosis'):
            raise ValueError('incident_material_not_terminal')
        source = checked_artifact(candidate['input'], tenant, iid, rid)
        rec = checked_artifact(candidate['receipt'], tenant, iid, rid)
        response = checked_artifact(candidate['response'], tenant, iid, rid)
        originals = {str(o['id']): checked_artifact(o, tenant, iid, rid) for o in candidate['originals']}
        receipt = validate_sources(rec, originals).model_dump(mode='json')
        input_id = str(candidate['input']['id'])
        if (receipt['stage'] != 'I' or receipt['run_id'] != rid or receipt['input_artifact_id'] != input_id
                or str(a['input_artifact_id']) != input_id or str(r['input_artifact_id']) != input_id
                or source['kind'] != 'incident_diagnosis' or source['version'] != VERSION
                or source['parent']['id'] != iid or source['selection_version'] != SELECTION_VERSION
                or a['input_digest'] != digest(source['change_view'])
                or response['citation_review']['original_response_artifact_id'] not in originals):
            raise ValueError('incident_material_identity_invalid')
        selected = source['input_selection']['selected_alert_ids']
        if len(set(selected)) != len(selected) or set(selected) != {m['alert']['id'] for m in source['members']}:
            raise ValueError('incident_material_selection_invalid')
        request = next(originals[o['artifact_id']] for o in receipt['originals'] if o['kind'] == 'request')
        units, content = project(receipt, response['received_analysis'], source, input_id, request['source_map'])
        signal = {'input_digest': digest(source['change_view']), 'conclusion_available': receipt['use']['conclusion_available'],
                  'content': content, 'member_ids': sorted(selected)}
        # The full immutable input stays on its original I Run; C1 freezes an
        # exact source identity, not a copy of raw alert records for the model.
        value = {'version': MATERIAL_VERSION, 'tenant_id': tenant, 'incident_id': iid, 'source_run_id': rid,
            'task_id': str(t['id']), 'attempt_id': str(a['id']), 'input': identity(candidate['input']),
            'response': identity(candidate['response']), 'receipt_source': identity(candidate['receipt']),
            'originals': [identity(o) for o in candidate['originals']], 'receipt': receipt,
            'input_selection': copy.deepcopy(source['input_selection']), 'units': units,
            'case_selected_alert_ids': sorted(set(selected) & set(map(str, case_members))),
            'business_view': signal}
        return value, [] if receipt['delivery']['state'] == 'complete' else ['incident_analysis_incomplete']
    except (KeyError, TypeError, ValueError, IndexError, StopIteration, ValidationError):
        return None, ['incident_terminal_material_invalid']


def source_members(material, path, case_members):
    parts = path.split('.')
    if len(parts) < 7 or parts[4:5] != ['units'] or not parts[5].isdigit():
        return []
    unit = material['units'][int(parts[5])]
    return sorted(set(unit['scope']['alert_ids']) & set(case_members))
