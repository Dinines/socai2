"""Bounded diagnostics for A/I contracts; no inference repair or truth guarantee."""
import re

from .baseline_store import StoreError
from .model_input_view import items

SOURCE_TOKEN = r"(?<![A-Za-z0-9_])(?:N[1-9][0-9]*_)?S[1-9][0-9]*(?![A-Za-z0-9_])"


def literal_source_name(sid, data, owned=None):
    """Only an exact received name, never a phrase in a prior model answer."""
    for item in items(data):
        if owned is not None and (not item.get("alert_ids") or not set(item["alert_ids"]) <= set(owned)):
            continue
        if item.get("role") not in {"observation", "source_label"}:
            continue
        field = item.get("field", "")
        if not field.endswith((".name", ".hostname", ".username", ".user_name", ".host_name")):
            continue
        value = item.get("value")
        if value == sid or isinstance(value, dict) and len(value) == 1 and sid in value.values():
            return True
    return False


class Checks:
    def __init__(self, diagnostics=None):
        self.entries = diagnostics if diagnostics is not None else []
        self.first_error = None

    def add(self, code, path, category="source", severity="error", check_state="failed"):
        if severity == "error" and self.first_error is None:
            self.first_error = code
        if len(self.entries) < 64:
            self.entries.append({"code": code, "path": path, "category": category,
                "severity": severity, "check_state": check_state})

    def require(self, condition, code, path, category="source"):
        if not condition:
            self.add(code, path, category)
        return condition

    def finish(self):
        if self.first_error:
            raise StoreError(self.first_error, 422)

    def prose(self, text, path, permitted, source_map, data, prefix, *, owned=None):
        for sid in sorted(set(re.findall(SOURCE_TOKEN, text))):
            if literal_source_name(sid, data, owned):
                continue
            if sid not in source_map:
                self.add(prefix + "_prose_source_unbound", path)
            elif owned is not None and (not source_map[sid].get("alert_ids") or
                    not set(source_map[sid]["alert_ids"]) <= set(owned)):
                self.add(prefix + "_prose_source_wrong_member", path, "scope")
            elif data.get("citations") == "structured_v3":
                # Structured arrays are authoritative. Do not infer/add a source
                # from prose, and do not invalidate an otherwise sound array
                # because the model redundantly mentioned a visible local ID.
                code = "source_alias_in_prose" if sid in permitted else "inline_source_not_structured_evidence"
                self.add(code, path, "presentation", "warning", "observed")
            elif sid not in permitted:
                self.add(prefix + "_prose_source_unbound", path)
            else:
                self.add("source_alias_in_prose", path, "presentation", "warning", "observed")
