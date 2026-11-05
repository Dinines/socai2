"""Export current task and prepare-baseline API contracts without business I/O."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api"))


def main():
    from app.api.v1.endpoints.socai2_cases import router as cases
    from app.api.v1.endpoints.socai2_tasks import router as tasks
    from fastapi import FastAPI

    for title, router, paths in [
        ("socai2 Human Tasks API", tasks, ["docs/design/socai2-human-tasks-v1.openapi.json"]),
        ("socai2 Case API", cases, ["docs/design/socai2-case-api-v1.openapi.json",
            "docs/investigation/socai2-case-api-20261104.openapi.json"]),
    ]:
        app = FastAPI(title=title, version="1.0.0")
        app.include_router(router, prefix="/api/v1")
        body = json.dumps(app.openapi(), ensure_ascii=False, indent=2)+"\n"
        for path in paths:
            (ROOT/path).write_text(body, "utf-8")
        print(json.dumps({"title": title, "templates": len(app.openapi()["paths"])}))


if __name__ == "__main__":
    main()
