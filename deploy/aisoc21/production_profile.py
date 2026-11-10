"""Explicit deployment configuration for on-demand processing, without secrets."""
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import UUID

import tomllib

SECTIONS = {
    "paths": {"private_dir", "transport_env_file", "ca_file", "ca_mount", "policy_file", "policy_mount"},
    "image": {"tag", "id", "user"},
    "postgres": {"container", "admin_user", "database", "host", "port", "processor_role", "ingress_role", "tls_mode"},
    "lake": {"container", "database", "host", "port", "reader_role"},
    "model": {"base_url", "alias", "protocol", "schema_profile"},
    "docker": {"network", "memory", "pids_limit", "tmpfs", "api_pythonpath", "fusion_pythonpath"},
}


class ProfileError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise ProfileError(code)


def validate_policy(path):
    # Reuse the application's dependency-free loader, shipped with this entry.
    # Do not duplicate a subset of budget/model validations in deployment code.
    source = Path(__file__).resolve().parents[2] / "services/api/app/socai2/runtime_policy.py"
    need(source.is_file(), "processing_policy_validator_missing")
    spec = importlib.util.spec_from_file_location("socai2_deployment_policy_validation", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    try:
        return module.load_policy(path)
    except ValueError as exc:
        message = str(exc)
        raise ProfileError(message if re.fullmatch(r"[a-z0-9_]+", message) else "investigation_policy_invalid") from None


def load(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode())
    need(set(data) == {"version", "default_tenant", "runtime", *SECTIONS}, "processing_profile_incomplete")
    need(data["version"] == "socai2.production-profile.v1.2", "processing_profile_version_unsupported")
    for name, keys in SECTIONS.items():
        need(isinstance(data[name], dict) and set(data[name]) == keys, "processing_profile_section_invalid")
        need(all(type(v) in {str, int} and not isinstance(v, bool) for v in data[name].values()), "processing_profile_value_invalid")
        need(all(not isinstance(v, str) or v and not any(c in v for c in "\n\r\x00") for v in data[name].values()), "processing_profile_value_invalid")
    for section, keys in {"postgres": ["admin_user", "database", "processor_role", "ingress_role"],
                          "lake": ["database", "reader_role"]}.items():
        need(all(isinstance(data[section][k], str) and re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", data[section][k]) for k in keys),
             "processing_profile_identifier_invalid")
    for section in ("postgres", "lake"):
        need(type(data[section]["port"]) is int and 0 < data[section]["port"] < 65536, "processing_profile_port_invalid")
        need(isinstance(data[section]["host"], str) and re.fullmatch(r"[A-Za-z0-9.-]+", data[section]["host"]),
             "processing_profile_host_invalid")
    need(data["postgres"]["tls_mode"] == "verify-full", "processing_profile_verified_tls_required")
    need(re.fullmatch(r"sha256:[0-9a-f]{64}", data["image"]["id"]), "processing_profile_image_digest_required")
    need(re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", data["image"]["user"]), "processing_profile_image_user_invalid")
    need(type(data["docker"]["pids_limit"]) is int and data["docker"]["pids_limit"] > 0, "processing_profile_pid_limit_invalid")
    for value in data["paths"].values():
        need(isinstance(value, str) and Path(value).is_absolute() and "," not in value, "processing_profile_path_invalid")
    endpoint = urlsplit(data["model"]["base_url"])
    need(endpoint.scheme in {"http", "https"} and endpoint.hostname and not endpoint.username
         and not endpoint.query and not endpoint.fragment, "processing_profile_model_url_invalid")
    runtime = data["runtime"]
    required = {"ENVIRONMENT", "ENV", "DEBUG", "AISOC_DEV_AUTH_BYPASS", "AISOC_AIRGAPPED", "AISOC_AIRGAP_ALLOWLIST",
        "SOCAI2_SOURCE_UEBA_ENABLED", "SOCAI2_SOURCE_KNOWLEDGE_ENABLED", "SOCAI2_SOURCE_GRAPH_ENABLED",
        "SOCAI2_SOURCE_PRODUCT_HOST_ENABLED", "DATABASE_POOL_SIZE", "DATABASE_MAX_OVERFLOW"}
    need(isinstance(runtime, dict) and set(runtime) == required and all(isinstance(v, str) and
         not any(c in v for c in "\n\r\x00") for v in runtime.values()), "processing_profile_runtime_invalid")
    need(runtime["ENVIRONMENT"] == runtime["ENV"] == "production" and runtime["AISOC_DEV_AUTH_BYPASS"] == "false"
         and runtime["AISOC_AIRGAPPED"] == "true", "processing_profile_auth_and_airgap_required")
    policy_path = Path(data["paths"]["policy_file"])
    validated_policy = validate_policy(policy_path)
    policy_raw = policy_path.read_bytes()
    need(hashlib.sha256(policy_raw).hexdigest() == validated_policy.sha256, "investigation_policy_changed_during_load")
    policy = tomllib.loads(policy_raw.decode())
    need(all(data["model"][k] == policy["model"][k] for k in ("alias", "protocol", "schema_profile")),
         "processing_profile_policy_model_mismatch")
    allowlist = json.loads(runtime["AISOC_AIRGAP_ALLOWLIST"])
    need(isinstance(allowlist, list) and all(isinstance(v, str) for v in allowlist) and
         {endpoint.hostname, urlsplit(policy["model"]["tokenizer"]["endpoint"]).hostname} <= set(allowlist),
         "processing_profile_required_endpoints_not_allowed")
    return SimpleNamespace(path=path, sha256=hashlib.sha256(raw).hexdigest(),
        policy_sha256=hashlib.sha256(policy_raw).hexdigest(), policy=policy, runtime=runtime,
        default_tenant=UUID(data["default_tenant"]), **{key: SimpleNamespace(**data[key]) for key in SECTIONS})


def runtime_values(profile):
    p, db, lake = profile, profile.postgres, profile.lake
    return {**p.runtime, "PGSSLMODE": db.tls_mode, "PGSSLROOTCERT": p.paths.ca_mount, "SSL_CERT_FILE": p.paths.ca_mount,
        "OPENAI_BASE_URL": p.model.base_url, "OPENAI_MODEL": p.model.alias,
        "CLICKHOUSE_HOST": lake.host, "CLICKHOUSE_PORT": str(lake.port), "CLICKHOUSE_DATABASE": lake.database,
        "CLICKHOUSE_USER": lake.reader_role, "SOCAI2_SERVICE_DATABASE_NAME": db.database,
        "SOCAI2_LAKE_DATABASE": lake.database, "SOCAI2_PROCESSING_PROFILE": "production21",
        "SOCAI2_PROCESSING_DB_ROLE": db.processor_role, "SOCAI2_PROCESSING_DB_HOST": db.host,
        "SOCAI2_PROCESSING_DB_PORT": str(db.port), "SOCAI2_PROCESSING_INGRESS_ROLE": db.ingress_role,
        "SOCAI2_PROCESSING_API_KEY_FILE": "/dev/stdin", "SOCAI2_MODEL_PROTOCOL": p.model.protocol,
        "SOCAI2_MODEL_SCHEMA_PROFILE": p.model.schema_profile, "PYTHONPATH": p.docker.api_pythonpath,
        "SOCAI2_PROCESSING_FUSION_PYTHONPATH": p.docker.fusion_pythonpath,
        "SOCAI2_INVESTIGATION_POLICY": p.paths.policy_mount,
        "SOCAI2_INVESTIGATION_POLICY_SHA256": p.policy_sha256, "SOCAI2_PROCESSING_PROFILE_SHA256": p.sha256,
        "AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS": str(p.policy["model"]["max_prepared_bytes"])}
