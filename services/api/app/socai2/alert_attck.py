"""Validate AI ATT&CK mappings separately from the alert verdict."""

import json
from functools import cache
from pathlib import Path

from pydantic import Field, StrictStr, ValidationError

from .baseline_contracts import Contract, EvidenceRef
from .citation_quality import new_review

MAX_MAPPINGS = 8
FIELD = "attck_mappings"
CATALOG_VERSION = "enterprise-17.1"
BEHAVIOR_ROLES = {"observation", "human_statement"}
PROMPT = (
    "\n每次输出 attck_mappings 数组。按本轮实际行为证据映射 MITRE ATT&CK Enterprise 战术或技术。"
    "每项至少填写一个标准 ID，未知的 ID 填 null，evidence_ids 引用本轮直接观察或人工陈述。"
    "检测标注和历史判断只能参考。没有足够行为依据时返回空数组。待核实事项写入 recommendations。"
)


class MappingAnswer(Contract):
    tactic_id: str | None = Field(pattern=r"^TA[0-9]{4}$")
    technique_id: str | None = Field(pattern=r"^T[0-9]{4}(\.[0-9]{3})?$")
    evidence_ids: list[StrictStr] = Field(min_length=1, max_length=30)


class AlertAttckMapping(Contract):
    tactic_id: str | None
    tactic_name: str | None
    technique_id: str | None
    technique_name: str | None
    source_refs: list[EvidenceRef] = Field(min_length=1)


@cache
def catalog():
    path = Path(__file__).with_name("attck_data") / f"{CATALOG_VERSION}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def mapping_path(path):
    return path == "$." + FIELD or path.startswith("$." + FIELD + "[")


def receive(scanned, sources):
    # Use the same resolver as the other saved alert references. The existing
    # verdict parser and its delivery state do not depend on this optional result.
    from .ai_stage_delivery import references

    invalid = [unit for unit in scanned["invalid_units"] if mapping_path(unit["path"])]
    missing = [unit for unit in scanned["missing_units"] if mapping_path(unit["path"])]
    mappings = None
    for index, unit in enumerate(unit for unit in scanned["units"] if mapping_path(unit["path"])):
        path = unit["path"]
        if unit["kind"] == "empty_array":
            mappings = []
            break
        if index >= MAX_MAPPINGS:
            invalid.append({"path": path, "reason_code": "attck_mapping_limit_exceeded"})
            break
        try:
            taxonomy = catalog()
        except (OSError, json.JSONDecodeError):
            invalid.append({"path": path, "reason_code": "attck_catalog_unavailable"})
            break
        try:
            candidate = MappingAnswer.model_validate(unit["value"], strict=True)
            tactic, technique = candidate.tactic_id, candidate.technique_id
            tactic_name = taxonomy["tactics"].get(tactic)
            technique_entry = taxonomy["techniques"].get(technique)
            if (tactic is None and technique is None) or (tactic and not tactic_name) or (technique and not technique_entry):
                raise ValueError("attck_id_invalid")
            if tactic and technique_entry and tactic not in technique_entry["tactics"]:
                raise ValueError("attck_tactic_technique_mismatch")
            resolved = references(candidate.evidence_ids, sources, new_review(), path)
            if (len(resolved) != len(set(candidate.evidence_ids))
                    or any(item["ref"]["role"] not in BEHAVIOR_ROLES for item in resolved)):
                raise ValueError("attck_evidence_unavailable")
            mapping = AlertAttckMapping(tactic_id=tactic, tactic_name=tactic_name, technique_id=technique,
                technique_name=technique_entry["name"] if technique_entry else None,
                source_refs=[item["ref"] for item in resolved])
        except ValidationError:
            invalid.append({"path": path, "reason_code": "attck_mapping_shape_invalid"})
            continue
        except ValueError as exc:
            invalid.append({"path": path, "reason_code": str(exc)})
            continue
        if mappings is None:
            mappings = []
        mappings.append(mapping)
    return mappings, {"catalog_version": CATALOG_VERSION, "invalid_units": invalid, "missing_units": missing}
