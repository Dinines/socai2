"""Direct checks for read-only event inventory, with synthetic structures only."""
import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiokafka import TopicPartition

spec = importlib.util.spec_from_file_location(
    "event_inventory", Path(__file__).with_name("inspect_spirithub_event_types.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def config():
    return {
        "profile": "synthetic-inventory", "topics": ["lyc-inventory"],
        "field_paths": ["device.hostname", "is_alert"],
        "kafka": {"bootstrap_servers": ["unused:9092"], "security_protocol": "PLAINTEXT",
                  "client_id": "lyc-inventory", "isolation_level": "read_uncommitted"},
        "scan": {"poll_timeout_ms": 1, "max_records_per_poll": 10,
                 "max_duration_seconds_per_topic": 1, "request_timeout_ms": 1000,
                 "fetch_max_bytes": 4096, "max_partition_fetch_bytes": 4096},
    }


def test_profile_preserves_class_zero_false_and_invalid_messages():
    profile = module.Profile(config()["field_paths"])
    inputs = [
        {"class_uid": 0, "is_alert": False, "device": {"hostname": "private-observation"}},
        {"ocsf_event": {"class_uid": 0, "is_alert": None}},
        {"class_uid": 2004, "is_alert": 0},
        {"class_uid": "2004"},
        {"ocsf_event": None},
        [],
    ]
    for event in inputs:
        profile.add(json.dumps(event).encode())
    profile.add(b"{invalid")
    profile.add(None)
    report = profile.report()
    assert report["records"] == 8
    assert sum(report["message_kinds"].values()) == 8
    assert report["classes"]["0"]["is_alert"] == {"false": 1, "null": 1}
    assert report["classes"]["2004"]["is_alert"] == {"invalid": 1}
    assert report["classes"]["invalid"]["is_alert"] == {"missing": 1}
    assert report["classes"]["0"]["fields"]["device.hostname"] == {"string": 1, "missing": 1}
    assert "private-observation" not in json.dumps(report)


class Reader:
    def __init__(self, timeout=False):
        self.tp = TopicPartition("lyc-inventory", 0)
        self.offset = None
        self.closed = False
        self.timeout = timeout

    async def start(self):
        pass

    async def stop(self):
        self.closed = True

    async def metadata(self):
        return {self.tp.topic: [0]}

    async def beginning_offsets(self, _partitions):
        return {self.tp: 5}

    async def end_offsets(self, _partitions):
        return {self.tp: 9}

    def assign(self, partitions):
        assert partitions == [self.tp]

    def seek(self, tp, offset):
        assert tp == self.tp
        self.offset = offset

    async def position(self, _partition):
        return self.offset

    async def getmany(self, *partitions, **_kwargs):
        assert partitions == (self.tp,)
        if self.timeout:
            raise asyncio.TimeoutError()
        self.offset = 11
        return {self.tp: [SimpleNamespace(offset=i, value=b'{"class_uid":4001}')
                         for i in (5, 7, 10)]}


def test_scan_freezes_range_and_never_commits():
    reader = Reader()  # Has no commit or subscribe methods.
    report = asyncio.run(module.inventory(config(), reader, TopicPartition, reader.metadata))
    entry = report["topics"][reader.tp.topic]
    assert report["status"] == "complete" and reader.closed
    assert entry["profile"]["records"] == 2
    assert entry["partitions"]["0"] == {
        "start_offset": 5, "end_offset_exclusive": 9, "next_offset": 9, "records": 2}
    options = module.client_options(config())
    assert options["group_id"] is None and options["enable_auto_commit"] is False
    assert options["auto_offset_reset"] == "none"


def test_unfinished_read_is_not_reported_complete():
    reader = Reader(timeout=True)
    report = asyncio.run(module.inventory(config(), reader, TopicPartition, reader.metadata))
    entry = report["topics"][reader.tp.topic]
    assert report["status"] == entry["status"] == "incomplete"
    assert entry["error_type"] == "TimeoutError" and reader.closed
    assert entry["partitions"]["0"]["next_offset"] == 5


def test_private_report_readback_and_no_overwrite(tmp_path):
    path = tmp_path / "inventory.json"
    report = {"status": "complete", "profile": module.Profile([]).report()}
    module.write_report(path, report)
    assert json.loads(path.read_text()) == report
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        module.write_report(path, {"replaced": True})


def test_metadata_requires_all_partitions_and_ignores_other_topics():
    rows = [
        {"topic": "lyc-inventory", "error_code": 0,
         "partitions": [{"partition": 0, "error_code": 0},
                        {"partition": 1, "error_code": 5}]},
        {"topic": "lyc-unselected", "error_code": 0,
         "partitions": [{"partition": 0, "error_code": 0}]},
    ]
    assert module.available_partitions(rows, config()["topics"]) == {}
    rows[0]["partitions"][1]["error_code"] = 0
    assert module.available_partitions(rows, config()["topics"]) == {"lyc-inventory": [0, 1]}
