"""Independent Case browsing snapshots; no Run, membership or assessment writes."""
import json
import os
from pathlib import Path
from uuid import UUID, uuid5

from sqlalchemy import insert, select

from .baseline_store import A, F, StoreError, digest, encoded
from .case_service import CaseService
from .exploration import O
from .exploration_contracts import ExplorationMatch
from .exploration_matching import matching_value, object_view
from .exploration_state_contracts import (
    ExplorationSaved,
    ExplorationSnapshot,
    ExplorationSources,
)
from .exploration_state_sources import base, sources

SCHEMA = "socai2.case-exploration.v1"
ACTION = "case_exploration_saved"


def limits():
    path = Path(os.environ.get("SOCAI2_EXPLORATION_STATE_CONFIG_FILE", Path(__file__).with_name("exploration-state.json")))
    value = json.loads(path.read_text())
    if any(type(value.get(key)) is not int or value[key] <= 0 for key in ("max_snapshot_bytes", "max_expanded_links")):
        raise StoreError("invalid_exploration_state_config", 503)
    return value


class ExplorationStateService(CaseService):
    @staticmethod
    def scope(store, case_id):
        return store.where(F, F.c.case_id == case_id, F.c.run_id.is_(None),
            F.c.kind == "source_snapshot", F.c.schema_version == SCHEMA)

    async def saved(self, store, case_id, snapshot_id=None):
        query = select(F.c.content_json).where(*self.scope(store, case_id))
        if snapshot_id:
            query = query.where(F.c.id == snapshot_id)
        row = await store.one(query.order_by(F.c.captured_at.desc(), F.c.id.desc()).limit(1))
        if row is None and snapshot_id:
            raise StoreError("exploration_snapshot_not_found", 404)
        return ExplorationSnapshot.model_validate(row["content_json"]) if row else None

    async def read(self, tenant_id, case_id):
        async with self.transaction(tenant_id, readonly=True) as store:
            await store.case(case_id, lock=False)
            return ExplorationSaved(snapshot=await self.saved(store, case_id))

    async def read_base(self, tenant_id, case_id, run_id=None):
        async with self.transaction(tenant_id, readonly=True) as store:
            case = await store.case(case_id, lock=False)
            return await base(store, case, run_id, choose_latest=run_id is None)

    async def expand(self, store, case, original, previous, links):
        reachable = {a.id for a in original.sources.alerts}
        matches, pairs = [], set()
        old_matches = {(m.seed.id, m.candidate.id): m for m in previous.expanded_links} if previous else {}
        for link in links:
            pair = link.seed_object_id, link.candidate_object_id
            if pair in old_matches:
                match = old_matches[pair]
            else:
                rows = []
                for identity in pair:
                    row = await store.one(select(O).join(A,
                        (A.c.tenant_id == O.c.tenant_id) & (A.c.id == O.c.alert_id)).where(*store.where(O,
                            O.c.id == identity), A.c.source_namespace == case["source_namespace"]))
                    if row is None:
                        raise StoreError("exploration_object_not_found", 404)
                    rows.append(row)
                left, right = rows
                lv, la, le = matching_value(left)
                rv, ra, re = matching_value(right)
                if (le or re or left["alert_id"] == right["alert_id"] or
                    (left["namespace"], left["object_type"], lv, la) != (right["namespace"], right["object_type"], rv, ra)):
                    raise StoreError("exploration_objects_do_not_match", 422)
                match = ExplorationMatch(seed=object_view(left, la), candidate=object_view(right, ra),
                    basis="same_hash_algorithm_and_value" if la else "same_source_value")
            if match.seed.alert_id not in reachable:
                raise StoreError("exploration_disconnected_branch", 422)
            reachable.add(match.candidate.alert_id)
            matches.append(match)
            pairs.update((o.alert_id, o.material_id) for o in (match.seed, match.candidate))
        current = await sources(store, sorted(pairs, key=lambda p: (str(p[0]), str(p[1]))))
        if previous:
            # Existing saved source values remain frozen when continuing a canvas.
            old_alerts = {a.id: a for a in previous.expanded_sources.alerts}
            old_objects = {o.id: o for o in previous.expanded_sources.objects}
            current = ExplorationSources(alerts=[old_alerts.get(a.id, a) for a in current.alerts],
                objects=[old_objects.get(o.id, o) for o in current.objects])
        return matches, current

    async def save(self, tenant_id, case_id, request, *, actor):
        config = limits()
        intent = digest({"actor": str(actor.user_id), "request": request.model_dump(mode="json")})
        if len(encoded(request.model_dump(mode="json"))) > config["max_snapshot_bytes"] or len(request.expanded_links) > config["max_expanded_links"]:
            raise StoreError("exploration_snapshot_too_large", 422)
        async with self.transaction(tenant_id) as store:
            await self.actor(store, actor)
            case = await store.case(case_id)
            prior = await store.receipt(case_id, request.operation_key, ACTION)
            if prior:
                if prior["request_hash"] != intent:
                    raise StoreError("operation_key_conflict")
                return await self.saved(store, case_id, UUID(prior["snapshot_id"]))
            latest = await self.saved(store, case_id)
            if request.expected_snapshot_id != (latest.id if latest else None):
                raise StoreError("exploration_snapshot_changed")
            previous = await self.saved(store, case_id, request.base_snapshot_id) if request.base_snapshot_id else None
            original = previous.base if previous else await base(store, case, request.base_run_id)
            if previous is None and original.fingerprint != request.base_fingerprint:
                raise StoreError("exploration_base_changed")
            matches, expanded = await self.expand(store, case, original, previous, request.expanded_links)
            now = await store.now()
            out = ExplorationSnapshot(id=uuid5(case_id, "socai2.exploration:" + str(request.operation_key)),
                case_id=case_id, created_at=now, created_by=actor.user_id, base=original,
                expanded_links=matches, expanded_sources=expanded, view_state=request.view_state)
            content = out.model_dump(mode="json")
            size = len(encoded(content))
            if size > config["max_snapshot_bytes"]:
                raise StoreError("exploration_snapshot_too_large", 422)
            await store.db.execute(insert(F).values(id=out.id, tenant_id=tenant_id, case_id=case_id,
                kind="source_snapshot", schema_version=SCHEMA, content_json=content,
                mime_type="application/json", sha256=digest(content), size_bytes=size, captured_at=now,
                material_state="complete", source_refs=[], created_by=actor.user_id,
                retention={"original_size_bytes": size, "retained_size_bytes": size, "truncated": False,
                    "reason": "case_exploration_browsing_state", "omitted_paths": []}))
            await store.event(case_id, request.operation_key, actor.snapshot(), ACTION,
                {"request_hash": intent, "snapshot_id": str(out.id)}, [])
            return out
