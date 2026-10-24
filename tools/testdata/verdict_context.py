"""Given-evidence evaluation context; no external context retrieval.

Import this adapter without loading either service's ``app`` package. In the
isolated Agents evaluation process, temporarily replace ReplayRunner's reader
constructor with ``make_context_reader``. Snapshot memory, skills and priors
keep the original reader behavior; the three live cutoff sources are excluded.
This does not disable networking elsewhere in ReplayRunner or the worker.
"""
from __future__ import annotations

from copy import deepcopy


EXCLUDED_REASON = "excluded_from_given_evidence_evaluation; external source was not queried"
SOURCE = "testdata.given_evidence_context"


def make_context_reader(snapshot):
    """Construct the original frozen reader with external cutoff reads disabled.

    Imports are intentionally lazy because API and Agents both own an ``app``
    package. The caller must select the Agents runtime in a separate process.
    The supplied snapshot is copied once, preserving its contents and counters;
    this adapter never captures, refreshes, filters or rewrites those records.
    """
    from app.context import dispositions, identity, knowledge_base
    from app.replay.shadow import ContextSnapshot, FrozenTriageContextReader

    if not isinstance(snapshot, ContextSnapshot):
        raise TypeError("an Agents ContextSnapshot is required")

    class GivenEvidenceContextReader(FrozenTriageContextReader):
        def _excluded(self, read):
            # No server was contacted, so as_of stays None. A requested cutoff
            # is not an echoed/applied cutoff, and an omitted source is not a
            # successful zero-row lookup.
            read["source"] = SOURCE
            read["cache"] = {"source": "none", "freshness": "not_available",
                             "age_seconds": None, "ttl_seconds": None}
            return read

        async def retrieve_runbooks(self, tenant_id, *, query):
            self.reads["retrieve_runbooks"] += 1
            read = knowledge_base.make_read(tenant_id, query=query, as_of=self._snapshot.split_at,
                                           status="disabled", reason=EXCLUDED_REASON)
            return knowledge_base.RunbookRetrieval(read=self._excluded(read))

        async def recent_dispositions(self, tenant_id, *, rule_id, entities):
            self.reads["recent_dispositions"] += 1
            read = dispositions.make_read(tenant_id, rule_id=rule_id, entities=entities,
                                          as_of=self._snapshot.split_at,
                                          status="disabled", reason=EXCLUDED_REASON)
            return dispositions.RecentDispositions(read=self._excluded(read))

        async def fetch_identity_context(self, tenant_id, *, accounts):
            self.reads["fetch_identity_context"] += 1
            read = identity.make_read(tenant_id, accounts=accounts, as_of=self._snapshot.split_at,
                                      status="disabled", reason=EXCLUDED_REASON)
            return identity.IdentityContext(read=self._excluded(read))

        def as_method_note(self):
            # Do not reuse cutoff_totals: zero served/dropped there could look
            # like a real cutoff query that found nothing. None means unmeasured.
            return {"context_mode": "given_evidence_with_supplied_snapshot",
                    "snapshot": deepcopy(self._snapshot.as_method_note()),
                    "external_context": {
                        source: {"status": "excluded", "reason": EXCLUDED_REASON,
                                 "requested_by_triage": self.reads[method], "source_queried": False,
                                 "received_count": None, "matched_count": None,
                                 "cutoff_applied": False}
                        for source, method in (("runbooks", "retrieve_runbooks"),
                                               ("dispositions", "recent_dispositions"),
                                               ("identities", "fetch_identity_context"))},
                    "scope": "Only this reader is offline; other worker/model I/O is outside this adapter."}

    return GivenEvidenceContextReader(deepcopy(snapshot))
