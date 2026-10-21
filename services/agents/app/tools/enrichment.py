"""
Tool: IOC enrichment via the enrichment microservice.
"""

import os

import httpx
import structlog

logger = structlog.get_logger()

_ENRICHMENT_URL = os.getenv("ENRICHMENT_SERVICE_URL", "http://enrichment:8082").rstrip("/")


async def enrich_ioc(ioc_value: str, ioc_type: str) -> dict:
    """Call the enrichment service to get threat intel for an IOC."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{_ENRICHMENT_URL}/enrich",
                json={"value": ioc_value, "ioc_type": ioc_type},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("IOC enrichment failed", ioc=ioc_value, error=str(exc))
        return {"error": str(exc), "value": ioc_value, "ioc_type": ioc_type}


async def bulk_enrich_iocs(items: list[dict], *, raise_on_error: bool = False) -> list[dict]:
    """Bulk enrich up to 100 IOCs; bundle callers retain source failures."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_ENRICHMENT_URL}/enrich/bulk",
                json={"items": items},
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise ValueError("Invalid enrichment response")
            return data["results"]
    except Exception as exc:
        logger.warning("Bulk IOC enrichment failed", error=str(exc))
        if raise_on_error:
            raise
        return []
