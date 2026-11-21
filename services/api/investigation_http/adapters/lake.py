"""Translate core lake reads into public URL-bearing views."""
from urllib.parse import urlencode

from app.socai2.lake_queries import LakeQueries, active_profile


class LakeReadBackend:
    def __init__(self, service=None):
        self.service = service or LakeQueries(active_profile())

    async def search(self, tenant, query):
        result = (await self.service.search(tenant, query)).model_dump(mode="json")
        for item in result["items"]:
            ref = item["record_ref"]
            item["material_url"] = f"/api/v1/socai2/lake/events/{ref['event_id']}/material?" + urlencode(
                {name: value for name, value in ref.items() if name != "event_id"})
        return result

    async def material(self, tenant, ref):
        return await self.service.material(tenant, ref)
