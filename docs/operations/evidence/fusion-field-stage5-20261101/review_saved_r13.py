"""Read existing authorized r13 artifacts only; no new business/model calls."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = HERE.parent / "investigation-r13-20261101"
files = {}


def read(relative):
    path = SOURCE / relative
    raw = path.read_bytes()
    files[str(path.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw.decode("utf-8-sig"))


requests, results = [], []
for case in ("A", "B"):
    frozen = read(f"{case}/006-step-1.response.txt")["data"]
    alerts = {item["data"]["alert_id"]: item["data"] for item in frozen["evidence"] if item["kind"] == "alert"}
    for name in ("007-step-2.response.txt", "011-step-6.response.txt", "015-step-10.response.txt"):
        request = read(f"{case}/{name}")["data"]
        view = json.loads(request["messages"][1]["content"])
        fields = []
        for item in view["evidence"]:
            if item["kind"] != "alert":
                continue
            alert = item["data"]
            for field in ("description", "raw_event"):
                original = alerts[alert["alert_id"]]["source_material"][field]
                visible = alert["source_material"][field]
                fields.append({"alert_id": alert["alert_id"], "field": field,
                    "full_frozen_text_equal": original["text"] == visible["text"],
                    "original_bytes": original["original_bytes"],
                    "retained_bytes": original["retained_bytes"],
                    "model_retained_bytes": visible["model_retained_bytes"],
                    "snapshot_truncated": original["truncated"],
                    "model_truncated": visible.get("model_truncated", False),
                    "model_omission_reason": visible.get("model_omission_reason")})
        requests.append({"case": case, "file": name, "phase": request["phase"],
            "offered_tools": [t["function"]["name"] for t in request["tools"]],
            "alert_fields": [sorted(e["data"]) for e in view["evidence"] if e["kind"] == "alert"],
            "triage_fields": [sorted(e["data"]) for e in view["evidence"] if e["kind"] == "triage"],
            "source_comparisons": fields})
    for name in ("010-step-5.response.txt", "014-step-9.response.txt"):
        data = read(f"{case}/{name}")["data"]
        evidence, visible = data["evidence"], json.loads(data["model_message"])
        results.append({"case": case, "file": name, "tool": evidence["tool"],
            "saved_row_count": len(evidence["rows"]), "model_row_count": len(visible["rows"]),
            "saved_row_fields": [sorted(r) for r in evidence["rows"]],
            "model_row_fields": [sorted(r) for r in visible["rows"]],
            "query_status": visible["query_status"], "query_scope": evidence["query_scope"],
            "source_alignment": visible["source_alignment"],
            "reused": bool(evidence.get("reused_from")),
            "empty_result_boundary": visible.get("empty_result_boundary"),
            "model_omitted_fields": visible.get("model_omitted_fields")})

comparisons = [f for r in requests for f in r["source_comparisons"]]
summary = {"saved_request_count": len(requests), "saved_tool_result_count": len(results),
    "alert_source_field_exposures": len(comparisons),
    "all_short_source_texts_equal": all(f["full_frozen_text_equal"] for f in comparisons),
    "all_short_sources_untruncated": all(not f["snapshot_truncated"] and not f["model_truncated"] for f in comparisons),
    "tool_saved_rows": [r["saved_row_count"] for r in results],
    "tool_model_rows": [r["model_row_count"] for r in results],
    "historical_reuse_count": sum(r["reused"] for r in results),
    "new_runs": 0, "new_model_calls": 0, "new_lake_queries": 0}
(HERE / "saved-r13-review.json").write_text(json.dumps({
    "scope": "read-only review of existing r13 evidence, not a rerun or Fusion ingestion acceptance",
    "summary": summary, "requests": requests, "tool_results": results,
    "source_files": [{"path": p, "sha256": h} for p, h in sorted(files.items())],
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary))
