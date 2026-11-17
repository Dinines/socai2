#!/usr/bin/env python3
"""Prepare, explicitly run/append, and inspect or report a frozen acceptance session."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from acceptance_contract import Profile, Recipe
from acceptance_materials import (
    control,
    convert_package,
    inspect_package,
    read_json,
    save_report,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="验收材料转换、准备、显式分段执行、会话交互与只读报告")
    commands = parser.add_subparsers(dest="command", required=True)
    convert = commands.add_parser("convert", help="按显式recipe转换旧v2业务输入")
    convert.add_argument("--source", type=Path, required=True)
    convert.add_argument("--recipe", type=Path, required=True)
    convert.add_argument("--output", type=Path, required=True)
    inspect = commands.add_parser("inspect", help="校验材料并列出计划，不探测连接")
    inspect.add_argument("--materials", type=Path, required=True)
    inspect.add_argument("--part")
    inspect.add_argument("--report", type=Path, required=True, help="保存到一个不存在的新文件")
    prepare = commands.add_parser("prepare", help="离线生成新执行身份并冻结全包wire，不发送")
    prepare.add_argument("--materials", type=Path, required=True)
    prepare.add_argument("--execution", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", help="显式执行已准备的首段；已有执行不能重派",
                              description="显式执行已准备的首段；已有执行不能重派，请先查已保存状态与原回执。")
    run.add_argument("--prepared", type=Path, required=True)
    run.add_argument("--part")
    append = commands.add_parser("append", help="显式追加同一会话的下一未发送段；先核实时状态，不重发旧段",
                                 description="显式追加同一冻结会话的下一未发送段；先核实时状态，已有段不能重派。")
    append.add_argument("--prepared", type=Path, required=True)
    append.add_argument("--part", required=True)
    status = commands.add_parser("status", help="只读已存会话状态与下一候选段，不连接业务服务或追加",
                                 description="只反映本地保存时的状态，不代表远端当前状态；不会重发或追加。")
    status.add_argument("--prepared", type=Path, required=True)
    status.add_argument("--report", type=Path, required=True, help="保存到prepared和原材料目录外的不存在的新文件")
    report = commands.add_parser("report", help="只读汇总同一会话，导出中文报告与可见模型输入输出")
    report.add_argument("--prepared", type=Path, required=True)
    report.add_argument("--output", type=Path, required=True, help="prepared和原材料目录外的全新目录")
    session = commands.add_parser("session", help="先查看会话，再明确选择一段执行；空输入和退出不发送")
    session.add_argument("--prepared", type=Path, required=True)
    session.add_argument("--output", type=Path, required=True, help="本次操作回执写入外部全新目录")
    for command in (report, session):
        command.add_argument("--report-config", type=Path, help="可选公开展示配置，用于报告链接指定主体/Run；不修改冻结会话")
    for command in (convert, inspect, prepare):
        command.add_argument("--profile", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "session":
            from acceptance_console import run_console
            from acceptance_report_links import load_report_config
            return run_console(args.prepared, args.output, report_config=load_report_config(args.report_config))
        if args.command == "report":
            from acceptance_report import report_exit_code, write_session_report
            from acceptance_report_links import load_report_config
            result = write_session_report(args.prepared, args.output, report_config=load_report_config(args.report_config))
            print(json.dumps({k: result[k] for k in ("execution_id", "state", "statistics_state", "counts", "this_command")}
                             | {"report": str(args.output / "report.md")}, ensure_ascii=False, indent=2))
            return report_exit_code(result)
        if args.command == "status":
            from acceptance_status import write_status
            result = write_status(args.prepared, args.report)
            print(json.dumps({**{k: result[k] for k in ("execution_id", "state", "next_part", "next_action",
                              "selection_required", "first_part", "blocking_issues", "live_state_verified")},
                              "parts": [{k: p[k] for k in ("id", "recorded_state", "closure_verified", "actual",
                                        "planned_counts", "issues")} for p in result["parts"]],
                              "report": str(args.report)}, ensure_ascii=False, indent=2))
            return 3 if result["blocking_issues"] else 0
        if args.command in {"run", "append"}:
            if args.command == "append":
                from acceptance_append import append_part as execute
            else:
                from acceptance_run import run_part as execute
            result = asyncio.run(execute(args.prepared, args.part))
            print(json.dumps({k: result.get(k) for k in ("execution_id", "part", "status", "stage", "sent", "alerts", "incidents", "cases", "error_code")}, ensure_ascii=False, indent=2))
            return {"completed": 0, "completed_with_issues": 3}.get(result["status"], 2)
        profile = control(Profile, read_json(args.profile), "profile")
        if args.command == "convert":
            recipe = control(Recipe, read_json(args.recipe), "recipe")
            result = convert_package(args.source, recipe, profile, args.output)
            report = args.output / "plan.json"
        elif args.command == "prepare":
            from acceptance_runtime_contract import Execution
            from acceptance_session import prepare_execution
            execution = control(Execution, read_json(args.execution), "execution")
            session = prepare_execution(args.materials, profile, execution, args.output)
            print(json.dumps({"execution_id": execution.execution_id, "status": "prepared_not_executed",
                              "selected_part": session["plan"]["selected_part"], "records": len(session["identities"]),
                              "session": str(args.output / "session.json")}, ensure_ascii=False, indent=2))
            return 0
        else:
            if args.report.resolve().is_relative_to(args.materials.resolve()):
                raise ValueError("inspection report must be outside the read-only materials directory")
            result = inspect_package(args.materials, profile, selected_part=args.part)
            save_report(args.report, result)
            report = args.report
        print(json.dumps({"validation_status": "passed", "execution_status": "not_executed",
                          "selected_part": result["selected_part"],
                          "selection_required": result["selection_required"],
                          "parts": [{k: p[k] for k in ("id", "counts", "check_level", "selected", "execution_status")}
                                    for p in result["parts"]],
                          "connection_status": "not_checked", "report": str(report)}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        # No request contents, credential values, Pydantic input values or traceback.
        detail = str(exc) if isinstance(exc, ValueError) else f"file access failed ({type(exc).__name__})"
        print(json.dumps({"validation_status": "failed", "execution_status": "not_executed",
                          "error": detail}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
