"""Freeze a new execution from read-only material templates; no live connections."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from acceptance_contract import Profile
from acceptance_materials import (
    MaterialError,
    _event_schema,
    _safe_file,
    control,
    inspect_package,
    read_json,
    save_report,
)
from acceptance_runtime_contract import Execution
from alert_kafka import raw_alert_model, source_wire
from alert_scenarios import json_bytes, sha256


def _ocsf_objects(payload, role):
    if role == "context":
        return [(payload["ocsf_event"], "ocsf_event")]
    raw = payload["raw_event"]
    if isinstance(raw.get("ocsf_event"), dict):
        return [(raw["ocsf_event"], "raw_event.ocsf_event")]
    if "class_uid" in raw:
        return [(raw, "raw_event")]
    return []


def _nested_ocsf(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return None
    return raw if isinstance(raw, dict) and "class_uid" in raw else None


def prepare_execution(materials: Path, profile: Profile, execution: Execution, output: Path):
    if output.exists() or output.resolve().is_relative_to(materials.resolve()):
        raise MaterialError("execution output must be a new directory outside materials")
    plan = inspect_package(materials, profile)
    namespace = uuid5(NAMESPACE_URL, f"socai2.acceptance:{profile.tenant_id}:{execution.execution_id}")
    schema = _event_schema()
    original = {p: read_json(_safe_file(materials, p)) for p in plan["material_sha256"]}
    event_ids = set()

    def collect(ocsf):
        metadata = ocsf.get("metadata")
        for value in (ocsf.get("uid"), metadata.get("uid") if isinstance(metadata, dict) else None):
            if isinstance(value, str) and value:
                event_ids.add(schema.canonical_source_event_id(value))
        nested = _nested_ocsf(ocsf.get("raw_data"))
        if nested is not None:
            collect(nested)

    for path, payload in original.items():
        role = path.split("/")[1]
        if role == "context":
            event_ids.add(schema.resolve_source_event_id(payload, payload["ocsf_event"]))
        else:
            event_ids.update(schema.canonical_source_event_id(x) for x in payload["source_event_ids"])
        for ocsf, _ in _ocsf_objects(payload, role):
            collect(ocsf)
    mapping = {value: str(uuid5(namespace, "event:" + value)) for value in sorted(event_ids)}
    changes, identities, wires = [], {}, {}

    def change(record, target, key, new, position):
        if target.get(key) != new:
            changes.append({"record": record, "path": position + "." + key,
                            "old": target.get(key), "new": new})
            target[key] = new

    def remap_ocsf(record, value, path):
        metadata = value.get("metadata")
        for target, key, position in ((value, "uid", path), (metadata if isinstance(metadata, dict) else {}, "uid", path + ".metadata")):
            old = target.get(key)
            if isinstance(old, str) and schema.canonical_source_event_id(old) in mapping:
                change(record, target, key, mapping[schema.canonical_source_event_id(old)], position)
        raw = value.get("raw_data")
        nested = _nested_ocsf(raw)
        if nested is not None:
            before = copy.deepcopy(nested)
            remap_ocsf(record, nested, path + (".raw_data(JSON)" if isinstance(raw, str) else ".raw_data"))
            if isinstance(raw, str) and nested != before:
                encoded = json_bytes(nested).decode()
                changes.append({"record": record, "path": path + ".raw_data",
                                "old_sha256": sha256(raw.encode()), "new_sha256": sha256(encoded.encode()),
                                "reason": "serialize identified OCSF source identity changes"})
                value["raw_data"] = encoded

    for path, before in original.items():
        value = copy.deepcopy(before)
        role = path.split("/")[1]
        if role == "context":
            source_id = schema.resolve_source_event_id(before, before["ocsf_event"])
            identity = mapping[source_id]
            change(path, value, "event_id", identity, "$")
            if "id" in value:
                change(path, value, "id", identity, "$")
            entry = {"kind": "context", "source_id": source_id, "event_id": identity}
        else:
            identity = str(uuid5(namespace, "alert:" + before["id"]))
            change(path, value, "id", identity, "$")
            change(path, value, "source_alert_id", identity, "$")
            change(path, value, "source_event_ids",
                   [mapping[schema.canonical_source_event_id(x)] for x in before["source_event_ids"]], "$")
            value, canonical = source_wire(value, profile.tenant_id)
            entry = {"kind": "alert", "source_id": before["id"], "source_alert_id": identity,
                     "predicted_canonical_alert_id": canonical,
                     "correlation_key": raw_alert_model().model_validate(value).correlation_key()}
        for ocsf, position in _ocsf_objects(value, role):
            remap_ocsf(path, ocsf, position)
        identities[path] = entry
        wires[path] = value
    # In-memory validation before creating execution files.
    from acceptance_contract import Scenario
    from acceptance_materials import make_plan
    make_plan(control(Scenario, plan["scenario"], "scenario"), profile, wires)
    if any(sha256(_safe_file(materials, p).read_bytes()) != h for p, h in plan["material_sha256"].items()):
        raise MaterialError("material changed during preparation")
    output.mkdir(parents=True, exist_ok=False)
    for path, value in {"scenario.json": plan["scenario"], **wires}.items():
        target = output / "wire" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(json_bytes(value))
    prepared_plan = inspect_package(output / "wire", profile)
    session = {"schema_version": "socai2.acceptance-prepared.v1", "execution": execution.model_dump(),
               "profile": profile.model_dump(), "namespace": str(namespace), "source_directory": str(materials.resolve()),
               "source_material_sha256": plan["material_sha256"], "source_scenario_sha256": plan["scenario_sha256"],
               "wire_sha256": prepared_plan["material_sha256"], "scenario_sha256": prepared_plan["scenario_sha256"],
               "identities": identities, "event_identity_map": mapping, "changes": changes,
               "plan": prepared_plan, "execution_status": "prepared_not_executed", "time_policy": "preserved"}
    save_report(output / "session.json", session)
    load_execution(output)
    return session


def load_execution(directory: Path):
    session = read_json(directory / "session.json")
    if session.get("schema_version") != "socai2.acceptance-prepared.v1":
        raise MaterialError("unsupported prepared execution")
    profile = control(Profile, session["profile"], "prepared profile")
    control(Execution, session["execution"], "execution")
    plan = inspect_package(directory / "wire", profile)
    if plan != session["plan"] or plan["material_sha256"] != session["wire_sha256"] or plan["scenario_sha256"] != session["scenario_sha256"]:
        raise MaterialError("prepared material or plan changed")
    namespace = uuid5(NAMESPACE_URL, f"socai2.acceptance:{profile.tenant_id}:{session['execution']['execution_id']}")
    if str(namespace) != session["namespace"] or set(session["identities"]) != set(plan["material_sha256"]):
        raise MaterialError("prepared identity binding changed")
    for path, entry in session["identities"].items():
        wire = read_json(directory / "wire" / path)
        if entry["kind"] == "alert":
            parsed = raw_alert_model().model_validate(wire)
            if (wire["id"] != str(uuid5(namespace, "alert:" + entry["source_id"]))
                    or entry["source_alert_id"] != wire["id"]
                    or str(parsed.deterministic_id()) != entry["predicted_canonical_alert_id"]
                    or parsed.correlation_key() != entry["correlation_key"]):
                raise MaterialError("prepared alert identity changed")
        elif entry["kind"] != "context" or wire["event_id"] != entry["event_id"] or wire["event_id"] != str(uuid5(namespace, "event:" + entry["source_id"])):
            raise MaterialError("prepared context identity changed")
    return profile, session

