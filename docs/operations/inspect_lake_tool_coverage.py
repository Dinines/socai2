"""Read-only lake coverage; actual results remain in private files pending review."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

MISSING = object()


def values_at(document, path):
    current = [document]
    for segment in path.split("."):
        array = segment.endswith("[]")
        name = segment[:-2] if array else segment
        following = []
        for value in current:
            child = value.get(name, MISSING) if isinstance(value, dict) else MISSING
            if array:
                following.extend(child if isinstance(child, list) else [MISSING])
            else:
                following.append(child)
        current = following
    return current


def kind(value):
    if value is MISSING:
        return "missing"
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if type(value) is int:
        return "integer"
    if isinstance(value, (float, Decimal)):
        return "number"
    return {str: "string", list: "array", dict: "object"}.get(type(value), "unsupported")


def nonempty(value):
    return value is not MISSING and value is not None and not (isinstance(value, (str, list, dict)) and not value)


def class_id(value):
    return value if type(value) is int and 0 <= value < 2**32 else None


def object_available(document):
    for parent in ("device", "src_endpoint", "dst_endpoint"):
        for key in ("hostname", "ip"):
            value = values_at(document, parent+"."+key)[0]
            if not isinstance(value, str):
                continue
            if key == "hostname" and re.fullmatch(r"[A-Za-z0-9_.-]{1,253}", value):
                return True
            if key == "ip":
                try:
                    address = ipaddress.ip_address(value)
                    address = address.ipv4_mapped or address if isinstance(address, ipaddress.IPv6Address) else address
                    if not address.is_unspecified:
                        return True
                except ValueError:
                    pass
    return False


class Coverage:
    def __init__(self, paths):
        self.paths = paths
        self.groups = {}
        self.unparseable = 0

    def add(self, document, *, reliable_time):
        if not isinstance(document, dict):
            self.unparseable += 1
            return
        partial = values_at(document, "unmapped.spirithub.mapping_status")[0] == "partial"
        stated = values_at(document, "unmapped.spirithub.classification.class_uid")[0]
        key = (class_id(document.get("class_uid")), class_id(stated) if partial else None, partial)
        group = self.groups.setdefault(key, {"records": 0, "fields": {}, "joint": Counter()})
        group["records"] += 1
        root_object = object_available(document)
        group["joint"]["root_object_and_reliable_event_time"] += bool(root_object and reliable_time)
        fallback = values_at(document, "unmapped.spirithub.partial_fields")[0]
        group["joint"]["partial_object_and_reliable_event_time"] += bool(partial and object_available(fallback) and reliable_time)
        for prefix in ("", "unmapped.spirithub.partial_fields."):
            if prefix and not partial:
                continue
            for path in self.paths:
                values = values_at(document, prefix+path)
                types = {kind(value) for value in values} or {"missing"}
                entry = group["fields"].setdefault(prefix+path, {"types": Counter(), "nonempty_records": 0})
                entry["types"].update(types)
                entry["nonempty_records"] += any(nonempty(value) for value in values)

    def reports(self):
        private, review = [], []
        for (root, stated, partial), group in sorted(self.groups.items(), key=lambda item: str(item[0])):
            identity = {"class_uid": root, "declared_partial_class_uid": stated, "has_partial_declaration": partial}
            private.append({**identity, **group})
            fields = [{"path": path, "observed_types": sorted(t for t in field["types"] if t != "missing"),
                       "has_nonempty_value": field["nonempty_records"] > 0}
                      for path, field in sorted(group["fields"].items()) if set(field["types"]) != {"missing"}]
            review.append({**identity, "fields": fields,
                "same_record_conditions": {name: count > 0 for name, count in sorted(group["joint"].items())}})
        return ({"groups": private, "unparseable_records": self.unparseable},
                {"schema_version": "socai2.lake-tool-coverage-review.v1", "groups": review,
                 "requires_user_review_before_codex": True,
                 "notes": ["declared_partial_class_is_not_validated_classification",
                           "field_presence_is_not_semantic_validity",
                           "same_record_conditions_do_not_prove_alert_binding_or_index_projection",
                           "unlisted_fields_are_outside_the_allowlist_or_not_observed"]})


def save(path, body):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(body, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def review_markdown(review):
    lines = ["# 湖取证工具最小覆盖待审清单", "", "待您审阅确认后，才能提供给本次 Codex 使用。",
             "仅列类别、白名单字段路径/类型和可用性，不含数量、正文、具体对象或时间。",
             "partial 声明不等于已验证分类；有字段不等于语义有效；未列字段可能未观察到或不在白名单内。", ""]
    for group in review["groups"]:
        lines += [f"## 根 class_uid={group['class_uid']}；partial 声明类={group['declared_partial_class_uid']}", ""]
        for name, present in group["same_record_conditions"].items():
            label = {"root_object_and_reliable_event_time": "同条记录具备根对象和可靠事件时间",
                     "partial_object_and_reliable_event_time": "同条记录具备 partial 对象和可靠事件时间"}[name]
            lines.append(f"- {label}：{'存在' if present else '未观察到'}（未证明已生成告警绑定或索引列）")
        lines += ["", "| 字段路径 | 观察到的JSON类型 | 非空值 |", "| --- | --- | --- |"]
        for field in group["fields"]:
            lines.append(f"| `{field['path']}` | {', '.join(field['observed_types'])} | {'存在' if field['has_nonempty_value'] else '未观察到'} |")
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.profile).read_text())
    root = Path(config["output_directory"])
    os.umask(0o077)
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    client, passed = None, False
    try:
        from app.services.lake_alert_delivery import LakeDeliverySource
        from app.services.lake_alert_selection import SelectionPolicy
        from app.services.lake_ingress import decode
        from clickhouse_driver import Client

        selection = SelectionPolicy.load(config["selection_file"])
        connection = json.loads(Path(config["connection_file"]).read_text())["clickhouse"]
        if connection["database"] != selection.body["database"]:
            raise ValueError("coverage_database_mismatch")
        limits = selection.body["read_limits"]
        client = Client(**connection, disable_reconnect=True, connect_timeout=limits["connect_timeout_seconds"],
                        send_receive_timeout=limits["send_receive_timeout_seconds"])
        rows = LakeDeliverySource(client, selection)._scan()
        if not rows:
            raise ValueError("coverage_scope_empty")
        coverage = Coverage(config["field_paths"])
        for row in rows:
            document, _, _, version = decode(row["ocsf_json"].encode())
            if document is not None and version != row["source_version"]:
                raise ValueError("coverage_original_version_mismatch")
            coverage.add(document, reliable_time=row["event_time_source"] == "ocsf_time_ms")
        private, review = coverage.reports()
        save(root/"coverage-private.json", private)
        save(root/"coverage-review.json", review)
        with (root/"coverage-review.md").open("x") as handle:
            handle.write(review_markdown(review))
        passed = (json.loads((root/"coverage-private.json").read_text()) == private
                  and json.loads((root/"coverage-review.json").read_text()) == review)
        if not passed:
            raise ValueError("coverage_readback_mismatch")
    except Exception as exc:  # noqa: BLE001 -- errors stay private and contain no source samples.
        save(root/"failure.json", {"exception_type": type(exc).__name__})
    finally:
        if client:
            client.disconnect()
    status = {"execution": "completed" if passed else "incomplete", "validation": "passed" if passed else "not_passed",
              "private_report_saved": (root/"coverage-private.json").exists(), "review_file_saved": (root/"coverage-review.json").exists()}
    save(root/"status.json", status)
    print(json.dumps(status))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
