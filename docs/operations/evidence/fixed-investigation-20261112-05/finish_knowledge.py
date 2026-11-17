"""Finish the known successful import; never repeat the ingest request.

The batch driver incorrectly expected full content in a preview-only DTO.
Verify committed text through SQL, then perform the not-yet-attempted index.
"""
import asyncio
from pathlib import Path

from run import ROOT, application, initialize, plan_for, read, save, sha

config, folder = initialize(Path(__file__).with_name('config.json'))


async def main():
    from app.db import database
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text

    plan_for(config, folder)
    imported = read(folder / 'knowledge-http/import.json')
    assert imported['status'] == 201 and len(imported['body']) == 1
    assert not (folder / 'knowledge-index-intent.json').exists()
    assert not (folder / 'knowledge-http/index.json').exists()
    document_id = imported['body'][0]['id']
    expected = imported['request']['content']
    try:
        async with database.engine.connect() as db:
            assert (await db.execute(text('SELECT current_database()'))).scalar_one() == config['expected_database']
            await db.execute(text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {'tenant': config['tenant_id']})
            rows = (await db.execute(text('SELECT id,content,chunk_index,chunk_total FROM aisoc_kb_documents '
                'WHERE tenant_id=CAST(:tenant AS uuid) AND title=:title ORDER BY id'),
                {'tenant': config['tenant_id'], 'title': imported['request']['title']})).mappings().all()
        actual = {str(row['id']): {**dict(row), 'id': str(row['id'])} for row in rows}
        before = read(folder / 'knowledge-old-documents.json')
        assert all(actual[row['id']] == row for row in before)
        assert actual[document_id]['content'] == expected and actual[document_id]['chunk_total'] == 1
        save(folder / 'knowledge-sql-readback.json', {'new_document': actual[document_id],
            'old_documents_unchanged': len(before), 'database': config['expected_database']})
        save(folder / 'knowledge-index-intent.json', {'document_ids': [document_id], 'attempts': 1,
            'driver_sha256': sha(Path(__file__)), 'import_repeated': False,
            'prior_error': 'Driver expected content; original HTTP DTO returns content_preview. SQL full text verified.'})
        async with AsyncClient(transport=ASGITransport(app=application(config)), base_url=config['http_base_url'],
                               timeout=config['http_timeout_seconds']) as client:
            result = await client.post('/api/v1/kb/index', json={'document_ids': [document_id]})
            save(folder / 'knowledge-http/index.json', {'status': result.status_code, 'body': result.json()})
            assert result.is_success, result.json()
            indexed = result.json()
            result = await client.get('/api/v1/kb/documents/' + document_id)
            save(folder / 'knowledge-http/readback.json', {'status': result.status_code, 'body': result.json()})
            assert result.is_success and result.json()['content_preview'] == expected[:200]
        save(folder / 'knowledge-ready.json', {'state': indexed['state'], 'document_ids': [document_id],
            'collection': indexed['collection'], 'content_characters': len(expected),
            'old_documents_preserved': len(before), 'original_source_verified': True,
            'calls': indexed['calls'], 'generation_calls': 0})
        print({'state': indexed['state'], 'document_id': document_id, 'content_characters': len(expected),
               'old_documents_preserved': len(before), 'collection': indexed['collection']}, flush=True)
    finally:
        await database.engine.dispose()


asyncio.run(main())
