"""Fixed local workspace configuration; no imported server deployment helper."""
import os
from pathlib import Path
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".local/local-investigation"
PRIVATE = STATE / "private"
ENV_FILE = PRIVATE / "runtime.env"
PYTHON = ROOT / ".local/conda-envs/socai2/bin/python"
DATABASE = "socai2_local_20261105"
LAKE = "socai2_local_validation"
TENANT = str(uuid5(NAMESPACE_URL, "socai2-local-20261105:tenant"))
USER = str(uuid5(NAMESPACE_URL, "socai2-local-20261105:user"))
TOPIC = "socai2.local.20261105"
PORTS = {"postgres": 15432, "clickhouse_native": 19000, "clickhouse_http": 18123,
         "kafka": 19092, "redis": 16379, "api": 18020, "fusion": 18021}
API_ROLE = "local_socai2_api"
FUSION_ROLE = "local_socai2_fusion"
CH_READER = "local_socai2_reader"
CH_WRITER = "local_socai2_writer"


def read_private():
    assert ENV_FILE.is_file() and not ENV_FILE.is_symlink(), "local private configuration missing"
    assert ENV_FILE.stat().st_mode & 0o077 == 0 and PRIVATE.stat().st_mode & 0o077 == 0
    values = {}
    for line in ENV_FILE.read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        assert key not in values and key.replace("_", "").isalnum()
        values[key] = value
    return values


def runtime_environment(kind, values):
    assert kind in {"api", "fusion"}
    protocol = values["SOCAI2_MODEL_PROTOCOL"]
    profile = values["SOCAI2_MODEL_SCHEMA_PROFILE"]
    assert protocol in {"chat_completions", "deepseek_responses"}, "unsupported model protocol"
    assert profile in {"standard", "vllm_grammar_v1"}, "unsupported model schema profile"
    role = API_ROLE if kind == "api" else FUSION_ROLE
    password = values["API_DB_PASSWORD" if kind == "api" else "FUSION_DB_PASSWORD"]
    env = {"ENVIRONMENT": "local", "ENV": "local", "DEBUG": "false", "AISOC_DEV_AUTH_BYPASS": "false",
        "DATABASE_URL": "postgresql+asyncpg://" + role + ":" + quote(password, safe="") + "@127.0.0.1:15432/" + DATABASE + "?sslmode=disable",
        "REDIS_URL": "redis://127.0.0.1:16379/0", "CLICKHOUSE_HOST": "127.0.0.1", "CLICKHOUSE_PORT": "19000",
        "CLICKHOUSE_DATABASE": LAKE, "SOCAI2_LAKE_DATABASE": LAKE,
        "CLICKHOUSE_USER": CH_READER if kind == "api" else CH_WRITER,
        "CLICKHOUSE_PASSWORD": values["CH_READER_PASSWORD" if kind == "api" else "CH_WRITER_PASSWORD"],
        "KAFKA_BOOTSTRAP_SERVERS": "127.0.0.1:19092", "KAFKA_BROKERS": "127.0.0.1:19092",
        "KAFKA_SECURITY_PROTOCOL": "PLAINTEXT", "KAFKA_TOPIC_ALERTS_RAW": TOPIC + ".alerts.raw",
        "KAFKA_TOPIC_RAW_EVENTS": TOPIC + ".raw_events", "KAFKA_TOPIC_ALERTS_FUSED": TOPIC + ".alerts.fused",
        "KAFKA_CONSUMER_GROUP": TOPIC + ".fusion", "LOG_LEVEL": "INFO"}
    if kind == "api":
        for key in ("SECRET_KEY", "JWT_SECRET", "AISOC_CREDENTIAL_KEY", "REALTIME_INTERNAL_TOKEN",
                    "AISOC_REALTIME_JWT_SECRET", "METRICS_TOKEN", "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"):
            env[key] = values[key]
        env.update({"SOCAI2_SERVICE_DATABASE_NAME": DATABASE, "SOCAI2_CASE_API_ENABLED": "true",
            "SOCAI2_ANALYSIS_READ_ENABLED": "true", "SOCAI2_PAGE_READ_ENABLED": "true",
            "SOCAI2_STAGE_EXECUTION_ENABLED": "true", "SOCAI2_SOURCE_UEBA_ENABLED": "true",
            "SOCAI2_SOURCE_KNOWLEDGE_ENABLED": "true", "SOCAI2_SOURCE_GRAPH_ENABLED": "false",
            "SOCAI2_SOURCE_PRODUCT_HOST_ENABLED": "false", "SOCAI2_MODEL_PROTOCOL": protocol,
            "SOCAI2_MODEL_SCHEMA_PROFILE": profile, "DATABASE_POOL_SIZE": "4", "DATABASE_MAX_OVERFLOW": "2",
            "AISOC_DISABLE_NEO4J": "true", "AISOC_DISABLE_QDRANT": "true", "AISOC_DISABLE_OPENSEARCH": "true"})
    else:
        env.update({"AISOC_ALERT_STORE_SCHEMA": "socai2", "AISOC_EVENT_PROMOTION_ENABLED": "false",
            "AISOC_ALERT_SINK_ENABLED": "true", "AISOC_LAKE_WRITER_ENABLED": "true", "AISOC_LAKE_BATCH_SIZE": "1",
            "AISOC_DETECTION_ENGINE_ENABLED": "false", "AISOC_WINDOWED_DETECTION_ENABLED": "false",
            "AISOC_UEBA_FUSION_ENABLED": "false", "AISOC_ATTACK_CHAIN_GROUPING_ENABLED": "false",
            "AISOC_FUSION_MEMORY_NUDGE": "false", "HTTP_PORT": "18021"})
    return env


def minimal_process_environment():
    # Do not inherit a parent shell's service credentials or old routing flags.
    return {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SYSTEMROOT"}}
