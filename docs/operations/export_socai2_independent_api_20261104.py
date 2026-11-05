"""Export the independent app's current API contract without starting lifespan."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))


def main():
    from app.socai2_main import app

    document = app.openapi()
    paths = document["paths"]
    for required in (
        "/api/v1/socai2/alerts/{alert_id}/analyze",
        "/api/v1/socai2/incidents/{incident_id}/diagnose",
        "/api/v1/socai2/cases/{case_id}/tasks",
        "/api/v1/socai2/cases/{case_id}/baseline/prepare",
    ):
        assert required in paths, required
    for legacy in ("/api/v1/alerts", "/api/v1/cases", "/api/v1/lake/sql"):
        assert legacy not in paths, legacy
    target = ROOT / "docs/design/socai2-independent-api-v2.openapi.json"
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2)+"\n", "utf-8")
    print(json.dumps({"artifact": target.relative_to(ROOT).as_posix(), "templates": len(paths),
        "methods": sum(method in {"get", "post", "put", "patch", "delete", "head", "options"}
            for path in paths.values() for method in path), "lifespan_started": False}))


if __name__ == "__main__":
    main()
