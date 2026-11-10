"""Configured A text input and five-field output, retaining the original storage contract."""
from . import alert_basic_contract as legacy
from .alert_input_text import prepare
from .baseline_model_view import blocked, draft_limit
from .baseline_store import StoreError, digest, encoded


def build(source, input_id, queries, profile, *, execution_time=None):
    _, source_map, data = legacy.build(source, input_id, queries, execution_time=execution_time, complete_material=True)
    cfg = profile.config
    raw = (source["members"][0].get("material") or {}).get("raw_json")
    data["raw_alert_envelope"] = isinstance(raw, dict) and all(
        type(raw.get(key)).__name__ == kind for key, kind in cfg["render"]["raw_alert_envelope"]["required_fields"].items())
    data["prose_alias_format"] = cfg["output_validation"]["prose_alias_format"]
    prepared = prepare(data, source_map, cfg)
    messages = [{"role": "system", "content": cfg["system_prompt"]}, {"role": "user", "content": prepared["user"]}]
    if not prepared["source_map"] or blocked(messages) or len(encoded(messages)) > draft_limit():
        raise StoreError("alert_model_view_unavailable", 422)
    # The full frozen input stays in its source artifact; the request records
    # only the omission addresses/hashes and the actually visible aliases.
    prepared["boundary"] = {"version": profile.version, "profile_sha256": profile.sha256,
        "render_revision": cfg["render"]["revision"], "output_validation": cfg["output_validation"],
        "structural_omissions": [{k: v for k, v in entry.items() if k != "original"}
            | ({"value_sha256": digest(entry["original"])} if "original" in entry else {}) for entry in prepared["omissions"]]}
    return messages, prepared["source_map"], prepared["data"], prepared
