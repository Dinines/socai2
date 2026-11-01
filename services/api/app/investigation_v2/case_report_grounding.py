"""Narrow PID/account checks against cited source fields, not a semantic score."""
import json
import re


_PID = re.compile(r"(?<![A-Za-z0-9_])(?:PID|进程(?:ID|编号|号))\s*[:：=]?\s*(\d+)(?![A-Za-z0-9_])", re.I)
_USER = re.compile(r"(?:\buser(?:name)?\s+|(?:用户|账号|账户)\s*[:：]?\s*)[\"'“‘]?([A-Za-z0-9_][A-Za-z0-9_.@\\-]*)", re.I)
_UNDER_USER = re.compile(r"\bunder\s+([A-Za-z0-9_][A-Za-z0-9_.@\\-]*)", re.I)
_TOOL_CLAIM = re.compile(r"(?:由|经)?(?:工具|Tool)(?:结果)?(?:直接|独立)?(?:显示|记录|证实|确认|验证|核实|体现)|直接观察[：:]", re.I)
_NEGATIVE = re.compile(r"(?:未|不|非|不能|无法|尚未|未能|不是)\s*$")
_PID_FIELDS = {"pid", "process_id", "parent_pid", "child_pid", "parent_process_id"}
_USER_FIELDS = {"user_name", "username", "user", "account_name"}
_EMPTY_CAUSE = re.compile(r"(?:无|未|没有)(?:数据|历史数据|记录|日志)?(?:被)?(?:接入|采集|捕获)"
                         r"|(?:记录|日志)(?:已被|被|已经|已)?(?:清洗|丢失|阻断)"
                         r"|查询范围不匹配|(?:因|由于|可能)[^。；;，,\n]{0,12}(?:采样|丢日志|清洗|丢失)")
_CAUSE_UNCERTAIN = re.compile(r"(?:是否|不能(?:说明|证明)|不代表|不足以证明|无法确认|未能证实)[^。；;，,\n]{0,12}$")


def _identities(text, *, source=False):
    for match in _PID.finditer(text):
        yield "pid", str(int(match[1]))
    patterns = (_USER, _UNDER_USER) if source else (_USER,)
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = match[1].rstrip(".")
            # English field descriptions are not named accounts.
            if value.lower() not in {"name", "account", "activity", "context"}:
                yield "user", value


def _source_identities(item):
    """Keep field provenance; titles, saved judgments and query metadata are excluded."""
    found = {"pid": {}, "user": {}}

    def add(kind, value, path):
        found[kind].setdefault(value, set()).add(path)

    def fields(value, path, *, source_text=False):
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in _PID_FIELDS and isinstance(child, (int, str)) and not isinstance(child, bool) and str(child).isdigit():
                    add("pid", str(int(child)), child_path)
                if key in _USER_FIELDS and isinstance(child, str) and child:
                    add("user", child, child_path)
                fields(child, child_path, source_text=source_text)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                fields(child, f"{path}[{index}]", source_text=source_text)
        elif source_text and isinstance(value, str):
            for kind, identity in _identities(value, source=True):
                add(kind, identity, path)

    if item.get("kind") == "alert":
        data = item["data"]
        for name in ("description", "raw_event"):
            field = data.get("source_material", {}).get(name, {})
            text = field.get("text")
            if not isinstance(text, str) or field.get("model_blocked"):
                continue
            path = f"data.source_material.{name}"
            if name == "raw_event":
                try:
                    fields(json.loads(text), path, source_text=True)
                    continue
                except ValueError:
                    pass
            for kind, value in _identities(text, source=True):
                add(kind, value, path)
        for index, entity in enumerate(data.get("entities", [])):
            if entity.get("type") == "user" and isinstance(entity.get("value"), str):
                add("user", entity["value"], f"data.entities[{index}].value")
    elif item.get("kind") == "tool" and item.get("available") is True:
        fields(item.get("rows", []), "rows")
    return found


def source_value_errors(report, evidence):
    """Check explicit identity mentions. Passing does not establish causality or intent."""
    sources = {item["evidence_id"]: item for item in evidence}
    identities = {ref: _source_identities(item) for ref, item in sources.items()}
    texts = [(["summary"], report["summary"], list(sources))]
    for section, field in (("findings", "text"), ("member_assessments", "summary"), ("relationships", "basis")):
        texts.extend(([section, index, field], item[field], item["evidence_ids"])
                     for index, item in enumerate(report[section]))
    errors = []
    for location, text, refs in texts:
        for clause in re.split(r"[。；;，,\n]", text):
            tool_claim = any(not _NEGATIVE.search(clause[:m.start()]) for m in _TOOL_CLAIM.finditer(clause))
            candidates = [ref for ref in refs if ref in sources
                          and (not tool_claim or sources[ref].get("kind") == "tool")]
            for kind, value in dict.fromkeys(_identities(clause)):
                support = {}
                for ref in candidates:
                    for v, paths in identities[ref][kind].items():
                        support.setdefault(v, []).extend(f"{ref}.{path}" for path in sorted(paths))
                if value not in support:
                    error = {"location": location, "type": "unsupported_source_value", "kind": kind, "value": value,
                             "evidence_ids": candidates, "supported_source_fields": support}
                    if error not in errors:
                        errors.append(error)
    return errors


def empty_query_cause_errors(report, evidence):
    """Reject the observed r10/r12 invented causes; this is not a general text judge."""
    empty = {e["evidence_id"] for e in evidence if e.get("kind") == "tool" and e.get("available") is True
             and e.get("tool") in {"process_activity", "network_connections"} and not e.get("rows")}
    if not empty:
        return []
    texts = [(["summary"], report["summary"], False)]
    for section, field in (("findings", "text"), ("member_assessments", "summary"), ("relationships", "basis")):
        texts.extend(([section, index, field], item[field], True) for index, item in enumerate(report[section])
                     if empty.intersection(item["evidence_ids"]))
    texts.extend(([section, index], text, False) for section in ("gaps", "counterevidence")
                 for index, text in enumerate(report[section]))
    errors = []
    for location, text, cited_empty in texts:
        if not cited_empty and not re.search(r"查询|空结果|0\s*行|事件湖|工具", text):
            continue  # An unrelated data source's availability is not an empty-query cause.
        for clause in re.split(r"[。；;，,\n]|但是|然而|但|却|而是", text):
            unsupported = False
            for match in _EMPTY_CAUSE.finditer(clause):
                qualifier = _CAUSE_UNCERTAIN.search(clause[:match.start()])
                if qualifier is None or _NEGATIVE.search(clause[:qualifier.start()]):
                    unsupported = True
                    break
            if unsupported:
                errors.append({"location": location, "type": "unsupported_empty_query_cause"})
                break
    return errors
