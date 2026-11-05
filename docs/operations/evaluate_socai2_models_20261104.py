"""Frozen, no-business-write comparison. prepare/run/export/review are separate.

Twelve calls maximum, one attempt per cell, no retries. Credentials stay on 21.
The old A arm reuses actual r4 messages/schema, not a reconstruction of old code.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/operations/evidence/socai2-model-comparison-20261104/m1"
REMOTE = "/opt/sting-aisoc-socai2/evidence/next-model-comparison-20261104-m1"
RUNNER = ROOT / "deploy/aisoc21/model_comparison_remote.py"


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def snapshot(batch):
    summary = json.loads((ROOT / f"docs/operations/socai2-next-{batch}-validation-20261104.json").read_text("utf-8"))
    path = ROOT / summary["snapshot"]
    return json.loads(path.read_bytes()), {"path": summary["snapshot"], "sha256": sha(path.read_bytes())}


def build_packets():
    from app.services.llm_safety import LLMInputContract
    from app.socai2 import alert_basic_contract as alert
    from app.socai2 import (
        baseline_analysis,
        baseline_analysis_contract,
        baseline_enrichment,
        baseline_model_view,
    )
    from app.socai2 import incident_diagnosis_contract as incident
    from app.socai2.baseline_context import Context
    from app.socai2.baseline_store import encoded
    from app.socai2.model_input_view import items
    from app.socai2.model_protocol import prepare_request
    from app.socai2.structured_output import response_format

    r4, r4_info = snapshot("r4")
    r6, r6_info = snapshot("r6")
    packets = []
    for run in sorted((r for r in r4["runs"] if r["kind"] == "alert_basic"), key=lambda r: r["alert_id"]):
        arts = {a["id"]: a for a in r4["artifacts"]}
        selected = [a for a in arts.values() if a["run_id"] == run["id"]]
        source = arts[run["input_artifact_id"]]["content_json"]
        queries = [(a["id"], a["content_json"]) for a in selected if a["kind"] == "tool_response"]
        queries.sort(key=lambda pair: ("assets", "history", "threat_intel").index(pair[1]["tool_name"]))
        original = next(a["content_json"] for a in selected if a["kind"] == "model_request")
        old_body = original["body"]
        sample = "A0" if run["alert_id"].startswith("cfcd") else "A1"
        messages, refs, data = alert.build(source, run["input_artifact_id"], queries)
        for version in ("old", "current"):
            if version == "old":
                msg = old_body["input"]
                fmt = {"type": "json_schema", "json_schema": {k: v for k, v in old_body["text"]["format"].items() if k != "type"}}
                mapping, model_data = original["source_map"], json.loads(msg[1]["content"])
            else:
                msg, fmt, mapping, model_data = messages, response_format(alert.Answer, refs), refs, data
            packets.append({"id": sample + "-" + version, "stage": "A", "variant": version,
                "source_run_id": run["id"], "source_sha256": sha(encode(source)),
                "queries_sha256": sha(encode(queries)), "messages": msg, "response_format": fmt,
                "source_map": mapping, "data": model_data})
        old_items = items(packets[-2]["data"])
        new_items = items(packets[-1]["data"])
        new_values = {(i["field"], i["role"]): i["value"] for i in new_items}
        assert all(new_values[(i["field"], i["role"])] == i["value"] for i in old_items)

    arts = {a["id"]: a for a in r6["artifacts"]}
    run = next(r for r in r6["runs"] if r["kind"] == "incident_diagnosis")
    source = arts[run["input_artifact_id"]]["content_json"]
    messages, refs, data = incident.build(source, run["input_artifact_id"])
    packets.append({"id": "I-current", "stage": "I", "variant": "current", "source_run_id": run["id"],
        "source_sha256": sha(encode(source)), "messages": messages, "source_map": refs, "data": data,
        "response_format": response_format(incident.Answer, refs, members=[m["alert"]["id"] for m in source["members"]],
            member_sources=[sid for sid, ref in refs.items() if ref["alert_ids"]])})

    run = next(r for r in r6["runs"] if r["kind"] == "baseline")
    selected = [a for a in arts.values() if a["run_id"] == run["id"]]
    context_art = next(a for a in selected if a["schema_version"] == "socai2.baseline-context.v1")
    context = Context.model_validate(context_art["content_json"])
    tools = {a["id"]: a["content_json"] for a in selected if a["kind"] == "tool_response"}
    c2 = next(a["content_json"] for a in selected if a["kind"] == "source_snapshot" and a["schema_version"] == baseline_enrichment.SCHEMA)
    enrichment = [(s["artifact_id"], tools[s["artifact_id"]], baseline_enrichment.citation_roles(tools[s["artifact_id"]])) for s in c2["sources"]]
    states = [{k: s[k] for k in ("source", "outcome", "truncated", "reason", "limitations")} for s in c2["sources"]]
    materials = {m["alert_id"]: m for m in r6["alert_materials"] if m["alert_id"] in context.alerts}
    prepared = baseline_model_view.build(context, context_art["id"], enrichment, states, materials)
    assert prepared["ready"], prepared
    messages, refs = baseline_analysis.messages(prepared, context, tools)
    packets.append({"id": "C3-current", "stage": "C3", "variant": "current", "source_run_id": run["id"],
        "source_sha256": sha(encode(context_art["content_json"])), "messages": messages, "source_map": refs,
        "coverage": prepared["coverage"], "context": context.model_dump(mode="json"), "data": json.loads(messages[1]["content"]),
        "response_format": response_format(baseline_analysis_contract.Analysis, refs, members=context.alerts,
            questions=[q.id for q in context.questions], objects=context.scope.object_keys)})
    cells = []
    for packet in packets:
        assert LLMInputContract.validate(packet["messages"]) == packet["messages"]
        assert len(packet["messages"][1]["content"].encode()) <= 8192
        assert len(encoded(packet["messages"])) <= 12288
        packet["messages_sha256"] = sha(encode(packet["messages"]))
        packet["schema_sha256"] = sha(encode(packet["response_format"]))
        packet["user_bytes"] = len(packet["messages"][1]["content"].encode())
        for backend, model, protocol in (("small", "aisoc-investigation", "chat_completions"),
                                         ("deepseek", "deepseek-flash", "deepseek_responses")):
            body = prepare_request(SimpleNamespace(provider=protocol), {"model": model, "messages": packet["messages"],
                "response_format": packet["response_format"], "temperature": 0, "max_tokens": 3000})
            reservation = len(encoded(body)) + 3000 + 256
            assert reservation <= 24000, (packet["id"], backend, reservation)
            cells.append({"id": packet["id"] + "-" + backend, "packet_id": packet["id"], "backend": backend,
                "body": body, "body_sha256": sha(encode(body)), "reservation": reservation})
    return {"batch": "m1", "snapshots": [r4_info, r6_info], "packets": packets, "cells": cells,
        "plan": {"max_model_calls": 12, "attempts_per_cell": 1, "retries": 0, "timeout_seconds": 120,
            "max_output_tokens": 3000, "temperature": 0, "business_writes": False, "tools_executed": False,
            "current_C_is_initial_analysis_only": True, "old_and_current_A_all_original_visible_values_equal": True,
            "prior_I_and_C_judgments_frozen_not_replaced_by_this_evaluation": True,
            "expected": ["source_labels_do_not_establish_benign_or_authorization", "empty_lookup_is_not_counterevidence",
                "TCP_443_does_not_prove_HTTPS", "network_PID_and_user_unknown", "same_host_near_time_does_not_prove_causality",
                "stored_complete_not_full_material_review", "skipped_is_not_disconnected", "uncertainty_must_be_preserved"],
            "limits": ["one_attempt_per_cell_not_statistical_accuracy", "different_provider_protocol_and_reasoning_policy",
                "A_old_new_is_complete_input_contract_change_not_only_grouping", "no_Deep_C6_H_end_to_end_acceptance"]},
        "code_hashes": {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in (ROOT / "services/api/app/socai2").glob("*.py")}}


def ssh(args, body=None):
    from verify_socai2_store_20261103 import DEST, SSH
    result = subprocess.run([*SSH, DEST, *args], input=body, capture_output=True, timeout=1800, check=False)
    if result.returncode:
        raise RuntimeError(f"SSH command failed ({result.returncode}); remote may contain partial evidence; do not retry calls")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "upload", "preflight", "run", "export"))
    args = parser.parse_args()
    if args.phase == "prepare":
        OUT.mkdir(parents=True, exist_ok=True)
        bundle = build_packets()
        write(OUT / "plan-and-packets.json", bundle)
        write(OUT / "preparation.json", {"packet_sha256": sha((OUT / "plan-and-packets.json").read_bytes()),
            "runner_sha256": sha(RUNNER.read_bytes()), "cells": len(bundle["cells"]),
            "sizes": {p["id"]: p["user_bytes"] for p in bundle["packets"]}})
        print((OUT / "preparation.json").read_text("utf-8"))
    elif args.phase == "upload":
        preparation = json.loads((OUT / "preparation.json").read_text("utf-8"))
        assert sha(RUNNER.read_bytes()) == preparation["runner_sha256"]
        assert sha((OUT / "plan-and-packets.json").read_bytes()) == preparation["packet_sha256"]
        files = {"runner.py": RUNNER.read_text("utf-8"), "plan-and-packets.json": (OUT / "plan-and-packets.json").read_text("utf-8")}
        code = "import json,sys,pathlib,os; p=pathlib.Path('" + REMOTE + "'); p.mkdir(mode=0o700); d=json.load(sys.stdin); [(p/k).write_text(v,encoding='utf-8') for k,v in d.items()]; [os.chmod(p/k,0o600) for k in d]; print('uploaded frozen evaluation only')"
        import shlex
        print(ssh(["python3 -c " + shlex.quote(code)], encode(files)).decode())
    elif args.phase == "export":
        import shlex
        code = "import json,pathlib; p=pathlib.Path('" + REMOTE + "'); print(json.dumps({f.name:json.loads(f.read_text()) for f in p.glob('*.json') if f.name!='plan-and-packets.json'}))"
        result = json.loads(ssh(["python3 -c " + shlex.quote(code)]))
        directory = OUT / "remote"
        directory.mkdir(exist_ok=True)
        for name, data in result.items():
            assert Path(name).name == name
            path = directory / name
            if path.exists():
                assert json.loads(path.read_text("utf-8")) == data
            else:
                write(path, data)
        print(json.dumps({"exported_files": len(result), "directory": str(directory)}))
    elif args.phase == "run":
        from verify_socai2_store_20261103 import DEST, SSH
        with subprocess.Popen([*SSH, DEST, f"python3 {REMOTE}/runner.py run"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
            for line in process.stdout:
                print(line.decode().rstrip(), flush=True)
            if process.wait():
                raise RuntimeError("Remote evaluation stopped; export partial evidence; no retries")
    else:
        print(ssh([f"python3 {REMOTE}/runner.py {args.phase}"]).decode())


if __name__ == "__main__":
    main()
