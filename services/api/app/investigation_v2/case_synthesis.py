"""Scoped multi-alert judgments and a timeline derived from saved evidence."""
from collections import Counter
from datetime import UTC, datetime
import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from .case_navigation import citation_links, evidence_url


class MemberAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alert_id: UUID
    status: Literal["addressed", "unresolved"]
    role: Literal["supporting", "background", "undetermined"]
    summary: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1)


class AlertRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alert_ids: list[UUID] = Field(min_length=2)
    kind: Literal["shared_context", "behavioral_link", "contradiction"]
    assessment: Literal["supported", "hypothesis", "not_supported"]
    basis: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(min_length=1)


class OpenQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)
    alert_ids: list[UUID] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence: str = Field(min_length=1, max_length=2000)
    suggested_action: str = Field(default="", max_length=2000)


OUTPUT_INSTRUCTIONS = """
同时输出以下数组，无对应内容时返回空数组：
member_assessments: [{alert_id,status,role,summary,evidence_ids}]。
逐个评估选定且可读成员，每条仅一项；status为addressed（给出判断）或unresolved（尚未判断清楚）；
role为supporting（支持本次发现）、background（当前作为背景）或undetermined。每项引用自身A类告警编号及采用的其他证据。
addressed不表示攻击已证实或告警已解决；background不表示安全或已证明无关。读不到材料的成员不要编造判断。
relationships: [{alert_ids,kind,assessment,basis,evidence_ids}]。
每项至少两条选定告警，引用每条参与告警的A编号及采用的其他证据；kind为shared_context（共同实体/时间）、
behavioral_link（行为联系）或contradiction（证据矛盾）；assessment为supported、hypothesis或not_supported。
共主机、账号、IP或时间接近只说明shared_context，不能直接当因果；行为联系需要说明直接证据与缺口。
只列有依据或明确待核的关联，不要求枚举所有组合。没有关联条目不等于已经证明互不相关。
open_questions: [{question,alert_ids,evidence_ids,missing_evidence,suggested_action}]。
明确未决问题影响哪些选定成员、已有何种依据、还缺什么、建议下一步；alert_ids为空表示本次全案。
unresolved成员、hypothesis关联需有对应未决问题。不得引用范围外成员或不存在的证据。
时间线由程序从A和E的原始时间字段生成，不在JSON中编造timeline或时间。
"""


def validate_synthesis(report, context, evidence):
    """Validate scope and references; this does not prove the model's interpretation."""
    selected = set(context["selected_member_ids"])
    known = {item["evidence_id"] for item in evidence}
    alerts = {item["data"]["alert_id"]: item["evidence_id"] for item in evidence if item["kind"] == "alert"}

    def references(item, members, *, own_alerts=False):
        if len(members) != len(set(members)) or not set(members).issubset(selected):
            raise ValueError("invalid_member_reference")
        if not set(item["evidence_ids"]).issubset(known):
            raise ValueError("unknown_evidence_reference")
        if own_alerts and any(alerts.get(member) not in item["evidence_ids"] for member in members):
            raise ValueError("missing_member_source_reference")

    assessed = []
    for item in report["member_assessments"]:
        references(item, [item["alert_id"]], own_alerts=True)
        assessed.append(item["alert_id"])
    if len(assessed) != len(set(assessed)):
        raise ValueError("duplicate_member_assessment")
    for item in report["relationships"]:
        references(item, item["alert_ids"], own_alerts=True)
    for item in report["open_questions"]:
        references(item, item["alert_ids"])

    # A port is not application-protocol evidence. Keep unverified protocol
    # names in gaps/questions, rather than accepting them in conclusion fields.
    network = [item for item in evidence if item.get("kind") == "tool" and item.get("tool") == "network_connections"]
    if network:
        network_rows = [row for item in network if item.get("available") is True for row in item.get("rows", [])]
        protocol = re.compile(r"(?<![A-Za-z0-9_])(HTTPS|TLS|SSL)(?:v?\d+(?:\.\d+)*)?(?![A-Za-z0-9_])", re.I)
        observed = {match.group(1).upper() for row in network_rows
                    if (match := protocol.fullmatch(str(row.get("protocol", "")).strip()))}
        conclusions = [report["summary"], *(item["text"] for item in report["findings"]),
                       *(item["summary"] for item in report["member_assessments"]),
                       *(item["basis"] for item in report["relationships"])]
        if any(match.group(1).upper() not in observed for text in conclusions for match in protocol.finditer(text)):
            raise ValueError("unobserved_application_protocol_use_gaps")
    if set(assessed) != set(context["read_member_ids"]):
        raise ValueError("missing_readable_member_assessment")


def _timestamp(value):
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC) if parsed.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def build_timeline(context, evidence):
    entries = []
    start, end = _timestamp(context["start"]), _timestamp(context["end"])
    alerts = {item["data"]["alert_id"]: item["data"] for item in evidence if item["kind"] == "alert"}

    def add(item, raw_time, kind, description, members, row_index=None, record_id=None):
        at = _timestamp(raw_time)
        entries.append({"timestamp": at.isoformat() if at else None,
            "source_time": str(raw_time) if raw_time is not None else None,
            "time_kind": kind, "in_window": start <= at < end if at and kind != "snapshot" else None,
            "description": description, "candidate_member_ids": sorted(members),
            "evidence_id": item["evidence_id"], "row_index": row_index, "source_record_id": record_id})

    for item in evidence:
        if item["kind"] == "alert":
            data = item["data"]
            add(item, data.get("event_time"), "alert", data["title"], [data["alert_id"]])
        elif item["kind"] == "tool" and item.get("available") is True:
            snapshot = item.get("query_scope", {}).get("time_semantics") == "current_snapshot"
            for index, row in enumerate(item.get("rows", [])):
                source_member = item.get("source", {}).get("source_alert_id")
                hostname = row.get("src_hostname") or item.get("query_scope", {}).get("hostname")
                members = ([source_member] if source_member in alerts else
                           [key for key, data in alerts.items() if hostname in data.get("hosts", [])])
                record_id = row.get("event_id") or row.get("device_id")
                if snapshot:
                    description = f"主机当前快照：{row.get('hostname') or hostname}"
                elif item.get("tool") == "network_connections":
                    description = f"{row.get('process_name') or '未知进程'}：{row.get('source_ip')} → {row.get('dest_ip')}:{row.get('dst_port')}"
                else:
                    description = f"进程：{row.get('process_name') or '未提供'}；路径：{row.get('file_path') or '未提供'}"
                add(item, item.get("observed_at") if snapshot else row.get("event_time"),
                    "snapshot" if snapshot else "event", description, members, index, record_id)
    return sorted(entries, key=lambda item: (item["timestamp"] is None, item["timestamp"] or ""))


def complete_synthesis(report, context, evidence):
    assessments = {item["alert_id"]: item for item in report["member_assessments"]}
    read = set(context["read_member_ids"])
    members, questions = [], report["open_questions"]

    def question_for(member_ids, question, missing, refs):
        if not any(not item["alert_ids"] or (member_ids and set(member_ids).issubset(item["alert_ids"])) for item in questions):
            questions.append({"question": question, "alert_ids": member_ids, "evidence_ids": refs,
                              "missing_evidence": missing, "suggested_action": "补充材料或明确问题后发起后续调查。"})

    for member_id in context["selected_member_ids"]:
        item = assessments.get(member_id)
        if member_id not in read or item is None:
            unavailable = member_id not in read
            item = {"alert_id": member_id, "status": "source_unavailable" if unavailable else "not_assessed",
                    "role": "undetermined", "summary": "未读取到成员材料" if unavailable else "模型未提供该成员的逐项判断",
                    "evidence_ids": []}
        members.append(item)
        if item["status"] != "addressed":
            report["gaps"].append(f"成员{member_id}：{item['summary']}")
            question_for([member_id], item["summary"], "可支持该成员判断的材料或明确分析", item["evidence_ids"])
    for relation in report["relationships"]:
        if relation["assessment"] == "hypothesis":
            report["gaps"].append(f"关联待核实：{relation['basis']}")
            question_for(relation["alert_ids"], f"该关联是否成立：{relation['basis']}",
                         "足以确认该关联的证据", relation["evidence_ids"])
    report["member_assessments"] = members
    counts = Counter(item["status"] for item in members)
    report["member_coverage"] = {"selected_count": len(members), "read_count": len(read),
        **{f"{key}_count": counts[key] for key in ("addressed", "unresolved", "not_assessed", "source_unavailable")}}
    report["timeline"] = build_timeline(context, evidence)
    unknown_time_refs = sorted({item["evidence_id"] for item in report["timeline"] if item["timestamp"] is None})
    if unknown_time_refs:
        report["gaps"].append("部分来源记录时间或时区未知，不能确认其时序。")
        question_for([], "哪些来源记录的发生时间尚需确认？", "来源发生时间及其时区", unknown_time_refs)
    report["gaps"].extend(f"未决问题：{item['question']}" for item in questions)
    report["gaps"] = list(dict.fromkeys(report["gaps"]))


def synthesis_markdown(report, case_id, run_id):
    coverage = report["member_coverage"]
    lines = ["", "## 成员覆盖与判断",
        f"选定{coverage['selected_count']}条，读取{coverage['read_count']}条；给出判断{coverage['addressed_count']}条，"
        f"尚未明确{coverage['unresolved_count']}条，未逐项分析{coverage['not_assessed_count']}条，材料不可读{coverage['source_unavailable_count']}条。",
        "给出判断不等于证实攻击或已解决；背景成员不等于已证明安全。"]
    for item in report["member_assessments"]:
        lines.append(f"- {item['alert_id']} [{item['status']}/{item['role']}]：{item['summary']}（依据：{citation_links(case_id, run_id, item['evidence_ids'])}）")
    lines.extend(["", "## 跨告警关联依据", "共同实体或时间接近不等于因果关系。"])
    for item in report["relationships"]:
        lines.append(f"- {', '.join(item['alert_ids'])} [{item['kind']}/{item['assessment']}]：{item['basis']}（依据：{citation_links(case_id, run_id, item['evidence_ids'])}）")
    if not report["relationships"]:
        lines.append("未给出明确关联条目，不代表已证明全部成员互不相关。")
    lines.extend(["", "## 来源时间线", "按来源时间排列；候选成员仅表示查询主机/来源范围的匹配，不证明因果。"])
    labels = {"alert": "告警时间", "event": "来源事件时间", "snapshot": "当前快照读取时间"}
    for item in report["timeline"]:
        location = f"{item['evidence_id']}" + (f"/rows/{item['row_index']}" if item["row_index"] is not None else "")
        location = f"[{location}]({evidence_url(case_id, run_id, item['evidence_id'], item['row_index'])})"
        outside = "，窗口外" if item["in_window"] is False else ""
        lines.append(f"- {item['timestamp'] or '时间未知'} [{labels[item['time_kind']]}{outside}]：{item['description']}"
                     f"（依据：{location}；来源记录：{item['source_record_id'] or '见原告警'}；候选成员：{', '.join(item['candidate_member_ids']) or '未匹配'}）")
    lines.extend(["", "## 未决问题"])
    for item in report["open_questions"]:
        lines.append(f"- {item['question']}（成员：{', '.join(item['alert_ids']) or '本次全案'}；依据：{citation_links(case_id, run_id, item['evidence_ids'])}）"
                     f" 缺少：{item['missing_evidence']}；建议：{item['suggested_action'] or '未提供'}")
    if not report["open_questions"]:
        lines.append("本次未列出结构化未决问题；其余限制见报告缺口。")
    return lines
