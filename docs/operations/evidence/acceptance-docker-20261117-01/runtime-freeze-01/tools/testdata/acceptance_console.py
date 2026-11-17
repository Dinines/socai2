"""Explicit one-part console over the existing acceptance execution functions."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from acceptance_materials import save_report
from acceptance_report import new_output, report_exit_code, token, write_session_report
from acceptance_report_render import cell
from acceptance_status import session_status


def now():
    return datetime.now(timezone.utc).isoformat()


def candidate(status):
    if status.get("blocking_issues"):
        return None
    if status["state"] == "selection_required":
        return "run", status["first_part"]
    if status["state"] == "ready":
        return "run", status["next_part"]
    if status["state"] == "waiting_append":
        return "append", status["next_part"]
    return None


def selection(status):
    return candidate(status), status["execution_id"], status["environment"], status["sources"]


def display(status, write, unconfirmed=()):
    write(f"\n会话 {status['execution_id']} · 环境 {status['environment']['label']}")
    write(f"已存状态：{cell(status['state'])}；未查询远端实时状态。")
    for part in status["parts"]:
        planned, sent = part["planned_counts"], part.get("recorded_sent") or (
            {"context": 0, "alerts": 0} if not part["execution_directory_exists"] else {})
        write(f"  {part['id']}：计划上下文 {planned['context']} / 告警 {planned['alerts']}；"
              f"记录 {cell(part['recorded_state'])}；已发送 {cell(sent.get('context'))} / {cell(sent.get('alerts'))}；"
              f"保存读回 {'已确认' if part['closure_verified'] else '未确认'}")
    for problem in status["blocking_issues"]:
        write(f"  需核对：{problem['code']}，原件 {problem['path']}")
    action = candidate(status)
    write("命令：view 查看；report 生成报告；finish 结束并报告；quit 退出查看。空输入只重显。")
    if action and action[1] not in unconfirmed:
        write(f"可显式执行：{action[0]} {action[1]}（仅这一段，执行前重新核对）")
    else:
        write("当前没有可执行候选；不会重派或自动追加。")


def execute_part(action, prepared, part):
    # Drivers and their connection files are imported only after an explicit valid action.
    if action == "run":
        from acceptance_run import run_part as execute
    else:
        from acceptance_append import append_part as execute
    return asyncio.run(execute(prepared, part))


def run_console(prepared: Path, output: Path, *, read=None, write=None, execute=None):
    """Injected I/O/executor supports direct console checks, not a second runtime mode."""
    read, write, execute = read or input, write or print, execute or execute_part
    new_output(prepared, output)
    current = session_status(prepared)
    output.mkdir(parents=True)
    save_report(output / "start.json", {"schema_version": "socai2.acceptance-console-start.v1",
        "execution_id": current["execution_id"], "observed_at": now(), "observation": current})
    events, reports, issues, uncertain_parts = 0, 0, [], set()
    execution_attempts = 0
    last_report = None

    def event(kind, values):
        nonlocal events
        events += 1
        save_report(output / f"{events:04d}-{kind}.json", {"at": now(), **values})

    def observe():
        nonlocal current
        try:
            current = session_status(prepared)
            return True
        except (ValueError, OSError, TypeError, AttributeError):
            issues.append({"code": "observation_unavailable"})
            event("observation", {"code": "observation_unavailable"})
            write("当前原件无法核对；不执行。此前状态仅供追溯。")
            return False

    def end(reason, observed=True):
        # Leaving this console is not a business cancellation or permanent session close.
        value = {"schema_version": "socai2.acceptance-console-end.v1", "execution_id": current["execution_id"],
                 "ended_at": now(), "reason": reason, "operator_finished": reason == "finish",
                 "observed_execution_state": current["state"] if observed else "observation_unavailable",
                 "all_parts_completed": observed and current["state"] == "all_parts_completed",
                 "unsent_parts": [p["id"] for p in current["parts"] if not p["execution_directory_exists"] and p["id"] not in uncertain_parts] if observed else None,
                 "blocked_parts": sorted(uncertain_parts | {p["id"] for p in current["parts"] if p["execution_directory_exists"] and not p["closure_verified"]}) if observed else None,
                 "unconfirmed_parts": sorted(uncertain_parts),
                 "report": last_report, "execution_attempts": execution_attempts, "issues": issues,
                 "permanently_closed": False, "remote_cancellation_requested": False,
                 "provenance": "saved_local_receipts", "live_state_verified": False}
        code = 130 if reason == "interrupt" else (3 if issues or not observed or current["blocking_issues"] else 0)
        value["exit_code"] = code
        save_report(output / "end.json", value)
        write(f"已退出本次操作；执行状态：{cell(value['observed_execution_state'])}。回执：{output / 'end.json'}")
        return code

    def report():
        nonlocal reports, last_report
        reports += 1
        last_report = None
        relative = f"reports/{reports:04d}"
        try:
            value = write_session_report(prepared, output / relative)
            last_report = relative + "/report.md"
            event("report", {"report": last_report, "exit_code": report_exit_code(value)})
            if report_exit_code(value):
                issues.append({"code": "report_needs_review", "report": last_report})
            write(f"报告已保存：{output / last_report}")
            return True
        except (ValueError, OSError, TypeError, AttributeError):
            issues.append({"code": "report_unavailable"})
            event("report", {"code": "report_unavailable"})
            write("报告未完整保存；原件保持，请核对输出与原件目录。")
            return False

    observed = True
    display(current, write, uncertain_parts)
    def loop():
        nonlocal observed, execution_attempts
        while True:
            try:
                command = read("> ").strip()
            except EOFError:
                return end("eof", observe())
            except KeyboardInterrupt:
                return end("interrupt", observe())
            if command in {"quit", "q", "exit"}:
                return end("quit", observe())
            if command == "finish":
                report()
                return end("finish", observe())
            if command in {"", "view", "status", "1"}:
                observed = observe()
                if observed:
                    display(current, write, uncertain_parts)
                continue
            if command in {"report", "2"}:
                report()
                observed = observe()
                if observed:
                    display(current, write, uncertain_parts)
                continue
            words = command.split()
            chosen = tuple(words) if len(words) == 2 and words[0] in {"run", "append"} else None
            # Never persist arbitrary free-form input, which can contain credentials.
            if chosen is None or not observed or chosen != candidate(current) or chosen[1] in uncertain_parts:
                write("未执行：请使用当前显示的完整命令；查看不会发送，未知操作不能重派。")
                continue
            shown = selection(current)
            observed = observe()
            if not observed or selection(current) != shown:
                write("未执行：候选状态已变化，请查看后重新选择。")
                if observed:
                    display(current, write, uncertain_parts)
                continue
            event("intent", {"execution_id": current["execution_id"], "action": chosen[0], "part": chosen[1],
                             "observed_state": current["state"], "sources": current["sources"]})
            execution_attempts += 1
            interrupted = False
            try:
                result = execute(chosen[0], prepared, chosen[1])
                outcome = result.get("status") if isinstance(result, dict) else None
                if outcome not in {"completed", "completed_with_issues", "incomplete"}:
                    raise ValueError("unrecognized execution outcome")
                event("result", {"action": chosen[0], "part": chosen[1], "status": outcome,
                                 "stage": token(result.get("stage"))})
                if outcome != "completed":
                    issues.append({"code": "execution_needs_review", "part": chosen[1]})
            except (Exception, KeyboardInterrupt) as exc:  # noqa: BLE001 - never echo provider/credential exceptions
                interrupted = isinstance(exc, KeyboardInterrupt)
                uncertain_parts.add(chosen[1])
                issues.append({"code": "execution_outcome_unconfirmed", "part": chosen[1]})
                event("result", {"action": chosen[0], "part": chosen[1], "status": "unconfirmed"})
                write("执行结果需核对，已保存意图；不会自动重试或取消远端任务。")
            observed = observe()
            if interrupted:
                return end("interrupt", observed)
            if observed:
                display(current, write, uncertain_parts)
            write("本次选择已返回；等待下一次明确选择。")

    try:
        return loop()
    except KeyboardInterrupt:
        return end("interrupt", observe())
