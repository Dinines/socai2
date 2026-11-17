"""The acceptance CLI's bounded HTTP, Kafka and read-only database clients."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from uuid import UUID

import httpx
from acceptance_materials import MaterialError, control, read_json, save_report
from acceptance_runtime_contract import (
    HttpConnection,
    KafkaConnection,
    LakeConnection,
    PostgresConnection,
)
from alert_kafka import kafka_config, send_records
from alert_scenarios import json_bytes, sha256


def require(condition, code):
    if not condition:
        raise MaterialError(code)


def now():
    return datetime.now(timezone.utc).isoformat()


class Http:
    def __init__(self, config, output, transport=None):
        self.config, self.output, self.sequence = config, output, 0
        output.mkdir()
        self.client = httpx.Client(timeout=config.timeout_seconds, follow_redirects=False, trust_env=False, transport=transport)

    def close(self):
        self.client.close()

    def request(self, method, path, body=None, *, allowed=(200,)):
        require(path.startswith("/api/v1/socai2/") and not urlsplit(path).netloc and ".." not in path, "invalid_business_http_path")
        self.sequence += 1
        stem = f"{self.sequence:05d}"
        request = {"method": method, "path": path, "body": body, "started_at": now()}
        if method != "GET":
            require(method == "POST", "unsupported_http_method")
            save_report(self.output / (stem + ".intent.json"), {"state": "started_outcome_unknown", "request": request})
        record = {"request": request}
        try:
            response = self.client.request(method, self.config.base_url + path, json=body if method != "GET" else None)
            (self.output / (stem + ".body")).write_bytes(response.content)
            try:
                value = response.json()
            except ValueError:
                value = None
            record.update(outcome="returned", response={"status": response.status_code, "body": value,
                          "body_file": stem + ".body", "sha256": sha256(response.content)}, ended_at=now())
        except (httpx.HTTPError, OSError) as exc:
            record.update(outcome="unknown", error_type=type(exc).__name__, ended_at=now())
            save_report(self.output / (stem + ".json"), record)
            raise MaterialError("http_outcome_unknown_no_retry") from exc
        save_report(self.output / (stem + ".json"), record)
        require(response.status_code in allowed, f"http_status_{response.status_code}")
        return value

    def pages(self, path, params=None):
        params = {**(params or {}), "limit": self.config.page_size}
        result, seen = [], set()
        while True:
            page = self.request("GET", path + "?" + urlencode(params))
            require(isinstance(page, dict) and isinstance(page.get("items"), list), "invalid_http_page")
            result.extend(page["items"])
            cursor = page.get("next_cursor")
            if not cursor:
                require(len(result) == page["total"], "incomplete_http_pagination")
                return result
            require(cursor not in seen, "repeated_http_cursor")
            seen.add(cursor)
            params["cursor"] = cursor

    def readiness(self):
        response = self.client.get(self.config.fusion_ready_url)
        value = response.json()
        require(response.status_code == 200 and value.get("status") == "ready", "fusion_not_ready")
        self.request("GET", "/api/v1/socai2/alerts?" + urlencode({"limit": self.config.page_size}))
        return value


class Postgres:
    def __init__(self, config, tenant):
        self.config, self.tenant, self.connection = config, UUID(tenant), None

    async def connect(self):
        import asyncpg
        url = Path(self.config.database_url_file).read_text().strip().replace("postgresql+asyncpg://", "postgresql://", 1)
        self.connection = await asyncpg.connect(url, ssl=self.config.ssl, timeout=self.config.connect_timeout_seconds,
                                               command_timeout=self.config.query_timeout_seconds)
        actual = await self.connection.fetchrow("SELECT current_database() AS database, current_user AS role")
        require(actual["database"] == self.config.expected_database and actual["role"] == self.config.expected_user,
                "postgres_target_mismatch")
        return dict(actual)

    async def close(self):
        if self.connection:
            await self.connection.close()

    async def snapshot(self, alert_ids, case_ids=(), *, full=False):
        s, c = self.config.schema_name, self.connection
        async with c.transaction(isolation="repeatable_read", readonly=True):
            await c.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(self.tenant))

            async def rows(table, column, identities):
                if not identities:
                    return []
                values = await c.fetchval(
                    f"SELECT coalesce(json_agg(row_to_json(t) ORDER BY t.id),'[]'::json) FROM {s}.{table} t "
                    f"WHERE t.tenant_id=$1 AND t.{column}=ANY($2::uuid[])", self.tenant, [UUID(x) for x in identities])
                return json.loads(values)

            out = {"alerts": await rows("alerts", "id", alert_ids)}
            out["alert_materials"] = await rows("alert_materials", "alert_id", alert_ids)
            out["alert_source_refs"] = await rows("alert_source_refs", "alert_id", alert_ids)
            out["incident_alerts"] = await rows("incident_alerts", "alert_id", alert_ids)
            incident_ids = sorted({x["incident_id"] for x in out["incident_alerts"]})
            # Whole incident/case membership is needed to detect unintended historical association.
            out["incident_members"] = await rows("incident_alerts", "incident_id", incident_ids)
            out["incidents"] = await rows("incidents", "id", incident_ids)
            out["cases"] = await rows("cases", "id", case_ids)
            out["case_alerts"] = await rows("case_alerts", "case_id", case_ids)
            subjects = list(alert_ids) + incident_ids + list(case_ids)
            out["analysis_tasks"] = await rows("analysis_tasks", "subject_id", subjects)
            out["analysis_attempts"] = await rows("analysis_attempts", "subject_id", subjects)
            run_ids = sorted({x["run_id"] for x in out["analysis_attempts"] if x["run_id"]})
            out["runs"] = await rows("runs", "id", run_ids)
            out["results"] = await rows("results", "case_id", case_ids)
            if full:
                out["run_members"] = await rows("run_members", "run_id", run_ids)
                out["run_steps"] = await rows("run_steps", "run_id", run_ids)
                out["artifacts"] = await rows("artifacts", "run_id", run_ids)
                out["alert_assessments"] = await rows("alert_assessments", "alert_id", alert_ids)
                out["incident_diagnoses"] = await rows("incident_diagnoses", "incident_id", incident_ids)
            out["readonly"] = await c.fetchval("SHOW transaction_read_only") == "on"
            return out

    async def preflight(self, alerts, correlation_keys, known_alert_ids=()):
        c, s = self.connection, self.config.schema_name
        async with c.transaction(readonly=True):
            await c.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(self.tenant))
            connectors = sorted({a["connector_id"] for a in alerts if a.get("connector_id")})
            rows = await c.fetch("SELECT id,connector_type FROM public.connectors WHERE tenant_id=$1 AND id=ANY($2::uuid[])",
                                 self.tenant, [UUID(x) for x in connectors])
            found = {str(x["id"]): x["connector_type"] for x in rows}
            require(set(found) == set(connectors), "connector_not_registered_for_target_tenant")
            require(all(not a.get("connector_type") or found.get(a.get("connector_id")) == a["connector_type"]
                        for a in alerts if a.get("connector_id")), "connector_type_mismatch")
            collisions = await c.fetchval(
                f"SELECT count(*) FROM {s}.incident_alerts WHERE tenant_id=$1 "
                "AND correlation_basis->>'correlation_key'=ANY($2::text[]) AND NOT (alert_id=ANY($3::uuid[]))",
                self.tenant, correlation_keys, [UUID(v) for v in known_alert_ids])
            require(collisions == 0, "historical_correlation_scope_choose_new_materials")
            return {"registered_connectors": connectors, "matching_historical_members": collisions, "readonly": True}


class Lake:
    def __init__(self, config, tenant):
        from clickhouse_driver import Client
        self.config, self.tenant = config, tenant
        self.client = Client(host=config.host, port=config.port, database=config.database, user=config.user,
                             password=Path(config.password_file).read_text().strip(), secure=config.secure,
                             verify=config.verify, ca_certs=config.ca_certs, connect_timeout=config.connect_timeout_seconds,
                             send_receive_timeout=config.read_timeout_seconds,
                             settings={"readonly": 1, "max_execution_time": config.query_timeout_seconds})

    def close(self):
        self.client.disconnect()

    def query(self, ids):
        if not ids:
            return []
        rows = self.client.execute(
            f"SELECT event_id,tenant_id,toUnixTimestamp64Milli(event_time),class_uid,ocsf_json FROM "
            f"{self.config.database}.{self.config.table} WHERE tenant_id=%(tenant)s AND event_id IN %(ids)s",
            {"tenant": self.tenant, "ids": tuple(ids)})
        return [{"event_id": str(a), "tenant_id": str(b), "event_time_ms": c, "class_uid": d,
                 "ocsf_json": json.loads(e) if isinstance(e, str) else e} for a, b, c, d, e in rows]

    def history_count(self, hosts, known_event_ids=()):
        if not hosts:
            return 0
        return self.client.execute(
            f"SELECT count() FROM {self.config.database}.{self.config.table} WHERE tenant_id=%(tenant)s AND src_hostname IN %(hosts)s"
            + (" AND event_id NOT IN %(known)s" if known_event_ids else ""),
            {"tenant": self.tenant, "hosts": tuple(hosts), "known": tuple(known_event_ids)})[0][0]


class Connections:
    def __init__(self, profile, output, *, transport=None, producer_factory=None):
        kinds = {"http": HttpConnection, "kafka": KafkaConnection, "postgres": PostgresConnection, "lake": LakeConnection}
        self.configs, self.hashes = {}, {}
        for name, model in kinds.items():
            path = Path(getattr(profile.connection_files, name))
            require(path.is_absolute(), "absolute_connection_file_required")
            self.configs[name] = control(model, read_json(path), name + " connection")
            self.hashes[name] = sha256(path.read_bytes())
        require(self.configs["http"].tenant_id == profile.tenant_id, "http_profile_tenant_mismatch")
        self.profile, self.output, self.producer_factory = profile, output, producer_factory
        self.http = Http(self.configs["http"], output / "http", transport)
        self.pg = Postgres(self.configs["postgres"], profile.tenant_id)
        self.lake = None
        self.transport = None

    async def open(self):
        try:
            database = await self.pg.connect()
            self.lake = Lake(self.configs["lake"], self.profile.tenant_id)
            config = self.configs["kafka"]
            self.transport = kafka_config(Path(config.producer_env_file))
            require(self.transport["bootstrap_servers"] == config.expected_bootstrap_servers
                    and self.transport["security_protocol"] == config.security_protocol, "kafka_target_mismatch")
            readiness = self.http.readiness()
            return {"database": database, "fusion": readiness, "connection_sha256": self.hashes}
        except Exception:
            await self.close()
            raise

    async def close(self):
        self.http.close()
        await self.pg.close()
        if self.lake:
            self.lake.close()

    async def send(self, role, path, payload):
        data, config = json_bytes(payload), self.configs["kafka"]
        receipt = self.output / ("send-" + path.replace("/", "-"))
        return await send_records(records=[{"material": path, "wire_sha256": sha256(data)}], values=[data],
                                  tenant=self.profile.tenant_id, topic=getattr(config.topics, role), receipt=receipt,
                                  config=self.transport, timeout=config.timeout_seconds,
                                  request_timeout_ms=config.request_timeout_ms,
                                  identity={"schema_version": "socai2.acceptance-send.v1", "material": path},
                                  producer_factory=self.producer_factory)

