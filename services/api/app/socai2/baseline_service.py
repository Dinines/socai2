"""Transaction boundary for the opt-in baseline store.

The authenticated adapter supplies tenant/actor/permissions and a fully
configured executor. No adapter is installed into the old application yet.
"""
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .baseline_store import BaselineStore, StoreError


class BaselineService:
    def __init__(self, session_factory):
        self.sessions = session_factory

    @asynccontextmanager
    async def transaction(self, tenant_id, *, readonly=False):
        try:
            async with self.sessions() as db, db.begin():
                if readonly:
                    await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
                await db.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"),
                                 {"tenant": str(tenant_id)})
                yield BaselineStore(db, tenant_id)
        except IntegrityError as exc:
            constraint = getattr(exc.orig.__cause__, "constraint_name", None)
            conflicts = {"runs_request_once": "operation_key_conflict",
                         "results_business_key": "publication_key_conflict",
                         "runs_one_active_baseline": "baseline_already_active"}
            if constraint in conflicts:
                raise StoreError(conflicts[constraint]) from exc
            raise

    async def replace_members(self, tenant_id, case_id, alert_ids, **kwargs):
        async with self.transaction(tenant_id) as store:
            return await store.replace_members(case_id, set(alert_ids), **kwargs)

    async def start(self, tenant_id, case_id, run_id, request, *, actor, executor,
                    executor_version, limits):
        if executor is None:
            raise StoreError("full_baseline_executor_not_configured", 503)
        async with self.transaction(tenant_id) as store:
            claimed = await store.claim(case_id, run_id, request, actor=actor,
                                        executor_version=executor_version, limits=limits)
        # Leaving the context commits the running state and all frozen sources.
        # A replay never invokes the executor a second time.
        if claimed.newly_claimed:
            try:
                await executor(claimed)
            except (Exception, asyncio.CancelledError):
                # A transport/cancellation error cannot prove the executor did
                # no work. Keep the active slot; there is no automatic retry.
                async with self.transaction(tenant_id) as store:
                    await store.mark_unknown(case_id, run_id)
                raise
        return claimed

    async def publish(self, tenant_id, case_id, run_id, publication):
        async with self.transaction(tenant_id) as store:
            return await store.publish(case_id, run_id, publication)

    async def start_full(self, tenant_id, case_id, run_id, request, *, actor, limits, gateway=None, lake=None):
        """Authenticated server adapter entry; completes inline, never enqueues.

        The adapter supplies the existing server-owned allowance. Tests can
        inject model/lake substitutes; an HTTP body must not expose these knobs.
        """
        from .baseline_contracts import FULL_EXECUTOR_VERSION
        from .baseline_executor import BaselineExecutor
        from .runtime_policy import active_policy
        async with self.transaction(tenant_id) as store:
            now = await store.now()
            if not active_policy().case.allows(limits, now):
                raise StoreError("full_executor_limits_outside_policy", 422)
        return await self.start(tenant_id, case_id, run_id, request, actor=actor, limits=limits,
            executor_version=FULL_EXECUTOR_VERSION,
            executor=BaselineExecutor(self, tenant_id, gateway=gateway, lake=lake))

    async def history(self, tenant_id, case_id, **kwargs):
        async with self.transaction(tenant_id) as store:
            return await store.history(case_id, **kwargs)

    async def read_context(self, tenant_id, case_id, run_id):
        async with self.transaction(tenant_id) as store:
            return await store.read_context(case_id, run_id)

    async def read_material(self, tenant_id, case_id, run_id, material_id):
        async with self.transaction(tenant_id) as store:
            return await store.read_material(case_id, run_id, material_id)

    async def enrich(self, tenant_id, case_id, run_id):
        from .baseline_enrichment import BaselineEnrichment
        return await BaselineEnrichment(self).execute(tenant_id, case_id, run_id)

    async def prepare_model_view(self, tenant_id, case_id, run_id):
        async with self.transaction(tenant_id) as store:
            return await store.prepare_model_view(case_id, run_id)

    async def analyze(self, tenant_id, case_id, run_id, *, gateway=None, lake=None):
        from .baseline_analysis import BaselineAnalysis
        return await BaselineAnalysis(self).execute(tenant_id, case_id, run_id, gateway, lake)

    async def prepare_evidence(self, tenant_id, case_id, run_id):
        from .baseline_evidence import BaselineEvidence
        return await BaselineEvidence(self).prepare(tenant_id, case_id, run_id)

    async def query_evidence(self, tenant_id, case_id, run_id, binding_id, question_id, *, gateway=None):
        from .baseline_evidence import BaselineEvidence
        return await BaselineEvidence(self).query(tenant_id, case_id, run_id, binding_id, question_id, gateway)

    async def prepare_evidence_view(self, tenant_id, case_id, run_id, question_id):
        from .baseline_evidence import BaselineEvidence
        return await BaselineEvidence(self).model_view(tenant_id, case_id, run_id, question_id)

    async def deepen(self, tenant_id, case_id, run_id, question_id, *, gateway=None, lake=None):
        from .baseline_deep import BaselineDeep
        return await BaselineDeep(self).execute(tenant_id, case_id, run_id, question_id, gateway, lake)

    async def reanalyze(self, tenant_id, case_id, run_id, *, gateway=None):
        from .baseline_reanalysis import BaselineReanalysis
        return await BaselineReanalysis(self).execute(tenant_id, case_id, run_id, gateway)

    async def build_graph(self, tenant_id, case_id, run_id):
        from .baseline_graph import BaselineGraph
        return await BaselineGraph(self).execute(tenant_id, case_id, run_id)

    async def finalize(self, tenant_id, case_id, run_id, *, gateway=None):
        from .baseline_delivery import BaselineDelivery
        return await BaselineDelivery(self).execute(tenant_id, case_id, run_id, gateway)
