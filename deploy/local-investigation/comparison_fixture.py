"""Three fixed synthetic cases, using the existing source-v1 pipeline recipe.

Commands below are inert log values. No command in a fixture is executed.
Attack patterns are adapted from tools/testdata/upstream, not copied verdicts.
"""
import copy
import json

SCENARIOS = ("routine", "credential", "impact")


def apply(case, scenario, *, account="operator-0"):
    assert scenario in SCENARIOS
    if scenario == "routine":
        title = "账户清点与报表复制"
        description = "同一主机先执行账户信息查询，随后执行向内部共享目录复制报表的命令。核查用途、执行结果及授权。"
        records = [
            ("Account enumeration command observed", "whoami.exe", "whoami.exe /all", "process_start", None),
            ("Report copy command observed", "robocopy.exe",
             r"robocopy.exe C:\Ops\reports \\192.0.2.80\inventory /E /R:0 /W:0", "process_start", None),
        ]
        truth = "benign"
        expected = "Routine inventory and report copying; authorization and completion remain unverified in supplied observations."
        source_template = "existing maintenance recipe; new routine commands"
    elif scenario == "credential":
        title = "进程内存转储与文件归档"
        description = "同一主机出现进程内存转储命令及随后针对转储文件的归档命令。核查凭据访问风险及影响范围。"
        records = [
            ("Process memory dump command observed", "rundll32.exe",
             r"rundll32.exe C:\Windows\System32\comsvcs.dll, MiniDump 688 C:\Windows\Temp\lsass.dmp full", "process_start", None),
            ("Dump archive command observed", "7z.exe",
             r"7z.exe a C:\Windows\Temp\stage.7z C:\Windows\Temp\lsass.dmp", "process_start", None),
        ]
        truth = "malicious"
        expected = "Credential-dumping and staging attempts warrant escalation; PID 688 identity, successful dumping and exfiltration are not independently confirmed."
        source_template = "lsass-memory-dump; added explicit process-start and archive observations"
    else:
        title = "恢复副本删除与文件改名"
        description = "同一主机出现删除卷影副本命令及文档改名记录。核查恢复能力、文件变更范围和业务影响。"
        records = [
            ("Shadow copy deletion command observed", "vssadmin.exe",
             "vssadmin.exe delete shadows /all /quiet", "process_start", None),
            ("Document rename observed", "enc.exe",
             r"C:\ProgramData\enc.exe --encrypt C:\Users\operator-0\Documents --extension .locked --note R3ADM3.txt",
             "file_rename", r"C:\Users\operator-0\Documents\notes.docx.locked"),
        ]
        truth = "malicious"
        expected = "Recovery-inhibition attempt and a file rename consistent with ransomware warrant escalation; no proof of completed shadow deletion or all-files encryption."
        source_template = "ransomware-encryption; added shadow-copy deletion command, one explicit rename only"

    process_event = copy.deepcopy(case["events"][0])
    for index, (label, name, command, action, file_path) in enumerate(records):
        alert = case["alerts"][index]
        event = copy.deepcopy(process_event)
        event["event_id"] = alert["source_event_ids"][0]
        event["ocsf_event"].update(time=alert["event_time"], class_uid=1001 if file_path else 1007)
        ocsf = event["ocsf_event"]
        ocsf["actor"]["user"]["name"] = account
        ocsf["process"] = {"name": name, "pid": 4242 + index, "cmd_line": command,
                           "parent_process": {"pid": 2100, "name": "cmd.exe"}}
        ocsf["activity"] = {"action": action, "outcome": "success"}
        if file_path:
            ocsf["file"] = {"path": file_path}
        ocsf.pop("raw_data", None)
        ocsf["raw_data"] = json.dumps(ocsf, ensure_ascii=False, sort_keys=True)
        case["events"][index] = event
        alert.update(title=label, rule_name=label, description="Recorded endpoint action; assess its scope and outcome from retained observations.",
                     username=account, severity="medium", mitre_tactics=[], mitre_techniques=[], raw_event=copy.deepcopy(event))
    case.update(scenario=scenario, title=title, description=description, rounds=1)
    return {
        "behavior_truth": truth, "truth_scope": expected,
        "source_template": source_template,
        "authorization_available_after_H_only": False,
        "evaluation_limit": "Synthetic known-intent examples; absent authorization is not evidence of malice. No population accuracy estimate.",
        "tool_expected_event_ids": {
            "process_activity": [e["event_id"] for e in case["events"] if e["ocsf_event"]["class_uid"] == 1007],
            "network_connections": [], "authentication_activity": [],
        },
        "unsupported_claims": ["process start proves command completion", "filename proves contents",
                               "shared host proves process causality", "missing authorization proves malicious intent",
                               "one file rename proves all-files encryption", "archive command proves exfiltration"],
    }
