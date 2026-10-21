"""Read-only source census; run separately on host21 and host20.

Only metadata/counts leave the host. No event bodies, credentials, Kafka
consumer groups, schema migrations, ingestion or service restarts are used.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone


def run(args, content=None):
    p = subprocess.run(args, input=content, text=True, capture_output=True, timeout=45)
    if p.returncode:
        raise RuntimeError("metadata command failed; private stderr deliberately omitted")
    return p.stdout


def inspect(name):
    return json.loads(run(["docker", "inspect", name]))[0]


def env(item):
    return dict(x.split("=", 1) for x in item["Config"]["Env"] if "=" in x)


def pg(container, database, sql):
    e = env(inspect(container))
    return json.loads(run(["docker", "exec", "-i", container, "psql", "-XqAt", "-v", "ON_ERROR_STOP=1",
                           "-U", e["POSTGRES_USER"], "-d", database], "BEGIN READ ONLY; SET LOCAL statement_timeout='5s';\n" + sql + "\nROLLBACK;"))


def main(host):
    names = run(["docker", "ps", "-aq"]).split()
    items = json.loads(run(["docker", "inspect", *names]))
    before = {x["Name"]: [x["Id"], x["Image"], x["State"]["StartedAt"], x["RestartCount"]] for x in items}
    pgname = "spirithub-postgres-1" if host == "21" else "aisoc-postgres"
    kafka = "sting-infra21-kafka-1" if host == "21" else "aisoc-kafka"
    out = {"batch": "2c-sources-20261020", "host": host, "queried_at": datetime.now(timezone.utc).isoformat(),
           "read_only": True, "pg": {}, "clickhouse": {"container_present": False}}
    # Catalog row estimates are labelled; UEBA contract tables get exact counts below.
    for db in (["sting", "sting_ueba_test", "sting_investigation_test", "aisoc"] if host == "21" else ["aisoc"]):
        out["pg"][db] = pg(pgname, db, "SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT relname, n_live_tup AS estimated_rows FROM pg_stat_user_tables WHERE relname ~* 'event|ueba|anomal|baseline|signal' ORDER BY relname) t;")
    if host == "21":
        tables = ["anomalies", "entity_baselines", "event_results", "input_events", "peer_baselines", "signal_current"]
        out["ueba_exact_counts"] = {t: pg(pgname, "sting_ueba_test", f"SELECT count(*) FROM sting_ueba.{t};") for t in tables}
        ch = "sting-infra21-clickhouse-1"; e = env(inspect(ch))
        def query(sql):
            return json.loads(run(["docker", "exec", "-i", "-e", "CLICKHOUSE_PASSWORD=" + e["CLICKHOUSE_PASSWORD"], ch,
                                   "clickhouse-client", "--user", e["CLICKHOUSE_USER"], "--query", sql + " FORMAT JSON"]))["data"]
        out["clickhouse"] = {"container_present": True,
            "databases": query("SELECT name FROM system.databases ORDER BY name"),
            "business_tables": query("SELECT database,name,engine,total_rows FROM system.tables WHERE database NOT IN ('system','INFORMATION_SCHEMA','information_schema') ORDER BY database,name"),
            "all_table_read_grant": any("ON *.*" in str(v) and ("SELECT" in str(v) or "ALL" in str(v)) for x in query("SHOW GRANTS") for v in x.values())}
    topics = run(["docker", "exec", kafka, "kafka-topics", "--bootstrap-server", "localhost:9092", "--list"]).splitlines()
    selected = [t for t in topics if t in ["aisoc.raw_events", "ueba.anomalies"]]
    out["kafka"] = {"topic_count_excluding_internal": len([x for x in topics if not x.startswith("__")]),
                    "event_ueba_topics": selected, "offsets": {}}
    for t in selected:
        out["kafka"]["offsets"][t] = {label: run(["docker", "exec", kafka, "kafka-run-class", "kafka.tools.GetOffsetShell",
            "--broker-list", "localhost:9092", "--topic", t, "--time", number]).splitlines() for label, number in [("earliest", "-2"), ("latest", "-1")]}
    api = "socai2-api-1" if host == "21" else "aisoc-api"
    out["api_lake_configuration"] = json.loads(run(["docker", "exec", "-i", api, "python", "-"],
        "import json\nfrom app.core.config import settings\nprint(json.dumps({'host':settings.CLICKHOUSE_HOST,'port':settings.CLICKHOUSE_PORT,'database':settings.CLICKHOUSE_DATABASE,'startup_disabled':settings.AISOC_DISABLE_CLICKHOUSE}))\n"))
    if host == "20":
        out["clickhouse"]["configured_host_resolves_from_api"] = json.loads(run(["docker", "exec", "-i", api, "python", "-"],
            "import socket,json\ntry: socket.getaddrinfo('clickhouse',9000); ok=True\nexcept OSError: ok=False\nprint(json.dumps(ok))\n"))
        # Inspect the single retained event by digest/schema only, never export its body.
        code = '''import asyncio,hashlib,json,os
from aiokafka import AIOKafkaConsumer,TopicPartition
async def main():
 c=AIOKafkaConsumer(bootstrap_servers=os.environ['KAFKA_BOOTSTRAP_SERVERS'],enable_auto_commit=False,group_id=None)
 await c.start()
 try:
  tp=TopicPartition('aisoc.raw_events',0); c.assign([tp]); start=(await c.beginning_offsets([tp]))[tp]; end=(await c.end_offsets([tp]))[tp]
  out={'start':start,'end':end,'group_id':None,'commits':False}
  if end>start:
   c.seek(tp,start); r=await asyncio.wait_for(c.getone(),10); data=json.loads(r.value)
   out.update({'offset':r.offset,'sha256':hashlib.sha256(r.value).hexdigest(),'top_level_fields':sorted(data),'synthetic_marker_present':any(s in r.value.lower() for s in [b'smoke',b'test',b'synthetic'])})
  print(json.dumps(out))
 finally: await c.stop()
asyncio.run(main())
'''
        out["retained_event_metadata"] = json.loads(run(["docker", "exec", "-i", "aisoc-fusion", "python", "-"], code))
    after = {x["Name"]: [x["Id"], x["Image"], x["State"]["StartedAt"], x["RestartCount"]] for x in json.loads(run(["docker", "inspect", *names]))}
    out["containers_unchanged"] = before == after
    out["container_count"] = len(before)
    assert before == after
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("host", choices=["20", "21"])
    main(parser.parse_args().host)
