"""Offline representation experiment; no provider, database, or production edits."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = Path("E:/aisoc/.reference-audits/AiSOC/34ca18c57dd4175539e5c6dd3d04a72dc057306b")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def grouped(data):
    result = {k: copy.deepcopy(v) for k, v in data.items() if k != "items"}
    groups = {}
    for item in data["items"]:
        key = (tuple(item["alert_ids"]), item["role"])
        group = groups.setdefault(key, {"alert_ids": item["alert_ids"], "role": item["role"], "items": []})
        group["items"].append({k: v for k, v in item.items() if k not in {"alert_ids", "role"}})
    result["source_groups"] = list(groups.values())
    restored = [{**item, "alert_ids": group["alert_ids"], "role": group["role"]}
                for group in result["source_groups"] for item in group["items"]]
    assert sorted(restored, key=lambda x: x["id"]) == sorted(data["items"], key=lambda x: x["id"])
    return result


def main():
    report = {"scope": "offline_representation_experiment_not_dispatchable_contract",
        "model_calls": 0, "database_calls": 0, "business_code_changed": False,
        "measures": "UTF-8 bytes, not provider tokens", "inputs": [], "reference_files": []}
    manifest = json.loads((ROOT / "docs/handoff/1g-source-manifest.json").read_text("utf-8"))
    manifest_files = {f["source"]: f for f in manifest["files"]}
    for rel in ("services/agents/app/prompt_serialization.py", "services/agents/app/context/bundle.py",
                "services/agents/app/investigator/limits.py", "services/agents/app/investigator/forensic_agent.py",
                "services/agents/app/investigator/report_writer_agent.py", "services/agents/app/orchestrator/router.py",
                "services/agents/app/agents/identity_agent.py", "services/agents/app/orchestrator/report.py"):
        path = REFERENCE / rel
        if not path.exists():
            path = ROOT / rel
        raw = path.read_bytes()
        lf = raw.replace(b"\r\n", b"\n")
        blob = hashlib.sha1(b"blob " + str(len(lf)).encode() + b"\0" + lf).hexdigest()
        prior = manifest_files.get(rel)
        report["reference_files"].append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "lf_git_blob": blob, "matches_fixed_import_git_blob": bool(prior and blob == prior["git_blob"]),
            "fixed_import_manifest_entry_found": prior is not None})
    for batch, folder in (("r4", "20261104T074438-r4-export"), ("r5", "20261104T075920-r5-export")):
        path = max((ROOT / "docs/operations/evidence/socai2-next-acceptance-20261104" / folder).glob("database-*.json"))
        original = path.read_bytes()
        db = json.loads(original)
        artifacts = {a["id"]: a for a in db["artifacts"]}
        run = next(r for r in db["runs"] if r["kind"] == "incident_diagnosis")
        request = next(a["content_json"] for a in db["artifacts"]
                       if a["run_id"] == run["id"] and a["kind"] == "model_request")
        request = request.get("payload", request)
        body = request["body"]
        data = json.loads(body["input"][1]["content"])
        compact = grouped(data)
        with_triage = copy.deepcopy(data)
        source = artifacts[run["input_artifact_id"]]["content_json"]
        restored_ids = []
        for index, member in enumerate(source["members"]):
            field = f"$.members.{index}.triage"
            aid = member["alert"]["id"]
            paired = member["triage"]
            if not paired or any(item["field"] == field for item in data["items"]):
                continue
            validity = source["triage_validation"][aid]
            assert validity["usable"] and validity["triage_id"] == paired["id"]
            projected = {k: paired.get(k) for k in ("verdict", "rationale", "confidence", "score_state", "assessed_at")}
            sid = "S" + str(1 + max(int(i["id"][1:]) for i in with_triage["items"]))
            with_triage["items"].append({"id": sid, "alert_ids": [aid], "role": "prior_analysis",
                                        "field": field, "value": projected})
            coverage = next(m for m in with_triage["members"] if m["alert_id"] == aid)
            coverage["included"] += 1
            coverage["omitted"] -= 1
            with_triage["omissions"]["view_size"] -= 1
            restored_ids.append({"alert_id": aid, "triage_id": paired["id"], "projected_bytes": len(encoded(projected))})
        restored = grouped(with_triage)
        report["inputs"].append({"batch": batch, "run_id": run["id"],
            "snapshot_path": path.relative_to(ROOT).as_posix(), "snapshot_sha256": hashlib.sha256(original).hexdigest(),
            "actual_request_bytes": len(encoded(body)), "actual_schema_bytes": len(encoded(body["text"]["format"]["schema"])),
            "system_content_bytes": len(body["input"][0]["content"].encode()),
            "original_view_bytes": len(encoded(data)), "grouped_view_bytes": len(encoded(compact)),
            "byte_reduction_percent": round(100 * (1 - len(encoded(compact)) / len(encoded(data))), 2),
            "visible_items_before": len(data["items"]), "roundtrip_exact_items": True,
            "removed_fields": 0, "removed_detection_items": 0, "restored_triages": restored_ids,
            "grouped_with_triage_bytes": len(encoded(restored)), "fits_original_reserved_limit": len(encoded(restored)) <= 8192 - 256,
            "limitations": ["not_token_measurement", "not_provider_quality_test", "not_final_input_contract",
                "new_visibility_metadata_and_prompt_not_yet_fitted", "production_guard_not_run_on_proposed_representation"]})
        assert path.read_bytes() == original
    output = ROOT / "docs/operations/socai2-compact-input-measurement-20261104.json"
    assert not output.exists(), "Do not overwrite an earlier experiment"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
