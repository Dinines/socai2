"""Host21 disposable-container probe. Uses the 20 helper unchanged; no business workers."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

import httpx

sys.path.insert(0, '/helper')
from aisoc_local_embeddings import MODEL, DIMENSION, embed_vectors, validate_vectors

BATCH = '1d-20261020'
COLLECTION = 'socai2_verify_1d_20261020_qwen06b_1024'
ROOT = Path('/evidence')
TEXTS = [
    'socai2 1d-20261020 sample-A: suspicious PowerShell execution on a test host.',
    'socai2 1d-20261020 sample-B: approved maintenance task on a test host.',
    'socai2 1d-20261020 sample-C: 材料不足的测试告警，待补充来源与时间。',
]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(name, data):
    path = ROOT / name
    # Never replace earlier successful or failed evidence on a repeated invocation.
    with path.open('x') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


async def main(action):
    async with httpx.AsyncClient(base_url=os.environ['QDRANT_URL'],
                                headers={'api-key': os.environ['QDRANT_API_KEY']}, timeout=30) as q:
        async def call(method, path, body=None):
            r = await q.request(method, path, json=body)
            r.raise_for_status()
            return r.json()['result']
        path = '/collections/' + COLLECTION
        if action == 'before':
            assert not (ROOT / 'written.json').exists()
            collections = await call('GET', '/collections')
            assert COLLECTION not in [v['name'] for v in collections['collections']]
            root = (await q.get('/')).json()
            async with httpx.AsyncClient(timeout=10) as unauth:
                denied = await unauth.get(os.environ['QDRANT_URL'] + '/collections')
            assert denied.status_code in (401,403), denied.status_code
            vectors = await embed_vectors(TEXTS)
            validate_vectors(vectors, len(TEXTS))
            points = []
            for n, (text, vector) in enumerate(zip(TEXTS, vectors, strict=True)):
                points.append({'id': str(uuid.uuid5(uuid.NAMESPACE_URL, BATCH + ':' + str(n))),
                               'vector': vector,
                               'payload': {'batch': BATCH, 'sample_index': n, 'text': text,
                                           'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                                           'embedding_model': MODEL,
                                           'embedding_manifest_sha256': os.environ['EMBEDDING_MANIFEST_SHA256'],
                                           'dimension': DIMENSION, 'tenant_id': 'socai2-dependency-test'}})
            # Retain the actual vectors/inputs before any durable Qdrant write.
            save('embedding.json', {'model': MODEL, 'dimension': DIMENSION, 'points': points,
                                   'vectors_sha256': [digest(v) for v in vectors],
                                   'qdrant_version': root['version'],
                                   'without_api_key_http_status': denied.status_code,
                                   'collections_before': collections})
            await call('PUT', path, {'vectors': {'size': DIMENSION, 'distance': 'Cosine'}})
            result = await call('PUT', path + '/points?wait=true', {'points': points})
            assert result['status'] == 'completed', result
            invalid = await q.put(path + '/points?wait=true', json={'points': [
                {'id': str(uuid.uuid5(uuid.NAMESPACE_URL, BATCH + ':bad-dimension')),
                 'vector': [1.0, 2.0], 'payload': {'batch': BATCH}}]})
            assert invalid.status_code == 400
            save('written.json', {'collection': COLLECTION, 'ids': [p['id'] for p in points],
                                  'operation': result, 'points': len(points),
                                  'wrong_dimension_http_status': invalid.status_code,
                                  'vector_space': {'model': MODEL, 'size': DIMENSION, 'distance': 'Cosine',
                                                   'manifest_sha256': os.environ['EMBEDDING_MANIFEST_SHA256']}})
        expected = json.loads((ROOT / 'embedding.json').read_text())['points']
        readback = await call('POST', path + '/points', {'ids': [p['id'] for p in expected],
                                                       'with_payload': True, 'with_vector': True})
        got = {p['id']: p for p in readback}
        assert set(got) == {p['id'] for p in expected}
        for point in expected:
            assert got[point['id']]['payload'] == point['payload']
            validate_vectors([got[point['id']]['vector']], 1)
        queries = []
        for point in expected:
            hits = await call('POST', path + '/points/search', {'vector': point['vector'], 'limit': 3,
                                'with_payload': True,
                                'filter': {'must': [{'key': 'batch', 'match': {'value': BATCH}}]}})
            assert hits and hits[0]['id'] == point['id'], hits
            assert hits[0]['payload'] == point['payload']
            assert abs(hits[0]['score'] - 1) < 0.0001
            queries.append({'query_id': point['id'], 'top_hit_id': hits[0]['id'],
                            'score': hits[0]['score'], 'payload_equal': True})
        info = await call('GET', path)
        assert info['points_count'] == 3
        count = await call('POST', path + '/points/count', {'exact': True})
        assert count['count'] == 3
        result = {'action': action, 'collection': COLLECTION, 'points_count': count['count'],
                  'same_ids_and_payloads': True, 'read_vectors_finite_nonzero_1024': True,
                  'queries': queries, 'qdrant_config': info['config'],
                  'note': 'Self-vector identity search; no semantic relevance or Agent consumption claim'}
        if action == 'after':
            assert (ROOT / 'before.json').exists()
            await call('DELETE', path)
            assert (await q.get(path)).status_code == 404
            remaining = await call('GET', '/collections')
            assert remaining == json.loads((ROOT/'embedding.json').read_text())['collections_before']
            result.update(only_batch_collection_deleted=COLLECTION, remaining_collections=remaining)
        save(action + '.json', result)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('before', 'after'))
    args = parser.parse_args()
    try:
        asyncio.run(main(args.action))
    except Exception as exc:
        # Credentials/request headers never appear in diagnostics.
        failure = {'action': args.action, 'error_type': type(exc).__name__}
        save(args.action + '.failed.' + uuid.uuid4().hex + '.json', failure)
        print(json.dumps(failure))
        raise SystemExit(1)
