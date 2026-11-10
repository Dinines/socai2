"""Relay one actual tokenizer request through the already configured SSH host."""
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request


def main():
    value = json.load(sys.stdin)
    config = value['tokenizer']
    assert config['authentication'] == 'none'
    body = value['body']
    assert body['model'] == config['served_model']
    request = urllib.request.Request(config['endpoint'], json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=config['timeout_seconds']) as response:
            raw = response.read()
            data = json.loads(raw)
            result = {'status': response.status, 'body': {k: data[k] for k in ('count', 'max_model_len')},
                'raw_response_sha256': hashlib.sha256(raw).hexdigest(), 'measurement_is_real': True}
    except urllib.error.HTTPError as exc:
        result = {'status': exc.code, 'body': {'error_type': 'tokenizer_http_error'}}
    result['seconds'] = round(time.monotonic() - start, 6)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
