"""Offline material conversion and planning. No connections or execution here."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from acceptance_contract import Profile, Recipe, Scenario
from alert_kafka import ROOT, source_wire
from alert_scenarios import _without_answers, json_bytes, sha256
from pydantic import ValidationError


class MaterialError(ValueError):
    """A file/field error that does not disclose the rejected business value."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MaterialError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(_value):
    raise MaterialError("non-finite JSON number")


def parse_json(data: bytes, label: str) -> dict:
    try:
        value = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_nonfinite)
    except (ValueError, UnicodeError) as exc:
        raise MaterialError(f"{label}: invalid JSON object") from exc
    if not isinstance(value, dict):
        raise MaterialError(f"{label}: expected a JSON object")
    return value


def read_json(path: Path) -> dict:
    return parse_json(path.read_bytes(), str(path))


def control(model, value: dict, label: str):
    try:
        return model.model_validate(value)
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, e["loc"])) for e in exc.errors())
        raise MaterialError(f"{label}: invalid control fields ({fields})") from exc


def _safe_file(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if (not relative or parts.is_absolute() or ".." in parts.parts or "\\" in relative
            or str(parts) != relative):
        raise MaterialError("material file must use a normalized relative path")
    path = root
    for part in parts.parts:
        path = path / part
        if path.is_symlink():
            raise MaterialError(f"{relative}: material symlinks are not supported")
    if not path.is_file():
        raise MaterialError(f"{relative}: file is missing")
    return path


def _event_schema():
    name = "socai2_acceptance_event_schema"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "services/fusion/app/services/event_schema.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def _time(value: Any, label: str, *, numeric=False):
    if numeric and type(value) in (int, float):
        return
    if isinstance(value, str):
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is not None and stamp.utcoffset() is not None:
                return
        except ValueError:
            pass
    raise MaterialError(f"{label}: an explicit timezone is required")


def _business(payload: dict, role: str, tenant: str, label: str) -> tuple[dict, str]:
    if payload.get("schema_version") != "v1" or payload.get("tenant_id") != tenant:
        raise MaterialError(f"{label}: schema_version or tenant_id differs from the explicit profile")
    try:
        _without_answers(payload)
    except ValueError as exc:
        raise MaterialError(f"{label}: answer/test management fields belong in control sidecars") from exc
    if role == "alerts":
        required = {"id", "source", "title", "severity", "event_time", "created_at", "source_event_ids", "raw_event"}
        if required - payload.keys():
            raise MaterialError(f"{label}: missing alert fields: {', '.join(sorted(required - payload.keys()))}")
        for key in ("event_time", "created_at"):
            _time(payload[key], f"{label}.{key}")
        refs = payload["source_event_ids"]
        if not isinstance(refs, list) or any(not isinstance(x, str) or not x for x in refs):
            raise MaterialError(f"{label}: source_event_ids must be a list of nonempty strings")
        try:
            return source_wire(payload, tenant)
        except (ValueError, KeyError, TypeError) as exc:
            raise MaterialError(f"{label}: current RawAlert/source-v1 contract rejected the record") from exc
    schema = _event_schema()
    result = schema.validate_raw_event(payload)
    if not result.ok or not result.source_event_id:
        raise MaterialError(f"{label}: current context contract requires a valid source identity")
    ocsf = payload["ocsf_event"]
    _time(ocsf.get("time"), f"{label}.ocsf_event.time", numeric=True)
    if type(ocsf.get("class_uid")) is not int or ocsf["class_uid"] <= 0:
        raise MaterialError(f"{label}: ocsf_event.class_uid must be a positive integer")
    metadata = ocsf.get("metadata", {})
    ids = [payload.get("event_id"), payload.get("id"), ocsf.get("uid")]
    if isinstance(metadata, dict):
        ids.append(metadata.get("uid"))
    if any(value is not None and (not isinstance(value, str)
           or schema.canonical_source_event_id(value) != result.source_event_id) for value in ids):
        raise MaterialError(f"{label}: conflicting context source identities")
    if "tenant_uid" in ocsf and ocsf["tenant_uid"] != tenant:
        raise MaterialError(f"{label}: conflicting nested tenant_uid")
    return payload, result.source_event_id


def _numbered(root: Path, part: str, role: str) -> list[str]:
    directory = root / part / role
    if directory.is_symlink() or (root / part).is_symlink():
        raise MaterialError(f"{part}/{role}: material symlinks are not supported")
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise MaterialError(f"{part}/{role}: expected directory")
    found = {}
    for path in directory.iterdir():
        if not re.fullmatch(r"[0-9]+\.json", path.name) or int(path.stem) < 1:
            raise MaterialError(f"{part}/{role}: use positive numeric JSON filenames")
        number = int(path.stem)
        if number in found:
            raise MaterialError(f"{part}/{role}: duplicate numeric filename")
        relative = f"{part}/{role}/{path.name}"
        _safe_file(root, relative)
        found[number] = relative
    return [found[key] for key in sorted(found)]


def make_plan(scenario: Scenario, profile: Profile, records: dict[str, dict], *, selected_part=None) -> dict:
    order = [p.id for p in scenario.parts]
    if len(set(order)) != len(order):
        raise MaterialError("scenario.parts: duplicate part ID")
    if selected_part is not None and selected_part not in order:
        raise MaterialError("selected part is not declared in scenario.parts")
    selected_part = selected_part or ("part1" if "part1" in order else None)
    schema = _event_schema()
    contexts, alert_ids, alert_canonicals, alerts = {}, set(), set(), {}
    for path, payload in records.items():
        part, role, _ = path.split("/")
        wire, identity = _business(payload, role, profile.tenant_id, path)
        if part not in order:
            raise MaterialError(f"{path}: undeclared part")
        if role == "context":
            if identity in contexts:
                raise MaterialError(f"{path}: duplicate context identity")
            contexts[identity] = {"path": path, "part_index": order.index(part)}
        else:
            if wire["id"] in alert_ids or identity in alert_canonicals:
                raise MaterialError(f"{path}: duplicate alert identity")
            alert_ids.add(wire["id"])
            alert_canonicals.add(identity)
            alerts[path] = wire
    parts = []
    for index, part in enumerate(scenario.parts):
        paths = {role: [p for p in records if p.startswith(f"{part.id}/{role}/")]
                 for role in ("alerts", "context")}
        if not paths["alerts"]:
            raise MaterialError(f"{part.id}: at least one alert is required")
        for role, maximum in (("alerts", profile.limits.max_alerts_per_part),
                              ("context", profile.limits.max_context_events_per_part)):
            if len(paths[role]) > maximum:
                raise MaterialError(f"{part.id}/{role}: exceeds explicit profile limit")
        if part.context_required and not any(c["part_index"] <= index for c in contexts.values()):
            raise MaterialError(f"{part.id}: independent context is required")
        links = []
        for path in paths["alerts"]:
            for source in alerts[path]["source_event_ids"]:
                target = contexts.get(schema.canonical_source_event_id(source))
                if target and target["part_index"] > index:
                    raise MaterialError(f"{path}: source_event_ids refers to a future part")
                if not target and part.context_required:
                    raise MaterialError(f"{path}: required independent context source is not provided")
                links.append({"alert": path, "source_event_id": source,
                              "context": target["path"] if target else None,
                              "material_status": "provided_not_ingested" if target else "not_provided"})
        parts.append({**part.model_dump(), "counts": {k: len(v) for k, v in paths.items()},
                      "files": paths, "source_links": links, "execution_status": "not_executed",
                      "context_query_verification": "planned" if part.context_required else "not_covered",
                      "case_actions": [], "selected": part.id == selected_part})
    case_keys = set()
    for case in scenario.cases:
        if case.key in case_keys or case.create_after_part not in order:
            raise MaterialError("scenario.cases: duplicate key or unknown creation part")
        case_keys.add(case.key)
        index = order.index(case.create_after_part)
        if len(set(case.alert_refs)) != len(case.alert_refs) or (case.scope == "incident" and len(case.alert_refs) != 1):
            raise MaterialError(f"case {case.key}: invalid alert selector")
        if any(ref not in alerts or order.index(ref.split('/')[0]) > index for ref in case.alert_refs):
            raise MaterialError(f"case {case.key}: alert reference is missing or in a future part")
        if len(set(case.check_after_parts)) != len(case.check_after_parts):
            raise MaterialError(f"case {case.key}: duplicate check part")
        actions = [(case.create_after_part, "create")]
        for part_id in case.check_after_parts:
            if part_id not in order or order.index(part_id) <= index:
                raise MaterialError(f"case {case.key}: check must follow creation")
            actions.append((part_id, "check"))
        for part_id, action in actions:
            target = parts[order.index(part_id)]
            if target["check_level"] != "case":
                raise MaterialError(f"{part_id}: case action requires check_level=case")
            target["case_actions"].append({"key": case.key, "action": action})
    if any(p["check_level"] == "case" and not p["case_actions"] for p in parts):
        raise MaterialError("case-level part requires a case create/check plan")
    for part in parts:
        steps = []
        if part["counts"]["context"]:
            steps.append("context_publish_ack")
        if part["counts"]["context"] or part["context_required"]:
            steps.append("context_lake_readback")
        steps.extend(["alerts_publish_ack", "alert_triage_wait", "alert_saved_readback"])
        if part["check_level"] in {"incident", "case"}:
            steps.extend(["incident_diagnosis_wait", "incident_saved_readback"])
        if part["case_actions"]:
            steps.extend(["case_create_or_check", "case_task_wait", "case_saved_readback"])
        part["planned_steps"] = steps
    return {"schema_version": "socai2.acceptance-plan.v1", "scenario": scenario.model_dump(),
            "profile": profile.model_dump(), "validation_status": "passed", "execution_status": "not_executed",
            "connection_status": "not_checked", "execution_identity": "requires_new_execution_identity",
            "time_policy": "preserved", "selected_part": selected_part,
            "selection_required": selected_part is None, "parts": parts,
            "business_connections": 0, "kafka_sends": 0, "model_calls": 0}


def inspect_package(root: Path, profile: Profile, *, selected_part=None) -> dict:
    scenario = control(Scenario, read_json(_safe_file(root, "scenario.json")), "scenario.json")
    declared = {part.id for part in scenario.parts}
    if any(p.name.startswith("part") and p.is_dir() and p.name not in declared for p in root.iterdir()):
        raise MaterialError("package contains an undeclared part directory")
    records = {}
    for part in scenario.parts:
        for role in ("alerts", "context"):
            for relative in _numbered(root, part.id, role):
                records[relative] = read_json(_safe_file(root, relative))
    plan = make_plan(scenario, profile, records, selected_part=selected_part)
    plan["material_sha256"] = {path: sha256(_safe_file(root, path).read_bytes()) for path in records}
    plan["scenario_sha256"] = sha256(_safe_file(root, "scenario.json").read_bytes())
    plan["sidecars_not_executed"] = sorted(p.name for p in root.iterdir()
                                         if p.name not in {"scenario.json", "plan.json"} and p.name not in declared)
    return plan


def convert_package(source: Path, recipe: Recipe, profile: Profile, output: Path) -> dict:
    if output.exists():
        raise MaterialError("output directory already exists; choose a new directory")
    if output.resolve().is_relative_to(source.resolve()):
        raise MaterialError("conversion output must be outside the source directory")
    manifest_path = _safe_file(source, "manifest.json")
    manifest_data = manifest_path.read_bytes()
    manifest = parse_json(manifest_data, "manifest.json")
    streaming = recipe.source_format == "streaming-v2"
    expected_version = "socai2-streaming-s01-s04/v2" if streaming else "socai2-existing-alert-fixtures/v2"
    if manifest.get("dataset_version" if streaming else "schema_version") != expected_version:
        raise MaterialError("source manifest: unsupported version")
    if manifest.get("tenant_id") != profile.tenant_id:
        raise MaterialError("source manifest: tenant differs from explicit profile")
    if [p.id for p in recipe.parts] != [p.id for p in recipe.scenario.parts]:
        raise MaterialError("recipe part mapping must match scenario order exactly")
    entries = manifest.get("records", [])
    if not streaming and (not isinstance(entries, list) or any(not isinstance(e, dict)
                          or not isinstance(e.get("payload"), str) for e in entries)
                          or len({e.get("payload") for e in entries}) != len(entries)
                          or manifest.get("count") != len(entries)):
        raise MaterialError("source manifest: inconsistent payload records")
    payload_entries = {e["payload"]: e for e in entries} if not streaming else {}
    hashes = manifest.get("inputs", {}) if streaming else {p: e.get("payload_sha256") for p, e in payload_entries.items()}
    if not isinstance(hashes, dict):
        raise MaterialError("source manifest: missing input hashes")
    records, origins, consumed, used = {}, [], {}, set()
    for part in recipe.parts:
        for role in ("alerts", "context"):
            number = 0
            for relative in getattr(part, role):
                if relative in used:
                    raise MaterialError("recipe: a source file is selected more than once")
                used.add(relative)
                allowed = (relative.endswith("/alerts.jsonl") if role == "alerts" else relative.endswith("/context-events.jsonl"))
                if not streaming:
                    allowed = role == "alerts" and relative in payload_entries
                if relative not in hashes or not allowed:
                    raise MaterialError("recipe: selected file is not a supported business input")
                data = _safe_file(source, relative).read_bytes()
                if sha256(data) != hashes[relative]:
                    raise MaterialError(f"{relative}: source hash differs from manifest")
                consumed[relative] = sha256(data)
                values = data.splitlines() if streaming else [data]
                if not values:
                    raise MaterialError(f"{relative}: selected input is empty")
                if streaming:
                    counts = manifest.get("counts", {})
                    source_part = counts.get(str(PurePosixPath(relative).parent), {}) if isinstance(counts, dict) else {}
                    expected_count = source_part.get("alerts" if role == "alerts" else "context_events") if isinstance(source_part, dict) else None
                    if type(expected_count) is not int or expected_count != len(values):
                        raise MaterialError(f"{relative}: record count differs from source manifest")
                for line, raw in enumerate(values, 1):
                    payload = parse_json(raw, f"{relative}:{line}")
                    if not streaming and (payload.get("id") != payload_entries[relative].get("alert_id")
                                          or payload.get("source") != manifest.get("source_namespace")):
                        raise MaterialError(f"{relative}: payload identity differs from manifest")
                    wire, _ = _business(payload, role, profile.tenant_id, f"{relative}:{line}")
                    number += 1
                    target = f"{part.id}/{role}/{number:03d}.json"
                    records[target] = wire
                    origins.append({"source": relative, "source_sha256": sha256(data),
                                    "source_line": line if streaming else None,
                                    "target": target, "target_sha256": sha256(json_bytes(wire)),
                                    "added_identity_fields": sorted(wire.keys() - payload.keys())})
    make_plan(recipe.scenario, profile, records)  # Validate every relation before writing anything.
    output.mkdir(parents=True, exist_ok=False)
    for relative, value in {"scenario.json": recipe.scenario.model_dump(), **records}.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(json_bytes(value))
    receipt = {"schema_version": "socai2.acceptance-conversion-receipt.v1",
               "source_format": recipe.source_format, "source_directory": str(source.resolve()),
               "source_manifest_sha256": sha256(manifest_data),
               "recipe_sha256": sha256(json_bytes(recipe.model_dump())),
               "source_files": consumed, "records": origins, "business_values_preserved": True,
               "execution_status": "not_executed", "execution_identity": "requires_new_execution_identity",
               "time_policy": "preserved", "omitted_sidecars": sorted(set(hashes) - used),
               "historical_controls": "not_loaded_or_imported", "optional_sources": "not_imported",
               "business_connections": 0, "kafka_sends": 0, "model_calls": 0}
    for origin in origins:
        if sha256(_safe_file(output, origin["target"]).read_bytes()) != origin["target_sha256"]:
            raise MaterialError("converted file failed readback")
    if manifest_path.read_bytes() != manifest_data or any(
            sha256(_safe_file(source, p).read_bytes()) != digest for p, digest in consumed.items()):
        raise MaterialError("source changed during conversion")
    (output / "conversion.json").write_bytes(json_bytes(receipt))
    plan = inspect_package(output, profile)
    save_report(output / "plan.json", plan)
    return plan


def save_report(path: Path, value: dict):
    with path.open("xb") as stream:
        stream.write(json_bytes(value))
    if read_json(path) != value:
        raise MaterialError("report failed readback")
