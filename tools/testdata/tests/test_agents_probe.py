"""Offline observation/transport boundaries; no broker, database or model calls."""
import asyncio
from collections import namedtuple
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents_probe import (CURRENT_ALERT, EXPECTED_COUNT, REQUEST_LIMIT, ROOT, ModelObserver,
                          committed_count, consumer_offsets, read_configuration, save)


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = {"run_id": "offline-20261023", "tenant_id": "22222222-2222-4222-8222-222222222222",
            "fused_topic": "socai2.testdata.offline-20261023.fused", "group": "socai2.testdata.offline-20261023.agents",
            "dlq": "socai2.testdata.offline-20261023.agents-dlq", "api_port": 24942}
        for name in ("env_file", "reader_keys_file", "writer_keys_file", "neo4j_config"):
            self.config[name] = name + ".json"
            save(self.base / self.config[name], {"uri": "bolt://127.0.0.1:1", "username": "fixture",
                "password": "private-fixture", "database": "neo4j"} if name == "neo4j_config" else {})
        self.path = self.base / "config.json"

    def read(self, **changes):
        save(self.path, {**self.config, **changes}, replace=True)
        return read_configuration(self.path)

    def test_explicit_batch_and_private_files(self):
        result = self.read()
        self.assertEqual(result["expected_count"] if "expected_count" in result else EXPECTED_COUNT, 2)
        self.assertEqual(result["env_file"], str((self.base / "env_file.json").resolve()))
        self.assertEqual(result["max_seconds"], 600)
        for changes in ({"tenant_id": "invalid"}, {"run_id": "../../old"},
                        {"fused_topic": "socai2.alerts.fused"}, {"dlq": self.config["fused_topic"]},
                        {"group": "socai2.testdata.other.agents"}, {"request_limit": 15},
                        {"expected_count": 3}, {"max_seconds": 901}, {"api_port": 80}):
            with self.subTest(keys=list(changes)), self.assertRaises(ValueError):
                self.read(**changes)
        (self.base / self.config["reader_keys_file"]).chmod(0o644)
        with self.assertRaises(ValueError):
            self.read()

    def test_receipts_refuse_overwrite_and_atomic_progress_stays_private(self):
        path = self.base / "receipt.json"
        save(path, {"committed_count": 0})
        with self.assertRaises(FileExistsError):
            save(path, {"committed_count": 1})
        save(path, {"committed_count": 1}, replace=True)
        self.assertEqual(json.loads(path.read_text()), {"committed_count": 1})
        self.assertEqual(path.stat().st_mode & 0o077, 0)

    def test_original_api_routers_import_in_separate_process_without_network(self):
        config = self.read()
        Path(config["env_file"]).write_text("DATABASE_URL=postgresql://fixture:private@127.0.0.1/fixture\n"
            "KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:1\nLLM_GATEWAY_URL=http://127.0.0.1:1\n"
            "AISOC_AGENT_ESCALATE_TO_GRAPH=1\nAISOC_SIEM_WRITEBACK_ENABLED=0\n"
            "AISOC_ALERT_PLAYBOOKS_ENABLED=0\nENV=development\nENVIRONMENT=development\n")
        script = """
import json, os, pathlib, socket, sys
sys.path.insert(0, sys.argv[1])
from agents_probe import configure_process, api_app, read_configuration
def denied(*args, **kwargs):
    raise AssertionError('Network forbidden during offline import')
socket.socket.connect = denied
socket.getaddrinfo = denied
cfg = read_configuration(pathlib.Path(sys.argv[2]))
configure_process(cfg, 'api')
app = api_app(cfg, pathlib.Path.cwd())
from starlette.routing import Match
paths = ('/probe-ready', '/api/v1/graph/investigation-context', '/api/v1/graph/identity-context',
         '/api/v1/kb/runbooks/for-triage', '/api/v1/alerts', '/api/v1/lake/sql',
         '/api/v1/feedback/context-statements', '/api/v1/feedback/recent-dispositions',
         '/api/v1/tenant-skills/resolved/active')
for path in paths:
    method = 'POST' if path.endswith('/sql') else 'GET'
    scope = {'type': 'http', 'path': path, 'root_path': '', 'method': method}
    assert any(route.matches(scope)[0] == Match.FULL for route in app.routes), path
print(json.dumps(list(paths)))
assert 'app.main' not in sys.modules
assert 'app.workers.fused_alert_consumer' not in sys.modules
assert 'OPENAI_API_KEY' not in os.environ
"""
        result = subprocess.run([sys.executable, "-c", script, str(ROOT / "tools/testdata"), str(self.path)],
            cwd=self.base, text=True, capture_output=True, timeout=30,
            env={"PATH": "/usr/bin:/bin", "OPENAI_API_KEY": "ambient-secret-must-not-leak"})
        self.assertEqual(result.returncode, 0, result.stderr[-2500:])
        paths = json.loads(result.stdout.splitlines()[-1])
        for path in ("/probe-ready", "/api/v1/graph/investigation-context", "/api/v1/graph/identity-context",
                     "/api/v1/kb/runbooks/for-triage", "/api/v1/alerts", "/api/v1/lake/sql"):
            self.assertIn(path, paths)


class OffsetTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        partition = namedtuple("Partition", "topic partition")("test", 0)
        class Consumer:
            beginning, end, current, committed_value = 0, 0, 0, None
            def assignment(self): return {partition}
            async def beginning_offsets(self, parts): return {partition: self.beginning}
            async def end_offsets(self, parts): return {partition: self.end}
            async def position(self, part): return self.current
            async def committed(self, part): return self.committed_value
        self.consumer = Consumer()

    async def test_empty_topic_is_required_even_if_latest_position_looks_ready(self):
        self.assertEqual(committed_count(await consumer_offsets(self.consumer, require_empty=True)), 0)
        for field, value in (("beginning", 1), ("end", 1), ("current", 1), ("committed_value", 1)):
            with self.subTest(field=field):
                old = getattr(self.consumer, field)
                setattr(self.consumer, field, value)
                with self.assertRaises(ValueError):
                    await consumer_offsets(self.consumer, require_empty=True)
                setattr(self.consumer, field, old)

    async def test_fetched_or_processed_message_is_not_claimed_as_committed(self):
        self.consumer.end = self.consumer.current = 1
        rows = await consumer_offsets(self.consumer)
        self.assertEqual(committed_count(rows), 0)
        self.consumer.committed_value = 1
        self.assertEqual(committed_count(await consumer_offsets(self.consumer)), 1)


class OriginalWorkerLoopTest(unittest.TestCase):
    def test_original_start_commits_after_observed_processing_and_cooperative_stop_cleans_up(self):
        # The probe's complete control loop uses the original Worker.start/stop.
        # Kafka and the business operation are offline doubles here, explicitly
        # not evidence of real triage, model behavior or database durability.
        script = r'''
import asyncio, json, os, pathlib, socket, sys, tempfile
from collections import namedtuple
sys.path.insert(0, sys.argv[1])
from agents_probe import ModelObserver, consume
sys.path.insert(0, sys.argv[2])
def denied(*args, **kwargs): raise AssertionError('Network forbidden')
socket.socket.connect = denied
socket.getaddrinfo = denied
os.environ['KAFKA_BOOTSTRAP_SERVERS'] = '127.0.0.1:1'
os.environ.pop('DATABASE_URL', None)
os.environ.pop('DATABASE_DSN', None)
from app.workers.fused_alert_consumer import FusedAlertTriageWorker
import aiokafka
TP = namedtuple('TP', 'topic partition')('isolated', 0)
calls = []
active = {}
class Consumer:
    def __init__(self, *args, **kwargs):
        self.pos, self.end, self.commit_value = 0, 0, None
        self.closed = asyncio.Event()
        assert kwargs['enable_auto_commit'] is False
    async def start(self): pass
    def assignment(self): return {TP}
    async def beginning_offsets(self, parts): return {TP: 0}
    async def end_offsets(self, parts): return {TP: self.end}
    async def position(self, part): return self.pos
    async def committed(self, part): return self.commit_value
    async def commit(self):
        calls.append(('commit', self.pos))
        self.commit_value = self.pos
    async def stop(self):
        calls.append(('consumer_stop', self.pos))
        self.closed.set()
    def __aiter__(self): return self
    async def __anext__(self):
        out = active['out']
        while not (out / 'consumer-ready.json').exists(): await asyncio.sleep(.01)
        if active['stop']:
            (out / 'stop-request.json').write_text('{}')
            await self.closed.wait()
            raise StopAsyncIteration
        if self.pos == 2:
            await self.closed.wait()
            raise StopAsyncIteration
        if self.pos:
            while not (out / 'progress.json').exists() or json.loads((out / 'progress.json').read_text())['committed_count'] != 1:
                await asyncio.sleep(.01)
        self.pos += 1
        self.end = self.pos
        aid = f'00000000-0000-4000-8000-{self.pos:012d}'
        payload = {'tenant_id': active['tenant_id'], 'id': aid, 'alert': {'id': aid, 'tenant_id': active['tenant_id'], 'title': 'offline'}}
        return namedtuple('Message', 'value partition offset')(payload, 0, self.pos - 1)
async def business(self, message):
    calls.append(('processed', int(message['id'][-1])))
    await self.triage(message)
    return True
async def triage(self, message): return {'run': 'offline-double', 'response_dispatched': False}
aiokafka.AIOKafkaConsumer = Consumer
FusedAlertTriageWorker._process_with_retry = business
FusedAlertTriageWorker.triage = triage
async def check(stop):
    with tempfile.TemporaryDirectory() as temporary:
        out = pathlib.Path(temporary)
        config = {'tenant_id': '22222222-2222-4222-8222-222222222222', 'fused_topic': 'isolated',
                  'group': 'isolated-group', 'dlq': 'isolated-dlq', 'run_id': 'offline', 'max_seconds': 5}
        active.update(out=out, stop=stop, tenant_id=config['tenant_id'])
        result = await consume(config, out, ModelObserver(out))
        assert not result['cleanup_errors'], result
        if stop:
            assert result['status'] == 'incomplete' and result['error_type'] == 'ProbeStopped', result
            assert not result['processed'], result
        else:
            assert result['status'] == 'processed_and_committed', result
            assert len(result['processed']) == 2
            assert json.loads((out / 'progress.json').read_text())['committed_count'] == 2
            assert calls[:4] == [('processed', 1), ('commit', 1), ('processed', 2), ('commit', 2)], calls
        assert any(call[0] == 'consumer_stop' for call in calls)
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]
async def main():
    await check(False)
    calls.clear()
    await check(True)
asyncio.run(main())
print('original worker loop: two durable doubles committed; cooperative stop cleaned up; zero network/models')
'''
        result = subprocess.run([sys.executable, "-c", script, str(ROOT / "tools/testdata"), str(ROOT / "services/agents")],
            text=True, capture_output=True, timeout=30, cwd=ROOT,
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode, 0, result.stdout[-1000:] + result.stderr[-2500:])


class ObservationTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.observer = ModelObserver(self.out)

    async def test_request_and_visible_response_keep_body_usage_but_not_headers_or_reasoning(self):
        import httpx
        body = {"model": "original-alias", "messages": [{"role": "user", "content": "source facts"}]}
        request = httpx.Request("POST", "http://local.invalid/v1/chat/completions", json=body,
                               headers={"Authorization": "Bearer private-secret"})
        identity = {"canonical_alert_id": "input1", "run_id": "actual-business-run"}
        token = CURRENT_ALERT.set(identity)
        try:
            await self.observer.request(request)
        finally:
            CURRENT_ALERT.reset(token)
        reply = {"model": "resolved-model", "usage": {"total_tokens": 12}, "choices": [{"index": 0,
            "finish_reason": "stop", "message": {"role": "assistant", "content": "visible reply",
                "reasoning_content": "private internal text", "tool_calls": []}}]}
        response = httpx.Response(200, json=reply, request=request, headers={"X-private": "private-secret"})
        await self.observer.response(response)
        recorded_request = json.loads((self.out / "model-request-01.json").read_text())
        self.assertEqual(recorded_request["body"], body)
        self.assertEqual(recorded_request["alert"], identity)
        recorded_response = (self.out / "model-response-01.json").read_text()
        self.assertNotIn("private", recorded_response)
        self.assertNotIn("private", json.dumps(recorded_request))
        self.assertEqual(json.loads(recorded_response)["body"]["usage"], {"total_tokens": 12})
        self.assertEqual(self.observer.summary()["requests_without_response"], [])

    async def test_request_cap_under_concurrency_and_missing_reply_are_explicit(self):
        import httpx
        requests = [httpx.Request("POST", "http://local.invalid/chat", json={"model": "same"})
                    for _ in range(REQUEST_LIMIT + 1)]
        results = await asyncio.gather(*(self.observer.request(request) for request in requests), return_exceptions=True)
        self.assertEqual(sum(isinstance(result, RuntimeError) for result in results), 1)
        self.assertEqual(len(self.observer.requests), REQUEST_LIMIT)
        self.assertEqual(self.observer.summary()["requests_without_response"], list(range(1, REQUEST_LIMIT + 1)))
        self.assertTrue(self.observer.summary()["cap_reached"])

    async def test_factory_preserves_model_io_options_and_only_bounds_transport(self):
        calls, result, client = [], object(), object()
        def original(role, **kwargs):
            calls.append((role, kwargs))
            return result
        factory = self.observer.factory(original, client)
        kwargs = {"temperature": 0.0, "max_tokens": 2048, "json_output": True, "extra_body": {"unchanged": True}}
        before = copy.deepcopy(kwargs)
        self.assertIs(factory("investigation", **kwargs), result)
        self.assertEqual(kwargs, before)
        self.assertEqual(calls, [("investigation", {**kwargs, "max_retries": 0, "timeout": 45.0, "http_async_client": client})])

    async def test_tool_wrapper_calls_original_once_returns_original_and_records_failure(self):
        calls, result, registry = [], {"rows": [], "status": "no_match"}, object()
        async def execute(instance, name, args):
            calls.append((instance, name, args))
            if name == "failing":
                raise ValueError("do not serialize credentials in exception strings")
            return result
        wrapped = self.observer.execute(execute, lambda value: json.dumps(value))
        args = {"query": "original"}
        self.assertIs(await wrapped(registry, "lookup", args), result)
        self.assertEqual(calls, [(registry, "lookup", args)])
        with self.assertRaises(ValueError):
            await wrapped(registry, "failing", {})
        record = json.loads((self.out / "tool-result-02.json").read_text())
        self.assertEqual(record["interrupted_by"], "ValueError")
        self.assertNotIn("credentials", json.dumps(record))


if __name__ == "__main__":
    unittest.main()
