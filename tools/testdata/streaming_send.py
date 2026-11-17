"""Prepare/send one explicitly selected frozen S01 or S04 phase; no investigation."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Literal
from uuid import UUID

from alert_kafka import kafka_config, send_records, source_wire
from alert_scenarios import RUN_ID, _without_answers, json_bytes, sha256
from pydantic import BaseModel, ConfigDict, Field, model_validator
from streaming_fixture import ROOT, load_inputs

VERSION = "socai2.streaming-send.v1"
PHASES = {"S01-context": ("S01/context-events.jsonl", "raw_events", 12),
          "S01-alerts": ("S01/alerts.jsonl", "raw", 3)}
S04_PHASES = {"S04-context": ("S04/context-events.jsonl", "raw_events", 1),
              "S04-alerts": ("S04/alerts.jsonl", "raw", 1)}
CONTRACTS = ("tools/testdata/streaming_send.py", "tools/testdata/alert_kafka.py",
             "services/fusion/app/models/alert.py", "services/fusion/app/services/event_schema.py")


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["socai2.streaming-send.v1"]
    candidate_id: str
    batch_id: str
    tenant_id: UUID
    topics: dict[str, str]
    producer_env_file: str
    expected_bootstrap_servers: str = Field(min_length=1)
    security_protocol: Literal["PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"]
    timeout_seconds: float = Field(gt=0, le=60)
    request_timeout_ms: int = Field(gt=0)
    resource_readback_file: str
    resource_readback_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    phase_set: Literal["S01", "S04"] = "S01"
    baseline_snapshot_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def bound_candidate(self):
        if not RUN_ID.fullmatch(self.batch_id) or not RUN_ID.fullmatch(self.candidate_id):
            raise ValueError("invalid batch or candidate ID")
        expected = {role: f"socai2.testdata.{self.candidate_id}.{role}"
                    for role in ("raw", "raw_events", "fused", "dlq")}
        if self.topics != expected:
            raise ValueError("topics must bind the explicit candidate, independently of batch ID")
        if not Path(self.producer_env_file).is_absolute():
            raise ValueError("producer env file must be explicit and absolute")
        if self.request_timeout_ms > self.timeout_seconds * 1000:
            raise ValueError("producer timeout exceeds send deadline")
        if (self.phase_set == "S04") != (self.baseline_snapshot_sha256 is not None):
            raise ValueError("only S04 requires the frozen prior investigation snapshot hash")
        return self


def _event_schema():
    name = "socai2_streaming_event_schema"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "services/fusion/app/services/event_schema.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _record(value, phase, tenant):
    payload = json.loads(value)
    _without_answers(payload)
    if phase.endswith("-context"):
        result = _event_schema().validate_raw_event(payload)
        if not result.ok or result.tenant_id != tenant or not result.source_event_id:
            raise ValueError("invalid context event or tenant")
        if (payload["ocsf_event"].get("tenant_uid") != tenant
                or payload["ocsf_event"].get("uid") != result.source_event_id):
            raise ValueError("nested context identity differs")
        identity = {"source_event_id": str(UUID(result.source_event_id))}
    else:
        wire, prediction = source_wire(payload, tenant)
        if wire != payload:
            raise ValueError("prepared alert must already be source-v1")
        identity = {"alert_id": payload["id"], "predicted_canonical_alert_id": prediction,
                    "source_event_ids": payload["source_event_ids"]}
    return {**identity, "wire_sha256": sha256(value)}


def prepare(dataset, profile_path, out):
    dataset, profile_path, out = Path(dataset), Path(profile_path), Path(out)
    profile = Profile.model_validate_json(profile_path.read_bytes())
    config, source_manifest, inputs = load_inputs(dataset)  # Does not read expected/control files.
    if config["batch_id"] != profile.batch_id or config["tenant_id"] != str(profile.tenant_id):
        raise ValueError("dataset and selected execution profile differ")
    if source_manifest["candidate_binding"]["value"]["candidate_id"] != profile.candidate_id:
        raise ValueError("candidate identity differs")
    resource = (profile_path.parent / profile.resource_readback_file).read_bytes()
    if sha256(resource) != profile.resource_readback_sha256 or json.loads(resource).get("status") != "passed":
        raise ValueError("actual resource readback must be passed and hash-bound")
    frozen = profile.model_copy(update={"resource_readback_file": "resource-readback.json"})
    files = {"profile.json": json_bytes(frozen.model_dump(mode="json")), "resource-readback.json": resource}
    phases = {}
    for phase, (source_path, role, count) in (S04_PHASES if profile.phase_set == "S04" else PHASES).items():
        values = [line + b"\n" for line in inputs[source_path].splitlines()]
        if len(values) != count:
            raise ValueError("wrong selected phase size")
        records = []
        for index, value in enumerate(values, 1):
            name = f"wire/{phase}/{index:03d}.json"
            records.append({**_record(value, phase, str(profile.tenant_id)), "wire": name})
            files[name] = value
        phases[phase] = {"topic": profile.topics[role], "count": count, "records": records}
    manifest = {"schema_version": VERSION, "batch_id": profile.batch_id, "candidate_id": profile.candidate_id,
        "tenant_id": str(profile.tenant_id), "dataset_manifest_sha256": sha256((dataset / "manifest.json").read_bytes()),
        "profile_sha256": sha256(files["profile.json"]), "resource_readback_sha256": sha256(resource),
        "source_sha256": {p: sha256((ROOT / p).read_bytes()) for p in CONTRACTS},
        "phases": phases, "phase_set": profile.phase_set, "baseline_snapshot_sha256": profile.baseline_snapshot_sha256,
        "prepared_only": True, "processing_confirmed": False}
    out.mkdir(parents=True, exist_ok=False)
    (out / "receipts").mkdir()
    for name, body in {**files, "manifest.json": json_bytes(manifest)}.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    load_prepared(out)
    return manifest


def load_prepared(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_bytes())
    profile_bytes = (directory / "profile.json").read_bytes()
    profile = Profile.model_validate_json(profile_bytes)
    if (manifest["schema_version"] != VERSION or manifest["batch_id"] != profile.batch_id
            or manifest["candidate_id"] != profile.candidate_id or manifest["tenant_id"] != str(profile.tenant_id)
            or manifest.get("phase_set", "S01") != profile.phase_set
            or manifest.get("baseline_snapshot_sha256") != profile.baseline_snapshot_sha256
            or manifest["profile_sha256"] != sha256(profile_bytes)
            or profile.resource_readback_file != "resource-readback.json"
            or manifest["source_sha256"] != {p: sha256((ROOT / p).read_bytes()) for p in CONTRACTS}):
        raise ValueError("prepared identity/profile/contracts changed")
    resource = (directory / "resource-readback.json").read_bytes()
    if (manifest["resource_readback_sha256"] != sha256(resource)
            or profile.resource_readback_sha256 != sha256(resource) or json.loads(resource).get("status") != "passed"):
        raise ValueError("resource readback changed")
    selected = S04_PHASES if profile.phase_set == "S04" else PHASES
    if set(manifest["phases"]) != set(selected):
        raise ValueError("only the two selected stages are allowed")
    values_by_phase = {}
    for phase, (_, role, count) in selected.items():
        plan = manifest["phases"][phase]
        if plan["topic"] != profile.topics[role] or plan["count"] != count or len(plan["records"]) != count:
            raise ValueError("stage topic or count changed")
        values = []
        for index, record in enumerate(plan["records"], 1):
            name = f"wire/{phase}/{index:03d}.json"
            if record["wire"] != name:
                raise ValueError("invalid stage path")
            path = directory / name
            if path.is_symlink() or path.parent.is_symlink():
                raise ValueError("wire symlinks are not accepted")
            body = path.read_bytes()
            if record != {**_record(body, phase, str(profile.tenant_id)), "wire": name}:
                raise ValueError("stage bytes or identity changed")
            values.append(body)
        values_by_phase[phase] = values
    context_phase, alert_phase = profile.phase_set + "-context", profile.phase_set + "-alerts"
    events = {r["source_event_id"] for r in manifest["phases"][context_phase]["records"]}
    alerts = manifest["phases"][alert_phase]["records"]
    if len(events) != selected[context_phase][2] or len({r["alert_id"] for r in alerts}) != selected[alert_phase][2] or any(
            len(r["source_event_ids"]) != 1 or r["source_event_ids"][0] not in events for r in alerts):
        raise ValueError("duplicate identities or invalid direct source links")
    return profile, manifest, values_by_phase


def _context_gate(directory, manifest, readback_path):
    if readback_path is None:
        raise ValueError("actual context readback required before alerts")
    phase = manifest.get("phase_set", "S01") + "-context"
    count = manifest["phases"][phase]["count"]
    sent = json.loads((directory / "receipts" / (phase + ".json")).read_bytes())
    body = Path(readback_path).read_bytes()
    readback = json.loads(body)
    event_ids = {r["source_event_id"] for r in manifest["phases"][phase]["records"]}
    digest = sha256((directory / "manifest.json").read_bytes())
    if (sent.get("status") != "accepted_only" or sent.get("accepted") != count
            or sent.get("phase") != phase or sent.get("batch_id") != manifest["batch_id"]
            or sent.get("tenant_id") != manifest["tenant_id"] or sent.get("not_attempted") != 0
            or sent.get("topic") != manifest["phases"][phase]["topic"]
            or sent.get("prepared_manifest_sha256") != digest
            or readback.get("status") != "passed" or readback.get("source") != "real_lake_readback"
            or readback.get("batch_id") != manifest["batch_id"] or readback.get("tenant_id") != manifest["tenant_id"]
            or readback.get("prepared_manifest_sha256") != digest
            or set(readback.get("event_ids", [])) != event_ids or len(readback.get("event_ids", [])) != count):
        raise ValueError("context has not passed actual same-batch readback")
    if manifest.get("phase_set", "S01") == "S04":
        if (readback.get("baseline_snapshot_sha256") != manifest["baseline_snapshot_sha256"]
                or readback.get("business_baseline_unchanged") is not True
                or readback.get("delta_counts") != dict.fromkeys(("alerts", "incidents", "tasks", "attempts", "runs", "model_calls"), 0)):
            raise ValueError("S04 context has not passed actual same-batch readback against the prior baseline")
    elif any(readback.get(key) != 0 for key in ("unexpected_alerts", "unexpected_incidents",
             "unexpected_tasks", "attempts", "runs", "model_calls")):
        raise ValueError("context has not passed actual same-batch readback")
    return sha256(body)


def _s04_preflight_gate(directory, manifest, path):
    if path is None:
        raise ValueError("S04 requires actual preflight readback before context")
    body = Path(path).read_bytes()
    value = json.loads(body)
    if (value.get("status") != "passed" or value.get("source") != "real_lake_and_postgres_readback"
            or value.get("batch_id") != manifest["batch_id"] or value.get("tenant_id") != manifest["tenant_id"]
            or value.get("prepared_manifest_sha256") != sha256((directory / "manifest.json").read_bytes())
            or value.get("baseline_snapshot_sha256") != manifest["baseline_snapshot_sha256"]
            or value.get("new_alert_absent") is not True or value.get("new_event_absent") is not True
            or value.get("business_baseline_unchanged") is not True):
        raise ValueError("S04 preflight has not verified absence and unchanged prior baseline")
    return sha256(body)


async def send_phase(directory, phase, *, context_readback=None, preflight_readback=None, producer_factory=None):
    directory = Path(directory)
    profile, manifest, values = load_prepared(directory)
    if phase not in manifest["phases"]:
        raise ValueError("only " + profile.phase_set + " phases selected in this prepared directory may be sent")
    receipt = directory / "receipts" / f"{phase}.json"
    if receipt.exists():
        raise FileExistsError("stage already has a send intent; never resend")
    prior = _context_gate(directory, manifest, context_readback) if phase.endswith("-alerts") else None
    preflight = _s04_preflight_gate(directory, manifest, preflight_readback) if phase == "S04-context" else None
    transport = kafka_config(Path(profile.producer_env_file))
    if (transport["bootstrap_servers"] != profile.expected_bootstrap_servers
            or transport["security_protocol"] != profile.security_protocol):
        raise ValueError("actual producer transport differs from frozen profile")
    records = [{k: v for k, v in r.items() if k != "wire"} for r in manifest["phases"][phase]["records"]]
    return await send_records(records=records, values=values[phase], tenant=manifest["tenant_id"],
        topic=manifest["phases"][phase]["topic"], receipt=receipt, config=transport,
        timeout=profile.timeout_seconds, request_timeout_ms=profile.request_timeout_ms,
        identity={"schema_version": VERSION, "batch_id": manifest["batch_id"], "phase": phase,
            "prepared_manifest_sha256": sha256((directory / "manifest.json").read_bytes()),
            "context_readback_sha256": prior, "preflight_readback_sha256": preflight}, producer_factory=producer_factory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--dataset", type=Path, required=True)
    prep.add_argument("--profile", type=Path, required=True)
    prep.add_argument("--out", type=Path, required=True)
    check = commands.add_parser("validate")
    check.add_argument("--prepared", type=Path, required=True)
    send = commands.add_parser("send")
    send.add_argument("--prepared", type=Path, required=True)
    send.add_argument("--phase", choices=tuple(PHASES) + tuple(S04_PHASES), required=True)
    send.add_argument("--context-readback", type=Path)
    send.add_argument("--preflight-readback", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        manifest = prepare(args.dataset, args.profile, args.out)
        print(json.dumps({"batch_id": manifest["batch_id"], "prepared_only": True, "phases": list(manifest["phases"])}))
    elif args.command == "validate":
        _, manifest, _ = load_prepared(args.prepared)
        print(json.dumps({"batch_id": manifest["batch_id"], "prepared_only": True, "phases": list(manifest["phases"])}))
    else:
        result = asyncio.run(send_phase(args.prepared, args.phase, context_readback=args.context_readback,
                                       preflight_readback=args.preflight_readback))
        print(json.dumps({k: result[k] for k in ("batch_id", "phase", "status", "accepted", "not_attempted")}))
        sys.exit(0 if result["status"] == "accepted_only" else 1)
