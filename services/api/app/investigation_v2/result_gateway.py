"""One authenticated internal GET and version/identity checks; no fallback."""
from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from fastapi import HTTPException

URL_ENV = "AISOC_INVESTIGATION_V2_READ_URL"
TOKEN_ENV = "AISOC_INVESTIGATION_V2_READ_TOKEN"
MAX_BYTES = 1024 * 1024


def _canonical(value) -> bytes:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(body) > MAX_BYTES:
        raise ValueError("bounded result reference required")
    return body


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require(condition: bool) -> None:
    if not condition:
        raise ValueError("invalid versioned backend result")


def _uuid(value) -> UUID:
    identity = UUID(str(value))
    _require(identity.int != 0)
    return identity


def _reference(reference: dict, expected: str) -> None:
    _require(isinstance(reference, dict) and isinstance(reference["sha256"], str)
             and re.fullmatch(r"[0-9a-f]{64}", reference["sha256"]) is not None)
    _uuid(reference["artifact_id"])
    _require(reference["sha256"] == expected)


def checked_result(payload, *, tenant_id: UUID, run_id: UUID) -> dict:
    _require(isinstance(payload, dict))
    _require((payload.get("schema"), payload.get("tenant_id"), payload.get("run_id"), payload.get("profile"), payload.get("objective"))
             == ("owned_fixed_recon_result.v1", str(tenant_id), str(run_id), "alert_recon", "verify_source_network_observation"))
    target = payload["target"]
    _require(target["type"] == "alert")
    _uuid(target["id"])
    _require(payload["notification"] is None and isinstance(payload["legacy_run_status"], str))
    publication = payload["publication_state"]
    common = {"publication_state", "manifest_artifact", "manifest", "markdown", "retention", "notification",
              "schema", "tenant_id", "run_id", "profile", "target", "objective", "legacy_run_status"}
    if publication == "not_published":
        _require(set(payload) == common | {"candidate", "progress", "delivery_gap"})
        _require(payload["manifest"] is None and payload["manifest_artifact"] is None and payload["markdown"] is None)
        return payload
    _require(publication == "published")
    _require(set(payload) == common | {"execution_snapshot"})
    manifest = payload["manifest"]
    _require((manifest["schema"], manifest["publication_state"], manifest["tenant_id"], manifest["run_id"], manifest["profile"], manifest["objective"])
             == ("fixed_recon_result_manifest.v1", "published", str(tenant_id), str(run_id), "alert_recon", payload["objective"]))
    _require((manifest["target"]["type"], manifest["target"]["id"]) == (target["type"], target["id"]))
    _require(type(manifest["version"]) is int and manifest["version"] == 1 and manifest["investigation_id"] == str(run_id)
             and manifest["previous_manifest_ref"] is None and manifest["retention"]["publication_artifacts"] == "committed")
    _require((manifest["renderer_version"], manifest["mapping_version"], manifest["sections_version"], manifest["runtime_version"], manifest["completion_policy_ref"])
             == ("fixed_recon_markdown.v1", "fixed_recon_publication_state.v1", "fixed_recon_handoff_sections.v1", "fixed_alert_recon_runtime.v1", "bounded_full_window_source_check.v1"))
    _require(manifest["manifest_ref"] == "recon-manifest:" + _sha(_canonical({k: v for k, v in manifest.items() if k != "manifest_ref"})))
    _reference(payload["manifest_artifact"], _sha(_canonical(manifest)))
    execution = payload["execution_snapshot"]
    _require((execution["schema"], execution["tenant_id"], execution["run_id"]) == ("fixed_recon_publication_execution.v1", str(tenant_id), str(run_id)))
    _require((execution["mapping_version"], execution["runtime_version"], execution["runtime_plan_ref"], execution["scope_hash"])
             == (manifest["mapping_version"], manifest["runtime_version"], manifest["runtime_plan_ref"], manifest["scope_hash"]))
    _require(manifest["snapshots"]["execution"]["artifact_schema"] == execution["schema"])
    _reference(manifest["snapshots"]["execution"], _sha(_canonical(execution)))
    markdown = payload["markdown"]
    _require(isinstance(markdown, str) and len(markdown.encode("utf-8")) <= MAX_BYTES)
    _require(manifest["report"]["renderer_version"] == manifest["renderer_version"] and manifest["report"]["media_type"] == "text/markdown")
    _reference(manifest["report"], _sha(markdown.encode("utf-8")))
    return payload


class ResultReadGateway:
    def __init__(self, *, backend_url: str, read_token: str, transport=None):
        parsed = urlsplit(backend_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("explicit investigation v2 read backend required")
        parsed.port  # Reject invalid port syntax at configuration time.
        try:
            valid = isinstance(read_token, str) and 32 <= len(read_token.encode("ascii")) <= 256 and read_token == read_token.strip() and not any(c.isspace() for c in read_token)
        except UnicodeEncodeError:
            valid = False
        if not valid:
            raise ValueError("explicit investigation v2 read token required")
        self._url, self._token, self._transport = backend_url.rstrip("/"), read_token, transport

    @classmethod
    def from_environment(cls):
        return cls(backend_url=os.getenv(URL_ENV) or "", read_token=os.getenv(TOKEN_ENV) or "")

    async def read(self, *, tenant_id: UUID, actor_id: UUID, run_id: UUID) -> dict:
        try:
            tenant, actor, run = _uuid(tenant_id), _uuid(actor_id), _uuid(run_id)
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(502, "investigation_v2_current_identity_invalid") from None
        headers = {"Authorization": "Bearer " + self._token, "X-AiSOC-Tenant-ID": str(tenant), "X-AiSOC-Actor-ID": str(actor)}
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=False, transport=self._transport) as client:
                response = await client.get(self._url + "/internal/investigation-v2/runs/" + str(run), headers=headers)
        except httpx.HTTPError:
            raise HTTPException(503, "investigation_v2_result_backend_unavailable") from None
        if response.status_code == 404:
            raise HTTPException(404, "investigation_v2_result_not_found")
        if response.status_code == 409:
            raise HTTPException(409, "investigation_v2_result_integrity_or_version_unavailable")
        if response.status_code in {500, 502, 503, 504}:
            raise HTTPException(503, "investigation_v2_result_backend_unavailable")
        if response.status_code != 200:
            raise HTTPException(502, "investigation_v2_result_backend_response_invalid")
        try:
            return checked_result(response.json(), tenant_id=tenant, run_id=run)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise HTTPException(502, "investigation_v2_result_backend_response_invalid") from None
