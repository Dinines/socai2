"""New program atomic publication and one manifest-based read path.

No external dispatch or legacy Run/status writes. All returns claiming published
occur after commit confirmation; notification values are descriptors, not sends.
"""
from __future__ import annotations

import json
from uuid import UUID, uuid4
from datetime import datetime

from .execution_state import ExecutionRejected
from .execution_store import canonical_json, content_hash, _object
from .program_recon_publication import (prepare_program_recon_publication, MANIFEST_SCHEMA, EXECUTION_SCHEMA,
                                RENDERER_VERSION)
from .program_runtime_store import ProgramReconExecutionStore, HANDOFF_KIND, OBSERVATION_KIND, CONTROL_KINDS
from .program_runtime_state import _runtime_copy

PUBLICATION_EVENT = "unified_program_result_published"
MANIFEST_KIND = "program_result_manifest"
EXECUTION_KIND = "program_recon_published_execution"
REPORT_KIND = "program_recon_report_markdown"
POINTER_SCHEMA = "program_recon_publication_pointer.v1"


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ExecutionRejected(reason)


def _ref(artifact: dict) -> dict:
    return {"artifact_id": str(artifact["id"]), "sha256": artifact["sha256"]}


def _seal(package: dict, execution_ref: dict, report_ref: dict) -> dict:
    manifest = json.loads(canonical_json(package["manifest_basis"]))
    manifest["publication_state"] = "published"
    manifest["retention"]["publication_artifacts"] = "committed"
    manifest["snapshots"]["execution"] = execution_ref
    manifest["report"] = report_ref
    manifest["manifest_ref"] = "program-recon-manifest:" + content_hash(canonical_json(manifest))
    return manifest


def _without_write_metadata(state: dict) -> dict:
    return {key: value for key, value in state.items() if key not in {"persistence", "updated_at"}}


class ProgramReconPublicationStore(ProgramReconExecutionStore):
    event_kinds = (*ProgramReconExecutionStore.event_kinds, PUBLICATION_EVENT)

    async def _origin(self, conn, state):
        frozen = await super()._origin(conn, state)
        rows = await conn.fetch("SELECT id FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 "
            "AND kind=ANY($3::text[]) ORDER BY seq ASC LIMIT 2", self.run_id, self.tenant_id, [CONTROL_KINDS[0]])
        _require(len(rows) == 1, "unique owned program origin required")
        event = await self._event(conn, rows[0]["id"])
        payload = _object(event["payload"])
        snapshot = await self._read_artifact(conn, UUID(payload["state_artifact_id"]), event["id"])
        await self._check_event_bodies(conn, event, _object(snapshot["content"]))
        return frozen

    async def _load(self, conn):
        state = await super()._load(conn)
        checked, _ = _runtime_copy(state, datetime.fromisoformat(state["updated_at"]))
        _require(canonical_json(checked) == canonical_json(state), "stored program state usage differs from reconstructed state")
        return state

    async def _check_event_bodies(self, conn, event, state):
        _require(type(event["seq"]) is int and type(state["persistence"]["seq"]) is int
                 and event["seq"] >= 1 and state["persistence"]["seq"] >= 1,
                 "typed positive program event sequence required")
        if event["kind"] != PUBLICATION_EVENT:
            return await super()._check_event_bodies(conn, event, state)
        payload = _object(event["payload"])
        receipt = state["persistence"]
        _require(canonical_json(receipt) == canonical_json({k:v for k,v in payload.items() if k != "state_hash"})
                 and canonical_json([receipt["event_id"], receipt["seq"], receipt["tenant_id"], receipt["run_id"], receipt["stage_id"], receipt["attempt_id"]])
                 == canonical_json([str(event["id"]), event["seq"], str(self.tenant_id), str(self.run_id), state["stage_id"], None]),
                 "program publication event receipt mismatch")
        artifact = await self._read_artifact(conn, UUID(receipt["body_artifact_id"]), event["id"])
        _require(artifact["kind"] == MANIFEST_KIND and artifact["sha256"] == receipt["body_hash"]
                 and event["input_hash"] is None and event["output_hash"] is None,
                 "program publication event body pin mismatch")

    async def _publication_event(self, conn):
        rows = await conn.fetch("SELECT id,tenant_id,run_id,seq,agent,kind,payload,input_hash,output_hash "
            "FROM investigation_events WHERE run_id=$1 AND tenant_id=$2 AND kind=ANY($3::text[]) ORDER BY seq ASC LIMIT 2",
            self.run_id, self.tenant_id, [PUBLICATION_EVENT])
        _require(len(rows) <= 1, "unique program publication event required")
        if not rows:
            return None
        event = await self._event(conn, rows[0]["id"])
        payload = _object(event["payload"])
        _require(event["kind"] == PUBLICATION_EVENT and event["input_hash"] is None and event["output_hash"] is None,
                 "program publication event kind or hash mismatch")
        _require(type(event["seq"]) is int and type(payload["seq"]) is int
                 and canonical_json([payload["event_id"], payload["seq"], payload["tenant_id"], payload["run_id"]])
                 == canonical_json([str(event["id"]), event["seq"], str(self.tenant_id), str(self.run_id)]),
                 "typed owned publication event identity mismatch")
        return event

    async def _reference(self, conn, reference: dict, kind: str, event_id=None) -> dict:
        row = await self._read_artifact(conn, UUID(reference["artifact_id"]), event_id)
        _require(row["kind"] == kind and row["sha256"] == reference["sha256"], "published artifact reference mismatch")
        return row

    async def _required_materials(self, conn, handoff: dict, state: dict) -> None:
        candidate = handoff["candidate"]
        # Pin the original completion even when semantic adoption was refused.
        # Self-consistent artifact bytes alone do not prove the original event
        # association, kind or hash attested by the fixed M3 attempt.
        tool = await self._tool_artifact(conn, state)
        if tool is not None:
            _require("urn:uuid:" + str(tool["id"]) in candidate["retained_artifact_refs"],
                     "publication handoff is stale: original completion is not retained")
        for reference in candidate["retained_artifact_refs"]:
            _require(reference.startswith("urn:uuid:"), "owned retained artifact reference required")
            await self._read_artifact(conn, UUID(reference.removeprefix("urn:uuid:")))
        if candidate["preparation"] is not None:
            material = candidate["preparation"]["material"]
            _require(tool is not None and str(tool["id"]) == material["artifact_id"]
                     and tool["sha256"] == material["stored_sha256"] == material["sha256"]
                     and material["artifact_ref"] == "urn:uuid:" + str(tool["id"])
                     and (material["tenant_id"], material["source_run_id"]) == (str(self.tenant_id), str(self.run_id)),
                     "publication source material mismatch")
        reference = candidate["unconfirmed_observation_ref"]
        if reference is not None:
            row = await self._reference(conn, reference, OBSERVATION_KIND, handoff["artifact"]["event_id"])
            observation = _object(row["content"])
            _require(observation["attempt_id"] == state["recon"]["plan"]["attempt_id"]
                     and observation["provenance"] == "process_observation_not_original_completion"
                     and observation["tool_result_hash"] == content_hash(canonical_json(observation["tool_result"])),
                     "publication unconfirmed observation mismatch")

    async def _package(self, conn, request, state: dict, handoff: dict, stopped_reference: dict | None = None):
        await self._required_materials(conn, handoff, state)
        source_id = UUID(handoff["candidate"]["execution"]["source_state_artifact_ref"].removeprefix("urn:uuid:"))
        source = await self._read_artifact(conn, source_id)
        if stopped_reference is None:
            stopped = await self._read_artifact(conn, UUID(state["persistence"]["state_artifact_id"]))
        else:
            stopped = await self._reference(conn, stopped_reference, "unified_state_snapshot")
        return prepare_program_recon_publication(request, handoff_artifact=handoff["artifact"],
                                          source_state_artifact=source, current_state_artifact=stopped)

    async def _read_published(self, conn, request, state: dict, event) -> dict:
        pointer = state.get("publication")
        _require(isinstance(pointer, dict) and pointer.get("schema") == POINTER_SCHEMA,
                 "publication event exists but current pointer is missing")
        payload = _object(event["payload"])
        manifest_row = await self._reference(conn, pointer["manifest_artifact"], MANIFEST_KIND, event["id"])
        published_state_row = await self._read_artifact(conn, UUID(payload["state_artifact_id"]), event["id"])
        published_state = _object(published_state_row["content"])
        _require(payload["body_artifact_id"] == str(manifest_row["id"])
                 and payload["body_hash"] == manifest_row["sha256"]
                 and published_state_row["kind"] == "unified_state_snapshot"
                 and payload["state_hash"] == published_state_row["sha256"]
                 and canonical_json(published_state["persistence"]) == canonical_json({k: v for k, v in payload.items() if k != "state_hash"})
                 and payload["event_id"] == str(event["id"]) and payload["seq"] == event["seq"]
                 and (payload["tenant_id"], payload["run_id"]) == (str(self.tenant_id), str(self.run_id)),
                 "publication event body/state linkage mismatch")
        _require(canonical_json(_without_write_metadata(state)) == canonical_json(_without_write_metadata(published_state)),
                 "published result is no longer current")
        manifest = _object(manifest_row["content"])
        _require(manifest.get("schema") == MANIFEST_SCHEMA
                 and manifest["manifest_ref"] == pointer["manifest_ref"]
                 == "program-recon-manifest:" + content_hash(canonical_json({k: v for k, v in manifest.items() if k != "manifest_ref"})),
                 "published manifest identity mismatch")
        handoff = await self._read_handoff(conn, state, request)
        _require(canonical_json(_ref(handoff["artifact"])) == canonical_json(manifest["handoff_ref"]), "published handoff pointer mismatch")
        stopped = await self._reference(conn, manifest["stopped_state_ref"], "unified_state_snapshot")
        _require(canonical_json({k: v for k, v in _without_write_metadata(published_state).items() if k != "publication"})
                 == canonical_json(_without_write_metadata(_object(stopped["content"]))),
                 "publication state changed the frozen execution basis")
        package = await self._package(conn, request, state, handoff, manifest["stopped_state_ref"])
        execution_ref, report_ref = manifest["snapshots"]["execution"], manifest["report"]
        execution = await self._reference(conn, execution_ref, EXECUTION_KIND, event["id"])
        report = await self._reference(conn, report_ref, REPORT_KIND, event["id"])
        _require(canonical_json(_object(execution["content"])) == canonical_json(package["execution_snapshot"]), "published execution differs from frozen basis")
        _require(report["content"] == package["markdown"], "published report differs from frozen basis")
        expected_execution_ref = {**_ref(execution), "artifact_schema": EXECUTION_SCHEMA}
        expected_report_ref = {**_ref(report), "renderer_version": RENDERER_VERSION, "media_type": "text/markdown"}
        _require(canonical_json(manifest) == canonical_json(_seal(package, expected_execution_ref, expected_report_ref)),
                 "published manifest differs from frozen basis")
        return {"publication_state": "published", "manifest_artifact": _ref(manifest_row), "manifest": manifest,
                "execution_snapshot": package["execution_snapshot"], "markdown": report["content"], "retention": "committed"}

    async def publish(self, request) -> dict:
        fresh = False
        async with self._locked() as (conn, _):
            state = await self._load(conn)
            await self._bound(conn, state, request)
            event = await self._publication_event(conn)
            if event is not None:
                result = await self._read_published(conn, request, state, event)
            else:
                _require("publication" not in state, "publication pointer has no event")
                handoff = await self._read_handoff(conn, state, request)
                package = await self._package(conn, request, state, handoff)
                execution_body, report_body = canonical_json(package["execution_snapshot"]), package["markdown"]
                execution_id, report_id, manifest_id = uuid4(), uuid4(), uuid4()
                execution_ref = {"artifact_id": str(execution_id), "sha256": content_hash(execution_body), "artifact_schema": EXECUTION_SCHEMA}
                report_ref = {"artifact_id": str(report_id), "sha256": content_hash(report_body), "renderer_version": RENDERER_VERSION, "media_type": "text/markdown"}
                manifest = _seal(package, execution_ref, report_ref)
                body = canonical_json(manifest)
                manifest_reference = {"artifact_id": str(manifest_id), "sha256": content_hash(body)}
                state["publication"] = {"schema": POINTER_SCHEMA, "manifest_artifact": manifest_reference, "manifest_ref": manifest["manifest_ref"]}
                now = await conn.fetchval("SELECT clock_timestamp()")
                state["updated_at"] = now.isoformat(timespec="microseconds")
                saved = await self._append(conn, state, kind=PUBLICATION_EVENT, body=body, body_id=manifest_id,
                                           body_kind=MANIFEST_KIND, now=now)
                event_id = UUID(saved["receipt"]["event_id"])
                await self._insert_artifact(conn, artifact_id=execution_id, event_id=event_id, kind=EXECUTION_KIND, body=execution_body)
                await self._insert_artifact(conn, artifact_id=report_id, event_id=event_id, kind=REPORT_KIND, body=report_body)
                result = {"publication_state": "published", "manifest_artifact": manifest_reference, "manifest": manifest,
                          "execution_snapshot": package["execution_snapshot"], "markdown": report_body, "retention": "committed"}
                fresh = True
        # No success or notification can escape an unconfirmed commit.
        notification = {"schema": "program_recon_result_notification.v1", "type": "result_published",
            "tenant_id": str(self.tenant_id), "run_id": str(self.run_id), "manifest_ref": result["manifest"]["manifest_ref"],
            "manifest_artifact": result["manifest_artifact"], "delivery_status": "not_attempted"} if fresh else None
        return {**result, "repeated": not fresh, "notification": notification}

    async def _read_result_locked(self, conn, request) -> dict:
        """Internal read under an already-held owned Run lock/transaction."""
        state = await self._load(conn)
        await self._bound(conn, state, request)
        event = await self._publication_event(conn)
        if event is not None:
            result = await self._read_published(conn, request, state, event)
        else:
            _require("publication" not in state, "publication pointer has no event")
            handoff = await self._read_handoff(conn, state, request) if state["recon"]["phase"] == "stopped" else None
            result = {"publication_state": "not_published", "manifest_artifact": None, "manifest": None, "markdown": None,
                "candidate": handoff["candidate"] if handoff else None, "progress": {"phase": state["recon"]["phase"],
                    "stage_usage": state["stage_usage"], "run_total": state["run_total"]},
                "delivery_gap": "result_not_published", "retention": "progress_only"}
        return {**result, "notification": None}

    async def read_result(self, request) -> dict:
        async with self._locked() as (conn, _):
            result = await self._read_result_locked(conn, request)
        return result
