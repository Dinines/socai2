"""Bounded source snapshots and a separate model input view."""
import hashlib
import json

from app.services.llm_safety import classify_message

SOURCE_SCHEMA = "case.source-material.v1"
DESCRIPTION_BYTES = 4096
RAW_BYTES = 16384
RUN_BYTES = 131072
MODEL_BYTES = 8192


def utf8_prefix(text: str, limit: int) -> str:
    # Valid UTF-8 input: only an incomplete final character can be omitted.
    return text.encode("utf-8")[:max(0, limit)].decode("utf-8", errors="ignore")


def _freeze(value, path, limit, remaining, *, json_value=False):
    text = (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            if json_value else value) if value is not None else None
    raw = text.encode("utf-8") if text is not None else b""
    retained = utf8_prefix(text, min(limit, remaining)) if text is not None else None
    retained_bytes = len(retained.encode("utf-8")) if retained is not None else 0
    truncated = retained_bytes < len(raw)
    field = {"source_path": path, "status": "missing" if value is None else "empty" if value in ("", {}, []) else "present",
             "encoding": "canonical_json_utf8" if json_value else "utf8",
             "sha256": hashlib.sha256(raw).hexdigest() if text is not None else None,
             "original_bytes": len(raw), "retained_bytes": retained_bytes, "text": retained,
             "truncated": truncated,
             "omission_reason": ("run_limit" if remaining < limit else "field_limit") if truncated else None,
             # Validate standalone source BEFORE nesting/clipping, so raw logs or
             # secrets cannot be encoded into an envelope to evade the guard.
             "model_blocked": bool(text is not None and classify_message(text))}
    return field, remaining - retained_bytes


def freeze_sources(case, alerts):
    description, remaining = _freeze(case.description, "Case.description", DESCRIPTION_BYTES, RUN_BYTES)
    sources = {}
    for alert in alerts:
        body, remaining = _freeze(alert.description, "Alert.description", DESCRIPTION_BYTES, remaining)
        raw, remaining = _freeze(alert.raw_event, "Alert.raw_event", RAW_BYTES, remaining, json_value=True)
        sources[str(alert.id)] = {"description": body, "raw_event": raw}
    return {"description": description}, sources


def _model_field(field, limit):
    text = "" if field["model_blocked"] else utf8_prefix(field["text"] or "", limit)
    size = len(text.encode("utf-8"))
    truncated = size < field["original_bytes"]
    reason = ("llm_input_contract" if field["model_blocked"] else field["omission_reason"]
              if size == field["retained_bytes"] else "model_limit") if truncated else None
    # Fingerprints and full retention metadata remain in the saved snapshot.
    return {"source_path": field["source_path"], "status": field["status"], "text": text if field["text"] is not None else None,
            "model_retained_bytes": size, "model_truncated": truncated, "model_omission_reason": reason}


def model_source_view(context):
    if context.get("source_material_schema") != SOURCE_SCHEMA:
        return context
    view = {**context}
    description = _model_field(context["case_material"]["description"], 1024)
    view["case_material"] = {"description": description}
    alerts = [item for item in context["evidence"] if item.get("kind") == "alert"]
    share = (MODEL_BYTES - description["model_retained_bytes"]) // max(1, len(alerts))
    view["evidence"] = []
    for item in context["evidence"]:
        if item.get("kind") == "alert":
            source = item["data"]["source_material"]
            body = _model_field(source["description"], min(1024, share))
            raw = _model_field(source["raw_event"], min(2048, share - body["model_retained_bytes"]))
            item = {**item, "data": {**item["data"], "source_material": {"description": body, "raw_event": raw}}}
        view["evidence"].append(item)
    return view


def source_fields(context):
    yield from context.get("case_material", {}).values()
    for item in context.get("evidence", []):
        if item.get("kind") == "alert":
            yield from item.get("data", {}).get("source_material", {}).values()
