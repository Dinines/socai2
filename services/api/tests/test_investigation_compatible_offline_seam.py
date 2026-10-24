"""Portable offline two-app seam and owned subprocess failure contracts."""
import asyncio
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
PROBE = ROOT / "openspec/changes/continue-isolated-investigation-v2/probes/compatible_result_offline_seam.py"
spec = importlib.util.spec_from_file_location("compatible_offline_seam", PROBE)
seam = importlib.util.module_from_spec(spec); spec.loader.exec_module(seam)


class CompatibleOfflineSeamTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_two_process_SQL_ASGI_composition_is_read_only(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".local") as directory:
            output = Path(directory) / "result.json"
            result = await seam.run_probe(output)
            self.assertEqual(result["status"], "passed_offline_only")
            self.assertEqual(result["direct_fixture_cases"], 12)
            self.assertEqual(result["selected_ledger_cases"], 14)
            self.assertEqual(len(result["observations"]), 39)
            self.assertEqual(result["backend_calls"], 32)
            self.assertTrue(result["nil_run_refused"])
            self.assertEqual(result["owned_process"]["returncode"], 0)
            self.assertTrue(result["owned_process"]["stopped"])
            self.assertEqual(seam.canonical(json.loads(output.read_text(encoding="utf-8"))), seam.canonical(result))
            for row in result["observations"]:
                if row["internal"]:
                    baseline = result["inventory"][row["fixture"]]
                    self.assertEqual(row["internal"]["ledger_sha256"], baseline["ledger_sha256"])
                    self.assertEqual(row["internal"]["tool_calls"], baseline["tool_calls"])

    async def _failed_channel(self, code, error, *, timeout=1, payload=None):
        channel = seam.OwnedAgentChannel(command=[sys.executable, "-B", "-c", code], timeout=timeout)
        await channel.start()
        try:
            with self.assertRaises(error): await channel.exchange(payload or {"op": "test"})
            self.assertIsNotNone(channel.process.poll())
            before = channel.exchanges
            with self.assertRaises(seam.ProbeFailure): await channel.exchange({"op": "test"})
            self.assertEqual(channel.exchanges, before)
        finally:
            await channel.finish()
        return channel

    async def test_EOF_is_terminal_and_cleans_only_owned_handle(self):
        await self._failed_channel("import sys;sys.stdin.buffer.readline()", seam.ProbeFailure)

    async def test_bad_JSON_is_terminal_without_replay(self):
        await self._failed_channel("import sys;sys.stdin.buffer.readline();print('not json',flush=True)", ValueError)

    async def test_oversized_response_is_terminal_and_process_is_reaped(self):
        await self._failed_channel("import sys;sys.stdin.buffer.readline();sys.stdout.buffer.write(b'x'*(3*1024*1024+1));sys.stdout.buffer.flush()", seam.ProbeFailure)

    async def test_read_timeout_covers_exchange_and_reaps_process(self):
        await self._failed_channel("import sys,time;sys.stdin.buffer.readline();time.sleep(60)", asyncio.TimeoutError, timeout=0.15)

    async def test_write_timeout_is_covered_by_same_exchange_deadline(self):
        # Child never reads; a frame larger than the OS pipe capacity blocks
        # write(), so timing only readline() would leave this test hanging.
        await self._failed_channel("import time;time.sleep(60)", asyncio.TimeoutError, timeout=0.15, payload={"body": "x" * (2*1024*1024)})

    async def test_oversized_request_never_writes_or_replays(self):
        c = await self._failed_channel("import time;time.sleep(60)", seam.ProbeFailure, payload={"body": "x" * seam.MAX_FRAME})
        self.assertEqual(c.exchanges, 0)

    async def test_output_outside_workspace_missing_parent_or_existing_file_is_refused(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".local") as directory:
            path = Path(directory) / "existing.json"; path.write_text("original", encoding="utf-8")
            with self.assertRaises(FileExistsError): await seam.run_probe(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "original")
            with self.assertRaises(seam.ProbeFailure): seam.checked_output(Path(directory) / "absent" / "output.json")
        with self.assertRaises(seam.ProbeFailure): seam.checked_output(ROOT.parent / "outside.json")
        with self.assertRaises(seam.ProbeFailure): seam.checked_output(ROOT / ".git" / "test.json")
        for timeout in (0, -1, 31, True, float("nan")):
            with self.assertRaises(seam.ProbeFailure): seam.OwnedAgentChannel(timeout=timeout)

    async def test_probe_failure_still_saves_failed_receipt_and_reaps_owned_child(self):
        channel = seam.OwnedAgentChannel(command=[sys.executable, "-B", "-c", "import sys;sys.stdin.buffer.readline()"], timeout=1)
        with tempfile.TemporaryDirectory(dir=ROOT / ".local") as directory:
            path = Path(directory) / "failed.json"
            with patch.object(seam, "OwnedAgentChannel", return_value=channel):
                with self.assertRaises(seam.ProbeFailure): await seam.run_probe(path)
            result = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["owned_process"]["stopped"])
            self.assertIsNotNone(channel.process.poll())


if __name__ == "__main__": unittest.main()
