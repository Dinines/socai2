"""Attach native source URLs to the shared Case investigation projection."""
from app.socai2.case_investigations import CaseInvestigationService

from .case_story import investigation_urls


class CaseInvestigationBackend(CaseInvestigationService):
    async def read(self, tenant_id, case_id, *, limit, cursor):
        page = await super().read(tenant_id, case_id, limit=limit, cursor=cursor)
        return {**page, "items": [investigation_urls(item, case_id) for item in page["items"]]}

    async def lookup(self, tenant_id, case_id, run_id):
        result = await super().lookup(tenant_id, case_id, run_id)
        return {**result, "item": investigation_urls(result["item"], case_id)}
