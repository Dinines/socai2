"""Offline JSON structure audit. Data-derived output is private until user review."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from app.services.lake_ingress import ABSENT, BLOCKED, epoch_time, nested, tagged
from export_opensearch_target_json import file_hash, loads, require
from inspect_lake_tool_coverage import kind

PARTIAL = "unmapped.spirithub.partial_fields."


def at(document, path):
    return nested(document, tuple(path.split(".")))


def is_partial(document):
    return at(document, "unmapped.spirithub.mapping_status") == "partial"


def resolve(document, path):
    """No coercion; explicit null/empty/invalid ancestors block fallback."""
    root = at(document, path)
    fallback = at(document, PARTIAL + path) if is_partial(document) else ABSENT
    if root is not ABSENT:
        conflict = (fallback is not ABSENT and fallback is not BLOCKED
                    and (root is BLOCKED or tagged(root) != tagged(fallback)))
        return root, "root", conflict
    return fallback, "partial" if fallback is not ABSENT else "absent", False


def values(document, path, mode):
    """Choose an entire array once; never merge corresponding array elements."""
    parent, separator, tail = path.partition("[]")
    if mode == "effective":
        value, origin, conflict = resolve(document, parent if separator else path)
    else:
        value = at(document, (PARTIAL if mode == "partial" else "") + (parent if separator else path))
        if mode == "partial" and not is_partial(document):
            value = ABSENT
        origin, conflict = mode, False
    if not separator:
        return [value], origin, conflict
    if value is ABSENT or value is BLOCKED or value is None:
        return [value], origin, conflict
    if not isinstance(value, list):
        return [BLOCKED], origin, conflict
    if not value:
        return [], origin, conflict
    tail = tail.removeprefix(".")
    return [at(item, tail) if tail else item for item in value], origin, conflict


def state(value):
    if value is ABSENT:
        return "missing"
    if value is BLOCKED:
        return "ancestor_not_object"
    if value is None:
        return "null"
    if isinstance(value, (dict, list, str)) and not value:
        return "empty_" + kind(value)
    return kind(value)


def usable(value, rule):
    if value is ABSENT or value is BLOCKED or value is None:
        return False
    if kind(value) != rule["type"]:
        return False
    if isinstance(value, (dict, list, str)) and not value:
        return False
    semantic = rule.get("semantic")
    if semantic == "ip":
        try:
            return not ipaddress.ip_address(value).is_unspecified
        except ValueError:
            return False
    if semantic == "hostname":
        return re.fullmatch(r"[A-Za-z0-9_.-]{1,253}", value) is not None
    if semantic == "port":
        return 0 <= value <= 65535
    if semantic == "time":
        return epoch_time(value)[1] == "ocsf_time_ms"
    if semantic == "nonblank":
        return bool(value.strip())
    if semantic == "unsigned":
        return value >= 0
    return True


def classification(document, targets):
    root = document.get("class_uid")
    partial = is_partial(document)
    stated = at(document, "unmapped.spirithub.classification.class_uid")
    identity = {
        "root_class_uid": root if type(root) is int and root in targets else "outside_scope_or_invalid",
        "declared_class_uid": (stated if type(stated) is int and stated in targets
                               else "outside_scope_or_missing") if partial else None,
        "partial": partial,
    }
    if type(root) is not int or root not in targets:
        return identity, None, "invalid_root_class"
    if partial and root != 0 and stated is not ABSENT and (type(stated) is not int or stated != root):
        return identity, None, "conflicting_class_declaration"
    source = at(document, "unmapped.spirithub.classification") if root == 0 and partial else document
    cls = source.get("class_uid") if isinstance(source, dict) else None
    if type(cls) is not int or cls == 0 or cls not in targets:
        return identity, None, "unclassified_or_outside_scope"
    category, activity, typ = (source.get(k) for k in ("category_uid", "activity_id", "type_uid"))
    if (not all(type(v) is int for v in (category, activity, typ)) or category != cls // 1000
            or not 0 <= activity <= 99 or typ != cls * 100 + activity):
        return identity, None, "inconsistent_class_arithmetic"
    return identity, cls, "class_arithmetic_consistent"


def coverage(count, total):
    return "none" if count == 0 else "all" if count == total else "some"


def inventory(document, prefix=""):
    """Unrestricted key names stay only in the private inventory, never in review."""
    result = defaultdict(set)

    def walk(value, path):
        result[path or "$"].add(kind(value))
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, path + "." + key if path else key)
        elif isinstance(value, list):
            for child in value:
                walk(child, path + "[]")

    walk(document, prefix)
    return result


class Audit:
    def __init__(self, profile):
        self.profile = profile
        self.groups = {}
        self.total = 0

    def add(self, document):
        require(isinstance(document, dict), "ocsf_object_required")
        identity, cls, class_state = classification(document, self.profile["target_class_uids"])
        key = json.dumps(identity, sort_keys=True)
        group = self.groups.setdefault(key, {"identity": identity, "records": 0,
            "classification": Counter(), "fields": {}, "arrays": {}, "joint": Counter(), "inventory": {}})
        group["records"] += 1
        self.total += 1
        group["classification"][class_state] += 1
        usable_by_mode = {mode: {} for mode in ("root", "partial", "effective")}
        for path, rule in self.profile["fields"].items():
            field = group["fields"].setdefault(path, {mode: {"states": Counter(), "usable_records": 0}
                for mode in ("root", "partial", "effective")})
            field.setdefault("origins", Counter())
            field.setdefault("conflicts", 0)
            for mode, mode_fields in usable_by_mode.items():
                found, origin, conflict = values(document, path, mode)
                field[mode]["states"].update({state(v) for v in found} or {"empty_parent_array"})
                good = any(usable(v, rule) for v in found) and not conflict
                mode_fields[path] = good
                field[mode]["usable_records"] += good
                if mode == "effective":
                    field["origins"][origin] += 1
                    field["conflicts"] += conflict
        for path, pairs in self.profile["arrays"].items():
            array = group["arrays"].setdefault(path, {"element_types": Counter(), "shapes": Counter(),
                "same_element": Counter()})
            value, _, conflict = resolve(document, path)
            array["shapes"][state(value)] += 1
            if not isinstance(value, list):
                continue
            types = {kind(v) for v in value}
            array["element_types"].update(types)
            array["shapes"]["mixed_element_types"] += len(types) > 1
            array["shapes"]["non_object_element"] += any(not isinstance(v, dict) for v in value)
            for pair in pairs:
                name = " + ".join(pair)
                array["same_element"][name] += not conflict and any(
                    all(usable(at(item, child), self.profile["fields"][path + "[]." + child]) for child in pair)
                    for item in value if isinstance(item, dict))
        for path, types in inventory(document).items():
            group["inventory"].setdefault(path, Counter()).update(types)
        identity_ok = usable(at(document, "metadata.uid"), self.profile["fields"]["metadata.uid"])
        time_ok = usable(at(document, "time"), self.profile["fields"]["time"])
        version_ok = at(document, "metadata.version") == self.profile["ocsf_version"]
        group["joint"]["root_identity"] += identity_ok
        group["joint"]["root_event_time"] += time_ok
        group["joint"]["supported_ocsf_version"] += version_ok
        for mode in ("root", "effective"):
            usable_fields = usable_by_mode[mode]
            object_ok = any(usable_fields[p] for p in self.profile["object_paths"])
            group["joint"][mode + "_object_and_root_time"] += object_ok and time_ok
            for target, candidate in self.profile["candidates"].items():
                # Each candidate clause is OR; clauses are AND, in this same record.
                business_ok = all(any(usable_fields[p] for p in clause) for clause in candidate["minimum"])
                core = cls == int(target) and identity_ok and version_ok and business_ok
                group["joint"][candidate["tool"] + ":" + mode + "_material_prerequisites"] += core
                group["joint"][candidate["tool"] + ":" + mode + "_query_prerequisites"] += core and object_ok and time_ok

    def reports(self):
        groups = []
        for group in self.groups.values():
            total = group["records"]
            fields = []
            for path, field in group["fields"].items():
                fields.append({"path": path, "expected_type": self.profile["fields"][path]["type"],
                    "modes": {mode: {"states": {k: coverage(v, total) for k, v in field[mode]["states"].items()},
                                      "usable": coverage(field[mode]["usable_records"], total)}
                              for mode in ("root", "partial", "effective")},
                    "origins": {k: coverage(v, total) for k, v in field["origins"].items()},
                    "conflicts": coverage(field["conflicts"], total)})
            groups.append({**group["identity"], "classification": {k: coverage(v, total) for k, v in group["classification"].items()},
                "fields": fields,
                "arrays": {path: {"element_types": sorted(a["element_types"]),
                    "shapes": {k: coverage(v, total) for k, v in a["shapes"].items()},
                    "same_element": {k: coverage(v, total) for k, v in a["same_element"].items()}}
                    for path, a in group["arrays"].items()},
                "same_record": {k: coverage(v, total) for k, v in group["joint"].items()}})
        review = {"schema_version": "socai2.json-structure-review.v1", "requires_user_review_before_codex": True,
            "groups": groups, "notes": ["class_arithmetic_is_not_full_ocsf_schema_validation",
                "prerequisites_are_not_proof_of_lake_projection_or_frozen_case_binding",
                "not_observed_means_only_this_exported_snapshot", "unlisted_dynamic_keys_remain_private",
                "some_all_none_are_record_coverage_not_business_judgments"]}
        private = {"records": self.total, "groups": list(self.groups.values())}
        return private, review


def review_markdown(review, profile):
    lines = ["# JSON 结构审计待审报告", "", "请先审阅。确认脱敏并允许后，才向本次 Codex 提供这份报告及同名 JSON。",
        "只含类别、约定字段/类型、缺失与冲突形态、同条记录/数组元素可用性；无数量、正文、对象值、ID、时间或数据摘要。",
        "all / some / none 表示本组记录全部 / 部分 / 未观察到。可用性只是结构前提；未执行 ClickHouse 查询，未验证冻结 Case 绑定。",
        "类别只检查 class/category/activity/type 算式，未进行完整 OCSF Schema 校验。未覆盖类别不等于上游永远不会发送。", ""]
    for group in review["groups"]:
        lines += [f"## 根类 {group['root_class_uid']} / partial 声明 {group['declared_class_uid']}", "",
            "分类检查：" + json.dumps(group["classification"], ensure_ascii=False), "",
            "### 同记录查询前提", "", "| 条件 | 覆盖 |", "| --- | --- |"]
        lines += [f"| `{key}` | {value} |" for key, value in group["same_record"].items()
                  if ":" not in key or value != "none"]
        lines += ["", "### 可观察字段及必须核对的缺项", "",
            "root / partial / effective 分别为根路径、partial 对应路径、严格选择后的结果。冲突字段暂不算可用。",
            "null、空值、祖先不是对象不会用 partial 掩盖；空数组也不会从另一来源补元素。", "",
            "| 路径 | 预期类型 | root 状态 | partial 状态 | effective 可用 | 冲突 |", "| --- | --- | --- | --- | --- | --- |"]
        cls = group["declared_class_uid"] if group["root_class_uid"] == 0 else group["root_class_uid"]
        candidate = profile["candidates"].get(str(cls), {})
        needed = {"metadata.uid", "metadata.version", "class_uid", "category_uid", "activity_id", "type_uid", "time", *profile["object_paths"]}
        needed.update(p for clause in candidate.get("minimum", []) for p in clause)
        for field in group["fields"]:
            modes = field["modes"]
            observed = any(set(modes[m]["states"]) - {"missing"} for m in ("root", "partial"))
            if not observed and field["path"] not in needed:
                continue
            shown = {mode: "; ".join(f"{k}:{v}" for k, v in modes[mode]["states"].items()) for mode in ("root", "partial")}
            lines.append(f"| `{field['path']}` | {field['expected_type']} | {shown['root']} | {shown['partial']} | {modes['effective']['usable']} | {field['conflicts']} |")
        lines += ["", "### 数组元素关系", "", "| 数组 | 元素类型 | 形态 | 同元素字段可用 |", "| --- | --- | --- | --- |"]
        for path, array in group["arrays"].items():
            if set(array["shapes"]) == {"missing"}:
                continue
            lines.append(f"| `{path}` | {', '.join(array['element_types'])} | {json.dumps(array['shapes'])} | {json.dumps(array['same_element'])} |")
        lines.append("")
    lines += ["## 选择工具的固定判据", "",
        "已有工具具备结构前提时优先复用或修投影；新的活动工具只有同条记录同时具备可靠根时间、对象及业务字段才接入。",
        "Finding 只作为上游发现材料；数组中的进程/网络描述不会自动成为独立活动记录。",
        "只有 material_prerequisites 而没有 query_prerequisites 时，考虑冻结原文定点读取，不开放全来源时间范围扫描。",
        "具体工具需要审阅本报告后结合业务用途确定，程序不按数量自动宣布优先级。", ""]
    return "\n".join(lines)


def save(path, body):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(body, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def run(profile):
    os.umask(0o077)
    output = Path(profile["output_directory"])
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    passed = False
    try:
        root = Path(profile["input_directory"])
        manifest = loads((root / "manifest.json").read_text())
        expected = manifest["files"]["ocsf.ndjson"]
        original = root / "ocsf.ndjson"
        before = file_hash(original)
        require(before == expected["sha256"] and original.stat().st_size == expected["bytes"], "input_integrity_mismatch")
        require(set(manifest["target_class_uids"]) == set(profile["target_class_uids"]), "input_scope_mismatch")
        audit = Audit(profile)
        with original.open() as handle:
            for line in handle:
                require(line.endswith("\n"), "incomplete_input_line")
                audit.add(loads(line))
        require(audit.total == manifest["snapshot_total"], "input_count_mismatch")
        require(file_hash(original) == before, "input_changed_during_audit")
        private, review = audit.reports()
        save(output / "structure-private.json", private)
        save(output / "structure-review.json", review)
        markdown = review_markdown(review, profile)
        with (output / "structure-review.md").open("x") as handle:
            handle.write(markdown)
        require(json.loads((output / "structure-private.json").read_text()) == private, "private_readback_mismatch")
        require(json.loads((output / "structure-review.json").read_text()) == review, "review_readback_mismatch")
        require((output / "structure-review.md").read_text() == markdown, "markdown_readback_mismatch")
        passed = True
    except Exception as exc:  # noqa: BLE001 -- raw exception text may contain data.
        save(output / "failure.json", {"exception_type": type(exc).__name__})
    status = {"execution": "completed" if passed else "incomplete", "validation": "passed" if passed else "not_passed",
        "input_verified_and_unchanged": passed, "full_snapshot_scanned": passed, "reports_saved_and_read_back": passed,
        "actual_query_executed": False, "data_report_disclosed_to_codex": False}
    save(output / "status.json", status)
    print(json.dumps(status))
    return 0 if passed else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    raise SystemExit(run(json.loads(Path(args.profile).read_text())))
