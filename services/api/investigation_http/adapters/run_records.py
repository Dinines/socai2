"""Map core record identities to external URLs without changing stored ownership."""
from app.socai2.run_records import RunRecordService

from investigation_http.record_links import content_url


def step_view(row):
    return {**row, "artifact_refs": [{**ref, "content_url": content_url(
        ref["subject_type"], ref["subject_id"], ref["run_id"], ref["artifact_id"])}
        for ref in row["artifact_refs"]]}


class RunRecordBackend:
    def __init__(self, sessions, *, limits=None):
        self.reader = RunRecordService(sessions, limits=limits)

    async def step(self, tenant, run_id, step_id):
        return step_view(await self.reader.step(tenant, run_id, step_id))

    async def page(self, tenant, run_id, directory, **query):
        page = await self.reader.page(tenant, run_id, directory, **query)
        if directory == "steps":
            items = [step_view(row) for row in page["items"]]
        else:
            items = [{**row, "content_url": content_url(page["subject_type"], page["subject_id"],
                     row["run_id"], row["id"])} for row in page["items"]]
        return {**page, "items": items}
