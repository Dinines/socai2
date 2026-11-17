"""Connect with ordinary candidate credentials, then start the frozen native consumer."""
import hashlib
import json
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

c = json.load(sys.stdin)
root = Path(c["root"])
k = c["kafka"]
out = {"candidate_id": c["candidate_id"], "status": "running", "model_calls": 0,
       "kafka_messages_sent": 0, "started_at": datetime.now(timezone.utc).isoformat()}
stage = "ordinary_connections"


def run(args, body=None):
    result = subprocess.run(args, input=body, text=True, capture_output=True,
                            timeout=c["timeout_seconds"], check=False)
    if result.returncode:
        # SQL errors and transport diagnostics can contain credentials.
        p = root / "private" / ("ingress-start-error-" + stage + "-" + secrets.token_hex(4) + ".txt")
        with p.open("x") as f:
            p.chmod(0o600)
            f.write(result.stderr + "\n" + result.stdout)
        raise RuntimeError("command_exit_" + str(result.returncode) + "; private_detail=" + str(p))
    return result.stdout


docker_base = ["docker", "run", "--network", c["network"], "--workdir", c["fusion_workdir"],
               "--env-file", str(root / "private/fusion.env"),
               "--mount", "type=bind,src=" + k["ca_source"] + ",dst=" + k["ca_target"] + ",readonly",
               "--mount", "type=bind,src=" + str(root / "initial-task-policy.json") + ",dst=/run/config/initial-task-policy.json,readonly"]
probe = '''import asyncio,json,os,uuid
import asyncpg
import redis.asyncio as redis
from aiokafka import AIOKafkaConsumer, TopicPartition
from clickhouse_driver import Client
from app.core.config import settings as s
from app.core.kafka_security import kafka_client_kwargs
import app.main

async def main():
 result={"module":app.main.__file__}
 conn=await asyncpg.connect(s.database_url.replace("postgresql+asyncpg://","postgresql://"))
 try:
  result["postgres"]=dict(await conn.fetchrow("SELECT current_database() AS database,current_user AS role,ssl,version FROM pg_stat_ssl WHERE pid=pg_backend_pid()"))
  tx=conn.transaction(); await tx.start()
  try:
   await conn.execute("SELECT set_config('app.current_tenant_id',$1,true)",os.environ["PROBE_TENANT"])
   for table in ("sessions","aisoc_ai_assets"):
    await conn.fetch("SELECT * FROM public."+table+" LIMIT 0")
   await conn.execute("INSERT INTO public.aisoc_dead_letters(tenant_id,topic,reason) VALUES ($1,$2,$3)",uuid.UUID(os.environ["PROBE_TENANT"]),s.kafka_topic_alerts_raw,"candidate_connection_probe_rollback")
  finally: await tx.rollback()
  result["postgres"]["rolled_back_support_write"]=True
 finally: await conn.close()
 r=redis.from_url(s.redis_url)
 try: result["redis"]={"ping":await r.ping(),"keys":await r.dbsize()}
 finally: await r.aclose()
 lake=Client(host=s.clickhouse_host,port=s.clickhouse_port,database=s.clickhouse_database,user=s.clickhouse_user,password=s.clickhouse_password)
 try:
  result["clickhouse"]={"database":s.clickhouse_database,"user":lake.execute("SELECT currentUser()")[0][0],"rows":lake.execute("SELECT count(*) FROM raw_events")[0][0]}
 finally: lake.disconnect()
 consumer=AIOKafkaConsumer(*json.loads(os.environ["PROBE_TOPICS"]),bootstrap_servers=s.kafka_bootstrap_servers,group_id=None,enable_auto_commit=False,**kafka_client_kwargs())
 await consumer.start()
 try:
  await consumer.topics()
  result["kafka"]={}
  for topic in json.loads(os.environ["PROBE_TOPICS"]):
   parts=[TopicPartition(topic,p) for p in consumer.partitions_for_topic(topic) or []]
   assert parts
   begins=await consumer.beginning_offsets(parts); ends=await consumer.end_offsets(parts)
   result["kafka"][topic]=[{"partition":p.partition,"begin":begins[p],"end":ends[p]} for p in parts]
   assert all(begins[p]==ends[p]==0 for p in parts)
 finally: await consumer.stop()
 print(json.dumps(result))
asyncio.run(main())
'''
try:
    identity = c["identity"]
    # The probe joins no consumer group and cannot change the new group's offset.
    command = [*docker_base, "--rm", "-i", "--env", "PROBE_TENANT=" + identity["tenant_id"],
               "--env", "PROBE_TOPICS=" + json.dumps(list(k["topics"].values())),
               "--entrypoint", "python", c["processing_image"], "-"]
    out["connections"] = json.loads(run(command, probe).splitlines()[-1])
    assert out["connections"]["postgres"]["database"] == c["postgres"]["database"]
    assert out["connections"]["postgres"]["role"] == c["postgres"]["writer"]
    assert out["connections"]["postgres"]["ssl"] is True
    assert out["connections"]["redis"]["keys"] == 0
    assert out["connections"]["clickhouse"]["rows"] == 0
    stage = "consumer_start"
    out["container_id"] = run([*docker_base, "-d", "--name", c["fusion_container"], "--restart", "no",
                               "--entrypoint", "python", c["processing_image"], "-m", "uvicorn", "app.main:app",
                               "--host", "0.0.0.0", "--port", str(c["fusion_http_port"])]).strip()
    out["image_id"] = c["processing_image"]
    out["status"] = "started_awaiting_readback"
    out["config_sha256"] = hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
except Exception as exc:  # noqa: BLE001 -- preserve a failed one-shot deployment receipt
    out["status"] = "failed"
    out["failure_stage"] = stage
    out["error"] = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
finally:
    out["ended_at"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(out,ensure_ascii=False,indent=2))
sys.exit(1 if out["status"] == "failed" else 0)
