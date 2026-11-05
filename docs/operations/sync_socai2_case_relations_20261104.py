"""Update current catalogue and API export; never regenerate migration 123."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))


def main():
    from app.api.v1.endpoints.socai2_cases import router
    from fastapi import FastAPI

    path = ROOT / "docs/design/socai2-data-contract-20261103.json"
    cat = json.loads(path.read_text("utf-8"))
    cases = next(t for t in cat["tables"] if t["name"] == "cases")
    field = {"name": "source_namespace", "type": "text", "nullable": True, "default": None,
        "meaning": "Case固定数据身份命名空间；首次范围绑定后不可改，旧范围不能确认时NULL；不等于原始来源环境",
        "introduced_in_migration": 124}
    if not any(c["name"] == "source_namespace" for c in cases["columns"]):
        cases["columns"].insert(0, field)
    cat["incremental_migrations"] = [{"number": 124, "path": "services/api/migrations/124_socai2_case_source_binding.sql",
        "tables": 29, "columns": 459, "baseline_123_unchanged": True}]
    cat["status"] = "current_contract_123_plus_124_verified_in_isolated_pg_only"
    path.write_text(json.dumps(cat, ensure_ascii=False, indent=2)+"\n", "utf-8")
    app = FastAPI(title="socai2 Case API", version="1.0.0")
    app.include_router(router, prefix="/api/v1")
    document = json.dumps(app.openapi(), ensure_ascii=False, indent=2)+"\n"
    for name in ["docs/design/socai2-case-api-v1.openapi.json", "docs/investigation/socai2-case-api-20261104.openapi.json"]:
        (ROOT/name).write_text(document, "utf-8")
    print(json.dumps({"case_columns": len(cases["columns"])+2, "api_paths": len(app.openapi()["paths"])}))


if __name__ == "__main__":
    main()
