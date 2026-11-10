"""SSH only changes transport; use the production tokenizer and executor contracts."""
import asyncio
import json
import shlex
import subprocess
from pathlib import Path

import httpx
from app.socai2.baseline_store import StoreError
from app.socai2.model_errors import ModelCallError, provider_error
from app.socai2.runtime_policy import active_policy
from app.socai2.token_budget import BackendTokenMeter

from tools.testdata.alert_io_eval.evaluate import remote, save


def tokenizer_call(config, request):
    cfg = config['transport']
    worker = Path(__file__).with_name('remote_tokenizer.py').read_text()
    command = [cfg['ssh_binary'], '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'UpdateHostKeys=no', '-o', f"ConnectTimeout={cfg['connect_timeout_seconds']}", cfg['ssh_target'],
        shlex.join([cfg['remote_python'], '-c', worker])]
    result = subprocess.run(command, input=json.dumps(request), capture_output=True, text=True,
        timeout=cfg['command_timeout_seconds'], check=False)
    if result.returncode:
        raise StoreError('token_meter_ssh_unavailable', 503)
    return json.loads(result.stdout)


class TokenizerTransport(httpx.AsyncBaseTransport):
    def __init__(self, config, folder):
        self.config, self.folder, self.calls = config, folder, 0

    async def handle_async_request(self, request):
        config = active_policy().model.tokenizer
        assert str(request.url) == config['endpoint']
        body = json.loads(request.content)
        self.calls += 1
        value = await asyncio.to_thread(tokenizer_call, self.config, {'tokenizer': dict(config), 'body': body})
        save(self.folder / f'tokenizer-{self.calls}.json', {'request': body, 'response': value})
        return httpx.Response(value['status'], json=value['body'], request=request)


class Gateway:
    def __init__(self, config, folder, key):
        self.config, self.folder, self.key = config, folder, key
        policy = active_policy().model
        self.provider, self.model, self.schema_profile = policy.protocol, policy.alias, policy.schema_profile
        self.calls = 0

    async def configure(self, *_):
        return self.config['preflight']['state'] == 'ready'

    async def measure(self, body, stage):
        return await BackendTokenMeter(active_policy().model, transport=TokenizerTransport(self.config, self.folder)).measure(body, stage)

    async def complete(self, body, timeout):
        assert self.calls == 0 and timeout > 0
        self.calls += 1
        save(self.folder / 'model-intent.json', {'body': body, 'attempt': 1})
        value = await asyncio.to_thread(remote, self.config, {'phase': 'call', 'cell': self.key,
            'body': body, 'timeout_seconds': min(timeout, active_policy().single_model_timeout_seconds)})
        save(self.folder / 'model-receipt.json', value)
        if value['state'] != 'response_received':
            if value.get('error_body') and value.get('http_status'):
                response = httpx.Response(value['http_status'], content=value['error_body'], request=httpx.Request('POST', 'https://gateway.invalid'))
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise ModelCallError(provider_error(exc, '')) from None
            raise ModelCallError({'http_status': value.get('http_status'), 'fields': {}, 'body_state': 'unavailable',
                'exception_type': 'RemoteTransportUncertain'})
        return value['raw']
