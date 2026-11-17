"""Human-readable view of the saved report; no live state inference."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

LABELS = {"all_parts_completed": "全部段已完成保存和读回", "needs_review": "需要核对回执",
          "ready": "首段待显式执行", "waiting_append": "等待显式追加", "selection_required": "等待选择首段",
          "recorded_in_progress": "本地记录为执行中", "completed": "已完成", "completed_with_issues": "已完成，有执行问题",
          "incomplete": "未完成", "not_started": "未开始", "passed": "通过", "failed": "失败",
          "skipped": "跳过", "unknown": "未知", "partial": "部分交付", "none": "未交付",
          "ended": "本地已结束",
          "accepted": "已接收", "uncertain": "待复核", "case": "调查 Case", "incident": "事件", "alert": "告警",
          "context_publish_and_readback": "上下文投递与读回", "alerts_publish_and_triage": "告警投递与分诊",
          "incident_diagnosis": "事件诊断", "case_create_and_wait": "创建调查并等待执行",
          "case_check_and_wait": "等待同一调查后轮", "saved_http_readback": "保存与 HTTP 读回",
          "append_preflight": "追加前状态核对", "preflight": "连接与配置核对"}


def cell(value):
    if value is None:
        return "未知"
    return str(LABELS.get(value, value) if isinstance(value, str) else value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_report(value, prepared: Path, output: Path):
    lines = ["# 验收会话报告", "", f"会话：`{value['execution_id']}`。环境：{cell(value['environment']['label'])}。",
             f"保存记录状态：**{cell(value['state'])}**。", "",
             "本报告只读取这一个 prepared 会话中的已存原件；未查询远端当前状态，未发送告警，未调用模型。",
             "执行完成、结果交付、业务判定和正文质量分别列出。模型正文正确性尚未全面验收；质量问题保留，不中断独立流程。", "",
             "## 各段执行", "", "| 段 | 计划上下文 / 告警 | 已记录发送上下文 / 告警 | 保存状态 | 保存与读回 |",
             "|---|---:|---:|---|---|"]
    for part in value["parts"]:
        sent, planned = part.get("recorded_sent") or {}, part["planned_counts"]
        lines.append(f"| {cell(part['id'])} | {planned['context']} / {planned['alerts']} | {cell(sent.get('context'))} / {cell(sent.get('alerts'))} | {cell(part['recorded_state'])} | {'已核对' if part['closure_verified'] else '未确认'} |")
    for part in value["parts"]:
        lines += ["", f"### {cell(part['id'])}", ""]
        lines += [f"- {cell(s['stage'])}：{cell(s['status'])}" for s in part["stages"]] or ["尚无已存阶段回执。"]
        if part.get("error_code"):
            lines += [f"- 未完成位置：{cell(part.get('stage'))}；原因代码：`{part['error_code']}`。"]
        lines += [f"快照：{cell(part['snapshot_state'])}；本段新观察 Run {cell(part['newly_observed']['runs'])}，Result {cell(part['newly_observed']['results'])}；快照累计 Run {cell(part['observed_counts']['runs'])}。"]
    lines += ["", "## 实际主体和轮次", "", "以下按保存的主体、任务、尝试、Run、步骤和工件 ID 去重；后段累计快照不会重复加总。", "",
              "| 告警 | 事件 | Case | 任务 | 尝试 | Run | 步骤 | 工件 | Result |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
              "| " + " | ".join(cell(value["counts"][k]) for k in ("alerts", "incidents", "cases", "analysis_tasks", "analysis_attempts", "runs", "run_steps", "artifacts", "results")) + " |"]
    if value["statistics_state"] == "incomplete":
        lines += ["", "**统计不完整：已开始的段缺少可核对快照或原件冲突，总量未知。可读部分仅列作已观察记录，不用零代替未知。**"]
    for subject in value["subjects"]:
        lines += ["", f"### {cell(subject['kind'])} `{subject['id']}`", ""]
        for run in subject["rounds"]:
            stages = []
            for step in run["stages"]:
                label = f"{cell(step.get('stage_code'))} / {cell(step.get('name'))}（{cell(step.get('state'))}）"
                if label not in stages:
                    stages.append(label)
            lines += [f"- 第 {run['round']} 轮：{cell(run['state'])}；交付：{cell(run['delivery_state'])}；本轮选入告警 {cell(run['scope']['selected_count'])} / 当时范围总量 {cell(run['scope']['total_count'])} 条。Run `{run['run_id']}`。",
                      "  流程：" + (" → ".join(stages) or "无步骤原件。")]
            for attempt in value["attempts"]:
                if attempt.get("run_id") == run["run_id"]:
                    lines += [f"  尝试 `{attempt['id']}`：{cell(attempt.get('local_state'))} / {cell(attempt.get('outcome'))}；结束记录 {cell(attempt.get('local_ended_at') or attempt.get('interruption_observed_at'))}。"]
            for result in run["results"]:
                lines += [f"  结果 `{result['id']}`：接收 {cell(result['validation_state'])}；判定 {cell(result['conclusion_state'])}；交付 {cell(result['delivery_state'])}。"]
            if run["previous_run_ids"]:
                lines += ["  前轮：" + ", ".join(f"`{r}`" for r in run["previous_run_ids"]) + "。"]
            if run["comparison_result_id"]:
                lines += [f"  比较基线 Result：`{run['comparison_result_id']}`。"]
    models = value["models"]
    lines += ["", "## 模型输入输出", "", f"已保存请求 {models['saved_request_count']} 个；本会话请求总量：{cell(models['request_count'])}。本次生成报告新增调用 0。",
              f"Token：输入 {cell(models['usage']['prompt_tokens'])}，输出 {cell(models['usage']['completion_tokens'])}，总计 {cell(models['usage']['total_tokens'])}；费用未知。",
              f"已知 Token 小计 {models['known_usage_subtotal']['total_tokens']}；总量 usage 未知请求 {models['unknown_usage_requests']['total_tokens']} 个。", "",
              "筛选导出仅包含消息 role/content、已保存 Schema 和可见原答；输出保留原空白，不含隐藏推理或 HTTP 认证字段。完整原件仍在来源快照。", "",
              "| 请求 / Run | 输入 | Schema | 可见原答 | 结束 | Token |", "|---|---|---|---|---|---:|"]
    for item in models["requests"]:
        links = [f"[{label}]({item['exports'][key]})" if key in item["exports"] else "未保存或不可读"
                 for key, label in (("messages", "输入"), ("schema", "Schema"), ("output", "原答"))]
        lines += ["| " + " | ".join([f"`{item['request_artifact_id']}` / `{item['run_id']}`", *links,
                                     cell(item["finish_reason"]), cell(item["usage"]["total_tokens"])]) + " |"]
    lines += ["", "## 问题与未验边界", "", f"模型质量诊断 {value['quality']['issue_count']} 项；步骤跳过或错误记录 {len(value['step_issues'])} 项，分别计数。"]
    lines += ["按阶段：" + "，".join(f"{stage} {count} 项" for stage, count in value["quality"]["issues_by_stage"].items()) + "。"]
    for code, count in value["quality"]["issues_by_code"].items():
        lines += [f"- 质量：`{code}` × {count}。"]
    for problem in value["step_issues"]:
        lines += [f"- 步骤：{cell(problem['stage'])} / {cell(problem['name'])}，{cell(problem['state'])}，`{problem['code']}`；Run `{problem['run_id']}`。"]
    for problem in value["blocking_issues"] + value["report_issues"] + models["issues"]:
        lines += [f"- 回执核对：`{problem['code']}`，{cell(problem.get('path') or problem.get('source', {}).get('path'))}。"]
    for part in value["parts"]:
        for problem in part.get("execution_issues") or []:
            lines += [f"- {part['id']} 执行问题：`{cell(problem.get('reason_code'))}`。"]
    lines += ["", "未执行段仍可在核对状态后显式选择；生成报告或退出查看不会关闭业务会话。未在本步重跑真实业务、验证远端实时状态或重新评估正文。", "",
              "## 原件与读回", "", "[结构化报告](report.json) · [文件 SHA 与来源清单](manifest.json)", "",
              "下列 SHA 对应 prepared 原件；导出文件的 SHA 单独保存在 manifest.json。JSON 中的 pointer 可定位具体行。", ""]
    # Link high-value snapshots; the manifest contains every source used by the status gate.
    for source in value["sources"]:
        if source["path"].endswith(("state.json", "saved-records.json", "readback.json")):
            relative = quote(os.path.relpath(prepared.resolve() / source["path"], output.resolve()), safe="/.")
            lines += [f"- [{source['path']}]({relative})：`{source['sha256']}`。"]
    return "\n".join(lines) + "\n"
