"""Freeze three paired synthetic scenarios and bounded real-test plan."""
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path(__file__).resolve().parents[2]
BATCH = 'k2'
OUT = ROOT / "docs/operations/evidence/socai2-kafka-chain-20261105" / BATCH
TENANT = str(uuid5(NAMESPACE_URL, "socai2-next-20261104:synthetic-tenant"))


def uid(label):
    return str(uuid5(NAMESPACE_URL, "socai2-kafka-" + BATCH + "-20261105:" + label))


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    now = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=2)
    cases = []
    for backend in ("deepseek", "small"):
        for number, scenario in enumerate(("maintenance", "credential_access", "sparse")):
            key = backend + "-" + scenario
            # Equal semantics, separate namespaces and windows avoid model A's
            # assessments becoming model B's historical evidence.
            base = now + timedelta(minutes=number * 10 + (40 if backend == "small" else 0))
            host = BATCH + "-endpoint-" + str(number + (3 if backend == 'small' else 0))
            source = BATCH + "-" + backend
            user = "operator-" + str(number)
            alerts, events = [], []
            for i in range(2):
                event_id, when = uid(key + "-event-" + str(i)), base + timedelta(seconds=i * 15)
                if i == 0:
                    command = (r'powershell.exe -File C:\Ops\inventory.ps1' if number != 1 else
                               r'rundll32.exe C:\Windows\System32\comsvcs.dll, MiniDump 612 C:\ProgramData\lsass.dmp full')
                    process = "powershell.exe" if number != 1 else "rundll32.exe"
                    ocsf = {"class_uid": 1007, "time": when.isoformat(), "device": {"name": host},
                        "actor": {"user": {"name": user}}, "process": {"pid": 4242, "name": process,
                        "cmd_line": command, "parent_process": {"pid": 2100, "name": "cmd.exe"}},
                        "activity": {"action": "process_start", "outcome": "success"}}
                    title = "Process command observed"
                else:
                    ocsf = {"class_uid": 4001, "time": when.isoformat(), "device": {"name": host},
                        "src_endpoint": {"hostname": host, "ip": "192.0.2." + str(30 + number), "port": 50123},
                        "dst_endpoint": {"ip": "198.51.100." + str(30 + number), "port": 443},
                        "connection_info": {"protocol_name": "tcp"},
                        "activity": {"action": "network_connect", "outcome": "success"}}
                    title = "Outbound connection observed"
                ocsf["raw_data"] = json.dumps(ocsf, sort_keys=True)
                envelope = {"schema_version": "v1", "tenant_id": TENANT, "event_id": event_id,
                    "connector_type": "validation", "original_vendor": "LabTelemetry", "ocsf_event": ocsf}
                alerts.append({"tenant_id": TENANT, "identity_version": "source-v1",
                    "source_alert_id": uid(key + "-alert-" + str(i)), "source": source,
                    "connector_type": "validation", "event_time": when.isoformat(), "title": title,
                    "description": "Recorded endpoint activity; relationship and authorization require evidence.",
                    "severity": "medium", "hostname": host, "username": user if i == 0 else None,
                    "source_event_ids": [event_id], "external_id": uid(key + "-vendor-" + str(i)),
                    "rule_id": "endpoint-observation-" + str(i), "rule_name": title,
                    "mitre_tactics": ["Execution"], "mitre_techniques": ["T1059.001"] if i == 0 and number != 1 else [],
                    "raw_event": envelope})
                # Sparse scenario intentionally has no corresponding lake rows.
                if scenario != "sparse":
                    events.append(envelope)
            cases.append({"key": key, "backend": backend, "scenario": scenario, "host": host,
                "window_start": (base - timedelta(minutes=1)).isoformat(),
                "window_end": (base + timedelta(minutes=1)).isoformat(), "alerts": alerts, "events": events})
    plan = {"batch": BATCH, "tenant_id": TENANT, "source": "new user full Kafka flow and paired-model test request",
        "destination": "192.168.1.21 independent next service", "new_alerts": 12, "lake_events": 8,
        "new_cases": 6, "max_runs": 26, "max_model_calls": 50, "retries": 0,
        "max_baseline_model_calls": 4, "max_baseline_tokens": 24000, "max_baseline_tool_calls": 4,
        "topic_prefix": "socai2.validation." + BATCH + ".20261105", "group": "socai2-validation-" + BATCH + "-20261105",
        "mutation": "synthetic next-DB tenant only, no production topic/group/config mutation",
        "pairing": "same semantic events; distinct neutral host IDs, source namespaces and 40min shifted windows prevent incident/history contamination",
        "predecessor": "k1 transport passed but same host+tactic merged paired backend records into 3 incidents; stopped before any model call",
        "excluded": ["Q implementation", "production scheduler", "original services", "external vendor connection claims"],
        "oracle_not_sent_to_models": {"maintenance": "benign; authorization only added via H in second C",
            "credential_access": "malicious simulation; process_start does not prove dump or exfil completed",
            "sparse": "unknown; missing lake rows cannot disprove source observations"},
        "pass_rule": "benign/malicious reversal is misclassification; needs_review acceptable abstention; unsupported facts judged separately",
        "cases": cases}
    path = OUT / "plan.json"
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({"plan": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "max_model_calls": 50}))


if __name__ == "__main__":
    main()
