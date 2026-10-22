#!/usr/bin/env python3
"""Bounded synthetic existing-alert fixtures; generation never sends traffic."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import NAMESPACE_URL, UUID, uuid5

HERE = Path(__file__).resolve().parent
SOURCE = "socai2-synthetic-eval"
ANSWER_FIELDS = frozenset({"expected_tactics", "expected_techniques", "response_class", "evidence_keywords"})
MAX_COUNT = 20
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ENTITY_KEYS = {
    "hostname": ("Computer", "hostname", "host"),
    "username": ("User", "UserId", "username", "user"),
    "src_ip": ("src_ip", "SourceIp", "sourceIPAddress", "ClientIP", "ipAddress"),
}


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _generator() -> Any:
    name = "socai2_synthetic_upstream_generator"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, HERE / "upstream/generate_eval_incidents.py")
        if spec is None or spec.loader is None:
            raise ValueError("upstream generator unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _event_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("event-time must include an explicit timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _without_answers(value: Any) -> None:
    if isinstance(value, dict):
        if ANSWER_FIELDS.intersection(value):
            raise ValueError("answer fields must remain outside the request payload")
        for child in value.values():
            _without_answers(child)
    elif isinstance(value, list):
        for child in value:
            _without_answers(child)


def _entities(telemetry: list[dict[str, Any]]) -> dict[str, str]:
    """Only explicit, unanimous scalar fields; no extraction from narratives/URLs."""
    projected = {}
    for target, keys in ENTITY_KEYS.items():
        values = {event[key].strip() for event in telemetry for key in keys
                  if isinstance(event.get(key), str) and event[key].strip()}
        if len(values) != 1:
            continue
        value = next(iter(values))
        if target == "src_ip":
            try:
                ipaddress.ip_address(value)
            except ValueError:
                continue
        projected[target] = value
    return projected


def generate_batch(*, run_id: str, tenant: str, event_time: str, count: int = 3, out: Path) -> dict[str, Any]:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("run-id must be 1..64 letters, digits, dots, underscores or hyphens")
    tenant = str(UUID(tenant))
    event_time = _event_time(event_time)
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_COUNT:
        raise ValueError("count must be 1..20")
    out = Path(out)
    if out.exists():
        raise FileExistsError("output directory already exists; choose a new directory")
    upstream = json.loads((HERE / "upstream/source-manifest.json").read_text())
    generator_hash = sha256((HERE / "upstream/generate_eval_incidents.py").read_bytes())
    expected_hash = next(row["sha256"] for row in upstream["files"]
                         if row["upstream_path"] == "scripts/generate_eval_incidents.py")
    if generator_hash != expected_hash:
        raise ValueError("upstream generator differs from its source manifest")
    scenarios = _generator().generate_incidents(count)
    # Validate/build all requests before creating the output directory.
    materials = []
    for index, scenario in enumerate(scenarios, 1):
        scenario_id = scenario["id"]
        alert_id = str(uuid5(NAMESPACE_URL, f"socai2:testdata:{tenant}:{run_id}:{scenario_id}"))
        payload = {
            "schema_version": "v1", "id": alert_id, "tenant_id": tenant,
            "source": SOURCE, "title": scenario["title"], "description": scenario["description"],
            "severity": scenario["severity"], "event_time": event_time, "created_at": event_time,
            "source_event_ids": [f"{run_id}:{scenario_id}:event:{n}" for n, _ in enumerate(scenario["telemetry"], 1)],
            "tags": ["synthetic", f"run:{run_id}"],
            "raw_event": {"synthetic": True, "run_id": run_id, "scenario_id": scenario_id,
                          "telemetry": scenario["telemetry"]},
            **_entities(scenario["telemetry"]),
        }
        _without_answers(payload)
        expected = {
            "scenario_id": scenario_id, "alert_id": alert_id, "template_id": scenario["template_id"],
            "synthetic": True, "expectation_source": "upstream synthetic template; not observed results",
            **{key: scenario[key] for key in sorted(ANSWER_FIELDS)},
        }
        materials.append((index, payload, expected))
    out.mkdir(parents=True, exist_ok=False)
    (out / "payloads").mkdir()
    (out / "expected").mkdir()
    records = []
    for index, payload, expected in materials:
        payload_name, expected_name = f"payloads/{index:03d}.json", f"expected/{index:03d}.json"
        payload_data, expected_data = json_bytes(payload), json_bytes(expected)
        (out / payload_name).write_bytes(payload_data)
        (out / expected_name).write_bytes(expected_data)
        records.append({"scenario_id": expected["scenario_id"], "alert_id": payload["id"],
                        "payload": payload_name, "payload_sha256": sha256(payload_data),
                        "expected": expected_name, "expected_sha256": sha256(expected_data)})
    manifest = {"schema_version": "socai2-existing-alert-fixtures/v1", "run_id": run_id,
                "tenant_id": tenant, "event_time": event_time, "count": count,
                "source": {"repository": upstream["repository"], "commit": upstream["commit"],
                           "generator_sha256": generator_hash},
                "mode": "synthetic-existing-alerts", "records": records,
                "limitations": ["No detection, model or business request runs during generation.",
                                "Template narratives contain authored conclusions; this is not a blind quality corpus.",
                                "No case/incident membership or attack-chain ground truth is supplied."]}
    (out / "manifest.json").write_bytes(json_bytes(manifest))
    return manifest


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _load_payloads(input_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = json.loads((input_dir / "manifest.json").read_text())
    records = manifest.get("records", [])
    if manifest.get("schema_version") != "socai2-existing-alert-fixtures/v1":
        raise ValueError("unsupported fixture manifest")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_COUNT or manifest.get("count") != len(records):
        raise ValueError("a send batch must contain 1..20 manifest records")
    payloads = []
    for index, record in enumerate(records, 1):
        if record.get("payload") != f"payloads/{index:03d}.json":
            raise ValueError("unexpected payload path")
        path = input_dir / record["payload"]
        if path.is_symlink():
            raise ValueError("payload symlinks are not accepted")
        data = path.read_bytes()
        if sha256(data) != record.get("payload_sha256"):
            raise ValueError("payload hash mismatch")
        payload = json.loads(data)
        _without_answers(payload)
        if (payload.get("id") != record.get("alert_id") or payload.get("tenant_id") != manifest.get("tenant_id")
                or payload.get("source") != SOURCE or "synthetic" not in payload.get("tags", [])
                or payload.get("raw_event", {}).get("synthetic") is not True):
            raise ValueError("payload does not match the synthetic batch identity")
        UUID(payload["id"])
        payloads.append(payload)
    if len({item["id"] for item in payloads}) != len(payloads):
        raise ValueError("duplicate alert IDs in batch")
    return manifest, payloads


def _accepted(response: Any, alert_id: str, tenant_id: str, source_event_ids: list[str]) -> bool:
    if not isinstance(response, dict):
        return False
    try:
        UUID(response["canonical_alert_id"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return False
    message = response.get("message")
    return (response.get("status") == "accepted" and response.get("input_id") == alert_id
            and response.get("tenant_id") == tenant_id
            and response.get("source_event_ids") == source_event_ids
            and response.get("identity_version") == "source-v1" and response.get("processing_confirmed") is False
            and isinstance(message, dict) and isinstance(message.get("topic"), str) and bool(message["topic"])
            and type(message.get("partition")) is int and message["partition"] >= 0
            and type(message.get("offset")) is int and message["offset"] >= 0)


def send_batch(*, input_dir: Path, url: str, token_env: str, receipt: Path, timeout: float = 20) -> dict[str, Any]:
    """Explicit send only. A transport error may follow acceptance; never retry here."""
    parts = urlsplit(url)
    if (parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password
            or parts.query or parts.fragment or parts.path != "/api/v1/alert-ingress"):
        raise ValueError("url must be a full http(s) /api/v1/alert-ingress URL without credentials/query/fragment")
    if not ENV_NAME.fullmatch(token_env) or not os.environ.get(token_env):
        raise ValueError("token-env must name a nonempty environment variable")
    if not 0 < timeout <= 60:
        raise ValueError("timeout must be greater than zero and at most 60 seconds")
    manifest, payloads = _load_payloads(Path(input_dir))
    receipt = Path(receipt)
    # Exclusive creation must succeed before any request can begin.
    fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    state: dict[str, Any] = {"schema_version": "socai2-existing-alert-send/v1", "run_id": manifest["run_id"],
                             "tenant_id": manifest["tenant_id"], "url": url, "requested": len(payloads),
                             "accepted": 0, "processing_confirmed": False, "status": "running", "records": []}
    opener = build_opener(NoRedirect())
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        def save() -> None:
            output.seek(0)
            output.write(json_bytes(state).decode("utf-8"))
            output.truncate()
            output.flush()
            os.fsync(output.fileno())

        save()
        for payload in payloads:
            item: dict[str, Any] = {"alert_id": payload["id"], "state": "started_outcome_unknown"}
            state["records"].append(item)
            save()
            request = Request(url, data=json_bytes(payload), method="POST",
                              headers={"Content-Type": "application/json", "Authorization": f"Bearer {os.environ[token_env]}"})
            try:
                with opener.open(request, timeout=timeout) as result:
                    item["http_status"] = result.status
                    body = result.read(65537)
                    if len(body) > 65536:
                        raise ValueError("response too large")
                    response = json.loads(body)
                    # Only known non-secret response fields, never a server error body.
                    if isinstance(response, dict):
                        item["response"] = {key: response[key] for key in
                                            ("status", "input_id", "tenant_id", "source_event_ids", "canonical_alert_id", "identity_version",
                                             "processing_confirmed", "message", "result_url") if key in response}
                    if result.status != 202 or not _accepted(response, payload["id"], payload["tenant_id"], payload["source_event_ids"]):
                        item["state"] = "response_unconfirmed"
                        state["status"] = "failed"
                    else:
                        item["state"] = "accepted_not_processed"
                        state["accepted"] += 1
            except HTTPError as exc:
                item.update(state="http_refused_or_unconfirmed", http_status=exc.code, error_type="HTTPError")
                state["status"] = "failed"
            except Exception as exc:  # Every interrupted/refused request stops the batch; never retry.
                item.update(state="outcome_unknown", error_type=type(exc).__name__)
                state["status"] = "failed"
            save()
            if state["status"] == "failed":
                break
        if state["status"] != "failed":
            state["status"] = "accepted_only"
        state["not_attempted"] = len(payloads) - len(state["records"])
        save()
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate", help="write a new local batch; no network")
    generate.add_argument("--run-id", required=True)
    generate.add_argument("--tenant", required=True)
    generate.add_argument("--event-time", required=True)
    generate.add_argument("--count", type=int, default=3)
    generate.add_argument("--out", required=True, type=Path)
    send = sub.add_parser("send", help="explicitly send 1..20 alerts once; no retries or redirects")
    send.add_argument("--input-dir", required=True, type=Path)
    send.add_argument("--url", required=True)
    send.add_argument("--token-env", required=True)
    send.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)
    values = vars(args).copy()
    command = values.pop("command")
    try:
        result = generate_batch(**values) if command == "generate" else send_batch(**values)
    except (OSError, ValueError, KeyError) as exc:
        # Avoid exception bodies that might contain a token or a server response.
        print(f"{command} refused ({type(exc).__name__}); check arguments, input manifest and fresh output path", file=sys.stderr)
        return 2
    print(json.dumps({"command": command, "run_id": result["run_id"],
                      "status": result.get("status", "generated"),
                      "count": result.get("count", result.get("requested")),
                      "accepted": result.get("accepted"), "processing_confirmed": False}))
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
