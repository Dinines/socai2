"""Export one authorized Case using existing scoped queries and page projection."""

import argparse
import asyncio
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import httpx
from processing_workbench_source import detail_query
from production_case_probe import query, save

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "deploy/local-investigation"), str(ROOT / "services/api")]
from app.socai2.case_data import export_page_data
from remote_profile import load_profile


def export(config_path, profile_path):
    config = json.loads(config_path.read_text())
    root = config_path.parent
    created = json.loads((root / "case-create-receipt.json").read_text())["receipt"]
    case = str(UUID(created["case_id"]))
    tenant = str(UUID(config["target"]["tenant_id"]))
    sql = detail_query().replace("$3", "NULL").replace("$2", "'" + case + "'").replace("$1", "'" + tenant + "'")
    snapshot = query(config, sql + ";")
    data = snapshot["data"]
    assert [row["id"] for row in data["cases"]] == [case]
    assert all(row["tenant_id"] == tenant for rows in data.values() for row in rows)
    folder = root / "exports" / datetime.fromisoformat(snapshot["captured_at"]).strftime("%Y%m%dT%H%M%S%fZ")
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / "database.json", data)
    profile = load_profile(profile_path)
    api = profile.config["api"]
    assert api["tenant_id"] == tenant and api["port"] == config["transport"]["local_api_port"]
    paths = [f"/cases/{case}", f"/cases/{case}/page-data", f"/cases/{case}/history", f"/cases/{case}/tasks"]
    for subject in ("alerts", "incidents"):
        paths.extend(f"/{subject}/{row['id']}{suffix}" for row in data[subject] for suffix in ("", "/analysis"))
    paths.extend(f"/alerts/{row['alert_id']}/materials/{row['id']}" for row in data["alert_materials"])
    for row in data["runs"]:
        if row["case_id"] == case:
            paths.append(f"/cases/{case}/runs/{row['id']}")
        else:
            subject = "alerts" if row.get("alert_id") else "incidents"
            identity = row.get("alert_id") or row.get("incident_id")
            paths.append(f"/{subject}/{identity}/analysis/runs/{row['id']}/trace")
    paths.extend(f"/cases/{case}/results/{row['id']}" for row in data["results"])
    responses = []
    with httpx.Client(base_url=f"http://{api['host']}:{api['port']}", timeout=api["request_timeout_seconds"],
                      headers={"Authorization": "Bearer " + profile.secrets["access_token"]}, trust_env=False) as client:
        for path in paths:
            response = client.get("/api/v1/socai2" + path)
            try:
                body = response.json()
            except ValueError:
                body = {"unparsed_body": response.text}
            responses.append({"method": "GET", "path": "/api/v1/socai2" + path,
                              "status": response.status_code, "body": body})
    save(folder / "api-responses.json", responses)
    save(folder / "case-page-data.json", asyncio.run(export_page_data(data)))
    sources = [{"file": name, "role": role, "sha256": hashlib.sha256((folder / name).read_bytes()).hexdigest()}
               for name, role in (("database.json", "database"), ("api-responses.json", "api_responses"),
                                  ("case-page-data.json", "case_page_data"))]
    manifest = {"schema_version": "socai2.page-export.v1", "batch_id": config["batch_id"],
                "source_environment": config["execution_environment"], "input_kind": config["input_kind"],
                "exported_at": snapshot["captured_at"], "source_sha256": sources[0]["sha256"], "sources": sources,
                "database": config["target"]["database"], "tenant_id": tenant, "case_id": case,
                "table_counts": {table: len(rows) for table, rows in data.items()},
                "database_snapshot": "single_readonly_repeatable_read", "revision": snapshot["revision"],
                "api_observations": "separate_later_GETs"}
    save(folder / "manifest.json", manifest)
    return {"folder": str(folder), "case_id": case, "counts": manifest["table_counts"],
            "http": {"total": len(responses), "errors": [r["path"] for r in responses if r["status"] != 200]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.config, args.profile), ensure_ascii=False))
