"""Replay fixed r2 input projections offline; no network or database writes."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))
from app.socai2 import alert_basic_contract as alert
from app.socai2 import baseline_analysis as analysis
from app.socai2 import baseline_enrichment as enrichment
from app.socai2 import baseline_model_view as view
from app.socai2 import incident_diagnosis_contract as incident
from app.socai2.baseline_context import Context
from app.socai2.baseline_store import encoded

snapshot = ROOT / "docs/operations/evidence/socai2-next-acceptance-20261104/20261104T054920-r2-export/database-20261104T054924.json"
data = json.loads(snapshot.read_text("utf-8"))
reports = []
for run in data["runs"]:
    artifacts = [a for a in data["artifacts"] if a["run_id"] == run["id"]]
    old_request = next(a["content_json"] for a in artifacts if a["kind"] == "model_request")
    old_body = old_request.get("body") or old_request["payload"]["body"]
    original = json.loads(old_body["messages"][1]["content"])
    frozen = next(a for a in artifacts if a["kind"] == "input_snapshot")
    if run["kind"] == "baseline":
        c1 = next(a for a in artifacts if a["schema_version"] == "socai2.baseline-context.v1")
        context = Context.model_validate(c1["content_json"])
        materials = {aid: next(m for m in data["alert_materials"] if m["id"] == member.material["id"])
            for aid, member in context.alerts.items() if member.material}
        tools = [(a["id"], a["content_json"], enrichment.citation_roles(a["content_json"])) for a in artifacts
            if a["kind"] == "tool_response" and a["schema_version"] == enrichment.SCHEMA]
        prepared = view.build(context, c1["id"], tools, original["source_states"], materials)
        messages, mapping = analysis.messages(prepared, context, {k: v for k, v, _ in tools})
    elif run["kind"] == "alert_basic":
        queries = [(a["id"], a["content_json"]) for a in artifacts if a["kind"] == "tool_response"]
        messages, mapping, _ = alert.build(frozen["content_json"], frozen["id"], queries)
    else:
        messages, mapping, _ = incident.build(frozen["content_json"], frozen["id"])
    visible = json.loads(messages[1]["content"])
    assert len(encoded(visible)) <= 8192 and len(encoded(messages)) <= 12288
    fields = [{"members": mapping[item["id"]].get("alert_ids", [visible.get("alert_id")]),
        "path": mapping[item["id"]]["ref"]["source_path"], "role": item["role"], "value": item["value"]}
        for item in visible["items"]]
    reports.append({"run_id": run["id"], "kind": run["kind"], "old_input_bytes": len(encoded(original)),
        "new_input_bytes": len(encoded(visible)), "new_messages_bytes": len(encoded(messages)),
        "old_observations": sum(x["role"] == "observation" for x in original["items"]),
        "new_observations": sum(x["role"] == "observation" for x in visible["items"]), "visible_fields": fields})
output = ROOT / "docs/operations/evidence/socai2-next-service-20261104/n6-projection-offline"
output.mkdir(parents=True, exist_ok=True)
record = {"synthetic_only": True, "network_calls": 0, "model_calls": 0,
    "original_snapshot": str(snapshot.relative_to(ROOT)), "original_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
    "reports": reports}
(output / "receipt.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps([{k: v for k, v in item.items() if k != "visible_fields"} for item in reports], ensure_ascii=False))
