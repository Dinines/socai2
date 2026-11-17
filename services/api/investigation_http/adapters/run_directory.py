"""External URL adaptation for the unified saved-Run directory."""
from app.socai2.run_directory import RunDirectoryService


def run_url(kind, identity, run_id):
    base = f"/api/v1/socai2/{kind}s/{identity}"
    return base + ("/runs/" if kind == "case" else "/analysis/runs/") + str(run_id)


def directory_view(page):
    items = []
    for row in page["items"]:
        detail = run_url(row["subject_type"], row["subject_id"], row["run_id"])
        results = [{**result, "url": (
            f"/api/v1/socai2/cases/{row['subject_id']}/results/{result['id']}"
            if result["result_type"] == "case_result" else detail)} for result in row["results"]]
        items.append({**row, "detail_url": detail, "results": results})
    return {**page, "items": items}


class RunDirectoryBackend:
    def __init__(self, sessions, *, limits=None):
        self.reader = RunDirectoryService(sessions, limits=limits)

    async def read(self, tenant, query):
        return directory_view(await self.reader.read(tenant, query))
