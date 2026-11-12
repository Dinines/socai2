"""Extract exact stored requests from the committed substitute-flow snapshot."""
import hashlib
import json
from collections import Counter
from pathlib import Path

FOLDER = Path(__file__).parent / "pg-03"
snapshot = json.loads((FOLDER / "database.json").read_text())
summary, counts = [], Counter()
for artifact in sorted(snapshot["artifacts"], key=lambda row: row["captured_at"]):
    payload = (artifact.get("content_json") or {}).get("payload", {})
    stage = payload.get("case_boundary", {}).get("stage")
    if artifact["kind"] != "model_request" or stage not in {"Deep", "C6"}:
        continue
    counts[stage] += 1
    name = f"{stage}-{counts[stage]:02d}"
    body = payload["body"]
    text = body["messages"][1]["content"]
    for filename, value in {name + "-model-input.txt": text, name + "-request.json":
            json.dumps(body, ensure_ascii=False, indent=2) + "\n"}.items():
        path = FOLDER / filename
        assert not path.exists()
        path.write_text(value)
    summary.append({"stage": stage, "file_prefix": name, "artifact_id": artifact["id"],
        "run_id": artifact["run_id"], "characters": len(text), "input_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "query_records": len({(s["ref"]["id"], s["record_key"]) for s in payload["source_map"].values()
                              if s.get("record_key")}),
        "dependencies": len(payload["followup_boundary"]["dependencies"]),
        "all_dependencies_visible": all(d["visible_id"] for d in payload["followup_boundary"]["dependencies"])})
result = {"kind": "exact_stored_requests_models_and_tools_substituted", "real_model_calls": 0,
    "inputs": summary, "results": [{k: row[k] for k in ("id", "validation_state", "delivery_state", "conclusion")}
                                   for row in snapshot["results"]],
    "presentation_note": "Saved before removing the repeated per-field membership sentence; the original requests remain unchanged."}
path = FOLDER / "input-summary.json"
assert not path.exists()
path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(result, ensure_ascii=False, indent=2))
