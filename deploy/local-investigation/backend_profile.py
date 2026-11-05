"""Freeze a local validation backend without exporting credentials or its URL."""
import hashlib
from urllib.parse import urlsplit

BACKENDS = ("deepseek", "deployed")
SCHEMA = "socai2.local-model-profile.v1"
DEEPSEEK_DEFAULTS = {"OPENAI_MODEL": "deepseek-flash", "OPENAI_BASE_URL": "https://api.deepseek.com",
    "SOCAI2_MODEL_PROTOCOL": "deepseek_responses", "SOCAI2_MODEL_SCHEMA_PROFILE": "standard"}


class ModelProfileMismatch(ValueError):
    """Safe diagnostic code; never includes configured values."""


def freeze(values, backend="deepseek"):
    if backend not in BACKENDS:
        raise ModelProfileMismatch("unsupported_validation_backend")
    model = values.get("OPENAI_MODEL", "").strip()
    protocol = values.get("SOCAI2_MODEL_PROTOCOL", "")
    profile = values.get("SOCAI2_MODEL_SCHEMA_PROFILE", "")
    base = values.get("OPENAI_BASE_URL", "").strip().rstrip("/")
    try:
        url = urlsplit(base)
        valid = url.scheme in {"http", "https"} and bool(url.hostname) and url.port != 0
    except ValueError:
        valid = False
    if not valid or url.username or url.password or url.query or url.fragment:
        raise ModelProfileMismatch("model_base_url_must_be_plain_http_endpoint")
    if not model or len(model) > 200 or any(ord(c) < 32 for c in model):
        raise ModelProfileMismatch("invalid_validation_model_name")
    if protocol not in {"chat_completions", "deepseek_responses"} or profile not in {"standard", "vllm_grammar_v1"}:
        raise ModelProfileMismatch("unsupported_validation_model_contract")
    if backend == "deepseek" and (base, model, protocol, profile) != (
            "https://api.deepseek.com", "deepseek-flash", "deepseek_responses", "standard"):
        raise ModelProfileMismatch("deepseek_backend_configuration_mismatch")
    if backend == "deployed" and protocol != "chat_completions":
        raise ModelProfileMismatch("deployed_backend_requires_chat_completions")
    # Authentication is deliberately absent, including any key fingerprint.
    return {"schema_version": SCHEMA, "backend": backend, "model": model, "protocol": protocol,
        "schema_profile": profile, "base_url_sha256": hashlib.sha256(base.encode()).hexdigest()}


def validate(plan, values):
    frozen = plan.get("model_profile")
    if frozen is None:
        if plan["case"].get("backend") != "deepseek":
            raise ModelProfileMismatch("legacy_plan_only_supports_original_deepseek")
        # Old plans have no endpoint fingerprint. Their sole allowed profile
        # remains the original official DeepSeek configuration, never inferred.
        return {**freeze(values), "compatibility": "legacy_deepseek_only"}
    if not isinstance(frozen, dict) or frozen.get("schema_version") != SCHEMA:
        raise ModelProfileMismatch("invalid_frozen_model_profile")
    if plan["case"].get("backend") != frozen.get("backend"):
        raise ModelProfileMismatch("case_backend_does_not_match_frozen_profile")
    current = freeze(values, frozen["backend"])
    if current != frozen:
        raise ModelProfileMismatch("model_configuration_changed_after_plan_freeze_new_batch_required")
    return {**current, "compatibility": "frozen_local_configuration"}
