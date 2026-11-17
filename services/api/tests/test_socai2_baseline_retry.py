"""Known unsent transport failures must not override another unsettled call."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from app.socai2.baseline_failure import settle_unsent, unsent_failure
from app.socai2.model_errors import ModelCallError, provider_error


@pytest.mark.parametrize("error_type,known", [(httpx.ConnectTimeout, True), (httpx.PoolTimeout, True),
    (httpx.ReadTimeout, False), (httpx.WriteTimeout, False)])
def test_gateway_transport_receipt_classification(error_type, known):
    failure = ModelCallError(provider_error(error_type("synthetic"), ""))
    assert bool(unsent_failure(failure)) is known


@pytest.mark.parametrize("run_state,unsettled", [("unknown", None), ("running", {"id": uuid4()})])
def test_known_connection_failure_does_not_rewrite_uncertain_work(run_state, unsettled):
    db = SimpleNamespace(execute=AsyncMock())
    store = SimpleNamespace(db=db, one=AsyncMock(return_value=unsettled), where=lambda table, *clauses: clauses)
    assert not asyncio.run(settle_unsent(store, {"id": uuid4(), "state": run_state}, httpx.ConnectTimeout("synthetic")))
    db.execute.assert_not_awaited()
