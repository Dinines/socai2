"""W3 temporary ASGI observation only. Saves actual complete HTTP responses."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from investigation_test.api import create_app
from investigation_test.config import Config
from investigation_test.proxy import UpstreamConfig
from investigation_test.viewer import ViewerConfig

ROOT = Path(__file__).resolve().parent
config = Config.load(ROOT / 'service-config.json')
app = create_app(config, UpstreamConfig.load(ROOT / 'upstream-config.json'),
                 viewer=ViewerConfig.load(ROOT / 'viewer-config.json'))
sequence = 0

async def record(scope, receive, send):
    global sequence
    if scope['type'] != 'http':
        return await app(scope, receive, send)
    sequence += 1
    seq = sequence
    chunks, status, headers = [], None, []
    async def observed_send(message):
        nonlocal status, headers
        if message['type'] == 'http.response.start':
            status, headers = message['status'], message.get('headers', [])
        if message['type'] == 'http.response.body':
            chunks.append(message.get('body', b''))
        await send(message)
    error = None
    try:
        await app(scope, receive, observed_send)
    except BaseException as exc:
        error = type(exc).__name__
        raise
    finally:
        body = b''.join(chunks)
        filename = None
        if scope['path'].startswith(('/test-api/', '/api/')):
            filename = f'responses/{seq:03}.json'
            (ROOT / filename).write_bytes(body)
        item = {'sequence':seq, 'observed_at':datetime.now(timezone.utc).isoformat(),
                'method':scope['method'], 'path':scope['path'],
                'query':scope.get('query_string',b'').decode(), 'status':status,
                'bytes':len(body), 'sha256':hashlib.sha256(body).hexdigest(),
                'headers':{k.decode():v.decode() for k,v in headers},
                'response_file':filename, 'error':error}
        with (ROOT / 'requests.jsonl').open('a') as out:
            out.write(json.dumps(item,ensure_ascii=False)+'\n')

if __name__ == '__main__':
    uvicorn.run(record, host=config.host, port=config.port)
