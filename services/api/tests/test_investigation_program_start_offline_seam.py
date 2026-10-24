"""Actual first-start two-app composition and owned-pipe failure contracts."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
PROBE=ROOT/'openspec/changes/continue-isolated-investigation-v2/probes/program_start_offline_seam.py'
spec=importlib.util.spec_from_file_location('program_start_offline_seam',PROBE)
seam=importlib.util.module_from_spec(spec);spec.loader.exec_module(seam)


class ProgramStartOfflineTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_six_new_ledger_two_process_start_and_read_composition(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.local') as directory:
            path=Path(directory)/'result.json';result=await seam.run_probe(path)
            self.assertEqual(result['status'],'passed_offline_only');self.assertEqual(result['scenarios'],6)
            self.assertEqual(result['API_requests'],80);self.assertEqual(result['backend_calls'],44)
            self.assertEqual(seam.canonical(json.loads(path.read_text('utf-8'))),seam.canonical(result))
            identities=[]
            for case in result['cases']:
                self.assertTrue(case['owned_process']['stopped']);self.assertEqual(case['owned_process']['returncode'],0)
                identities.append(case['owned_process']['identity'])
                final=case['final'];initial=case['initial'];self.assertEqual(final['admission']['intent']['request']['actor_id'],initial['actor_id'])
                self.assertEqual(final['admission']['intent']['request']['budget_policy'],initial['budget_policy'])
                get=next(r for r in case['observations'] if r['case']=='compatible_GET')
                self.assertEqual(seam.canonical(json.loads(get['body_utf8'])),seam.canonical(final['cold_owned']))
                for row in case['observations']:
                    self.assertEqual(seam.sha(row['body_utf8'].encode()),row['body_sha256'])
                    sent=row['API_request'];self.assertEqual(seam.sha(sent['body_utf8'].encode()),sent['body_sha256'])
                    if row['case']=='first':
                        current=row['injected_current_user'];forwarded=row['backend_request']['headers']
                        self.assertNotEqual(sent['headers']['x-aisoc-actor-id'],current['actor_id'])
                        self.assertEqual(forwarded['x-aisoc-actor-id'],current['actor_id'])
                        self.assertEqual(final['admission']['intent']['request']['actor_id'],current['actor_id'])
                    if row['internal']:
                        internal=row['internal'];self.assertEqual(seam.sha(internal['body_utf8'].encode()),internal['body_sha256'])
                        if row['case']!='first':self.assertFalse(internal['rows_changed']);self.assertEqual(internal['new_tool_calls'],0)
                for artifact in final['ledger']['artifacts']:
                    raw=artifact['content'].encode();self.assertEqual(len(raw),artifact['size_bytes']);self.assertEqual(seam.sha(raw),artifact['sha256'])
            self.assertEqual(len({seam.canonical(i) for i in identities}),6)

    async def failure(self, code, error, *, payload=None, timeout=1):
        ready="import sys;sys.stdin.buffer.readline();print('{\"ready\":true}',flush=True);"
        channel=seam.OwnedAgentChannel(command=[sys.executable,'-B','-c',ready+code],timeout=timeout)
        await channel.start()
        try:
            with self.assertRaises(error):await channel.exchange(payload or {'op':'test'})
            self.assertTrue(channel.receipt()['stopped']);before=channel.exchanges
            with self.assertRaises(seam.ProbeFailure):await channel.exchange({'op':'test'})
            self.assertEqual(channel.exchanges,before)
        finally:await channel.finish()
        return channel

    async def test_EOF_does_not_restart_or_replay(self):
        await self.failure('sys.stdin.buffer.readline()',seam.ProbeFailure)

    async def test_partial_frame_refused(self):
        await self.failure("sys.stdin.buffer.readline();sys.stdout.buffer.write(b'{}');sys.stdout.buffer.flush()",seam.ProbeFailure)

    async def test_duplicate_key_nonfinite_and_invalid_UTF8_frames_refused(self):
        for raw,error in ((b'{"a":1,"a":2}\n',seam.ProbeFailure),(b'{"a":NaN}\n',seam.ProbeFailure),(b'\xff\n',UnicodeError),(b'bad\n',ValueError)):
            await self.failure('sys.stdin.buffer.readline();sys.stdout.buffer.write('+repr(raw)+');sys.stdout.buffer.flush()',error)

    async def test_oversized_response_refused_and_owned_process_reaped(self):
        await self.failure("sys.stdin.buffer.readline();sys.stdout.buffer.write(b'x'*(12*1024*1024+1));sys.stdout.buffer.flush()",seam.ProbeFailure)

    async def test_read_timeout_terminal_without_replay(self):
        await self.failure('import time;sys.stdin.buffer.readline();time.sleep(60)',TimeoutError,timeout=.3)

    async def test_slow_frame_chunks_cannot_renew_total_deadline(self):
        code="import time;sys.stdin.buffer.readline();\nfor _ in range(100):\n sys.stdout.buffer.write(b' ');sys.stdout.buffer.flush();time.sleep(.02)"
        await self.failure(code,TimeoutError,timeout=.3)

    async def test_write_and_read_share_one_deadline(self):
        await self.failure('import time;time.sleep(60)',TimeoutError,timeout=.3,payload={'body':'x'*(8*1024*1024)})

    async def test_request_limit_refuses_before_write(self):
        channel=await self.failure('import time;time.sleep(60)',seam.ProbeFailure,payload={'body':'x'*seam.MAX_FRAME})
        self.assertEqual(channel.exchanges,1)  # Only ready was written.

    async def test_startup_handshake_failure_is_terminal_and_owned_only(self):
        channel=seam.OwnedAgentChannel(command=[sys.executable,'-B','-c','pass'],timeout=1)
        with self.assertRaises(seam.ProbeFailure):await channel.start()
        self.assertTrue(channel.receipt()['stopped']);self.assertIsNotNone(channel.receipt()['identity'])
        with self.assertRaises(seam.ProbeFailure):await channel.start()

    async def test_slow_shutdown_is_bounded_and_retained_handle_reaped(self):
        code="import sys,time;sys.stdin.buffer.readline();print('{}',flush=True);sys.stdin.buffer.readline();time.sleep(60)"
        channel=seam.OwnedAgentChannel(command=[sys.executable,'-B','-c',code],timeout=.3)
        await channel.start()
        with self.assertRaises(TimeoutError):await channel.finish()
        self.assertTrue(channel.receipt()['stopped'])

    async def test_output_existing_outside_or_missing_parent_and_bad_configuration_refused(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.local') as directory:
            path=Path(directory)/'existing.json';path.write_text('original','utf-8')
            with self.assertRaises(FileExistsError):await seam.run_probe(path,scenarios=('normal',))
            self.assertEqual(path.read_text('utf-8'),'original')
            with self.assertRaises(seam.ProbeFailure):seam.checked_output(Path(directory)/'missing'/'result.json')
        for path in (ROOT.parent/'outside.json',ROOT/'.git'/'bad.json'):
            with self.assertRaises(seam.ProbeFailure):seam.checked_output(path)
        for timeout in (0,-1,31,True,float('nan'),float('inf')):
            with self.assertRaises(seam.ProbeFailure):seam.OwnedAgentChannel(timeout=timeout)
        with self.assertRaises(seam.ProbeFailure):seam.OwnedAgentChannel(scenario='unknown')

    async def test_failed_probe_preserves_failed_receipt_and_cleans_own_child(self):
        channel=seam.OwnedAgentChannel(command=[sys.executable,'-B','-c','pass'],timeout=1)
        with tempfile.TemporaryDirectory(dir=ROOT/'.local') as directory:
            path=Path(directory)/'failed.json'
            with patch.object(seam,'OwnedAgentChannel',return_value=channel):
                with self.assertRaises(seam.ProbeFailure):await seam.run_probe(path,scenarios=('normal',))
            value=json.loads(path.read_text('utf-8'));self.assertEqual(value['status'],'failed')
            self.assertTrue(value['cases'][0]['owned_process']['stopped'])

    async def test_cleanup_failure_preserves_primary_error_and_nonempty_failed_receipt(self):
        class BrokenChannel:
            finishes=0
            async def start(self):raise ValueError('test-only-primary-startup-failure')
            async def finish(self):self.finishes+=1;raise RuntimeError('test-only-cleanup-failure')
            def receipt(self):return {'stopped':False,'identity':{'test_double':True}}
        channel=BrokenChannel()
        with tempfile.TemporaryDirectory(dir=ROOT/'.local') as directory:
            path=Path(directory)/'failure.json'
            with patch.object(seam,'OwnedAgentChannel',return_value=channel):
                with self.assertRaises(ValueError):await seam.run_probe(path,scenarios=('normal',))
            value=json.loads(path.read_text('utf-8'));case=value['cases'][0]
            self.assertEqual(value['status'],'failed');self.assertEqual(value['error_type'],'ValueError')
            self.assertEqual(case['error_type'],'ValueError');self.assertEqual(case['cleanup_error_type'],'RuntimeError')
            self.assertFalse(case['owned_process']['stopped']);self.assertEqual(channel.finishes,1)


if __name__=='__main__':unittest.main()
