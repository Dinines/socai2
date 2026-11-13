"""Direct synthetic list acceptance: normal TCP HTTP and local PostgreSQL.

Seed only the configured local validation database. Verify is GET/READ ONLY;
it never starts an investigation, model, consumer or retries a mutation.
"""
import argparse
import asyncio
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


async def database(cfg, action, fixture_path):
    os.environ.update(json.loads((ROOT / cfg["environment"]).read_text()))
    sys.path.insert(0, str(ROOT / "services/api"))
    from sqlalchemy import insert, select, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.db.database import _normalize_async_pg_url
    from app.models import socai2 as m
    from app.socai2.baseline_service import BaselineService

    url = os.environ["SOCAI2_CASE_DATABASE_URL"]
    assert make_url(url).database == cfg["database"]
    normalized, connect_args = _normalize_async_pg_url(url)
    engine = create_async_engine(normalized, connect_args=connect_args)
    tenant, actor = UUID(cfg["tenant_id"]), UUID(cfg["actor_id"])
    service = BaselineService(async_sessionmaker(engine, expire_on_commit=False))
    tables = {kind: getattr(m, name).__table__ for kind, name in
              (("alerts", "Alerts"), ("incidents", "Incidents"), ("cases", "Cases"))}
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("SELECT current_database()"))).scalar_one() == cfg["database"]
        if action == "seed":
            assert cfg["local_seed_allowed"] and cfg["database"] != "aisoc"
            assert not fixture_path.exists()
            prefix = "SYNTHETIC list-query " + str(uuid4())
            data = {"q": prefix, "tenant_id": str(tenant), "actor_id": str(actor),
                    "ids": {kind: [str(uuid4()) for _ in range(8 if kind == "alerts" else 6)] for kind in tables}}
            write(fixture_path.with_suffix(".intent.json"), data)
            start = datetime.fromisoformat(cfg["fixture_time"])
            severity = ["info", "high", "high", "critical", None, "low", "info", "critical"]
            offsets = [0, 1, 1, 3, None, 5, -1, 6]
            async with service.transaction(tenant) as store:
                for kind, table in tables.items():
                    for i, identity in enumerate(data["ids"][kind]):
                        when = start + timedelta(hours=offsets[i]) if offsets[i] is not None else None
                        row = dict(id=UUID(identity), tenant_id=tenant,
                            title=f"{prefix} {kind} {i}" + (" 100%_literal" if i == 0 else ""),
                            owner_id=actor if i == 1 else None,
                            assignment_state="assigned" if i == 1 else "unresolved" if i == 2 else "unassigned",
                            owner_source_value="synthetic missing owner" if i == 2 else None,
                            handling_status="in_progress" if i == 1 else "unknown" if i == 2 else
                                ("completed" if kind == "alerts" else "resolved") if i == 3 else "new",
                            tags=["synthetic", prefix])
                        if kind == "alerts":
                            row.update(source_namespace="synthetic-list-query", source_identity_key=identity,
                                severity=severity[i], event_time=when,
                                event_time_source="source" if when else "unknown",
                                ingested_at=start+timedelta(minutes=5-i))
                        elif kind == "incidents":
                            row.update(source_namespace="synthetic-list-query", source_incident_id=identity,
                                created_at=start+timedelta(minutes=5-i))
                            if i == 2:
                                row.update(severity_override="low", severity_override_reason="Synthetic override",
                                    severity_override_at=start, severity_override_by=actor)
                        else:
                            row.update(severity=severity[i], created_at=start+timedelta(minutes=5-i),
                                business_updated_at=when or start+timedelta(hours=4))
                        await store.db.execute(insert(table).values(**row))
                for i, members in enumerate(((0,), (1, 2), (3,), (4,), (6, 7), ())):
                    for member in members:
                        await store.db.execute(insert(m.IncidentAlerts).values(id=uuid4(), tenant_id=tenant,
                            incident_id=UUID(data["ids"]["incidents"][i]), alert_id=UUID(data["ids"]["alerts"][member]),
                            membership_source="manual", source_operation_id=uuid4(),
                            correlation_basis={"synthetic": True}, basis_version="synthetic.list.v1"))
            write(fixture_path, data)
        else:
            data = json.loads(fixture_path.read_text())
        snapshot = {}
        async with service.transaction(tenant, readonly=True) as store:
            for kind, table in tables.items():
                rows = (await store.db.execute(select(table).where(*store.where(table,
                    table.c.id.in_([UUID(x) for x in data["ids"][kind]]))).order_by(table.c.id))).mappings()
                snapshot[kind] = [dict(r) for r in rows]
            links = m.IncidentAlerts.__table__
            snapshot["links"] = [dict(r) for r in (await store.db.execute(select(links).where(*store.where(links,
                links.c.incident_id.in_([UUID(x) for x in data["ids"]["incidents"]]))).order_by(links.c.id))).mappings()]
        return json.loads(json.dumps(snapshot, default=str))
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "verify"])
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.profile.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    snapshot = asyncio.run(database(cfg, args.action, args.fixture))
    write(args.output / "sql-before.json", snapshot)
    if args.action == "seed":
        print(json.dumps({"seeded": {k: len(v) for k, v in snapshot.items()}, "models": 0}))
        return
    fixture = json.loads(args.fixture.read_text())
    secret = json.loads((ROOT / cfg["credential"]["file"]).read_text())
    token = secret["api_key"]
    responses = []

    def get(kind, params, *, code=200, base=None):
        path = "/api/v1/socai2/" + kind + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request((base or cfg["base_url"]) + path,
            headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(req, timeout=cfg["timeout_seconds"]) as r:
                status, body = r.status, json.load(r)
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read().decode()
            try:
                body = json.loads(raw)
            except ValueError:
                body = {"non_json_response": raw}
        responses.append({"method": "GET", "path": path, "base": base or cfg["base_url"],
                          "status": status, "body": body})
        write(args.output / "responses.json", responses)
        assert status == code, (kind, params, status, body)
        return body

    def identity(item, kind):
        return item["case" if kind == "cases" else "facts"]["id"]

    def check(kind, params, expected):
        result = get(kind, {"q": fixture["q"], **params})
        assert {identity(x, kind) for x in result["items"]} == set(expected), (kind, params)
        assert result["total" if kind == "cases" else "filtered_total"] == len(expected)
        return result

    ranks = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    alert_rows = {r["id"]: r for r in snapshot["alerts"]}
    data = {}
    for kind in ("alerts", "incidents", "cases"):
        data[kind] = []
        for row in snapshot[kind]:
            item = dict(row)
            if kind == "incidents":
                members = [alert_rows[r["alert_id"]] for r in snapshot["links"] if r["incident_id"] == row["id"]]
                item["times"] = [datetime.fromisoformat(r["event_time"]) for r in members if r["event_time"]]
                known = [ranks[r["severity"]] for r in members if r["severity"] in ranks]
                item["severity_value"] = ranks.get(row["severity_override"], max(known) if known else None)
                item["last_activity_at"] = max(item["times"]) if item["times"] else None
            else:
                item["severity_value"] = ranks.get(row["severity"])
                field = "event_time" if kind == "alerts" else "business_updated_at"
                item["times"] = [datetime.fromisoformat(row[field])] if row[field] else []
            data[kind].append(item)

    first_tokens = {}
    for kind, sort_fields in (("alerts", ("ingested_at", "event_time", "severity")),
            ("incidents", ("created_at", "last_activity_at", "severity")),
            ("cases", ("business_updated_at", "created_at", "severity"))):
        baseline = get(kind, {"q": fixture["q"]})
        global_key = "metrics" if kind == "cases" else "overall_stats"
        assert len(baseline["items"]) == len(data[kind])
        for sort_by in sort_fields:
            def value(row):
                result = row["severity_value"] if sort_by == "severity" else row[sort_by]
                return datetime.fromisoformat(result) if isinstance(result, str) else result
            for order in ("asc", "desc"):
                known = [r for r in data[kind] if value(r) is not None]
                unknown = [r for r in data[kind] if value(r) is None]
                expected = [r["id"] for r in sorted(known, key=lambda r: (value(r), r["id"]), reverse=order == "desc")]
                expected += [r["id"] for r in sorted(unknown, key=lambda r: r["id"], reverse=order == "desc")]
                params = {"q": fixture["q"], "sort_by": sort_by, "sort_order": order, "limit": 2}
                seen = []
                while True:
                    page = get(kind, params)
                    seen += [identity(r, kind) for r in page["items"]]
                    assert page["total" if kind == "cases" else "filtered_total"] == len(data[kind])
                    assert page[global_key] == baseline[global_key]
                    if kind != "cases":
                        assert page["total"] == baseline["total"] and page["next_before_id"] is None
                    if not page["next_cursor"]:
                        break
                    assert len(seen) <= len(data[kind])
                    first_tokens.setdefault(kind, page["next_cursor"])
                    params["cursor"] = page["next_cursor"]
                assert seen == expected, (kind, sort_by, order, seen, expected)
        for field, val in (("severity", "high"), ("handling_status", "new"), ("owner_id", cfg["actor_id"]),
                ("assignment_state", "unresolved")):
            expected = [r["id"] for r in data[kind] if
                (r["severity_value"] == ranks[val] if field == "severity" else r[field] == val)]
            result = check(kind, {field: val}, expected)
            assert result[global_key] == baseline[global_key]
        check(kind, {"q": fixture["q"] + " " + kind + " 0 100%_"}, [fixture["ids"][kind][0]])
        check(kind, {"q": fixture["ids"][kind][1]}, [fixture["ids"][kind][1]])
        check(kind, {"q": fixture["q"] + " absent"}, [])
        start = datetime.fromisoformat(cfg["fixture_time"]) + timedelta(hours=2)
        end = start + timedelta(hours=2)
        expected = [r["id"] for r in data[kind] if any(start <= t < end for t in r["times"])]
        check(kind, {"time_from": start.isoformat(), "time_to": end.isoformat()}, expected)
        for params in ({"time_from": start.replace(tzinfo=None).isoformat()},
                {"time_from": end.isoformat(), "time_to": start.isoformat()},
                {"cursor": "not-base64"}, {"sort_by": "not-a-sort"},
                {"cursor": first_tokens[kind], "q": fixture["q"] + " changed"}):
            get(kind, params, code=422)
    for kind in ("alerts", "incidents"):
        for params in ({"before_id": fixture["ids"][kind][0], "q": fixture["q"]},
                {"before_id": fixture["ids"][kind][0], "cursor": first_tokens[kind]}):
            get(kind, params, code=422)
        # Original endpoint on 18024 still runs the previous release against the same DB.
        params = {"limit": 2}
        for _ in range(2):
            new = get(kind, params)
            old = get(kind, params, base=cfg["legacy_base_url"])
            assert {k: v for k, v in new.items() if k not in {"filtered_total", "next_cursor", "observed_at"}} == {
                k: v for k, v in old.items() if k != "observed_at"}
            assert new["filtered_total"] == new["total"]
            params["before_id"] = new["next_before_id"]
    old = get("cases", {"q": fixture["q"], "limit": 2}, base=cfg["legacy_base_url"])
    assert json.loads(base64.urlsafe_b64decode(old["next_cursor"]))["version"] == 1
    params = {"q": fixture["q"], "limit": 2, "cursor": old["next_cursor"]}
    assert get("cases", params) == get("cases", params, base=cfg["legacy_base_url"])
    after = asyncio.run(database(cfg, "verify", args.fixture))
    write(args.output / "sql-after.json", after)
    assert after == snapshot
    result = {"state": "passed", "requests": len(responses), "database": cfg["database"],
        "transport": "TCP HTTP", "service_dependency_overrides": False, "real_model_calls": 0,
        "sorts": 9, "directions": 2, "rows_unchanged": {k: len(v) for k, v in snapshot.items()},
        "legacy_subject_pagination": True, "legacy_case_v1_cursor": True,
        "snapshot_sha256": hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()}
    write(args.output / "verification.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
