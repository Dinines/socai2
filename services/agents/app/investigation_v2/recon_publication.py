"""Pure M7a publication preparation for the finite fixed-recon path.

The caller must establish storage ownership. This module verifies supplied
bytes/references and the frozen runtime transition, but never claims commit,
delivers a notification, changes the ledger or calls a tool/model.
"""
from __future__ import annotations

from datetime import datetime
import html
import json
import re
from uuid import UUID

from .business_profile import BusinessProfileRequest
from .execution_state import ExecutionRejected
from .execution_store import canonical_json, content_hash, MAX_BODY_BYTES
from .fixed_recon import COMPLETION_POLICY_REF
from .recon_runtime_state import RUNTIME_VERSION, make_recon_plan, finish_recon, _runtime_copy
from .recon_runtime_store import HANDOFF_KIND

MANIFEST_SCHEMA = "fixed_recon_result_manifest.v1"
EXECUTION_SCHEMA = "fixed_recon_publication_execution.v1"
SECTIONS_VERSION = "fixed_recon_handoff_sections.v1"
MAPPING_VERSION = "fixed_recon_publication_state.v1"
RENDERER_VERSION = "fixed_recon_markdown.v1"
_RESULTS = {"fixed_alert_recon.v1": "fixed-recon:", "blocked_alert_recon.v1": "blocked-recon:",
            "fixed_runtime_unadopted_result.v1": "unadopted-recon:"}
_QUESTIONS = {"Q1", "Q2", "Q3a", "Q3b", "Q4", "Q5"}


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ExecutionRejected(reason)


def checked_artifact(row: dict, kind: str) -> tuple[dict, dict]:
    """Byte integrity only; actual tenant/Run/event ownership belongs to store."""
    _require(isinstance(row, dict) and row.get("kind") == kind, "publication artifact kind mismatch")
    identity = str(UUID(str(row["id"])))
    _require(UUID(identity).int != 0, "publication artifact UUID required")
    body = row["content"]
    _require(isinstance(body, str) and len(body.encode("utf-8")) <= MAX_BODY_BYTES
             and len(body.encode("utf-8")) == row["size_bytes"] and content_hash(body) == row["sha256"],
             "publication artifact integrity mismatch")
    data = json.loads(body)
    _require(isinstance(data, dict), "publication artifact object required")
    return data, {"artifact_id": identity, "sha256": row["sha256"]}


def _section(reference: dict, candidate: dict, path: str, value, required_type: type) -> dict:
    _require(isinstance(value, required_type), "publication section type mismatch")
    return {**reference, "artifact_schema": candidate["schema"], "sections_version": SECTIONS_VERSION,
            "section": path, "section_sha256": content_hash(canonical_json(value))}


def _safe(value) -> str:
    # Text only, never raw HTML or attacker-controlled Markdown link/fence syntax.
    text = str(value).replace("\r", "\\r").replace("\n", "\\n")
    return re.sub(r"([\\`*_{}\[\]()#+.!|>\-])", r"\\\1", html.escape(text, quote=True))


def _fact_text(fact: dict) -> str:
    """Display adopted typed values, without interpreting free source text."""
    predicate = fact["predicate"]
    if predicate == "network_observed":
        fields = fact["fields"]
        return (f"来源观察：时间{_safe(fields['observed_at'])}，主机{_safe(fields['hostname'])}，"
                f"{_safe(fields['source_ip'])} → {_safe(fields['dest_ip'])}:{_safe(fields['dst_port'])}，"
                f"协议{_safe(fields['protocol'])}，action={_safe(fields['action'])}，outcome={_safe(fields['outcome'])}。")
    if predicate == "outcome_unknown":
        return "来源结果为unknown，不能据此推断连接成功或失败。"
    if predicate == "alert_linked":
        return f"告警声明的来源事件UUID精确匹配：{_safe(fact['event_id'])}；仅表示声明的来源关联。"
    if predicate in {"bounded_query", "query_empty"}:
        text = (f"本次来源查询状态{_safe(fact['status'])}，返回{_safe(fact['returned_count'])}条，"
                f"行数上限{_safe(fact['coverage']['limit'])}，截断={_safe(fact['truncated'])}。")
        return text + ("零行只表示本次有界查询为空，不证明活动不存在。" if predicate == "query_empty" else "仅覆盖已声明窗口和过滤条件。")
    if predicate == "source_unavailable":
        return f"来源状态{_safe(fact['status'])}，执行状态{_safe(fact['execution_state'])}；不作为成功空查询。"
    if predicate == "source_versions_conflict":
        return "同一来源事件存在不同内容版本，保留各版本并待核。"
    return "已留存的程序事实：" + _safe(predicate)


def _render(request: BusinessProfileRequest, candidate: dict, execution: dict, availability: str) -> str:
    result, context = candidate["result"], request.context
    lines = ["# 告警有限来源核对", "", "本报告仅核对冻结窗口内的来源观察及告警UUID关联。行为性质未定，业务授权未知。", "",
             f"目标告警：{_safe(request.target.target_id)}", f"Run：{_safe(context.run_id)}",
             f"目标：{_safe(request.objective)}；完成政策：{_safe(COMPLETION_POLICY_REF)}",
             f"窗口：{_safe(context.query_scope.window.start.isoformat())} 至 {_safe(context.query_scope.window.end.isoformat())}（左闭右开）", "",
             "## 本轮结果", "",
             f"执行：{_safe(execution['run_state'])}；范围完整度：{_safe(execution['investigation_completeness'])}；续接：{_safe(execution['continuation'])}。",
             f"结束原因：{_safe(result['stop_reason'])}；证据视图：{_safe(availability)}。",
             "此完整度只针对上述有限目标，不代表恶意、正常、授权或因果攻击链结论。", "",
             "## 六问题", "", "| 问题 | 状态 |", "| --- | --- |"]
    for question in result["questions"]:
        lines.append(f"| {_safe(question['question'])} | {_safe(question['status'])} |")
    lines += ["", "## 已采用的程序事实", ""]
    for fact in result["facts"]:
        lines.append(f"- {_safe(fact['question'])}：{_fact_text(fact['fact'])} 引用：" + "; ".join(_safe(ref) for ref in fact["evidence_refs"]))
    if not result["facts"]:
        lines.append("当前没有采用的来源事实。")
    lines += ["", "## 缺口与保留材料", ""]
    gaps = sorted(set(result["coverage_gaps"] + result["blocking_gaps"]))
    lines += ["- " + _safe(gap) for gap in gaps] or ["有限目标未记录阻断；来源覆盖仍受本次查询和窗口限制。"]
    lines += ["- 材料引用：" + _safe(ref) for ref in sorted(set(result["held_refs"] + candidate["retained_artifact_refs"]))]
    if candidate["unconfirmed_observation_ref"] is not None:
        lines.append("存在单独留存的未确认观察，未作为原始已完成调用或来源事实采用。")
    stage, total = execution["stage_usage"], execution["run_total"]
    lines += ["", "## 实际执行与交接", "",
              f"本阶段模型{stage['model_calls']}次，工具{stage['tool_calls']}次，已知tokens {stage['known_tokens']}，预留tokens {stage['reserved_tokens']}；unknown {stage['unknown_attempts']}，未结算{stage['unsettled_attempts']}，unpriced {stage['unpriced_attempts']}。",
              "Run累计（包含期初分诊；未知用量与缺价不按零处理）：" + _safe(canonical_json(total)),
              "停止后的交接不追加查询、模型、Case或厂商动作。",
              "需要人工复核；此报告不证明已经投递或有人接手。" if execution["continuation"] == "awaiting_human" else "本有限目标无自动续接；本报告不触发业务关闭。", ""]
    body = "\n".join(lines)
    _require(len(body.encode("utf-8")) <= MAX_BODY_BYTES, "publication report exceeds bound")
    return body


def prepare_recon_publication(request: BusinessProfileRequest, *, handoff_artifact: dict,
                              source_state_artifact: dict, current_state_artifact: dict) -> dict:
    """Return a detached candidate package; no persistence or wall-clock reads."""
    _require(isinstance(request, BusinessProfileRequest), "checked publication request required")
    plan = make_recon_plan(request)
    candidate, handoff_ref = checked_artifact(handoff_artifact, HANDOFF_KIND)
    source, source_ref = checked_artifact(source_state_artifact, "unified_state_snapshot")
    current, current_ref = checked_artifact(current_state_artifact, "unified_state_snapshot")
    _require(candidate.get("schema") == "fixed_recon_runtime_handoff.v1", "publication handoff schema mismatch")
    _require(candidate["handoff_ref"] == "fixed-runtime-handoff:" + content_hash(canonical_json({k: v for k, v in candidate.items() if k != "handoff_ref"})), "publication handoff reference mismatch")
    _require(candidate["runtime_version"] == RUNTIME_VERSION and candidate["runtime_plan_ref"] == plan["plan_ref"]
             and candidate["business_profile"] == request.descriptor and candidate["scope_hash"] == plan["scope_hash"]
             and candidate["completion_policy_ref"] == COMPLETION_POLICY_REF, "publication handoff binding mismatch")
    result = candidate["result"]
    prefix = _RESULTS.get(result.get("schema"))
    _require(prefix is not None and result["result_ref"] == prefix + content_hash(canonical_json({k: v for k, v in result.items() if k != "result_ref"})), "publication result reference mismatch")
    _require((result["tenant_id"], result["run_id"], result["profile"], result["binding_ref"], result["delivery_target"])
             == (str(request.context.tenant_id), str(request.context.run_id), "alert_recon", request.descriptor["binding_ref"], request.descriptor["delivery_target"]), "publication result identity mismatch")
    _require(result["nature"] == "unresolved" and result["authorization"] == "unknown" and result["status"] == "stopped"
             and result["completion_policy_ref"] == COMPLETION_POLICY_REF, "publication result exceeds finite policy")
    questions = result["questions"]
    _require(isinstance(questions, list) and len(questions) == 6 and {q["question"] for q in questions} == _QUESTIONS, "publication requires six questions")
    _require(candidate["execution"]["source_state_artifact_ref"] == "urn:uuid:" + source_ref["artifact_id"], "publication source state reference mismatch")
    for raw, row, reference in ((source, source_state_artifact, source_ref), (current, current_state_artifact, current_ref)):
        checked, _ = _runtime_copy(raw, datetime.fromisoformat(raw["updated_at"]))
        _require(checked == raw, "publication state usage is inconsistent")
        _require(raw["recon"]["plan"] == plan, "publication state plan mismatch")
        _require(raw["persistence"]["state_artifact_id"] == reference["artifact_id"]
                 and raw["persistence"]["event_id"] == str(row["event_id"]), "publication state artifact link mismatch")
    _require("publication" not in current and current["recon"]["phase"] == "stopped"
             and current["recon"]["handoff"] == handoff_ref, "publication requires current stopped handoff")
    expected, _ = finish_recon(source, artifact_id=handoff_ref["artifact_id"], body_hash=handoff_ref["sha256"],
                               execution_stop=result["execution_stop"], now=datetime.fromisoformat(current["recon"]["stopped_at"]))
    _require({k: v for k, v in expected.items() if k != "persistence"} == {k: v for k, v in current.items() if k != "persistence"}, "publication handoff is stale against current state")
    _require(current["persistence"]["body_artifact_id"] == handoff_ref["artifact_id"]
             and current["persistence"]["body_hash"] == handoff_ref["sha256"]
             and str(current_state_artifact["event_id"]) == str(handoff_artifact["event_id"]),
             "publication stopped state handoff link mismatch")
    _require(candidate["execution"]["stage_usage"] == current["stage_usage"]
             and candidate["execution"]["run_total"] == current["run_total"]
             and candidate["execution"]["cancellation_observed_at"] == current["recon"].get("cancellation_observed_at"), "publication handoff execution mismatch")
    sections = {"questions": _section(handoff_ref, candidate, "/result/questions", questions, list),
                "analysis": _section(handoff_ref, candidate, "/result", result, dict), "evidence": None}
    preparation = candidate["preparation"]
    availability = "not_adopted"
    if preparation is not None:
        _require(preparation["result"] == result and preparation["preparation_ref"] == "recon-preparation:" + content_hash(canonical_json({k: v for k, v in preparation.items() if k != "preparation_ref"})), "publication preparation mismatch")
        availability = preparation["material_state"]
        _require(availability in {"view_ready", "material_projection_blocked"}, "publication material state unsupported")
        if availability == "view_ready":
            document = preparation["evidence_document"]
            _require(isinstance(document, dict) and document["model_view"]["snapshot_ref"] == preparation["evidence_snapshot_ref"] == result["snapshot_ref"], "publication evidence snapshot mismatch")
            sections["evidence"] = _section(handoff_ref, candidate, "/preparation/evidence_document", document, dict)
        else:
            _require(preparation["evidence_document"] is None and preparation["evidence_snapshot_ref"] is None, "blocked publication cannot invent evidence snapshot")
    ready = result["scope_readiness"] == "ready"
    _require(result["scope_readiness"] in {"ready", "partial"}, "publication readiness unsupported")
    if ready:
        _require(not result["blocking_gaps"] and result["execution_stop"] is None and result["coverage"]["full_window_queried"], "publication ready has blockers")
    cancelled = bool(current["recon"].get("cancellation_observed_at")) or result["execution_stop"] == "cancelled"
    _require(not ready or not cancelled, "cancelled publication cannot be ready")
    execution = {"schema": EXECUTION_SCHEMA, "mapping_version": MAPPING_VERSION, "tenant_id": str(request.context.tenant_id), "run_id": str(request.context.run_id),
        "runtime_version": RUNTIME_VERSION, "runtime_plan_ref": plan["plan_ref"], "scope_hash": plan["scope_hash"],
        "run_state": "cancelled" if cancelled else "finished" if ready else "stopped", "investigation_completeness": "complete_for_scope" if ready else "partial",
        "continuation": "none" if ready else "awaiting_human", "stop_reason": result["stop_reason"], "scope_readiness": result["scope_readiness"],
        "source_state_ref": source_ref, "stopped_state_ref": current_ref, "stage_usage": current["stage_usage"], "run_total": current["run_total"],
        "human_acknowledged": False}
    manifest = {"schema": MANIFEST_SCHEMA, "publication_state": "candidate", "version": 1, "investigation_id": str(request.context.run_id),
        "tenant_id": str(request.context.tenant_id), "run_id": str(request.context.run_id), "profile": request.profile, "target": request.descriptor["target"], "objective": request.objective,
        "runtime_version": RUNTIME_VERSION, "runtime_plan_ref": plan["plan_ref"], "completion_policy_ref": COMPLETION_POLICY_REF,
        "renderer_version": RENDERER_VERSION, "mapping_version": MAPPING_VERSION, "sections_version": SECTIONS_VERSION,
        "scope_hash": plan["scope_hash"], "scope_revision": request.context.revision, "coverage": result["coverage"], "result_ref": result["result_ref"],
        "handoff_ref": handoff_ref, "source_state_ref": source_ref, "stopped_state_ref": current_ref, "snapshots": {**sections, "execution": None}, "report": None,
        "previous_manifest_ref": None, "retention": {"publication_artifacts": "not_attempted", "source_availability": availability,
            "source_gaps": result["coverage_gaps"], "blocking_gaps": result["blocking_gaps"], "held_refs": sorted(set(result["held_refs"] + candidate["retained_artifact_refs"])),
            "unconfirmed_observation_ref": candidate["unconfirmed_observation_ref"], "unknown_calls": current["run_total"]["unknown_calls"],
            "unsettled_attempts": current["stage_usage"]["unsettled_attempts"], "unpriced_attempts": current["stage_usage"]["unpriced_attempts"]}}
    package = {"schema": "fixed_recon_publication_candidate.v1", "status": "candidate", "manifest_basis": manifest,
               "execution_snapshot": execution, "markdown": _render(request, candidate, execution, availability)}
    canonical_json(package)  # Enforce the existing bounded JSON artifact limit.
    package["prepared_ref"] = "recon-publication-candidate:" + content_hash(canonical_json(package))
    return json.loads(canonical_json(package))
