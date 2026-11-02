"""Keep bounded lake material parseable and expose every storage omission."""
import hashlib
import json


def bounded_material(value, limit, *, structured=False):
    text = json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":")) if structured or isinstance(value, (dict, list)) else str(value if value is not None else "")
    data = text.encode("utf-8")
    metadata = {"truncated": len(data) > limit, "original_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if len(data) <= limit:
        return text, metadata
    # A preview is explicitly a string, never a broken JSON object presented
    # as the original. Allow worst-case JSON escaping inside the byte budget.
    preview = data[:max(0, (limit - 512) // 6)].decode("utf-8", errors="ignore")
    stored = json.dumps({"_socai2_storage": metadata, "preview": preview}, ensure_ascii=False, separators=(",", ":"))
    return stored, metadata
