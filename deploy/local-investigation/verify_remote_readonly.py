"""Read-only SQL/TLS and HTTP verification; save counts/statuses, never source content."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg
from remote_profile import load_profile
from sqlalchemy.engine import make_url


def verify(profile):
    cfg = profile.config
    db, api = cfg["database"], cfg["api"]
    url = make_url(profile.database_url()).set(drivername="postgresql")
    summary = {"verified_at_utc": datetime.now(UTC).isoformat(), "profile": cfg["name"],
               "tenant_id": api["tenant_id"], "http": [], "production_mutations": 0, "model_calls": 0}
    # SQLAlchemy URL query encoding uses '+' for spaces; libpq URI parsing
    # does not. Pass decoded connection keywords, as the API dialect does.
    parameters = {"host": url.host, "port": url.port, "dbname": url.database,
                  "user": url.username, "password": url.password, **dict(url.query)}
    with psycopg.connect(**parameters) as conn:
        identity = conn.execute("""SELECT current_database(),current_user,
            current_setting('transaction_read_only'),ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()""").fetchone()
        assert identity[:4] == (db["name"], db["user"], "on", True)
        summary["database"] = dict(zip(("name", "role", "read_only", "tls", "tls_version"), identity, strict=True))
        conn.execute("SELECT set_config('app.current_tenant_id',%s,true)", (api["tenant_id"],))
        counts = dict(conn.execute("""SELECT 'alerts',count(*) FROM socai2.alerts
            UNION ALL SELECT 'incidents',count(*) FROM socai2.incidents
            UNION ALL SELECT 'cases',count(*) FROM socai2.cases
            UNION ALL SELECT 'runs',count(*) FROM socai2.runs""").fetchall())
        summary["counts"] = counts
        summary["schema"] = dict(zip(("tables", "columns"), conn.execute("""
            SELECT count(DISTINCT table_name),count(*) FROM information_schema.columns WHERE table_schema='socai2'
        """).fetchone(), strict=True))
    # The wrong certificate identity must fail before authentication/SQL. All
    # parameters, including the TCP destination, otherwise stay identical.
    try:
        with psycopg.connect(**{**parameters, "host": db["hostaddr"]}):
            raise AssertionError("wrong_certificate_identity_was_accepted")
    except psycopg.OperationalError as exc:
        assert "certificate" in str(exc).lower() and "does not match" in str(exc).lower()
        summary["wrong_tls_identity_rejected"] = True
    headers = {"Authorization": "Bearer " + profile.secrets["access_token"]}
    with httpx.Client(base_url=f"http://{api['host']}:{api['port']}", timeout=api["request_timeout_seconds"], trust_env=False) as client:
        def read(path):
            response = client.get(path, headers=headers)
            summary["http"].append({"path": path, "status": response.status_code})
            assert response.status_code == 200
            return response.json()

        read("/livez")
        read("/readyz")
        for subject in ("alerts", "incidents", "cases"):
            body = read(f"/api/v1/socai2/{subject}")
            assert body["total"] == counts[subject]
            if subject in ("alerts", "incidents") and body["items"]:
                identity = body["items"][0]["facts"]["id"]
                read(f"/api/v1/socai2/{subject}/{identity}")
                read(f"/api/v1/socai2/{subject}/{identity}/analysis")
                read(f"/api/v1/socai2/{subject}/{identity}/records/assets")
            elif subject == "cases" and body["items"]:
                identity = body["items"][0]["case"]["id"]
                read(f"/api/v1/socai2/cases/{identity}")
        for label, response, expected in (
            ("anonymous", client.get("/api/v1/socai2/cases"), 401),
            ("invalid_token", client.get("/api/v1/socai2/cases", headers={"Authorization": "Bearer invalid"}), 401),
            ("write_method", client.post("/api/v1/socai2/cases", headers=headers, json={}), 405),
        ):
            assert response.status_code == expected
            summary["http"].append({"check": label, "status": response.status_code})
        assert all(set(operations) <= {"get"} for operations in read("/openapi.json")["paths"].values())
    summary["passed"] = True
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = verify(load_profile(args.profile))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Separate receipts; a subsequent run must not overwrite old evidence.
    with target.open("x") as output:
        json.dump(result, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({"passed": result["passed"], "database": result["database"],
                      "schema": result["schema"], "counts": result["counts"],
                      "http_checks": len(result["http"]), "receipt": str(target)}))


if __name__ == "__main__":
    main()
