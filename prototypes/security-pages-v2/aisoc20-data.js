/* Historical synthetic inputs; actual AiSOC20 runtime results. */
window.aisoc20RecordedData = {
  "alerts": [
    {
      "id": "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
      "persistedRecord": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "title": "Office启动隐藏PowerShell [DEMO-FIN-11]",
      "description": "WINWORD.EXE spawned powershell.exe with hidden window on DEMO-FIN-11 under demo.finance. Parent PID 4100, child PID 4200. No payload contents or approval records supplied.",
      "severity": "高",
      "status": "In progress",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "执行",
      "source": "showcase-security-sensor",
      "entityIds": [
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-FIN-11",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.finance",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.10.11",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.41"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-24T03:51:40.277842+00:00",
      "first": "2026-10-24T03:51:40.277842+00:00",
      "last": null,
      "incidentId": "85b81836-be47-4ab0-8c1f-6d360c5fb0a2",
      "caseId": null,
      "comments": [],
      "disposition": "true_positive",
      "hostNames": [
        "DEMO-FIN-11"
      ],
      "tactics": [
        "Execution"
      ],
      "iocKeys": [
        "ip:10.78.10.11",
        "ip:198.51.100.41"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-24T03:51:40.277842+00:00",
            "title": "告警发生",
            "description": "Office启动隐藏PowerShell [DEMO-FIN-11]"
          },
          {
            "time": "2026-10-24T03:56:45.578739+00:00",
            "title": "自动分诊完成",
            "description": "verdict=true_positive confidence=0.95"
          },
          {
            "time": "2026-10-24T03:57:01.734293+00:00",
            "title": "调查结果交付",
            "description": "automatic graph delivery: partial"
          }
        ],
        "runs": [
          {
            "id": "b250e383-9221-550f-b192-bc1d62b450f1",
            "time": "2026-10-24T03:56:42.472372+00:00",
            "status": "Completed",
            "completion": "partial",
            "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
            "findings": [
              "Auto-triage: verdict=true_positive, confidence=0.95, latency=2684ms",
              "Auto-triage rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.",
              "Escalating to full pipeline — TP verdict",
              "Triage severity: critical (risk_score=0.92)",
              "Extracted 2 IOCs for enrichment: ['10.78.10.11', '198.51.100.41']",
              "MITRE kill chain: {'Unknown': ['T1059.001: Unknown']}",
              "Triage verdict: true_positive (confidence=0.95)",
              "Triage phase complete — proceeding to enrichment",
              "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
              "No strong threat actor attribution possible with current intelligence",
              "Graph context: host:DEMO-FIN-11: 0 nodes (depth=2)",
              "Graph context: user:demo.finance: 0 nodes (depth=2)",
              "{\"tool\": \"persistence_mechanisms\", \"available\": false, \"row_count\": 0, \"rows\": [], \"reason\": \"Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data class. An EDR or osquery connector would populate them.\"}",
              "Investigation depth: 3 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, historical_execution, process_activity.",
              "Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.",
              "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
              "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
              "Attack stages observed: Unknown. This indicates a single-stage attack.",
              "Investigation verdict: confirmed_incident (confidence=0.95)",
              "Investigation complete. Total proposed actions: 1"
            ],
            "calls": 7,
            "tokens": 22962,
            "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 85b81836-be47-4ab0-8c1f-6d360c5fb0a2\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.95 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.95\n- 1 proposed action(s)\n- (triage) vendor risk_score=0.92\n- (triage) critical-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=true_positive, confidence=0.95, latency=2684ms\n- Auto-triage rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.\n- Escalating to full pipeline — TP verdict\n- Triage severity: critical (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.10.11&#x27;, &#x27;198.51.100.41&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1059.001: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.95)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-FIN-11: 0 nodes (depth=2)\n- Graph context: user:demo.finance: 0 nodes (depth=2)\n- {&quot;tool&quot;: &quot;persistence_mechanisms&quot;, &quot;available&quot;: false, &quot;row_count&quot;: 0, &quot;rows&quot;: [], &quot;reason&quot;: &quot;Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data class. An EDR or osquery connector would populate them.&quot;}\n- Investigation depth: 3 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, historical_execution, process_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.95)\n- Investigation complete. Total proposed actions: 1\n\n## MITRE ATT&CK Mappings\n\n- `T1059.001`\n\n## Proposed Actions\n\n| # | Action | Target | Risk | Approval | Rationale |\n|---|--------|--------|------|----------|-----------|\n| 1 | isolate_host | DEMO-FIN-11 | high | yes | Critical severity alert with host identifier present |\n\n_Generated by AiSOC router on 2026-10-24 03:57 UTC_\n",
            "actions": [
              "Isolate host 'DEMO-FIN-11' from network"
            ],
            "steps": [
              {
                "name": "auto_triage:llm",
                "agent": "auto_triage:llm",
                "status": "Completed",
                "input": {},
                "output": {
                  "verdict": "true_positive",
                  "findings": [
                    "Auto-triage: verdict=true_positive, confidence=0.95, latency=2684ms",
                    "Auto-triage rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.",
                    "Escalating to full pipeline — TP verdict"
                  ],
                  "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.",
                  "confidence": 0.95,
                  "auto_closed": false
                }
              },
              {
                "name": "triage",
                "agent": "triage",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "triage",
                  "step_status": "completed"
                }
              },
              {
                "name": "enrichment",
                "agent": "enrichment",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "enrichment",
                  "step_status": "completed"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "process_activity",
                  "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-FIN-11 in the last 24h'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "process_tree",
                  "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "days": 90,
                    "process_name": "PowerShell"
                  },
                  "tool": "historical_execution",
                  "result_preview": "{'tool': 'historical_execution', 'available': True, 'row_count': 0, 'rows': [], 'query': 'executions of PowerShell across the fleet, last 90d'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 90,
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "entity_timeline",
                  "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:51:40.277000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-FIN-11"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "network_connections",
                  "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "persistence_mechanisms",
                  "result_preview": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
                }
              },
              {
                "name": "investigation",
                "agent": "investigation",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "investigation",
                  "reason": "Deep stopped before a complete investigation",
                  "step_status": "partial"
                }
              },
              {
                "name": "attack_path",
                "agent": "attack_path",
                "status": "已跳过",
                "input": {},
                "output": {
                  "node": "attack_path",
                  "reason": "no Case linked; attack-path traversal not performed",
                  "step_status": "skipped"
                }
              },
              {
                "name": "automatic_graph",
                "agent": "automatic_graph",
                "status": "Completed",
                "input": {},
                "output": {
                  "workflow": "automatic_graph",
                  "completion": "partial",
                  "stop_reasons": [
                    "Deep truncated: True"
                  ]
                }
              }
            ],
            "tools": [
              {
                "name": "process_activity",
                "time": "2026-10-24T03:57:01.681746+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-FIN-11 in the last 24h'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "process_tree",
                "time": "2026-10-24T03:57:01.682888+00:00",
                "args": {
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. ",
                "status": "已保存返回摘要"
              },
              {
                "name": "historical_execution",
                "time": "2026-10-24T03:57:01.683768+00:00",
                "args": {
                  "days": 90,
                  "process_name": "PowerShell"
                },
                "result": "{'tool': 'historical_execution', 'available': True, 'row_count': 0, 'rows': [], 'query': 'executions of PowerShell across the fleet, last 90d'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "entity_timeline",
                "time": "2026-10-24T03:57:01.684416+00:00",
                "args": {
                  "hours": 90,
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:51:40.277000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-FIN-11",
                "status": "已保存返回摘要"
              },
              {
                "name": "network_connections",
                "time": "2026-10-24T03:57:01.685049+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect",
                "status": "已保存返回摘要"
              },
              {
                "name": "persistence_mechanisms",
                "time": "2026-10-24T03:57:01.685636+00:00",
                "args": {
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data ",
                "status": "已保存返回摘要"
              }
            ]
          }
        ],
        "tenantName": "00000000-0000-0000-0000-000000000001",
        "techniques": [
          "T1059.001"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": 80
        },
        "risk": 95,
        "raw": {
          "id": "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
          "tenant_id": "00000000-0000-0000-0000-000000000001",
          "title": "Office启动隐藏PowerShell [DEMO-FIN-11]",
          "description": "WINWORD.EXE spawned powershell.exe with hidden window on DEMO-FIN-11 under demo.finance. Parent PID 4100, child PID 4200. No payload contents or approval records supplied.",
          "severity": "high",
          "status": "triaged",
          "event_time": "2026-10-24 03:51:40.277842+00:00",
          "case_id": null,
          "confidence": 80,
          "ai_score": 0.95,
          "disposition": "true_positive",
          "raw_event": {
            "full_log": "WINWORD.EXE spawned powershell.exe with hidden window on DEMO-FIN-11 under demo.finance. Parent PID 4100, child PID 4200. No payload contents or approval records supplied.",
            "approval_status": "not_supplied"
          },
          "entities": [
            {
              "type": "host",
              "value": "DEMO-FIN-11"
            },
            {
              "type": "user",
              "value": "demo.finance"
            }
          ],
          "enrichment_data": {},
          "incident_id": "85b81836-be47-4ab0-8c1f-6d360c5fb0a2",
          "original_input": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "source": "showcase-security-sensor",
            "title": "Office启动隐藏PowerShell [DEMO-FIN-11]",
            "description": "WINWORD.EXE spawned powershell.exe with hidden window on DEMO-FIN-11 under demo.finance. Parent PID 4100, child PID 4200. No payload contents or approval records supplied.",
            "severity": "high",
            "hostname": "DEMO-FIN-11",
            "username": "demo.finance",
            "src_ip": "10.78.10.11",
            "dst_ip": "198.51.100.41",
            "mitre_tactics": [
              "Execution"
            ],
            "mitre_techniques": [
              "T1059.001"
            ],
            "risk_score": 0.92,
            "event_time": "2026-10-24T03:51:40.277842+00:00",
            "rule_id": "AUTO-SHOWCASE-20261024-1-rule-1",
            "raw_event": {
              "full_log": "WINWORD.EXE spawned powershell.exe with hidden window on DEMO-FIN-11 under demo.finance. Parent PID 4100, child PID 4200. No payload contents or approval records supplied.",
              "approval_status": "not_supplied"
            },
            "tags": [
              "synthetic",
              "AUTO-SHOWCASE-20261024-1",
              "automatic-showcase"
            ]
          }
        },
        "responseRecommendations": [
          {
            "action": "Isolate host 'DEMO-FIN-11' from network",
            "target": "DEMO-FIN-11",
            "reason": "Critical severity alert with host identifier present",
            "approval": "需要审批",
            "execution": "未执行"
          }
        ]
      }
    },
    {
      "id": "d71b5c96-361d-5c21-b234-0b9ad3f854b2",
      "persistedRecord": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "title": "脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]",
      "description": "process PID 4200 on DEMO-FIN-11 opened TCP/443 to 198.51.100.41, 8192 outbound bytes. Destination is a documentation-only synthetic address; no threat-intel verdict or exfiltration confirmation supplied.",
      "severity": "高",
      "status": "In progress",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "执行",
      "source": "showcase-security-sensor",
      "entityIds": [
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-FIN-11",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.finance",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.10.11",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.41"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-24T03:53:40.277842+00:00",
      "first": "2026-10-24T03:53:40.277842+00:00",
      "last": null,
      "incidentId": "85b81836-be47-4ab0-8c1f-6d360c5fb0a2",
      "caseId": null,
      "comments": [],
      "disposition": "needs_review",
      "hostNames": [
        "DEMO-FIN-11"
      ],
      "tactics": [
        "Execution"
      ],
      "iocKeys": [
        "ip:10.78.10.11",
        "ip:198.51.100.41"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-24T03:53:40.277842+00:00",
            "title": "告警发生",
            "description": "脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]"
          },
          {
            "time": "2026-10-24T03:58:02.261723+00:00",
            "title": "自动分诊完成",
            "description": "verdict=needs_review confidence=0.65"
          },
          {
            "time": "2026-10-24T03:58:13.607780+00:00",
            "title": "调查结果交付",
            "description": "automatic graph delivery: partial"
          }
        ],
        "runs": [
          {
            "id": "74a54314-83c5-58be-b852-d1f22b3fed7e",
            "time": "2026-10-24T03:57:58.978134+00:00",
            "status": "Completed",
            "completion": "partial",
            "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
            "findings": [
              "Auto-triage: verdict=needs_review, confidence=0.65, latency=3237ms",
              "Auto-triage rationale: The alert indicates a script process connecting to a 'documentation-only synthetic address' (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).",
              "Escalating to full pipeline — confidence 0.65 < threshold 0.85",
              "Triage severity: critical (risk_score=0.92)",
              "Extracted 2 IOCs for enrichment: ['10.78.10.11', '198.51.100.41']",
              "MITRE kill chain: {'Unknown': ['T1071.001: Unknown']}",
              "Triage verdict: true_positive (confidence=0.95)",
              "Triage phase complete — proceeding to enrichment",
              "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
              "No strong threat actor attribution possible with current intelligence",
              "Graph context: host:DEMO-FIN-11: 0 nodes (depth=2)",
              "Graph context: user:demo.finance: 0 nodes (depth=2)",
              "{\"tool\": \"authentication_events\", \"available\": false, \"row_count\": 0, \"rows\": [], \"reason\": \"Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.\", \"query\": \"authentication events for demo.finance in the last 24h\"}",
              "Investigation depth: 2 distinct pivots across 6 reasoning steps (strategy: c2-beaconing) — entity_timeline, process_activity.",
              "Coverage gap: the following data classes are not ingested, so this investigation could not check them — authentication_events, network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.",
              "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
              "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
              "Attack stages observed: Unknown. This indicates a single-stage attack.",
              "Investigation verdict: confirmed_incident (confidence=0.95)",
              "Investigation complete. Total proposed actions: 1"
            ],
            "calls": 7,
            "tokens": 22318,
            "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 85b81836-be47-4ab0-8c1f-6d360c5fb0a2\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.95 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.95\n- 1 proposed action(s)\n- (triage) vendor risk_score=0.92\n- (triage) critical-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=needs_review, confidence=0.65, latency=3237ms\n- Auto-triage rationale: The alert indicates a script process connecting to a &#x27;documentation-only synthetic address&#x27; (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).\n- Escalating to full pipeline — confidence 0.65 &lt; threshold 0.85\n- Triage severity: critical (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.10.11&#x27;, &#x27;198.51.100.41&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1071.001: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.95)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-FIN-11: 0 nodes (depth=2)\n- Graph context: user:demo.finance: 0 nodes (depth=2)\n- {&quot;tool&quot;: &quot;authentication_events&quot;, &quot;available&quot;: false, &quot;row_count&quot;: 0, &quot;rows&quot;: [], &quot;reason&quot;: &quot;Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.&quot;, &quot;query&quot;: &quot;authentication events for demo.finance in the last 24h&quot;}\n- Investigation depth: 2 distinct pivots across 6 reasoning steps (strategy: c2-beaconing) — entity_timeline, process_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — authentication_events, network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.95)\n- Investigation complete. Total proposed actions: 1\n\n## MITRE ATT&CK Mappings\n\n- `T1071.001`\n\n## Proposed Actions\n\n| # | Action | Target | Risk | Approval | Rationale |\n|---|--------|--------|------|----------|-----------|\n| 1 | isolate_host | DEMO-FIN-11 | high | yes | Critical severity alert with host identifier present |\n\n_Generated by AiSOC router on 2026-10-24 03:58 UTC_\n",
            "actions": [
              "Isolate host 'DEMO-FIN-11' from network"
            ],
            "steps": [
              {
                "name": "auto_triage:llm",
                "agent": "auto_triage:llm",
                "status": "Completed",
                "input": {},
                "output": {
                  "verdict": "needs_review",
                  "findings": [
                    "Auto-triage: verdict=needs_review, confidence=0.65, latency=3237ms",
                    "Auto-triage rationale: The alert indicates a script process connecting to a 'documentation-only synthetic address' (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).",
                    "Escalating to full pipeline — confidence 0.65 < threshold 0.85"
                  ],
                  "rationale": "LLM auto-triage verdict: needs_review · LLM confidence: 0.65 · Rationale: The alert indicates a script process connecting to a 'documentation-only synthetic address' (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).",
                  "confidence": 0.65,
                  "auto_closed": false
                }
              },
              {
                "name": "triage",
                "agent": "triage",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "triage",
                  "step_status": "completed"
                }
              },
              {
                "name": "enrichment",
                "agent": "enrichment",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "enrichment",
                  "step_status": "completed"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "process_activity",
                  "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-FIN-11 in the last 24h'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "network_connections",
                  "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "entity_timeline",
                  "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:51:40.277000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-FIN-11"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "process_tree",
                  "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hostname": "DEMO-FIN-11"
                  },
                  "tool": "persistence_mechanisms",
                  "result_preview": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "user_name": "demo.finance"
                  },
                  "tool": "authentication_events",
                  "result_preview": "{'tool': 'authentication_events', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'authe"
                }
              },
              {
                "name": "investigation",
                "agent": "investigation",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "investigation",
                  "reason": "Deep stopped before a complete investigation",
                  "step_status": "partial"
                }
              },
              {
                "name": "attack_path",
                "agent": "attack_path",
                "status": "已跳过",
                "input": {},
                "output": {
                  "node": "attack_path",
                  "reason": "no Case linked; attack-path traversal not performed",
                  "step_status": "skipped"
                }
              },
              {
                "name": "automatic_graph",
                "agent": "automatic_graph",
                "status": "Completed",
                "input": {},
                "output": {
                  "workflow": "automatic_graph",
                  "completion": "partial",
                  "stop_reasons": [
                    "Deep truncated: True"
                  ]
                }
              }
            ],
            "tools": [
              {
                "name": "process_activity",
                "time": "2026-10-24T03:58:13.595212+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-FIN-11 in the last 24h'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "network_connections",
                "time": "2026-10-24T03:58:13.596162+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect",
                "status": "已保存返回摘要"
              },
              {
                "name": "entity_timeline",
                "time": "2026-10-24T03:58:13.596876+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:51:40.277000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-FIN-11",
                "status": "已保存返回摘要"
              },
              {
                "name": "process_tree",
                "time": "2026-10-24T03:58:13.598333+00:00",
                "args": {
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. ",
                "status": "已保存返回摘要"
              },
              {
                "name": "persistence_mechanisms",
                "time": "2026-10-24T03:58:13.598954+00:00",
                "args": {
                  "hostname": "DEMO-FIN-11"
                },
                "result": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data ",
                "status": "已保存返回摘要"
              },
              {
                "name": "authentication_events",
                "time": "2026-10-24T03:58:13.599620+00:00",
                "args": {
                  "hours": 24,
                  "user_name": "demo.finance"
                },
                "result": "{'tool': 'authentication_events', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'authe",
                "status": "已保存返回摘要"
              }
            ]
          }
        ],
        "tenantName": "00000000-0000-0000-0000-000000000001",
        "techniques": [
          "T1071.001"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": 80
        },
        "risk": 65,
        "raw": {
          "id": "d71b5c96-361d-5c21-b234-0b9ad3f854b2",
          "tenant_id": "00000000-0000-0000-0000-000000000001",
          "title": "脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]",
          "description": "process PID 4200 on DEMO-FIN-11 opened TCP/443 to 198.51.100.41, 8192 outbound bytes. Destination is a documentation-only synthetic address; no threat-intel verdict or exfiltration confirmation supplied.",
          "severity": "high",
          "status": "triaged",
          "event_time": "2026-10-24 03:53:40.277842+00:00",
          "case_id": null,
          "confidence": 80,
          "ai_score": 0.65,
          "disposition": "needs_review",
          "raw_event": {
            "full_log": "process PID 4200 on DEMO-FIN-11 opened TCP/443 to 198.51.100.41, 8192 outbound bytes. Destination is a documentation-only synthetic address; no threat-intel verdict or exfiltration confirmation supplied.",
            "approval_status": "not_supplied"
          },
          "entities": [
            {
              "type": "host",
              "value": "DEMO-FIN-11"
            },
            {
              "type": "user",
              "value": "demo.finance"
            }
          ],
          "enrichment_data": {},
          "incident_id": "85b81836-be47-4ab0-8c1f-6d360c5fb0a2",
          "original_input": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "source": "showcase-security-sensor",
            "title": "脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]",
            "description": "process PID 4200 on DEMO-FIN-11 opened TCP/443 to 198.51.100.41, 8192 outbound bytes. Destination is a documentation-only synthetic address; no threat-intel verdict or exfiltration confirmation supplied.",
            "severity": "high",
            "hostname": "DEMO-FIN-11",
            "username": "demo.finance",
            "src_ip": "10.78.10.11",
            "dst_ip": "198.51.100.41",
            "mitre_tactics": [
              "Execution"
            ],
            "mitre_techniques": [
              "T1071.001"
            ],
            "risk_score": 0.92,
            "event_time": "2026-10-24T03:53:40.277842+00:00",
            "rule_id": "AUTO-SHOWCASE-20261024-1-rule-2",
            "raw_event": {
              "full_log": "process PID 4200 on DEMO-FIN-11 opened TCP/443 to 198.51.100.41, 8192 outbound bytes. Destination is a documentation-only synthetic address; no threat-intel verdict or exfiltration confirmation supplied.",
              "approval_status": "not_supplied"
            },
            "tags": [
              "synthetic",
              "AUTO-SHOWCASE-20261024-1",
              "automatic-showcase"
            ]
          }
        },
        "responseRecommendations": [
          {
            "action": "Isolate host 'DEMO-FIN-11' from network",
            "target": "DEMO-FIN-11",
            "reason": "Critical severity alert with host identifier present",
            "approval": "需要审批",
            "execution": "未执行"
          }
        ]
      }
    },
    {
      "id": "9181b087-c9e0-5318-990f-085681201a92",
      "persistedRecord": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "title": "进程读取LSASS内存 [DEMO-APP-12]",
      "description": "process diagtool.exe PID 5300 opened lsass.exe on DEMO-APP-12 with memory-read access under demo.ops. The sensor reported handle access only; no credential output file was collected.",
      "severity": "高",
      "status": "In progress",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "执行",
      "source": "showcase-security-sensor",
      "entityIds": [
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-APP-12",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.ops",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.20.12",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.42"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-24T03:52:59.399398+00:00",
      "first": "2026-10-24T03:52:59.399398+00:00",
      "last": null,
      "incidentId": "014cbba0-d7f7-45ec-b87f-d81cc9c24772",
      "caseId": null,
      "comments": [],
      "disposition": "true_positive",
      "hostNames": [
        "DEMO-APP-12"
      ],
      "tactics": [
        "Execution"
      ],
      "iocKeys": [
        "ip:10.78.20.12",
        "ip:198.51.100.42"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-24T03:52:59.399398+00:00",
            "title": "告警发生",
            "description": "进程读取LSASS内存 [DEMO-APP-12]"
          },
          {
            "time": "2026-10-24T03:58:16.245759+00:00",
            "title": "自动分诊完成",
            "description": "verdict=true_positive confidence=0.95"
          },
          {
            "time": "2026-10-24T03:58:34.483260+00:00",
            "title": "调查结果交付",
            "description": "automatic graph delivery: partial"
          }
        ],
        "runs": [
          {
            "id": "fe2e84e8-e421-56d6-aa0b-7c9047a88051",
            "time": "2026-10-24T03:58:13.614496+00:00",
            "status": "Completed",
            "completion": "partial",
            "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
            "findings": [
              "Auto-triage: verdict=true_positive, confidence=0.95, latency=2568ms",
              "Auto-triage rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.",
              "Escalating to full pipeline — TP verdict",
              "Triage severity: high (risk_score=0.92)",
              "Extracted 2 IOCs for enrichment: ['10.78.20.12', '198.51.100.42']",
              "MITRE kill chain: {'Unknown': ['T1003.001: Unknown']}",
              "Triage verdict: true_positive (confidence=0.94)",
              "Triage phase complete — proceeding to enrichment",
              "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
              "No strong threat actor attribution possible with current intelligence",
              "Graph context: host:DEMO-APP-12: 0 nodes (depth=2)",
              "Graph context: user:demo.ops: 0 nodes (depth=2)",
              "[{\"type\": \"ip\", \"value\": \"10.78.20.12\"}]",
              "Investigation depth: 6 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, extract_iocs, fleet_ioc_hunt, lookup_technique, process_activity, technique_activity.",
              "Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.",
              "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
              "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
              "Attack stages observed: Unknown. This indicates a single-stage attack.",
              "Investigation verdict: confirmed_incident (confidence=0.94)",
              "Investigation complete. Total proposed actions: 0"
            ],
            "calls": 7,
            "tokens": 24748,
            "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 014cbba0-d7f7-45ec-b87f-d81cc9c24772\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.94 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.94\n- (triage) vendor risk_score=0.92\n- (triage) high-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=true_positive, confidence=0.95, latency=2568ms\n- Auto-triage rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.\n- Escalating to full pipeline — TP verdict\n- Triage severity: high (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.20.12&#x27;, &#x27;198.51.100.42&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1003.001: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.94)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-APP-12: 0 nodes (depth=2)\n- Graph context: user:demo.ops: 0 nodes (depth=2)\n- [{&quot;type&quot;: &quot;ip&quot;, &quot;value&quot;: &quot;10.78.20.12&quot;}]\n- Investigation depth: 6 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, extract_iocs, fleet_ioc_hunt, lookup_technique, process_activity, technique_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.94)\n- Investigation complete. Total proposed actions: 0\n\n## MITRE ATT&CK Mappings\n\n- `T1003.001`\n\n_Generated by AiSOC router on 2026-10-24 03:58 UTC_\n",
            "actions": [],
            "steps": [
              {
                "name": "auto_triage:llm",
                "agent": "auto_triage:llm",
                "status": "Completed",
                "input": {},
                "output": {
                  "verdict": "true_positive",
                  "findings": [
                    "Auto-triage: verdict=true_positive, confidence=0.95, latency=2568ms",
                    "Auto-triage rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.",
                    "Escalating to full pipeline — TP verdict"
                  ],
                  "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.",
                  "confidence": 0.95,
                  "auto_closed": false
                }
              },
              {
                "name": "triage",
                "agent": "triage",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "triage",
                  "step_status": "completed"
                }
              },
              {
                "name": "enrichment",
                "agent": "enrichment",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "enrichment",
                  "step_status": "completed"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-APP-12"
                  },
                  "tool": "process_activity",
                  "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-APP-12 in the last 24h'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hostname": "DEMO-APP-12"
                  },
                  "tool": "process_tree",
                  "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-APP-12"
                  },
                  "tool": "entity_timeline",
                  "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:52:59.399000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-APP-12"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-APP-12"
                  },
                  "tool": "network_connections",
                  "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hostname": "DEMO-APP-12"
                  },
                  "tool": "persistence_mechanisms",
                  "result_preview": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "days": 7,
                    "indicator": "10.78.20.12"
                  },
                  "tool": "fleet_ioc_hunt",
                  "result_preview": "{'tool': 'fleet_ioc_hunt', 'available': True, 'row_count': 1, 'rows': [{'src_hostname': 'DEMO-APP-12', 'user_name': '', 'connector_type': 'Okta System Log', 'first_seen': '2026-10-24T03:52:59.399000Z'"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "technique_id": "T1003.001"
                  },
                  "tool": "lookup_technique",
                  "result_preview": "{'id': 'T1003.001', 'name': 'Unknown', 'tactic': 'Unknown'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "days": 7,
                    "technique_id": "T1003.001"
                  },
                  "tool": "technique_activity",
                  "result_preview": "{'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1003.001 in the last 7d'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "text": "进程读取LSASS内存 [DEMO-APP-12] — High alert: 进程读取LSASS内存 [DEMO-APP-12] on 10.78.20.12 from showcase-security-sensor"
                  },
                  "tool": "extract_iocs",
                  "result_preview": "[{'type': 'ip', 'value': '10.78.20.12'}]"
                }
              },
              {
                "name": "investigation",
                "agent": "investigation",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "investigation",
                  "reason": "Deep stopped before a complete investigation",
                  "step_status": "partial"
                }
              },
              {
                "name": "attack_path",
                "agent": "attack_path",
                "status": "已跳过",
                "input": {},
                "output": {
                  "node": "attack_path",
                  "reason": "no Case linked; attack-path traversal not performed",
                  "step_status": "skipped"
                }
              },
              {
                "name": "automatic_graph",
                "agent": "automatic_graph",
                "status": "Completed",
                "input": {},
                "output": {
                  "workflow": "automatic_graph",
                  "completion": "partial",
                  "stop_reasons": [
                    "Deep truncated: True"
                  ]
                }
              }
            ],
            "tools": [
              {
                "name": "process_activity",
                "time": "2026-10-24T03:58:34.470348+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-APP-12"
                },
                "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-APP-12 in the last 24h'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "process_tree",
                "time": "2026-10-24T03:58:34.471374+00:00",
                "args": {
                  "hostname": "DEMO-APP-12"
                },
                "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. ",
                "status": "已保存返回摘要"
              },
              {
                "name": "entity_timeline",
                "time": "2026-10-24T03:58:34.472042+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-APP-12"
                },
                "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:52:59.399000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-APP-12",
                "status": "已保存返回摘要"
              },
              {
                "name": "network_connections",
                "time": "2026-10-24T03:58:34.472681+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-APP-12"
                },
                "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect",
                "status": "已保存返回摘要"
              },
              {
                "name": "persistence_mechanisms",
                "time": "2026-10-24T03:58:34.473282+00:00",
                "args": {
                  "hostname": "DEMO-APP-12"
                },
                "result": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data ",
                "status": "已保存返回摘要"
              },
              {
                "name": "fleet_ioc_hunt",
                "time": "2026-10-24T03:58:34.473866+00:00",
                "args": {
                  "days": 7,
                  "indicator": "10.78.20.12"
                },
                "result": "{'tool': 'fleet_ioc_hunt', 'available': True, 'row_count': 1, 'rows': [{'src_hostname': 'DEMO-APP-12', 'user_name': '', 'connector_type': 'Okta System Log', 'first_seen': '2026-10-24T03:52:59.399000Z'",
                "status": "已保存返回摘要"
              },
              {
                "name": "lookup_technique",
                "time": "2026-10-24T03:58:34.474449+00:00",
                "args": {
                  "technique_id": "T1003.001"
                },
                "result": "{'id': 'T1003.001', 'name': 'Unknown', 'tactic': 'Unknown'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "technique_activity",
                "time": "2026-10-24T03:58:34.475015+00:00",
                "args": {
                  "days": 7,
                  "technique_id": "T1003.001"
                },
                "result": "{'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1003.001 in the last 7d'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "extract_iocs",
                "time": "2026-10-24T03:58:34.475612+00:00",
                "args": {
                  "text": "进程读取LSASS内存 [DEMO-APP-12] — High alert: 进程读取LSASS内存 [DEMO-APP-12] on 10.78.20.12 from showcase-security-sensor"
                },
                "result": "[{'type': 'ip', 'value': '10.78.20.12'}]",
                "status": "已保存返回摘要"
              }
            ]
          }
        ],
        "tenantName": "00000000-0000-0000-0000-000000000001",
        "techniques": [
          "T1003.001"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": 80
        },
        "risk": 95,
        "raw": {
          "id": "9181b087-c9e0-5318-990f-085681201a92",
          "tenant_id": "00000000-0000-0000-0000-000000000001",
          "title": "进程读取LSASS内存 [DEMO-APP-12]",
          "description": "process diagtool.exe PID 5300 opened lsass.exe on DEMO-APP-12 with memory-read access under demo.ops. The sensor reported handle access only; no credential output file was collected.",
          "severity": "high",
          "status": "triaged",
          "event_time": "2026-10-24 03:52:59.399398+00:00",
          "case_id": null,
          "confidence": 80,
          "ai_score": 0.95,
          "disposition": "true_positive",
          "raw_event": {
            "full_log": "process diagtool.exe PID 5300 opened lsass.exe on DEMO-APP-12 with memory-read access under demo.ops. The sensor reported handle access only; no credential output file was collected.",
            "approval_status": "not_supplied"
          },
          "entities": [
            {
              "type": "host",
              "value": "DEMO-APP-12"
            },
            {
              "type": "user",
              "value": "demo.ops"
            }
          ],
          "enrichment_data": {},
          "incident_id": "014cbba0-d7f7-45ec-b87f-d81cc9c24772",
          "original_input": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "source": "showcase-security-sensor",
            "title": "进程读取LSASS内存 [DEMO-APP-12]",
            "description": "process diagtool.exe PID 5300 opened lsass.exe on DEMO-APP-12 with memory-read access under demo.ops. The sensor reported handle access only; no credential output file was collected.",
            "severity": "high",
            "hostname": "DEMO-APP-12",
            "username": "demo.ops",
            "src_ip": "10.78.20.12",
            "dst_ip": "198.51.100.42",
            "mitre_tactics": [
              "Execution"
            ],
            "mitre_techniques": [
              "T1003.001"
            ],
            "risk_score": 0.92,
            "event_time": "2026-10-24T03:52:59.399398+00:00",
            "rule_id": "AUTO-SHOWCASE-20261024-2-rule-1",
            "raw_event": {
              "full_log": "process diagtool.exe PID 5300 opened lsass.exe on DEMO-APP-12 with memory-read access under demo.ops. The sensor reported handle access only; no credential output file was collected.",
              "approval_status": "not_supplied"
            },
            "tags": [
              "synthetic",
              "AUTO-SHOWCASE-20261024-2",
              "automatic-showcase"
            ]
          }
        },
        "responseRecommendations": []
      }
    },
    {
      "id": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7",
      "persistedRecord": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "title": "同账号发起SMB远程服务访问 [DEMO-APP-12]",
      "description": "demo.ops on DEMO-APP-12 accessed ADMIN$ over SMB on DEMO-FILE-02 (10.77.20.22) three minutes after the memory-read event. Successful authentication is observed; remote code execution and account authorization remain unverified.",
      "severity": "高",
      "status": "In progress",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "执行",
      "source": "showcase-security-sensor",
      "entityIds": [
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-APP-12",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.ops",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.20.12",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.42"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-24T03:54:59.399398+00:00",
      "first": "2026-10-24T03:54:59.399398+00:00",
      "last": null,
      "incidentId": "014cbba0-d7f7-45ec-b87f-d81cc9c24772",
      "caseId": null,
      "comments": [],
      "disposition": "true_positive",
      "hostNames": [
        "DEMO-APP-12"
      ],
      "tactics": [
        "Execution"
      ],
      "iocKeys": [
        "ip:10.78.20.12",
        "ip:198.51.100.42"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-24T03:54:59.399398+00:00",
            "title": "告警发生",
            "description": "同账号发起SMB远程服务访问 [DEMO-APP-12]"
          },
          {
            "time": "2026-10-24T03:58:37.595655+00:00",
            "title": "自动分诊完成",
            "description": "verdict=true_positive confidence=0.85"
          },
          {
            "time": "2026-10-24T03:58:51.471021+00:00",
            "title": "调查结果交付",
            "description": "automatic graph delivery: partial"
          }
        ],
        "runs": [
          {
            "id": "a134b8e9-a843-5d91-a395-e4e5e1b51fab",
            "time": "2026-10-24T03:58:34.542093+00:00",
            "status": "Completed",
            "completion": "partial",
            "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
            "findings": [
              "Auto-triage: verdict=true_positive, confidence=0.85, latency=3006ms",
              "Auto-triage rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.",
              "Escalating to full pipeline — TP verdict",
              "Triage severity: high (risk_score=0.92)",
              "Extracted 2 IOCs for enrichment: ['10.78.20.12', '198.51.100.42']",
              "MITRE kill chain: {'Unknown': ['T1021.002: Unknown']}",
              "Triage verdict: true_positive (confidence=0.94)",
              "Triage phase complete — proceeding to enrichment",
              "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
              "No strong threat actor attribution possible with current intelligence",
              "Graph context: host:DEMO-APP-12: 0 nodes (depth=2)",
              "Graph context: user:demo.ops: 0 nodes (depth=2)",
              "{\"tool\": \"technique_activity\", \"available\": true, \"row_count\": 0, \"rows\": [], \"query\": \"activity mapped to T1021.002 in the last 90d\"}",
              "Investigation depth: 4 distinct pivots across 6 reasoning steps (strategy: lateral-movement) — entity_timeline, lookup_technique, process_activity, technique_activity.",
              "Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, process_tree. Treat them as unknown rather than clear.",
              "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
              "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
              "Attack stages observed: Unknown. This indicates a single-stage attack.",
              "Investigation verdict: confirmed_incident (confidence=0.94)",
              "Investigation complete. Total proposed actions: 0"
            ],
            "calls": 7,
            "tokens": 22464,
            "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 014cbba0-d7f7-45ec-b87f-d81cc9c24772\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.94 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.94\n- (triage) vendor risk_score=0.92\n- (triage) high-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=true_positive, confidence=0.85, latency=3006ms\n- Auto-triage rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.\n- Escalating to full pipeline — TP verdict\n- Triage severity: high (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.20.12&#x27;, &#x27;198.51.100.42&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1021.002: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.94)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-APP-12: 0 nodes (depth=2)\n- Graph context: user:demo.ops: 0 nodes (depth=2)\n- {&quot;tool&quot;: &quot;technique_activity&quot;, &quot;available&quot;: true, &quot;row_count&quot;: 0, &quot;rows&quot;: [], &quot;query&quot;: &quot;activity mapped to T1021.002 in the last 90d&quot;}\n- Investigation depth: 4 distinct pivots across 6 reasoning steps (strategy: lateral-movement) — entity_timeline, lookup_technique, process_activity, technique_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.94)\n- Investigation complete. Total proposed actions: 0\n\n## MITRE ATT&CK Mappings\n\n- `T1021.002`\n\n_Generated by AiSOC router on 2026-10-24 03:58 UTC_\n",
            "actions": [],
            "steps": [
              {
                "name": "auto_triage:llm",
                "agent": "auto_triage:llm",
                "status": "Completed",
                "input": {},
                "output": {
                  "verdict": "true_positive",
                  "findings": [
                    "Auto-triage: verdict=true_positive, confidence=0.85, latency=3006ms",
                    "Auto-triage rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.",
                    "Escalating to full pipeline — TP verdict"
                  ],
                  "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.85 · Rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.",
                  "confidence": 0.85,
                  "auto_closed": false
                }
              },
              {
                "name": "triage",
                "agent": "triage",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "triage",
                  "step_status": "completed"
                }
              },
              {
                "name": "enrichment",
                "agent": "enrichment",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "enrichment",
                  "step_status": "completed"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-APP-12"
                  },
                  "tool": "process_activity",
                  "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-APP-12 in the last 24h'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hostname": "DEMO-APP-12"
                  },
                  "tool": "process_tree",
                  "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "showcase-security-sensor"
                  },
                  "tool": "network_connections",
                  "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-APP-12"
                  },
                  "tool": "entity_timeline",
                  "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:52:59.399000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-APP-12"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "technique_id": "T1021.002"
                  },
                  "tool": "lookup_technique",
                  "result_preview": "{'id': 'T1021.002', 'name': 'Unknown', 'tactic': 'Unknown'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "days": 90,
                    "technique_id": "T1021.002"
                  },
                  "tool": "technique_activity",
                  "result_preview": "{'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1021.002 in the last 90d'}"
                }
              },
              {
                "name": "investigation",
                "agent": "investigation",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "investigation",
                  "reason": "Deep stopped before a complete investigation",
                  "step_status": "partial"
                }
              },
              {
                "name": "attack_path",
                "agent": "attack_path",
                "status": "已跳过",
                "input": {},
                "output": {
                  "node": "attack_path",
                  "reason": "no Case linked; attack-path traversal not performed",
                  "step_status": "skipped"
                }
              },
              {
                "name": "automatic_graph",
                "agent": "automatic_graph",
                "status": "Completed",
                "input": {},
                "output": {
                  "workflow": "automatic_graph",
                  "completion": "partial",
                  "stop_reasons": [
                    "Deep truncated: True"
                  ]
                }
              }
            ],
            "tools": [
              {
                "name": "process_activity",
                "time": "2026-10-24T03:58:51.460550+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-APP-12"
                },
                "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-APP-12 in the last 24h'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "process_tree",
                "time": "2026-10-24T03:58:51.461451+00:00",
                "args": {
                  "hostname": "DEMO-APP-12"
                },
                "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. ",
                "status": "已保存返回摘要"
              },
              {
                "name": "network_connections",
                "time": "2026-10-24T03:58:51.462091+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "showcase-security-sensor"
                },
                "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect",
                "status": "已保存返回摘要"
              },
              {
                "name": "entity_timeline",
                "time": "2026-10-24T03:58:51.462707+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-APP-12"
                },
                "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:52:59.399000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-APP-12",
                "status": "已保存返回摘要"
              },
              {
                "name": "lookup_technique",
                "time": "2026-10-24T03:58:51.463310+00:00",
                "args": {
                  "technique_id": "T1021.002"
                },
                "result": "{'id': 'T1021.002', 'name': 'Unknown', 'tactic': 'Unknown'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "technique_activity",
                "time": "2026-10-24T03:58:51.463884+00:00",
                "args": {
                  "days": 90,
                  "technique_id": "T1021.002"
                },
                "result": "{'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1021.002 in the last 90d'}",
                "status": "已保存返回摘要"
              }
            ]
          }
        ],
        "tenantName": "00000000-0000-0000-0000-000000000001",
        "techniques": [
          "T1021.002"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": 80
        },
        "risk": 85,
        "raw": {
          "id": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7",
          "tenant_id": "00000000-0000-0000-0000-000000000001",
          "title": "同账号发起SMB远程服务访问 [DEMO-APP-12]",
          "description": "demo.ops on DEMO-APP-12 accessed ADMIN$ over SMB on DEMO-FILE-02 (10.77.20.22) three minutes after the memory-read event. Successful authentication is observed; remote code execution and account authorization remain unverified.",
          "severity": "high",
          "status": "triaged",
          "event_time": "2026-10-24 03:54:59.399398+00:00",
          "case_id": null,
          "confidence": 80,
          "ai_score": 0.85,
          "disposition": "true_positive",
          "raw_event": {
            "full_log": "demo.ops on DEMO-APP-12 accessed ADMIN$ over SMB on DEMO-FILE-02 (10.77.20.22) three minutes after the memory-read event. Successful authentication is observed; remote code execution and account authorization remain unverified.",
            "approval_status": "not_supplied"
          },
          "entities": [
            {
              "type": "host",
              "value": "DEMO-APP-12"
            },
            {
              "type": "user",
              "value": "demo.ops"
            }
          ],
          "enrichment_data": {},
          "incident_id": "014cbba0-d7f7-45ec-b87f-d81cc9c24772",
          "original_input": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "source": "showcase-security-sensor",
            "title": "同账号发起SMB远程服务访问 [DEMO-APP-12]",
            "description": "demo.ops on DEMO-APP-12 accessed ADMIN$ over SMB on DEMO-FILE-02 (10.77.20.22) three minutes after the memory-read event. Successful authentication is observed; remote code execution and account authorization remain unverified.",
            "severity": "high",
            "hostname": "DEMO-APP-12",
            "username": "demo.ops",
            "src_ip": "10.78.20.12",
            "dst_ip": "198.51.100.42",
            "mitre_tactics": [
              "Execution"
            ],
            "mitre_techniques": [
              "T1021.002"
            ],
            "risk_score": 0.92,
            "event_time": "2026-10-24T03:54:59.399398+00:00",
            "rule_id": "AUTO-SHOWCASE-20261024-2-rule-2",
            "raw_event": {
              "full_log": "demo.ops on DEMO-APP-12 accessed ADMIN$ over SMB on DEMO-FILE-02 (10.77.20.22) three minutes after the memory-read event. Successful authentication is observed; remote code execution and account authorization remain unverified.",
              "approval_status": "not_supplied"
            },
            "tags": [
              "synthetic",
              "AUTO-SHOWCASE-20261024-2",
              "automatic-showcase"
            ]
          }
        },
        "responseRecommendations": []
      }
    },
    {
      "id": "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
      "persistedRecord": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "title": "服务账号批量读取并生成归档 [DEMO-DATA-13]",
      "description": "demo.export read 120 files under /srv/finance-demo on DEMO-DATA-13 and archive-demo created /tmp/finance-demo.tar (12 MiB). File names and contents are synthetic. No approved export job record supplied.",
      "severity": "高",
      "status": "In progress",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "执行",
      "source": "showcase-security-sensor",
      "entityIds": [
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-DATA-13",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.export",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.30.13",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.43"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-24T03:53:44.520078+00:00",
      "first": "2026-10-24T03:53:44.520078+00:00",
      "last": null,
      "incidentId": "775bf856-91e9-413b-8777-f2366f27102b",
      "caseId": null,
      "comments": [],
      "disposition": "true_positive",
      "hostNames": [
        "DEMO-DATA-13"
      ],
      "tactics": [
        "Execution"
      ],
      "iocKeys": [
        "ip:10.78.30.13",
        "ip:198.51.100.43"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-24T03:53:44.520078+00:00",
            "title": "告警发生",
            "description": "服务账号批量读取并生成归档 [DEMO-DATA-13]"
          },
          {
            "time": "2026-10-24T03:58:54.510311+00:00",
            "title": "自动分诊完成",
            "description": "verdict=true_positive confidence=0.95"
          },
          {
            "time": "2026-10-24T03:59:08.691972+00:00",
            "title": "调查结果交付",
            "description": "automatic graph delivery: partial"
          }
        ],
        "runs": [
          {
            "id": "c142792a-b1a0-5d5c-9a64-4a89db4d6b67",
            "time": "2026-10-24T03:58:51.500997+00:00",
            "status": "Completed",
            "completion": "partial",
            "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
            "findings": [
              "Auto-triage: verdict=true_positive, confidence=0.95, latency=2907ms",
              "Auto-triage rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.",
              "Escalating to full pipeline — TP verdict",
              "Triage severity: high (risk_score=0.92)",
              "Extracted 2 IOCs for enrichment: ['10.78.30.13', '198.51.100.43']",
              "MITRE kill chain: {'Unknown': ['T1560.001: Unknown']}",
              "Triage verdict: true_positive (confidence=0.94)",
              "Triage phase complete — proceeding to enrichment",
              "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
              "No strong threat actor attribution possible with current intelligence",
              "Graph context: host:DEMO-DATA-13: 0 nodes (depth=2)",
              "Graph context: user:demo.export: 0 nodes (depth=2)",
              "[{\"type\": \"ip\", \"value\": \"10.78.30.13\"}]",
              "Investigation depth: 4 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, extract_iocs, lookup_technique, process_activity.",
              "Coverage gap: the following data classes are not ingested, so this investigation could not check them — historical_execution, network_connections, process_tree. Treat them as unknown rather than clear.",
              "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
              "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
              "Attack stages observed: Unknown. This indicates a single-stage attack.",
              "Investigation verdict: confirmed_incident (confidence=0.94)",
              "Investigation complete. Total proposed actions: 0"
            ],
            "calls": 7,
            "tokens": 23351,
            "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 775bf856-91e9-413b-8777-f2366f27102b\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.94 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.94\n- (triage) vendor risk_score=0.92\n- (triage) high-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=true_positive, confidence=0.95, latency=2907ms\n- Auto-triage rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.\n- Escalating to full pipeline — TP verdict\n- Triage severity: high (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.30.13&#x27;, &#x27;198.51.100.43&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1560.001: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.94)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-DATA-13: 0 nodes (depth=2)\n- Graph context: user:demo.export: 0 nodes (depth=2)\n- [{&quot;type&quot;: &quot;ip&quot;, &quot;value&quot;: &quot;10.78.30.13&quot;}]\n- Investigation depth: 4 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, extract_iocs, lookup_technique, process_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — historical_execution, network_connections, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.94)\n- Investigation complete. Total proposed actions: 0\n\n## MITRE ATT&CK Mappings\n\n- `T1560.001`\n\n_Generated by AiSOC router on 2026-10-24 03:59 UTC_\n",
            "actions": [],
            "steps": [
              {
                "name": "auto_triage:llm",
                "agent": "auto_triage:llm",
                "status": "Completed",
                "input": {},
                "output": {
                  "verdict": "true_positive",
                  "findings": [
                    "Auto-triage: verdict=true_positive, confidence=0.95, latency=2907ms",
                    "Auto-triage rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.",
                    "Escalating to full pipeline — TP verdict"
                  ],
                  "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.",
                  "confidence": 0.95,
                  "auto_closed": false
                }
              },
              {
                "name": "triage",
                "agent": "triage",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "triage",
                  "step_status": "completed"
                }
              },
              {
                "name": "enrichment",
                "agent": "enrichment",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "enrichment",
                  "step_status": "completed"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-DATA-13"
                  },
                  "tool": "process_activity",
                  "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-DATA-13 in the last 24h'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hostname": "DEMO-DATA-13"
                  },
                  "tool": "process_tree",
                  "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-DATA-13"
                  },
                  "tool": "entity_timeline",
                  "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:53:44.520000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-DATA-1"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "technique_id": "T1560.001"
                  },
                  "tool": "lookup_technique",
                  "result_preview": "{'id': 'T1560.001', 'name': 'Unknown', 'tactic': 'Unknown'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "hours": 24,
                    "hostname": "DEMO-DATA-13"
                  },
                  "tool": "network_connections",
                  "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "days": 30
                  },
                  "tool": "historical_execution",
                  "result_preview": "{'tool': 'historical_execution', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Supply either process_name or sha256.'}"
                }
              },
              {
                "name": "deep-investigator",
                "agent": "deep-investigator",
                "status": "Completed",
                "input": {},
                "output": {
                  "args": {
                    "text": "服务账号批量读取并生成归档 [DEMO-DATA-13] — High alert: 服务账号批量读取并生成归档 [DEMO-DATA-13] on 10.78.30.13 from showcase-security-sensor"
                  },
                  "tool": "extract_iocs",
                  "result_preview": "[{'type': 'ip', 'value': '10.78.30.13'}]"
                }
              },
              {
                "name": "investigation",
                "agent": "investigation",
                "status": "Completed",
                "input": {},
                "output": {
                  "node": "investigation",
                  "reason": "Deep stopped before a complete investigation",
                  "step_status": "partial"
                }
              },
              {
                "name": "attack_path",
                "agent": "attack_path",
                "status": "已跳过",
                "input": {},
                "output": {
                  "node": "attack_path",
                  "reason": "no Case linked; attack-path traversal not performed",
                  "step_status": "skipped"
                }
              },
              {
                "name": "automatic_graph",
                "agent": "automatic_graph",
                "status": "Completed",
                "input": {},
                "output": {
                  "workflow": "automatic_graph",
                  "completion": "partial",
                  "stop_reasons": [
                    "Deep truncated: True"
                  ]
                }
              }
            ],
            "tools": [
              {
                "name": "process_activity",
                "time": "2026-10-24T03:59:08.680864+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-DATA-13"
                },
                "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-DATA-13 in the last 24h'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "process_tree",
                "time": "2026-10-24T03:59:08.681854+00:00",
                "args": {
                  "hostname": "DEMO-DATA-13"
                },
                "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. ",
                "status": "已保存返回摘要"
              },
              {
                "name": "entity_timeline",
                "time": "2026-10-24T03:59:08.682540+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-DATA-13"
                },
                "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:53:44.520000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-DATA-1",
                "status": "已保存返回摘要"
              },
              {
                "name": "lookup_technique",
                "time": "2026-10-24T03:59:08.683157+00:00",
                "args": {
                  "technique_id": "T1560.001"
                },
                "result": "{'id': 'T1560.001', 'name': 'Unknown', 'tactic': 'Unknown'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "network_connections",
                "time": "2026-10-24T03:59:08.683774+00:00",
                "args": {
                  "hours": 24,
                  "hostname": "DEMO-DATA-13"
                },
                "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect",
                "status": "已保存返回摘要"
              },
              {
                "name": "historical_execution",
                "time": "2026-10-24T03:59:08.684356+00:00",
                "args": {
                  "days": 30
                },
                "result": "{'tool': 'historical_execution', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Supply either process_name or sha256.'}",
                "status": "已保存返回摘要"
              },
              {
                "name": "extract_iocs",
                "time": "2026-10-24T03:59:08.684925+00:00",
                "args": {
                  "text": "服务账号批量读取并生成归档 [DEMO-DATA-13] — High alert: 服务账号批量读取并生成归档 [DEMO-DATA-13] on 10.78.30.13 from showcase-security-sensor"
                },
                "result": "[{'type': 'ip', 'value': '10.78.30.13'}]",
                "status": "已保存返回摘要"
              }
            ]
          }
        ],
        "tenantName": "00000000-0000-0000-0000-000000000001",
        "techniques": [
          "T1560.001"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": 80
        },
        "risk": 95,
        "raw": {
          "id": "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
          "tenant_id": "00000000-0000-0000-0000-000000000001",
          "title": "服务账号批量读取并生成归档 [DEMO-DATA-13]",
          "description": "demo.export read 120 files under /srv/finance-demo on DEMO-DATA-13 and archive-demo created /tmp/finance-demo.tar (12 MiB). File names and contents are synthetic. No approved export job record supplied.",
          "severity": "high",
          "status": "triaged",
          "event_time": "2026-10-24 03:53:44.520078+00:00",
          "case_id": null,
          "confidence": 80,
          "ai_score": 0.95,
          "disposition": "true_positive",
          "raw_event": {
            "full_log": "demo.export read 120 files under /srv/finance-demo on DEMO-DATA-13 and archive-demo created /tmp/finance-demo.tar (12 MiB). File names and contents are synthetic. No approved export job record supplied.",
            "approval_status": "not_supplied"
          },
          "entities": [
            {
              "type": "host",
              "value": "DEMO-DATA-13"
            },
            {
              "type": "user",
              "value": "demo.export"
            }
          ],
          "enrichment_data": {},
          "incident_id": "775bf856-91e9-413b-8777-f2366f27102b",
          "original_input": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "source": "showcase-security-sensor",
            "title": "服务账号批量读取并生成归档 [DEMO-DATA-13]",
            "description": "demo.export read 120 files under /srv/finance-demo on DEMO-DATA-13 and archive-demo created /tmp/finance-demo.tar (12 MiB). File names and contents are synthetic. No approved export job record supplied.",
            "severity": "high",
            "hostname": "DEMO-DATA-13",
            "username": "demo.export",
            "src_ip": "10.78.30.13",
            "dst_ip": "198.51.100.43",
            "mitre_tactics": [
              "Execution"
            ],
            "mitre_techniques": [
              "T1560.001"
            ],
            "risk_score": 0.92,
            "event_time": "2026-10-24T03:53:44.520078+00:00",
            "rule_id": "AUTO-SHOWCASE-20261024-3-rule-1",
            "raw_event": {
              "full_log": "demo.export read 120 files under /srv/finance-demo on DEMO-DATA-13 and archive-demo created /tmp/finance-demo.tar (12 MiB). File names and contents are synthetic. No approved export job record supplied.",
              "approval_status": "not_supplied"
            },
            "tags": [
              "synthetic",
              "AUTO-SHOWCASE-20261024-3",
              "automatic-showcase"
            ]
          }
        },
        "responseRecommendations": []
      }
    },
    {
      "id": "ef9c21f4-d703-5be8-a6d2-63195e09da36",
      "persistedRecord": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "title": "归档进程向文档地址上传字节 [DEMO-DATA-13]",
      "description": "archive-demo PID 6400 sent 12582912 bytes to 198.51.100.43:443 after creating finance-demo.tar. Transfer metadata is present; destination ownership and remote receipt are not verified. This is a synthetic demonstration, not a real breach.",
      "severity": "高",
      "status": "Resolved",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "执行",
      "source": "showcase-security-sensor",
      "entityIds": [
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-DATA-13",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.export",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.30.13",
        "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.43"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-24T03:55:44.520078+00:00",
      "first": "2026-10-24T03:55:44.520078+00:00",
      "last": null,
      "incidentId": null,
      "caseId": null,
      "comments": [],
      "disposition": "benign",
      "hostNames": [
        "DEMO-DATA-13"
      ],
      "tactics": [
        "Execution"
      ],
      "iocKeys": [
        "ip:10.78.30.13",
        "ip:198.51.100.43"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-24T03:55:44.520078+00:00",
            "title": "告警发生",
            "description": "归档进程向文档地址上传字节 [DEMO-DATA-13]"
          },
          {
            "time": "2026-10-24T03:59:11.134377+00:00",
            "title": "自动分诊完成",
            "description": "verdict=benign confidence=0.95"
          }
        ],
        "runs": [
          {
            "id": "78144611-32a4-56b9-bbc8-917d7900ed68",
            "time": "2026-10-24T03:59:11.134377+00:00",
            "status": "Completed",
            "completion": "not_escalated",
            "stop": "自动分诊已关闭此告警，未进入 Graph / Deep 调查。",
            "findings": [
              "Auto-triage: verdict=benign, confidence=0.95, latency=2338ms",
              "Auto-triage rationale: The raw event explicitly states that this is a 'synthetic demonstration, not a real breach,' indicating the activity is part of a controlled test environment rather than a genuine security incident. Although the alert has a high vendor risk score and correlates with other alerts, the context confirms the behavior is expected and non-threatening within this specific demo scenario. Therefore, it does not represent a valid threat requiring investigation or response.",
              "Auto-closed as benign (confidence 0.95 >= threshold 0.85, env)"
            ],
            "calls": 1,
            "tokens": 1443,
            "report": null,
            "actions": [],
            "steps": [
              {
                "name": "auto_triage:llm",
                "agent": "auto_triage:llm",
                "status": "Completed",
                "input": {},
                "output": {
                  "verdict": "benign",
                  "findings": [
                    "Auto-triage: verdict=benign, confidence=0.95, latency=2338ms",
                    "Auto-triage rationale: The raw event explicitly states that this is a 'synthetic demonstration, not a real breach,' indicating the activity is part of a controlled test environment rather than a genuine security incident. Although the alert has a high vendor risk score and correlates with other alerts, the context confirms the behavior is expected and non-threatening within this specific demo scenario. Therefore, it does not represent a valid threat requiring investigation or response.",
                    "Auto-closed as benign (confidence 0.95 >= threshold 0.85, env)"
                  ],
                  "rationale": "LLM auto-triage verdict: benign · LLM confidence: 0.95 · Rationale: The raw event explicitly states that this is a 'synthetic demonstration, not a real breach,' indicating the activity is part of a controlled test environment rather than a genuine security incident. Although the alert has a high vendor risk score and correlates with other alerts, the context confirms the behavior is expected and non-threatening within this specific demo scenario. Therefore, it does not represent a valid threat requiring investigation or response.",
                  "confidence": 0.95,
                  "auto_closed": true
                }
              }
            ],
            "tools": []
          }
        ],
        "tenantName": "00000000-0000-0000-0000-000000000001",
        "techniques": [
          "T1041"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": 80
        },
        "risk": 95,
        "raw": {
          "id": "ef9c21f4-d703-5be8-a6d2-63195e09da36",
          "tenant_id": "00000000-0000-0000-0000-000000000001",
          "title": "归档进程向文档地址上传字节 [DEMO-DATA-13]",
          "description": "archive-demo PID 6400 sent 12582912 bytes to 198.51.100.43:443 after creating finance-demo.tar. Transfer metadata is present; destination ownership and remote receipt are not verified. This is a synthetic demonstration, not a real breach.",
          "severity": "high",
          "status": "resolved",
          "event_time": "2026-10-24 03:55:44.520078+00:00",
          "case_id": null,
          "confidence": 80,
          "ai_score": 0.95,
          "disposition": "benign",
          "raw_event": {
            "full_log": "archive-demo PID 6400 sent 12582912 bytes to 198.51.100.43:443 after creating finance-demo.tar. Transfer metadata is present; destination ownership and remote receipt are not verified. This is a synthetic demonstration, not a real breach.",
            "approval_status": "not_supplied"
          },
          "entities": [
            {
              "type": "host",
              "value": "DEMO-DATA-13"
            },
            {
              "type": "user",
              "value": "demo.export"
            }
          ],
          "enrichment_data": {},
          "incident_id": null,
          "original_input": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "source": "showcase-security-sensor",
            "title": "归档进程向文档地址上传字节 [DEMO-DATA-13]",
            "description": "archive-demo PID 6400 sent 12582912 bytes to 198.51.100.43:443 after creating finance-demo.tar. Transfer metadata is present; destination ownership and remote receipt are not verified. This is a synthetic demonstration, not a real breach.",
            "severity": "high",
            "hostname": "DEMO-DATA-13",
            "username": "demo.export",
            "src_ip": "10.78.30.13",
            "dst_ip": "198.51.100.43",
            "mitre_tactics": [
              "Execution"
            ],
            "mitre_techniques": [
              "T1041"
            ],
            "risk_score": 0.92,
            "event_time": "2026-10-24T03:55:44.520078+00:00",
            "rule_id": "AUTO-SHOWCASE-20261024-3-rule-2",
            "raw_event": {
              "full_log": "archive-demo PID 6400 sent 12582912 bytes to 198.51.100.43:443 after creating finance-demo.tar. Transfer metadata is present; destination ownership and remote receipt are not verified. This is a synthetic demonstration, not a real breach.",
              "approval_status": "not_supplied"
            },
            "tags": [
              "synthetic",
              "AUTO-SHOWCASE-20261024-3",
              "automatic-showcase"
            ]
          }
        },
        "responseRecommendations": []
      }
    }
  ],
  "assets": [
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-FIN-11",
      "name": "DEMO-FIN-11",
      "type": "device",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.finance",
      "name": "demo.finance",
      "type": "user",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.10.11",
      "name": "10.78.10.11",
      "type": "ip",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.41",
      "name": "198.51.100.41",
      "type": "ip",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-APP-12",
      "name": "DEMO-APP-12",
      "type": "device",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.ops",
      "name": "demo.ops",
      "type": "user",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.20.12",
      "name": "10.78.20.12",
      "type": "ip",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.42",
      "name": "198.51.100.42",
      "type": "ip",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:device:DEMO-DATA-13",
      "name": "DEMO-DATA-13",
      "type": "device",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:user:demo.export",
      "name": "demo.export",
      "type": "user",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:10.78.30.13",
      "name": "10.78.30.13",
      "type": "ip",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    },
    {
      "id": "raw:aisoc20:00000000-0000-0000-0000-000000000001:ip:198.51.100.43",
      "name": "198.51.100.43",
      "type": "ip",
      "inventory": false,
      "tags": [],
      "sourceEnvironment": "aisoc20"
    }
  ],
  "cases": [
    {
      "id": "local-aisoc20-1",
      "title": "Office脚本执行与可疑外联（本地整理）",
      "localCollection": true,
      "sourceCaseId": null,
      "sourceEnvironment": "aisoc20",
      "alertIds": [
        "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
        "d71b5c96-361d-5c21-b234-0b9ad3f854b2"
      ],
      "created": "2026-10-27T23:54:11+00:00",
      "updated": "2026-10-27T23:54:11+00:00",
      "owner": "未分配",
      "status": "New",
      "severity": "高",
      "priority": null,
      "classification": "Not set",
      "tags": [],
      "tasks": [],
      "incidentId": null,
      "description": "按 2026-10-24 AiSOC 演示场景整理的本地案件。输入是合成告警，分诊、查询与报告为当时实际运行结果；源系统未创建 Case。"
    },
    {
      "id": "local-aisoc20-2",
      "title": "凭据访问与远程服务关联（本地整理）",
      "localCollection": true,
      "sourceCaseId": null,
      "sourceEnvironment": "aisoc20",
      "alertIds": [
        "9181b087-c9e0-5318-990f-085681201a92",
        "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7"
      ],
      "created": "2026-10-27T23:54:11+00:00",
      "updated": "2026-10-27T23:54:11+00:00",
      "owner": "未分配",
      "status": "New",
      "severity": "高",
      "priority": null,
      "classification": "Not set",
      "tags": [],
      "tasks": [],
      "incidentId": null,
      "description": "按 2026-10-24 AiSOC 演示场景整理的本地案件。输入是合成告警，分诊、查询与报告为当时实际运行结果；源系统未创建 Case。"
    },
    {
      "id": "local-aisoc20-3",
      "title": "服务账号批量读取与归档外传线索（本地整理）",
      "localCollection": true,
      "sourceCaseId": null,
      "sourceEnvironment": "aisoc20",
      "alertIds": [
        "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
        "ef9c21f4-d703-5be8-a6d2-63195e09da36"
      ],
      "created": "2026-10-27T23:54:11+00:00",
      "updated": "2026-10-27T23:54:11+00:00",
      "owner": "未分配",
      "status": "New",
      "severity": "高",
      "priority": null,
      "classification": "Not set",
      "tags": [],
      "tasks": [],
      "incidentId": null,
      "description": "按 2026-10-24 AiSOC 演示场景整理的本地案件。输入是合成告警，分诊、查询与报告为当时实际运行结果；源系统未创建 Case。"
    }
  ],
  "runs": [
    {
      "id": "b250e383-9221-550f-b192-bc1d62b450f1",
      "alertIds": [
        "6b75ea5e-ce23-598c-9e63-90043bcb53f4"
      ],
      "title": "Office启动隐藏PowerShell [DEMO-FIN-11]",
      "recorded": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "sourceCaseId": null,
      "status": "completed",
      "started": "2026-10-24T03:56:42.472372+00:00",
      "ended": null,
      "completion": "partial",
      "verdict": "confirmed_incident",
      "confidence": 0.95,
      "triage": {
        "verdict": "true_positive",
        "findings": [
          "Auto-triage: verdict=true_positive, confidence=0.95, latency=2684ms",
          "Auto-triage rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.",
          "Escalating to full pipeline — TP verdict"
        ],
        "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.",
        "confidence": 0.95,
        "auto_closed": false
      },
      "findings": [
        "Auto-triage: verdict=true_positive, confidence=0.95, latency=2684ms",
        "Auto-triage rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.",
        "Escalating to full pipeline — TP verdict",
        "Triage severity: critical (risk_score=0.92)",
        "Extracted 2 IOCs for enrichment: ['10.78.10.11', '198.51.100.41']",
        "MITRE kill chain: {'Unknown': ['T1059.001: Unknown']}",
        "Triage verdict: true_positive (confidence=0.95)",
        "Triage phase complete — proceeding to enrichment",
        "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
        "No strong threat actor attribution possible with current intelligence",
        "Graph context: host:DEMO-FIN-11: 0 nodes (depth=2)",
        "Graph context: user:demo.finance: 0 nodes (depth=2)",
        "{\"tool\": \"persistence_mechanisms\", \"available\": false, \"row_count\": 0, \"rows\": [], \"reason\": \"Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data class. An EDR or osquery connector would populate them.\"}",
        "Investigation depth: 3 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, historical_execution, process_activity.",
        "Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.",
        "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
        "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
        "Attack stages observed: Unknown. This indicates a single-stage attack.",
        "Investigation verdict: confirmed_incident (confidence=0.95)",
        "Investigation complete. Total proposed actions: 1"
      ],
      "steps": [
        {
          "seq": 0,
          "kind": "llm_call",
          "name": "auto_triage",
          "time": "2026-10-24T03:56:45.578739+00:00",
          "summary": "model call: triage.classify",
          "payload": {
            "model": "aisoc-triage",
            "purpose": "triage.classify",
            "duration_ms": 2684,
            "prompt_truncated": false,
            "response_truncated": false
          }
        },
        {
          "seq": 1,
          "kind": "triage_verdict",
          "name": "auto_triage:llm",
          "time": "2026-10-24T03:56:45.578739+00:00",
          "summary": "verdict=true_positive confidence=0.95",
          "payload": {
            "verdict": "true_positive",
            "findings": [
              "Auto-triage: verdict=true_positive, confidence=0.95, latency=2684ms",
              "Auto-triage rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.",
              "Escalating to full pipeline — TP verdict"
            ],
            "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.",
            "confidence": 0.95,
            "auto_closed": false
          }
        },
        {
          "seq": 2,
          "kind": "graph_step",
          "name": "triage",
          "time": "2026-10-24T03:56:45.647803+00:00",
          "summary": "graph node 'triage' completed",
          "payload": {
            "node": "triage",
            "step_status": "completed"
          }
        },
        {
          "seq": 3,
          "kind": "graph_step",
          "name": "enrichment",
          "time": "2026-10-24T03:56:45.659373+00:00",
          "summary": "graph node 'enrichment' completed",
          "payload": {
            "node": "enrichment",
            "step_status": "completed"
          }
        },
        {
          "seq": 10000,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:57:01.681746+00:00",
          "summary": "process_activity(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-FIN-11"
            },
            "tool": "process_activity",
            "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-FIN-11 in the last 24h'}"
          }
        },
        {
          "seq": 10001,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:57:01.682888+00:00",
          "summary": "process_tree(hostname)",
          "payload": {
            "args": {
              "hostname": "DEMO-FIN-11"
            },
            "tool": "process_tree",
            "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
          }
        },
        {
          "seq": 10002,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:57:01.683768+00:00",
          "summary": "historical_execution(days, process_name)",
          "payload": {
            "args": {
              "days": 90,
              "process_name": "PowerShell"
            },
            "tool": "historical_execution",
            "result_preview": "{'tool': 'historical_execution', 'available': True, 'row_count': 0, 'rows': [], 'query': 'executions of PowerShell across the fleet, last 90d'}"
          }
        },
        {
          "seq": 10003,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:57:01.684416+00:00",
          "summary": "entity_timeline(hostname, hours)",
          "payload": {
            "args": {
              "hours": 90,
              "hostname": "DEMO-FIN-11"
            },
            "tool": "entity_timeline",
            "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:51:40.277000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-FIN-11"
          }
        },
        {
          "seq": 10004,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:57:01.685049+00:00",
          "summary": "network_connections(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-FIN-11"
            },
            "tool": "network_connections",
            "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
          }
        },
        {
          "seq": 10005,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:57:01.685636+00:00",
          "summary": "persistence_mechanisms(hostname)",
          "payload": {
            "args": {
              "hostname": "DEMO-FIN-11"
            },
            "tool": "persistence_mechanisms",
            "result_preview": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
          }
        },
        {
          "seq": 4,
          "kind": "graph_step",
          "name": "investigation",
          "time": "2026-10-24T03:57:01.687338+00:00",
          "summary": "graph node 'investigation' completed",
          "payload": {
            "node": "investigation",
            "reason": "Deep stopped before a complete investigation",
            "step_status": "partial"
          }
        },
        {
          "seq": 5,
          "kind": "graph_step",
          "name": "attack_path",
          "time": "2026-10-24T03:57:01.688680+00:00",
          "summary": "graph node 'attack_path' completed",
          "payload": {
            "node": "attack_path",
            "reason": "no Case linked; attack-path traversal not performed",
            "step_status": "skipped"
          }
        },
        {
          "seq": 900000,
          "kind": "graph_result",
          "name": "automatic_graph",
          "time": "2026-10-24T03:57:01.734293+00:00",
          "summary": "automatic graph delivery: partial",
          "payload": {
            "workflow": "automatic_graph",
            "completion": "partial",
            "stop_reasons": [
              "Deep truncated: True"
            ]
          }
        }
      ],
      "tools": [
        {
          "name": "process_activity",
          "time": "2026-10-24T03:57:01.681746+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-FIN-11 in the last 24h'}"
        },
        {
          "name": "process_tree",
          "time": "2026-10-24T03:57:01.682888+00:00",
          "args": {
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
        },
        {
          "name": "historical_execution",
          "time": "2026-10-24T03:57:01.683768+00:00",
          "args": {
            "days": 90,
            "process_name": "PowerShell"
          },
          "result": "{'tool': 'historical_execution', 'available': True, 'row_count': 0, 'rows': [], 'query': 'executions of PowerShell across the fleet, last 90d'}"
        },
        {
          "name": "entity_timeline",
          "time": "2026-10-24T03:57:01.684416+00:00",
          "args": {
            "hours": 90,
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:51:40.277000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-FIN-11"
        },
        {
          "name": "network_connections",
          "time": "2026-10-24T03:57:01.685049+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
        },
        {
          "name": "persistence_mechanisms",
          "time": "2026-10-24T03:57:01.685636+00:00",
          "args": {
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
        }
      ],
      "depth": {
        "strategy_id": "endpoint-suspicious-process",
        "narrative": "{\"tool\": \"persistence_mechanisms\", \"available\": false, \"row_count\": 0, \"rows\": [], \"reason\": \"Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data class. An EDR or osquery connector would populate them.\"}",
        "pivots": [
          "process_activity",
          "historical_execution",
          "entity_timeline"
        ],
        "distinct_pivots": 3,
        "iterations": 6,
        "truncated": true,
        "latency_ms": 16010,
        "over_budget": false,
        "tokens": 0,
        "usd_cost": 0.0,
        "cost_capped": false,
        "reached_depth": true,
        "unavailable_data": [
          "process_tree",
          "network_connections",
          "persistence_mechanisms"
        ],
        "customer_tools": [],
        "coverage_notes": [
          "The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown.",
          "The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly."
        ],
        "ledger_rows": 6,
        "mcp_tools": [],
        "mcp_refusals": [],
        "tenant_skill": null,
        "error": null
      },
      "graphs": {},
      "artifacts": [
        {
          "run_id": "b250e383-9221-550f-b192-bc1d62b450f1",
          "kind": "graph_state",
          "event_id": "5cc1d1b4-d920-49d2-8308-d81151642bc2",
          "size_bytes": 8422,
          "actual_bytes": 8422,
          "hash_match": true
        },
        {
          "run_id": "b250e383-9221-550f-b192-bc1d62b450f1",
          "kind": "llm_prompt",
          "event_id": "fb79f624-f58d-4e0d-9022-285bbde8627b",
          "size_bytes": 4995,
          "actual_bytes": 4995,
          "hash_match": true
        },
        {
          "run_id": "b250e383-9221-550f-b192-bc1d62b450f1",
          "kind": "llm_response",
          "event_id": "fb79f624-f58d-4e0d-9022-285bbde8627b",
          "size_bytes": 564,
          "actual_bytes": 564,
          "hash_match": true
        },
        {
          "run_id": "b250e383-9221-550f-b192-bc1d62b450f1",
          "kind": "report_html",
          "event_id": "5cc1d1b4-d920-49d2-8308-d81151642bc2",
          "size_bytes": 4683,
          "actual_bytes": 4683,
          "hash_match": true
        },
        {
          "run_id": "b250e383-9221-550f-b192-bc1d62b450f1",
          "kind": "report_markdown",
          "event_id": "5cc1d1b4-d920-49d2-8308-d81151642bc2",
          "size_bytes": 3384,
          "actual_bytes": 3384,
          "hash_match": true
        }
      ],
      "actions": [
        {
          "id": "993e3488-9808-48bc-9240-f26598f1c878",
          "action_type": "isolate_host",
          "description": "Isolate host 'DEMO-FIN-11' from network",
          "risk_level": "high",
          "target": "DEMO-FIN-11",
          "parameters": {},
          "requires_approval": true,
          "rationale": "Critical severity alert with host identifier present"
        }
      ],
      "executed": [],
      "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 85b81836-be47-4ab0-8c1f-6d360c5fb0a2\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.95 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.95\n- 1 proposed action(s)\n- (triage) vendor risk_score=0.92\n- (triage) critical-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=true_positive, confidence=0.95, latency=2684ms\n- Auto-triage rationale: The alert indicates Word (WINWORD.EXE) spawned a hidden PowerShell instance, a classic indicator of fileless malware or living-off-the-land attacks (MITRE T1059.001). The high vendor risk score (0.92) and the specific behavior of hiding the PowerShell window strongly suggest malicious intent rather than authorized administration. No evidence of scheduled maintenance or approved scanning was provided, making this a valid detection of suspicious activity requiring immediate investigation.\n- Escalating to full pipeline — TP verdict\n- Triage severity: critical (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.10.11&#x27;, &#x27;198.51.100.41&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1059.001: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.95)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-FIN-11: 0 nodes (depth=2)\n- Graph context: user:demo.finance: 0 nodes (depth=2)\n- {&quot;tool&quot;: &quot;persistence_mechanisms&quot;, &quot;available&quot;: false, &quot;row_count&quot;: 0, &quot;rows&quot;: [], &quot;reason&quot;: &quot;Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data class. An EDR or osquery connector would populate them.&quot;}\n- Investigation depth: 3 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, historical_execution, process_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.95)\n- Investigation complete. Total proposed actions: 1\n\n## MITRE ATT&CK Mappings\n\n- `T1059.001`\n\n## Proposed Actions\n\n| # | Action | Target | Risk | Approval | Rationale |\n|---|--------|--------|------|----------|-----------|\n| 1 | isolate_host | DEMO-FIN-11 | high | yes | Critical severity alert with host identifier present |\n\n_Generated by AiSOC router on 2026-10-24 03:57 UTC_\n",
      "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
      "rawStopReasons": [
        "Deep truncated: True"
      ],
      "input": {
        "id": "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
        "title": "Office启动隐藏PowerShell [DEMO-FIN-11]",
        "rule_id": "AUTO-SHOWCASE-20261024-1-rule-1",
        "rule_name": null,
        "severity": "high",
        "src_ip": "10.78.10.11",
        "dst_ip": "198.51.100.41",
        "hostname": "DEMO-FIN-11",
        "username": "demo.finance",
        "file_hash": null,
        "domain": null,
        "url": null,
        "mitre_techniques": [
          "T1059.001"
        ],
        "risk_score": 0.92,
        "raw_event": {
          "full_log": "WINWORD.EXE spawned powershell.exe with hidden window on DEMO-FIN-11 under demo.finance. Parent PID 4100, child PID 4200. No payload contents or approval records supplied.",
          "approval_status": "not_supplied"
        },
        "confidence": 0.7952,
        "fusion_decision": "new_incident",
        "connector_id": null,
        "connector_type": null,
        "source_event_ids": [
          "c2a5496b-3119-4238-a539-1d2c3285ef0b"
        ]
      },
      "input_summary": "Office启动隐藏PowerShell [DEMO-FIN-11] — **High** alert: Office启动隐藏PowerShell [DEMO-FIN-11] on **10.78.10.11** from `showcase-security-sensor`.\n\nWhy we believe it:\n- + **ML priority rank** — 1.00\n- + **Alert severity** — high\n- + **Upstream vendor risk score** — 0.92\n- − **ML anomaly score** — 0.35\n- Confidence: **high** (80/100)\n\nCorrelated activity: this is the **first** alert on a newly opened incident.\n\nRecommended next step:\n- Triage the process tree and quarantine the binary if it is unsigned or rare.",
      "calls": 7,
      "tokens": 22962
    },
    {
      "id": "74a54314-83c5-58be-b852-d1f22b3fed7e",
      "alertIds": [
        "d71b5c96-361d-5c21-b234-0b9ad3f854b2"
      ],
      "title": "脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]",
      "recorded": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "sourceCaseId": null,
      "status": "completed",
      "started": "2026-10-24T03:57:58.978134+00:00",
      "ended": null,
      "completion": "partial",
      "verdict": "confirmed_incident",
      "confidence": 0.95,
      "triage": {
        "verdict": "needs_review",
        "findings": [
          "Auto-triage: verdict=needs_review, confidence=0.65, latency=3237ms",
          "Auto-triage rationale: The alert indicates a script process connecting to a 'documentation-only synthetic address' (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).",
          "Escalating to full pipeline — confidence 0.65 < threshold 0.85"
        ],
        "rationale": "LLM auto-triage verdict: needs_review · LLM confidence: 0.65 · Rationale: The alert indicates a script process connecting to a 'documentation-only synthetic address' (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).",
        "confidence": 0.65,
        "auto_closed": false
      },
      "findings": [
        "Auto-triage: verdict=needs_review, confidence=0.65, latency=3237ms",
        "Auto-triage rationale: The alert indicates a script process connecting to a 'documentation-only synthetic address' (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).",
        "Escalating to full pipeline — confidence 0.65 < threshold 0.85",
        "Triage severity: critical (risk_score=0.92)",
        "Extracted 2 IOCs for enrichment: ['10.78.10.11', '198.51.100.41']",
        "MITRE kill chain: {'Unknown': ['T1071.001: Unknown']}",
        "Triage verdict: true_positive (confidence=0.95)",
        "Triage phase complete — proceeding to enrichment",
        "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
        "No strong threat actor attribution possible with current intelligence",
        "Graph context: host:DEMO-FIN-11: 0 nodes (depth=2)",
        "Graph context: user:demo.finance: 0 nodes (depth=2)",
        "{\"tool\": \"authentication_events\", \"available\": false, \"row_count\": 0, \"rows\": [], \"reason\": \"Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.\", \"query\": \"authentication events for demo.finance in the last 24h\"}",
        "Investigation depth: 2 distinct pivots across 6 reasoning steps (strategy: c2-beaconing) — entity_timeline, process_activity.",
        "Coverage gap: the following data classes are not ingested, so this investigation could not check them — authentication_events, network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.",
        "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
        "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
        "Attack stages observed: Unknown. This indicates a single-stage attack.",
        "Investigation verdict: confirmed_incident (confidence=0.95)",
        "Investigation complete. Total proposed actions: 1"
      ],
      "steps": [
        {
          "seq": 0,
          "kind": "llm_call",
          "name": "auto_triage",
          "time": "2026-10-24T03:58:02.261723+00:00",
          "summary": "model call: triage.classify",
          "payload": {
            "model": "aisoc-triage",
            "purpose": "triage.classify",
            "duration_ms": 3237,
            "prompt_truncated": false,
            "response_truncated": false
          }
        },
        {
          "seq": 1,
          "kind": "triage_verdict",
          "name": "auto_triage:llm",
          "time": "2026-10-24T03:58:02.261723+00:00",
          "summary": "verdict=needs_review confidence=0.65",
          "payload": {
            "verdict": "needs_review",
            "findings": [
              "Auto-triage: verdict=needs_review, confidence=0.65, latency=3237ms",
              "Auto-triage rationale: The alert indicates a script process connecting to a 'documentation-only synthetic address' (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).",
              "Escalating to full pipeline — confidence 0.65 < threshold 0.85"
            ],
            "rationale": "LLM auto-triage verdict: needs_review · LLM confidence: 0.65 · Rationale: The alert indicates a script process connecting to a 'documentation-only synthetic address' (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).",
            "confidence": 0.65,
            "auto_closed": false
          }
        },
        {
          "seq": 2,
          "kind": "graph_step",
          "name": "triage",
          "time": "2026-10-24T03:58:02.306491+00:00",
          "summary": "graph node 'triage' completed",
          "payload": {
            "node": "triage",
            "step_status": "completed"
          }
        },
        {
          "seq": 3,
          "kind": "graph_step",
          "name": "enrichment",
          "time": "2026-10-24T03:58:02.317847+00:00",
          "summary": "graph node 'enrichment' completed",
          "payload": {
            "node": "enrichment",
            "step_status": "completed"
          }
        },
        {
          "seq": 10000,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:13.595212+00:00",
          "summary": "process_activity(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-FIN-11"
            },
            "tool": "process_activity",
            "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-FIN-11 in the last 24h'}"
          }
        },
        {
          "seq": 10001,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:13.596162+00:00",
          "summary": "network_connections(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-FIN-11"
            },
            "tool": "network_connections",
            "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
          }
        },
        {
          "seq": 10002,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:13.596876+00:00",
          "summary": "entity_timeline(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-FIN-11"
            },
            "tool": "entity_timeline",
            "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:51:40.277000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-FIN-11"
          }
        },
        {
          "seq": 10003,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:13.598333+00:00",
          "summary": "process_tree(hostname)",
          "payload": {
            "args": {
              "hostname": "DEMO-FIN-11"
            },
            "tool": "process_tree",
            "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
          }
        },
        {
          "seq": 10004,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:13.598954+00:00",
          "summary": "persistence_mechanisms(hostname)",
          "payload": {
            "args": {
              "hostname": "DEMO-FIN-11"
            },
            "tool": "persistence_mechanisms",
            "result_preview": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
          }
        },
        {
          "seq": 10005,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:13.599620+00:00",
          "summary": "authentication_events(hours, user_name)",
          "payload": {
            "args": {
              "hours": 24,
              "user_name": "demo.finance"
            },
            "tool": "authentication_events",
            "result_preview": "{'tool': 'authentication_events', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'authe"
          }
        },
        {
          "seq": 4,
          "kind": "graph_step",
          "name": "investigation",
          "time": "2026-10-24T03:58:13.601306+00:00",
          "summary": "graph node 'investigation' completed",
          "payload": {
            "node": "investigation",
            "reason": "Deep stopped before a complete investigation",
            "step_status": "partial"
          }
        },
        {
          "seq": 5,
          "kind": "graph_step",
          "name": "attack_path",
          "time": "2026-10-24T03:58:13.602743+00:00",
          "summary": "graph node 'attack_path' completed",
          "payload": {
            "node": "attack_path",
            "reason": "no Case linked; attack-path traversal not performed",
            "step_status": "skipped"
          }
        },
        {
          "seq": 900000,
          "kind": "graph_result",
          "name": "automatic_graph",
          "time": "2026-10-24T03:58:13.607780+00:00",
          "summary": "automatic graph delivery: partial",
          "payload": {
            "workflow": "automatic_graph",
            "completion": "partial",
            "stop_reasons": [
              "Deep truncated: True"
            ]
          }
        }
      ],
      "tools": [
        {
          "name": "process_activity",
          "time": "2026-10-24T03:58:13.595212+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-FIN-11 in the last 24h'}"
        },
        {
          "name": "network_connections",
          "time": "2026-10-24T03:58:13.596162+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
        },
        {
          "name": "entity_timeline",
          "time": "2026-10-24T03:58:13.596876+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:51:40.277000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-FIN-11"
        },
        {
          "name": "process_tree",
          "time": "2026-10-24T03:58:13.598333+00:00",
          "args": {
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
        },
        {
          "name": "persistence_mechanisms",
          "time": "2026-10-24T03:58:13.598954+00:00",
          "args": {
            "hostname": "DEMO-FIN-11"
          },
          "result": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
        },
        {
          "name": "authentication_events",
          "time": "2026-10-24T03:58:13.599620+00:00",
          "args": {
            "hours": 24,
            "user_name": "demo.finance"
          },
          "result": "{'tool': 'authentication_events', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'authe"
        }
      ],
      "depth": {
        "strategy_id": "c2-beaconing",
        "narrative": "{\"tool\": \"authentication_events\", \"available\": false, \"row_count\": 0, \"rows\": [], \"reason\": \"Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.\", \"query\": \"authentication events for demo.finance in the last 24h\"}",
        "pivots": [
          "process_activity",
          "entity_timeline"
        ],
        "distinct_pivots": 2,
        "iterations": 6,
        "truncated": true,
        "latency_ms": 11265,
        "over_budget": false,
        "tokens": 0,
        "usd_cost": 0.0,
        "cost_capped": false,
        "reached_depth": false,
        "unavailable_data": [
          "network_connections",
          "process_tree",
          "persistence_mechanisms",
          "authentication_events"
        ],
        "customer_tools": [],
        "coverage_notes": [
          "The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown.",
          "The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly."
        ],
        "ledger_rows": 6,
        "mcp_tools": [],
        "mcp_refusals": [],
        "tenant_skill": null,
        "error": null
      },
      "graphs": {},
      "artifacts": [
        {
          "run_id": "74a54314-83c5-58be-b852-d1f22b3fed7e",
          "kind": "graph_state",
          "event_id": "53495dfb-4234-4132-95b9-c7ceb29d5ab7",
          "size_bytes": 8915,
          "actual_bytes": 8915,
          "hash_match": true
        },
        {
          "run_id": "74a54314-83c5-58be-b852-d1f22b3fed7e",
          "kind": "llm_prompt",
          "event_id": "f4dd622d-bcbc-4ce9-ab4f-b9f371d8e2f5",
          "size_bytes": 5258,
          "actual_bytes": 5258,
          "hash_match": true
        },
        {
          "run_id": "74a54314-83c5-58be-b852-d1f22b3fed7e",
          "kind": "llm_response",
          "event_id": "f4dd622d-bcbc-4ce9-ab4f-b9f371d8e2f5",
          "size_bytes": 703,
          "actual_bytes": 703,
          "hash_match": true
        },
        {
          "run_id": "74a54314-83c5-58be-b852-d1f22b3fed7e",
          "kind": "report_html",
          "event_id": "53495dfb-4234-4132-95b9-c7ceb29d5ab7",
          "size_bytes": 4857,
          "actual_bytes": 4857,
          "hash_match": true
        },
        {
          "run_id": "74a54314-83c5-58be-b852-d1f22b3fed7e",
          "kind": "report_markdown",
          "event_id": "53495dfb-4234-4132-95b9-c7ceb29d5ab7",
          "size_bytes": 3558,
          "actual_bytes": 3558,
          "hash_match": true
        }
      ],
      "actions": [
        {
          "id": "5c0ebc06-aabb-440b-93bf-d7882d823f96",
          "action_type": "isolate_host",
          "description": "Isolate host 'DEMO-FIN-11' from network",
          "risk_level": "high",
          "target": "DEMO-FIN-11",
          "parameters": {},
          "requires_approval": true,
          "rationale": "Critical severity alert with host identifier present"
        }
      ],
      "executed": [],
      "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 85b81836-be47-4ab0-8c1f-6d360c5fb0a2\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.95 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.95\n- 1 proposed action(s)\n- (triage) vendor risk_score=0.92\n- (triage) critical-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=needs_review, confidence=0.65, latency=3237ms\n- Auto-triage rationale: The alert indicates a script process connecting to a &#x27;documentation-only synthetic address&#x27; (198.51.100.41), which is often used in testing or benign documentation scenarios. However, the high vendor risk score (0.92), the involvement of a script process, and the correlation with other alerts in an incident suggest potential malicious activity like data exfiltration or C2 communication. Since the destination is explicitly described as synthetic and no exfiltration confirmation is provided, human review is required to distinguish between a false positive (legitimate documentation access) and a true positive (covert channel).\n- Escalating to full pipeline — confidence 0.65 &lt; threshold 0.85\n- Triage severity: critical (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.10.11&#x27;, &#x27;198.51.100.41&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1071.001: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.95)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-FIN-11: 0 nodes (depth=2)\n- Graph context: user:demo.finance: 0 nodes (depth=2)\n- {&quot;tool&quot;: &quot;authentication_events&quot;, &quot;available&quot;: false, &quot;row_count&quot;: 0, &quot;rows&quot;: [], &quot;reason&quot;: &quot;Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.&quot;, &quot;query&quot;: &quot;authentication events for demo.finance in the last 24h&quot;}\n- Investigation depth: 2 distinct pivots across 6 reasoning steps (strategy: c2-beaconing) — entity_timeline, process_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — authentication_events, network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.95)\n- Investigation complete. Total proposed actions: 1\n\n## MITRE ATT&CK Mappings\n\n- `T1071.001`\n\n## Proposed Actions\n\n| # | Action | Target | Risk | Approval | Rationale |\n|---|--------|--------|------|----------|-----------|\n| 1 | isolate_host | DEMO-FIN-11 | high | yes | Critical severity alert with host identifier present |\n\n_Generated by AiSOC router on 2026-10-24 03:58 UTC_\n",
      "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
      "rawStopReasons": [
        "Deep truncated: True"
      ],
      "input": {
        "id": "d71b5c96-361d-5c21-b234-0b9ad3f854b2",
        "title": "脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]",
        "rule_id": "AUTO-SHOWCASE-20261024-1-rule-2",
        "rule_name": null,
        "severity": "high",
        "src_ip": "10.78.10.11",
        "dst_ip": "198.51.100.41",
        "hostname": "DEMO-FIN-11",
        "username": "demo.finance",
        "file_hash": null,
        "domain": null,
        "url": null,
        "mitre_techniques": [
          "T1071.001"
        ],
        "risk_score": 0.92,
        "raw_event": {
          "full_log": "process PID 4200 on DEMO-FIN-11 opened TCP/443 to 198.51.100.41, 8192 outbound bytes. Destination is a documentation-only synthetic address; no threat-intel verdict or exfiltration confirmation supplied.",
          "approval_status": "not_supplied"
        },
        "confidence": 0.7952,
        "fusion_decision": "correlated",
        "connector_id": null,
        "connector_type": null,
        "source_event_ids": [
          "66353cc8-4721-4ce6-979b-ef8343d0b1cf"
        ]
      },
      "input_summary": "脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11] — **High** alert: 脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11] on **10.78.10.11** from `showcase-security-sensor`.\n\nWhy we believe it:\n- + **ML priority rank** — 1.00\n- + **Alert severity** — high\n- + **Upstream vendor risk score** — 0.92\n- − **ML anomaly score** — 0.35\n- Confidence: **high** (80/100)\n\nCorrelated activity: this alert is part of an incident with **2** related alerts. Risk-based alerting has accumulated **118** points on `user:demo.finance` before this alert fired.\n\nRecommended next step:\n- Triage the process tree and quarantine the binary if it is unsigned or rare.",
      "calls": 7,
      "tokens": 22318
    },
    {
      "id": "fe2e84e8-e421-56d6-aa0b-7c9047a88051",
      "alertIds": [
        "9181b087-c9e0-5318-990f-085681201a92"
      ],
      "title": "进程读取LSASS内存 [DEMO-APP-12]",
      "recorded": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "sourceCaseId": null,
      "status": "completed",
      "started": "2026-10-24T03:58:13.614496+00:00",
      "ended": null,
      "completion": "partial",
      "verdict": "confirmed_incident",
      "confidence": 0.9420000000000001,
      "triage": {
        "verdict": "true_positive",
        "findings": [
          "Auto-triage: verdict=true_positive, confidence=0.95, latency=2568ms",
          "Auto-triage rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.",
          "Escalating to full pipeline — TP verdict"
        ],
        "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.",
        "confidence": 0.95,
        "auto_closed": false
      },
      "findings": [
        "Auto-triage: verdict=true_positive, confidence=0.95, latency=2568ms",
        "Auto-triage rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.",
        "Escalating to full pipeline — TP verdict",
        "Triage severity: high (risk_score=0.92)",
        "Extracted 2 IOCs for enrichment: ['10.78.20.12', '198.51.100.42']",
        "MITRE kill chain: {'Unknown': ['T1003.001: Unknown']}",
        "Triage verdict: true_positive (confidence=0.94)",
        "Triage phase complete — proceeding to enrichment",
        "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
        "No strong threat actor attribution possible with current intelligence",
        "Graph context: host:DEMO-APP-12: 0 nodes (depth=2)",
        "Graph context: user:demo.ops: 0 nodes (depth=2)",
        "[{\"type\": \"ip\", \"value\": \"10.78.20.12\"}]",
        "Investigation depth: 6 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, extract_iocs, fleet_ioc_hunt, lookup_technique, process_activity, technique_activity.",
        "Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.",
        "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
        "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
        "Attack stages observed: Unknown. This indicates a single-stage attack.",
        "Investigation verdict: confirmed_incident (confidence=0.94)",
        "Investigation complete. Total proposed actions: 0"
      ],
      "steps": [
        {
          "seq": 0,
          "kind": "llm_call",
          "name": "auto_triage",
          "time": "2026-10-24T03:58:16.245759+00:00",
          "summary": "model call: triage.classify",
          "payload": {
            "model": "aisoc-triage",
            "purpose": "triage.classify",
            "duration_ms": 2567,
            "prompt_truncated": false,
            "response_truncated": false
          }
        },
        {
          "seq": 1,
          "kind": "triage_verdict",
          "name": "auto_triage:llm",
          "time": "2026-10-24T03:58:16.245759+00:00",
          "summary": "verdict=true_positive confidence=0.95",
          "payload": {
            "verdict": "true_positive",
            "findings": [
              "Auto-triage: verdict=true_positive, confidence=0.95, latency=2568ms",
              "Auto-triage rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.",
              "Escalating to full pipeline — TP verdict"
            ],
            "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.",
            "confidence": 0.95,
            "auto_closed": false
          }
        },
        {
          "seq": 2,
          "kind": "graph_step",
          "name": "triage",
          "time": "2026-10-24T03:58:16.290318+00:00",
          "summary": "graph node 'triage' completed",
          "payload": {
            "node": "triage",
            "step_status": "completed"
          }
        },
        {
          "seq": 3,
          "kind": "graph_step",
          "name": "enrichment",
          "time": "2026-10-24T03:58:16.300939+00:00",
          "summary": "graph node 'enrichment' completed",
          "payload": {
            "node": "enrichment",
            "step_status": "completed"
          }
        },
        {
          "seq": 10000,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.470348+00:00",
          "summary": "process_activity(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-APP-12"
            },
            "tool": "process_activity",
            "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-APP-12 in the last 24h'}"
          }
        },
        {
          "seq": 10001,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.471374+00:00",
          "summary": "process_tree(hostname)",
          "payload": {
            "args": {
              "hostname": "DEMO-APP-12"
            },
            "tool": "process_tree",
            "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
          }
        },
        {
          "seq": 10002,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.472042+00:00",
          "summary": "entity_timeline(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-APP-12"
            },
            "tool": "entity_timeline",
            "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:52:59.399000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-APP-12"
          }
        },
        {
          "seq": 10003,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.472681+00:00",
          "summary": "network_connections(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-APP-12"
            },
            "tool": "network_connections",
            "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
          }
        },
        {
          "seq": 10004,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.473282+00:00",
          "summary": "persistence_mechanisms(hostname)",
          "payload": {
            "args": {
              "hostname": "DEMO-APP-12"
            },
            "tool": "persistence_mechanisms",
            "result_preview": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
          }
        },
        {
          "seq": 10005,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.473866+00:00",
          "summary": "fleet_ioc_hunt(days, indicator)",
          "payload": {
            "args": {
              "days": 7,
              "indicator": "10.78.20.12"
            },
            "tool": "fleet_ioc_hunt",
            "result_preview": "{'tool': 'fleet_ioc_hunt', 'available': True, 'row_count': 1, 'rows': [{'src_hostname': 'DEMO-APP-12', 'user_name': '', 'connector_type': 'Okta System Log', 'first_seen': '2026-10-24T03:52:59.399000Z'"
          }
        },
        {
          "seq": 10006,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.474449+00:00",
          "summary": "lookup_technique(technique_id)",
          "payload": {
            "args": {
              "technique_id": "T1003.001"
            },
            "tool": "lookup_technique",
            "result_preview": "{'id': 'T1003.001', 'name': 'Unknown', 'tactic': 'Unknown'}"
          }
        },
        {
          "seq": 10007,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.475015+00:00",
          "summary": "technique_activity(days, technique_id)",
          "payload": {
            "args": {
              "days": 7,
              "technique_id": "T1003.001"
            },
            "tool": "technique_activity",
            "result_preview": "{'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1003.001 in the last 7d'}"
          }
        },
        {
          "seq": 10008,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:34.475612+00:00",
          "summary": "extract_iocs(text)",
          "payload": {
            "args": {
              "text": "进程读取LSASS内存 [DEMO-APP-12] — High alert: 进程读取LSASS内存 [DEMO-APP-12] on 10.78.20.12 from showcase-security-sensor"
            },
            "tool": "extract_iocs",
            "result_preview": "[{'type': 'ip', 'value': '10.78.20.12'}]"
          }
        },
        {
          "seq": 4,
          "kind": "graph_step",
          "name": "investigation",
          "time": "2026-10-24T03:58:34.477591+00:00",
          "summary": "graph node 'investigation' completed",
          "payload": {
            "node": "investigation",
            "reason": "Deep stopped before a complete investigation",
            "step_status": "partial"
          }
        },
        {
          "seq": 5,
          "kind": "graph_step",
          "name": "attack_path",
          "time": "2026-10-24T03:58:34.478953+00:00",
          "summary": "graph node 'attack_path' completed",
          "payload": {
            "node": "attack_path",
            "reason": "no Case linked; attack-path traversal not performed",
            "step_status": "skipped"
          }
        },
        {
          "seq": 900000,
          "kind": "graph_result",
          "name": "automatic_graph",
          "time": "2026-10-24T03:58:34.483260+00:00",
          "summary": "automatic graph delivery: partial",
          "payload": {
            "workflow": "automatic_graph",
            "completion": "partial",
            "stop_reasons": [
              "Deep truncated: True"
            ]
          }
        }
      ],
      "tools": [
        {
          "name": "process_activity",
          "time": "2026-10-24T03:58:34.470348+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-APP-12"
          },
          "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-APP-12 in the last 24h'}"
        },
        {
          "name": "process_tree",
          "time": "2026-10-24T03:58:34.471374+00:00",
          "args": {
            "hostname": "DEMO-APP-12"
          },
          "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
        },
        {
          "name": "entity_timeline",
          "time": "2026-10-24T03:58:34.472042+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-APP-12"
          },
          "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:52:59.399000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-APP-12"
        },
        {
          "name": "network_connections",
          "time": "2026-10-24T03:58:34.472681+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-APP-12"
          },
          "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
        },
        {
          "name": "persistence_mechanisms",
          "time": "2026-10-24T03:58:34.473282+00:00",
          "args": {
            "hostname": "DEMO-APP-12"
          },
          "result": "{'tool': 'persistence_mechanisms', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Persistence mechanisms (run keys, scheduled tasks, launch agents, cron) are not stored as a distinct data "
        },
        {
          "name": "fleet_ioc_hunt",
          "time": "2026-10-24T03:58:34.473866+00:00",
          "args": {
            "days": 7,
            "indicator": "10.78.20.12"
          },
          "result": "{'tool': 'fleet_ioc_hunt', 'available': True, 'row_count': 1, 'rows': [{'src_hostname': 'DEMO-APP-12', 'user_name': '', 'connector_type': 'Okta System Log', 'first_seen': '2026-10-24T03:52:59.399000Z'"
        },
        {
          "name": "lookup_technique",
          "time": "2026-10-24T03:58:34.474449+00:00",
          "args": {
            "technique_id": "T1003.001"
          },
          "result": "{'id': 'T1003.001', 'name': 'Unknown', 'tactic': 'Unknown'}"
        },
        {
          "name": "technique_activity",
          "time": "2026-10-24T03:58:34.475015+00:00",
          "args": {
            "days": 7,
            "technique_id": "T1003.001"
          },
          "result": "{'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1003.001 in the last 7d'}"
        },
        {
          "name": "extract_iocs",
          "time": "2026-10-24T03:58:34.475612+00:00",
          "args": {
            "text": "进程读取LSASS内存 [DEMO-APP-12] — High alert: 进程读取LSASS内存 [DEMO-APP-12] on 10.78.20.12 from showcase-security-sensor"
          },
          "result": "[{'type': 'ip', 'value': '10.78.20.12'}]"
        }
      ],
      "depth": {
        "strategy_id": "endpoint-suspicious-process",
        "narrative": "[{\"type\": \"ip\", \"value\": \"10.78.20.12\"}]",
        "pivots": [
          "process_activity",
          "entity_timeline",
          "fleet_ioc_hunt",
          "lookup_technique",
          "technique_activity",
          "extract_iocs"
        ],
        "distinct_pivots": 6,
        "iterations": 6,
        "truncated": true,
        "latency_ms": 18157,
        "over_budget": false,
        "tokens": 0,
        "usd_cost": 0.0,
        "cost_capped": false,
        "reached_depth": true,
        "unavailable_data": [
          "process_tree",
          "network_connections",
          "persistence_mechanisms"
        ],
        "customer_tools": [],
        "coverage_notes": [
          "The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown.",
          "The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly."
        ],
        "ledger_rows": 9,
        "mcp_tools": [],
        "mcp_refusals": [],
        "tenant_skill": null,
        "error": null
      },
      "graphs": {},
      "artifacts": [
        {
          "run_id": "fe2e84e8-e421-56d6-aa0b-7c9047a88051",
          "kind": "graph_state",
          "event_id": "5cbea989-4554-42c8-aa63-2c0bc3475bac",
          "size_bytes": 7694,
          "actual_bytes": 7694,
          "hash_match": true
        },
        {
          "run_id": "fe2e84e8-e421-56d6-aa0b-7c9047a88051",
          "kind": "llm_prompt",
          "event_id": "59af9885-cbfd-418a-954d-6cfbd3769da8",
          "size_bytes": 5009,
          "actual_bytes": 5009,
          "hash_match": true
        },
        {
          "run_id": "fe2e84e8-e421-56d6-aa0b-7c9047a88051",
          "kind": "llm_response",
          "event_id": "59af9885-cbfd-418a-954d-6cfbd3769da8",
          "size_bytes": 532,
          "actual_bytes": 532,
          "hash_match": true
        },
        {
          "run_id": "fe2e84e8-e421-56d6-aa0b-7c9047a88051",
          "kind": "report_html",
          "event_id": "5cbea989-4554-42c8-aa63-2c0bc3475bac",
          "size_bytes": 4072,
          "actual_bytes": 4072,
          "hash_match": true
        },
        {
          "run_id": "fe2e84e8-e421-56d6-aa0b-7c9047a88051",
          "kind": "report_markdown",
          "event_id": "5cbea989-4554-42c8-aa63-2c0bc3475bac",
          "size_bytes": 2883,
          "actual_bytes": 2883,
          "hash_match": true
        }
      ],
      "actions": [],
      "executed": [],
      "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 014cbba0-d7f7-45ec-b87f-d81cc9c24772\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.94 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.94\n- (triage) vendor risk_score=0.92\n- (triage) high-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=true_positive, confidence=0.95, latency=2568ms\n- Auto-triage rationale: The alert correctly detected a process (diagtool.exe) attempting to read LSASS memory, which is a classic indicator of credential dumping (MITRE T1003.001). The high vendor risk score (0.92) and the specific nature of the event strongly suggest malicious activity rather than authorized administration, especially given the lack of an explicit approval status in the raw log. This requires immediate investigation to determine if credentials were exfiltrated.\n- Escalating to full pipeline — TP verdict\n- Triage severity: high (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.20.12&#x27;, &#x27;198.51.100.42&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1003.001: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.94)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-APP-12: 0 nodes (depth=2)\n- Graph context: user:demo.ops: 0 nodes (depth=2)\n- [{&quot;type&quot;: &quot;ip&quot;, &quot;value&quot;: &quot;10.78.20.12&quot;}]\n- Investigation depth: 6 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, extract_iocs, fleet_ioc_hunt, lookup_technique, process_activity, technique_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, persistence_mechanisms, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.94)\n- Investigation complete. Total proposed actions: 0\n\n## MITRE ATT&CK Mappings\n\n- `T1003.001`\n\n_Generated by AiSOC router on 2026-10-24 03:58 UTC_\n",
      "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
      "rawStopReasons": [
        "Deep truncated: True"
      ],
      "input": {
        "id": "9181b087-c9e0-5318-990f-085681201a92",
        "title": "进程读取LSASS内存 [DEMO-APP-12]",
        "rule_id": "AUTO-SHOWCASE-20261024-2-rule-1",
        "rule_name": null,
        "severity": "high",
        "src_ip": "10.78.20.12",
        "dst_ip": "198.51.100.42",
        "hostname": "DEMO-APP-12",
        "username": "demo.ops",
        "file_hash": null,
        "domain": null,
        "url": null,
        "mitre_techniques": [
          "T1003.001"
        ],
        "risk_score": 0.92,
        "raw_event": {
          "full_log": "process diagtool.exe PID 5300 opened lsass.exe on DEMO-APP-12 with memory-read access under demo.ops. The sensor reported handle access only; no credential output file was collected.",
          "approval_status": "not_supplied"
        },
        "confidence": 0.7952,
        "fusion_decision": "new_incident",
        "connector_id": null,
        "connector_type": null,
        "source_event_ids": [
          "e08fb5c6-ae60-45bb-94b5-e13568b064b5"
        ]
      },
      "input_summary": "进程读取LSASS内存 [DEMO-APP-12] — **High** alert: 进程读取LSASS内存 [DEMO-APP-12] on **10.78.20.12** from `showcase-security-sensor`.\n\nWhy we believe it:\n- + **ML priority rank** — 1.00\n- + **Alert severity** — high\n- + **Upstream vendor risk score** — 0.92\n- − **ML anomaly score** — 0.35\n- Confidence: **high** (80/100)\n\nCorrelated activity: this is the **first** alert on a newly opened incident.\n\nRecommended next step:\n- Triage the process tree and quarantine the binary if it is unsigned or rare.",
      "calls": 7,
      "tokens": 24748
    },
    {
      "id": "a134b8e9-a843-5d91-a395-e4e5e1b51fab",
      "alertIds": [
        "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7"
      ],
      "title": "同账号发起SMB远程服务访问 [DEMO-APP-12]",
      "recorded": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "sourceCaseId": null,
      "status": "completed",
      "started": "2026-10-24T03:58:34.542093+00:00",
      "ended": null,
      "completion": "partial",
      "verdict": "confirmed_incident",
      "confidence": 0.9420000000000001,
      "triage": {
        "verdict": "true_positive",
        "findings": [
          "Auto-triage: verdict=true_positive, confidence=0.85, latency=3006ms",
          "Auto-triage rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.",
          "Escalating to full pipeline — TP verdict"
        ],
        "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.85 · Rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.",
        "confidence": 0.85,
        "auto_closed": false
      },
      "findings": [
        "Auto-triage: verdict=true_positive, confidence=0.85, latency=3006ms",
        "Auto-triage rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.",
        "Escalating to full pipeline — TP verdict",
        "Triage severity: high (risk_score=0.92)",
        "Extracted 2 IOCs for enrichment: ['10.78.20.12', '198.51.100.42']",
        "MITRE kill chain: {'Unknown': ['T1021.002: Unknown']}",
        "Triage verdict: true_positive (confidence=0.94)",
        "Triage phase complete — proceeding to enrichment",
        "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
        "No strong threat actor attribution possible with current intelligence",
        "Graph context: host:DEMO-APP-12: 0 nodes (depth=2)",
        "Graph context: user:demo.ops: 0 nodes (depth=2)",
        "{\"tool\": \"technique_activity\", \"available\": true, \"row_count\": 0, \"rows\": [], \"query\": \"activity mapped to T1021.002 in the last 90d\"}",
        "Investigation depth: 4 distinct pivots across 6 reasoning steps (strategy: lateral-movement) — entity_timeline, lookup_technique, process_activity, technique_activity.",
        "Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, process_tree. Treat them as unknown rather than clear.",
        "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
        "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
        "Attack stages observed: Unknown. This indicates a single-stage attack.",
        "Investigation verdict: confirmed_incident (confidence=0.94)",
        "Investigation complete. Total proposed actions: 0"
      ],
      "steps": [
        {
          "seq": 0,
          "kind": "llm_call",
          "name": "auto_triage",
          "time": "2026-10-24T03:58:37.595655+00:00",
          "summary": "model call: triage.classify",
          "payload": {
            "model": "aisoc-triage",
            "purpose": "triage.classify",
            "duration_ms": 3006,
            "prompt_truncated": false,
            "response_truncated": false
          }
        },
        {
          "seq": 1,
          "kind": "triage_verdict",
          "name": "auto_triage:llm",
          "time": "2026-10-24T03:58:37.595655+00:00",
          "summary": "verdict=true_positive confidence=0.85",
          "payload": {
            "verdict": "true_positive",
            "findings": [
              "Auto-triage: verdict=true_positive, confidence=0.85, latency=3006ms",
              "Auto-triage rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.",
              "Escalating to full pipeline — TP verdict"
            ],
            "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.85 · Rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.",
            "confidence": 0.85,
            "auto_closed": false
          }
        },
        {
          "seq": 2,
          "kind": "graph_step",
          "name": "triage",
          "time": "2026-10-24T03:58:37.641845+00:00",
          "summary": "graph node 'triage' completed",
          "payload": {
            "node": "triage",
            "step_status": "completed"
          }
        },
        {
          "seq": 3,
          "kind": "graph_step",
          "name": "enrichment",
          "time": "2026-10-24T03:58:37.652443+00:00",
          "summary": "graph node 'enrichment' completed",
          "payload": {
            "node": "enrichment",
            "step_status": "completed"
          }
        },
        {
          "seq": 10000,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:51.460550+00:00",
          "summary": "process_activity(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-APP-12"
            },
            "tool": "process_activity",
            "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-APP-12 in the last 24h'}"
          }
        },
        {
          "seq": 10001,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:51.461451+00:00",
          "summary": "process_tree(hostname)",
          "payload": {
            "args": {
              "hostname": "DEMO-APP-12"
            },
            "tool": "process_tree",
            "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
          }
        },
        {
          "seq": 10002,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:51.462091+00:00",
          "summary": "network_connections(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "showcase-security-sensor"
            },
            "tool": "network_connections",
            "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
          }
        },
        {
          "seq": 10003,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:51.462707+00:00",
          "summary": "entity_timeline(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-APP-12"
            },
            "tool": "entity_timeline",
            "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:52:59.399000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-APP-12"
          }
        },
        {
          "seq": 10004,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:51.463310+00:00",
          "summary": "lookup_technique(technique_id)",
          "payload": {
            "args": {
              "technique_id": "T1021.002"
            },
            "tool": "lookup_technique",
            "result_preview": "{'id': 'T1021.002', 'name': 'Unknown', 'tactic': 'Unknown'}"
          }
        },
        {
          "seq": 10005,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:58:51.463884+00:00",
          "summary": "technique_activity(days, technique_id)",
          "payload": {
            "args": {
              "days": 90,
              "technique_id": "T1021.002"
            },
            "tool": "technique_activity",
            "result_preview": "{'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1021.002 in the last 90d'}"
          }
        },
        {
          "seq": 4,
          "kind": "graph_step",
          "name": "investigation",
          "time": "2026-10-24T03:58:51.465479+00:00",
          "summary": "graph node 'investigation' completed",
          "payload": {
            "node": "investigation",
            "reason": "Deep stopped before a complete investigation",
            "step_status": "partial"
          }
        },
        {
          "seq": 5,
          "kind": "graph_step",
          "name": "attack_path",
          "time": "2026-10-24T03:58:51.466764+00:00",
          "summary": "graph node 'attack_path' completed",
          "payload": {
            "node": "attack_path",
            "reason": "no Case linked; attack-path traversal not performed",
            "step_status": "skipped"
          }
        },
        {
          "seq": 900000,
          "kind": "graph_result",
          "name": "automatic_graph",
          "time": "2026-10-24T03:58:51.471021+00:00",
          "summary": "automatic graph delivery: partial",
          "payload": {
            "workflow": "automatic_graph",
            "completion": "partial",
            "stop_reasons": [
              "Deep truncated: True"
            ]
          }
        }
      ],
      "tools": [
        {
          "name": "process_activity",
          "time": "2026-10-24T03:58:51.460550+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-APP-12"
          },
          "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-APP-12 in the last 24h'}"
        },
        {
          "name": "process_tree",
          "time": "2026-10-24T03:58:51.461451+00:00",
          "args": {
            "hostname": "DEMO-APP-12"
          },
          "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
        },
        {
          "name": "network_connections",
          "time": "2026-10-24T03:58:51.462091+00:00",
          "args": {
            "hours": 24,
            "hostname": "showcase-security-sensor"
          },
          "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
        },
        {
          "name": "entity_timeline",
          "time": "2026-10-24T03:58:51.462707+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-APP-12"
          },
          "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:52:59.399000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-APP-12"
        },
        {
          "name": "lookup_technique",
          "time": "2026-10-24T03:58:51.463310+00:00",
          "args": {
            "technique_id": "T1021.002"
          },
          "result": "{'id': 'T1021.002', 'name': 'Unknown', 'tactic': 'Unknown'}"
        },
        {
          "name": "technique_activity",
          "time": "2026-10-24T03:58:51.463884+00:00",
          "args": {
            "days": 90,
            "technique_id": "T1021.002"
          },
          "result": "{'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1021.002 in the last 90d'}"
        }
      ],
      "depth": {
        "strategy_id": "lateral-movement",
        "narrative": "{\"tool\": \"technique_activity\", \"available\": true, \"row_count\": 0, \"rows\": [], \"query\": \"activity mapped to T1021.002 in the last 90d\"}",
        "pivots": [
          "process_activity",
          "entity_timeline",
          "lookup_technique",
          "technique_activity"
        ],
        "distinct_pivots": 4,
        "iterations": 6,
        "truncated": true,
        "latency_ms": 13796,
        "over_budget": false,
        "tokens": 0,
        "usd_cost": 0.0,
        "cost_capped": false,
        "reached_depth": true,
        "unavailable_data": [
          "process_tree",
          "network_connections"
        ],
        "customer_tools": [],
        "coverage_notes": [
          "The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown.",
          "The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly."
        ],
        "ledger_rows": 6,
        "mcp_tools": [],
        "mcp_refusals": [],
        "tenant_skill": null,
        "error": null
      },
      "graphs": {},
      "artifacts": [
        {
          "run_id": "a134b8e9-a843-5d91-a395-e4e5e1b51fab",
          "kind": "graph_state",
          "event_id": "32756f35-02d3-4b08-99e0-c4952dce50a7",
          "size_bytes": 7970,
          "actual_bytes": 7970,
          "hash_match": true
        },
        {
          "run_id": "a134b8e9-a843-5d91-a395-e4e5e1b51fab",
          "kind": "llm_prompt",
          "event_id": "faa4a15f-6080-42f7-b7d8-c324c283f4d5",
          "size_bytes": 5141,
          "actual_bytes": 5141,
          "hash_match": true
        },
        {
          "run_id": "a134b8e9-a843-5d91-a395-e4e5e1b51fab",
          "kind": "llm_response",
          "event_id": "faa4a15f-6080-42f7-b7d8-c324c283f4d5",
          "size_bytes": 626,
          "actual_bytes": 626,
          "hash_match": true
        },
        {
          "run_id": "a134b8e9-a843-5d91-a395-e4e5e1b51fab",
          "kind": "report_html",
          "event_id": "32756f35-02d3-4b08-99e0-c4952dce50a7",
          "size_bytes": 4225,
          "actual_bytes": 4225,
          "hash_match": true
        },
        {
          "run_id": "a134b8e9-a843-5d91-a395-e4e5e1b51fab",
          "kind": "report_markdown",
          "event_id": "32756f35-02d3-4b08-99e0-c4952dce50a7",
          "size_bytes": 3036,
          "actual_bytes": 3036,
          "hash_match": true
        }
      ],
      "actions": [],
      "executed": [],
      "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 014cbba0-d7f7-45ec-b87f-d81cc9c24772\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.94 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.94\n- (triage) vendor risk_score=0.92\n- (triage) high-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=true_positive, confidence=0.85, latency=3006ms\n- Auto-triage rationale: The alert indicates a high-risk SMB access attempt to the ADMIN$ share from an external IP (198.51.100.42) to an internal host, correlating with a prior memory-read event. The vendor risk score is critically high (0.92), and the activity aligns with known lateral movement techniques (MITRE T1021.002). Although successful authentication was observed, the context of an external source accessing administrative shares immediately following a memory read suggests a potential compromise or unauthorized lateral movement requiring immediate investigation.\n- Escalating to full pipeline — TP verdict\n- Triage severity: high (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.20.12&#x27;, &#x27;198.51.100.42&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1021.002: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.94)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-APP-12: 0 nodes (depth=2)\n- Graph context: user:demo.ops: 0 nodes (depth=2)\n- {&quot;tool&quot;: &quot;technique_activity&quot;, &quot;available&quot;: true, &quot;row_count&quot;: 0, &quot;rows&quot;: [], &quot;query&quot;: &quot;activity mapped to T1021.002 in the last 90d&quot;}\n- Investigation depth: 4 distinct pivots across 6 reasoning steps (strategy: lateral-movement) — entity_timeline, lookup_technique, process_activity, technique_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — network_connections, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.94)\n- Investigation complete. Total proposed actions: 0\n\n## MITRE ATT&CK Mappings\n\n- `T1021.002`\n\n_Generated by AiSOC router on 2026-10-24 03:58 UTC_\n",
      "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
      "rawStopReasons": [
        "Deep truncated: True"
      ],
      "input": {
        "id": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7",
        "title": "同账号发起SMB远程服务访问 [DEMO-APP-12]",
        "rule_id": "AUTO-SHOWCASE-20261024-2-rule-2",
        "rule_name": null,
        "severity": "high",
        "src_ip": "10.78.20.12",
        "dst_ip": "198.51.100.42",
        "hostname": "DEMO-APP-12",
        "username": "demo.ops",
        "file_hash": null,
        "domain": null,
        "url": null,
        "mitre_techniques": [
          "T1021.002"
        ],
        "risk_score": 0.92,
        "raw_event": {
          "full_log": "demo.ops on DEMO-APP-12 accessed ADMIN$ over SMB on DEMO-FILE-02 (10.77.20.22) three minutes after the memory-read event. Successful authentication is observed; remote code execution and account authorization remain unverified.",
          "approval_status": "not_supplied"
        },
        "confidence": 0.7952,
        "fusion_decision": "correlated",
        "connector_id": null,
        "connector_type": null,
        "source_event_ids": [
          "e97fe5fa-c7c9-4c5a-bfab-38ffb975ec87"
        ]
      },
      "input_summary": "同账号发起SMB远程服务访问 [DEMO-APP-12] — **High** alert: 同账号发起SMB远程服务访问 [DEMO-APP-12] on **10.78.20.12** from `showcase-security-sensor`.\n\nWhy we believe it:\n- + **ML priority rank** — 1.00\n- + **Alert severity** — high\n- + **Upstream vendor risk score** — 0.92\n- − **ML anomaly score** — 0.35\n- Confidence: **high** (80/100)\n\nCorrelated activity: this alert is part of an incident with **2** related alerts.\n\nRecommended next step:\n- Triage the process tree and quarantine the binary if it is unsigned or rare.",
      "calls": 7,
      "tokens": 22464
    },
    {
      "id": "c142792a-b1a0-5d5c-9a64-4a89db4d6b67",
      "alertIds": [
        "3c98c56d-5bde-570c-a0a1-1c4bef90d509"
      ],
      "title": "服务账号批量读取并生成归档 [DEMO-DATA-13]",
      "recorded": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "sourceCaseId": null,
      "status": "completed",
      "started": "2026-10-24T03:58:51.500997+00:00",
      "ended": null,
      "completion": "partial",
      "verdict": "confirmed_incident",
      "confidence": 0.9420000000000001,
      "triage": {
        "verdict": "true_positive",
        "findings": [
          "Auto-triage: verdict=true_positive, confidence=0.95, latency=2907ms",
          "Auto-triage rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.",
          "Escalating to full pipeline — TP verdict"
        ],
        "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.",
        "confidence": 0.95,
        "auto_closed": false
      },
      "findings": [
        "Auto-triage: verdict=true_positive, confidence=0.95, latency=2907ms",
        "Auto-triage rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.",
        "Escalating to full pipeline — TP verdict",
        "Triage severity: high (risk_score=0.92)",
        "Extracted 2 IOCs for enrichment: ['10.78.30.13', '198.51.100.43']",
        "MITRE kill chain: {'Unknown': ['T1560.001: Unknown']}",
        "Triage verdict: true_positive (confidence=0.94)",
        "Triage phase complete — proceeding to enrichment",
        "Enrichment complete: 0 IOCs enriched, none flagged as malicious",
        "No strong threat actor attribution possible with current intelligence",
        "Graph context: host:DEMO-DATA-13: 0 nodes (depth=2)",
        "Graph context: user:demo.export: 0 nodes (depth=2)",
        "[{\"type\": \"ip\", \"value\": \"10.78.30.13\"}]",
        "Investigation depth: 4 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, extract_iocs, lookup_technique, process_activity.",
        "Coverage gap: the following data classes are not ingested, so this investigation could not check them — historical_execution, network_connections, process_tree. Treat them as unknown rather than clear.",
        "Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.",
        "Investigation hit its 6-step cap; the line of enquiry was not exhausted.",
        "Attack stages observed: Unknown. This indicates a single-stage attack.",
        "Investigation verdict: confirmed_incident (confidence=0.94)",
        "Investigation complete. Total proposed actions: 0"
      ],
      "steps": [
        {
          "seq": 0,
          "kind": "llm_call",
          "name": "auto_triage",
          "time": "2026-10-24T03:58:54.510311+00:00",
          "summary": "model call: triage.classify",
          "payload": {
            "model": "aisoc-triage",
            "purpose": "triage.classify",
            "duration_ms": 2907,
            "prompt_truncated": false,
            "response_truncated": false
          }
        },
        {
          "seq": 1,
          "kind": "triage_verdict",
          "name": "auto_triage:llm",
          "time": "2026-10-24T03:58:54.510311+00:00",
          "summary": "verdict=true_positive confidence=0.95",
          "payload": {
            "verdict": "true_positive",
            "findings": [
              "Auto-triage: verdict=true_positive, confidence=0.95, latency=2907ms",
              "Auto-triage rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.",
              "Escalating to full pipeline — TP verdict"
            ],
            "rationale": "LLM auto-triage verdict: true_positive · LLM confidence: 0.95 · Rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.",
            "confidence": 0.95,
            "auto_closed": false
          }
        },
        {
          "seq": 2,
          "kind": "graph_step",
          "name": "triage",
          "time": "2026-10-24T03:58:54.551335+00:00",
          "summary": "graph node 'triage' completed",
          "payload": {
            "node": "triage",
            "step_status": "completed"
          }
        },
        {
          "seq": 3,
          "kind": "graph_step",
          "name": "enrichment",
          "time": "2026-10-24T03:58:54.562019+00:00",
          "summary": "graph node 'enrichment' completed",
          "payload": {
            "node": "enrichment",
            "step_status": "completed"
          }
        },
        {
          "seq": 10000,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:59:08.680864+00:00",
          "summary": "process_activity(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-DATA-13"
            },
            "tool": "process_activity",
            "result_preview": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-DATA-13 in the last 24h'}"
          }
        },
        {
          "seq": 10001,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:59:08.681854+00:00",
          "summary": "process_tree(hostname)",
          "payload": {
            "args": {
              "hostname": "DEMO-DATA-13"
            },
            "tool": "process_tree",
            "result_preview": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
          }
        },
        {
          "seq": 10002,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:59:08.682540+00:00",
          "summary": "entity_timeline(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-DATA-13"
            },
            "tool": "entity_timeline",
            "result_preview": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:53:44.520000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-DATA-1"
          }
        },
        {
          "seq": 10003,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:59:08.683157+00:00",
          "summary": "lookup_technique(technique_id)",
          "payload": {
            "args": {
              "technique_id": "T1560.001"
            },
            "tool": "lookup_technique",
            "result_preview": "{'id': 'T1560.001', 'name': 'Unknown', 'tactic': 'Unknown'}"
          }
        },
        {
          "seq": 10004,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:59:08.683774+00:00",
          "summary": "network_connections(hostname, hours)",
          "payload": {
            "args": {
              "hours": 24,
              "hostname": "DEMO-DATA-13"
            },
            "tool": "network_connections",
            "result_preview": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
          }
        },
        {
          "seq": 10005,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:59:08.684356+00:00",
          "summary": "historical_execution(days)",
          "payload": {
            "args": {
              "days": 30
            },
            "tool": "historical_execution",
            "result_preview": "{'tool': 'historical_execution', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Supply either process_name or sha256.'}"
          }
        },
        {
          "seq": 10006,
          "kind": "tool_call",
          "name": "deep-investigator",
          "time": "2026-10-24T03:59:08.684925+00:00",
          "summary": "extract_iocs(text)",
          "payload": {
            "args": {
              "text": "服务账号批量读取并生成归档 [DEMO-DATA-13] — High alert: 服务账号批量读取并生成归档 [DEMO-DATA-13] on 10.78.30.13 from showcase-security-sensor"
            },
            "tool": "extract_iocs",
            "result_preview": "[{'type': 'ip', 'value': '10.78.30.13'}]"
          }
        },
        {
          "seq": 4,
          "kind": "graph_step",
          "name": "investigation",
          "time": "2026-10-24T03:59:08.686470+00:00",
          "summary": "graph node 'investigation' completed",
          "payload": {
            "node": "investigation",
            "reason": "Deep stopped before a complete investigation",
            "step_status": "partial"
          }
        },
        {
          "seq": 5,
          "kind": "graph_step",
          "name": "attack_path",
          "time": "2026-10-24T03:59:08.687783+00:00",
          "summary": "graph node 'attack_path' completed",
          "payload": {
            "node": "attack_path",
            "reason": "no Case linked; attack-path traversal not performed",
            "step_status": "skipped"
          }
        },
        {
          "seq": 900000,
          "kind": "graph_result",
          "name": "automatic_graph",
          "time": "2026-10-24T03:59:08.691972+00:00",
          "summary": "automatic graph delivery: partial",
          "payload": {
            "workflow": "automatic_graph",
            "completion": "partial",
            "stop_reasons": [
              "Deep truncated: True"
            ]
          }
        }
      ],
      "tools": [
        {
          "name": "process_activity",
          "time": "2026-10-24T03:59:08.680864+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-DATA-13"
          },
          "result": "{'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on DEMO-DATA-13 in the last 24h'}"
        },
        {
          "name": "process_tree",
          "time": "2026-10-24T03:59:08.681854+00:00",
          "args": {
            "hostname": "DEMO-DATA-13"
          },
          "result": "{'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid. "
        },
        {
          "name": "entity_timeline",
          "time": "2026-10-24T03:59:08.682540+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-DATA-13"
          },
          "result": "{'tool': 'entity_timeline', 'available': True, 'row_count': 2, 'rows': [{'event_time': '2026-10-24T03:53:44.520000Z', 'connector_type': 'Okta System Log', 'user_name': '', 'src_hostname': 'DEMO-DATA-1"
        },
        {
          "name": "lookup_technique",
          "time": "2026-10-24T03:59:08.683157+00:00",
          "args": {
            "technique_id": "T1560.001"
          },
          "result": "{'id': 'T1560.001', 'name': 'Unknown', 'tactic': 'Unknown'}"
        },
        {
          "name": "network_connections",
          "time": "2026-10-24T03:59:08.683774+00:00",
          "args": {
            "hours": 24,
            "hostname": "DEMO-DATA-13"
          },
          "result": "{'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect"
        },
        {
          "name": "historical_execution",
          "time": "2026-10-24T03:59:08.684356+00:00",
          "args": {
            "days": 30
          },
          "result": "{'tool': 'historical_execution', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Supply either process_name or sha256.'}"
        },
        {
          "name": "extract_iocs",
          "time": "2026-10-24T03:59:08.684925+00:00",
          "args": {
            "text": "服务账号批量读取并生成归档 [DEMO-DATA-13] — High alert: 服务账号批量读取并生成归档 [DEMO-DATA-13] on 10.78.30.13 from showcase-security-sensor"
          },
          "result": "[{'type': 'ip', 'value': '10.78.30.13'}]"
        }
      ],
      "depth": {
        "strategy_id": "endpoint-suspicious-process",
        "narrative": "[{\"type\": \"ip\", \"value\": \"10.78.30.13\"}]",
        "pivots": [
          "process_activity",
          "entity_timeline",
          "lookup_technique",
          "extract_iocs"
        ],
        "distinct_pivots": 4,
        "iterations": 6,
        "truncated": true,
        "latency_ms": 14105,
        "over_budget": false,
        "tokens": 0,
        "usd_cost": 0.0,
        "cost_capped": false,
        "reached_depth": true,
        "unavailable_data": [
          "process_tree",
          "network_connections",
          "historical_execution"
        ],
        "customer_tools": [],
        "coverage_notes": [
          "The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM's contents as unknown.",
          "The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly."
        ],
        "ledger_rows": 7,
        "mcp_tools": [],
        "mcp_refusals": [],
        "tenant_skill": null,
        "error": null
      },
      "graphs": {},
      "artifacts": [
        {
          "run_id": "c142792a-b1a0-5d5c-9a64-4a89db4d6b67",
          "kind": "graph_state",
          "event_id": "fc27d118-cea2-4ad9-a00c-fdfacc5a22d8",
          "size_bytes": 7836,
          "actual_bytes": 7836,
          "hash_match": true
        },
        {
          "run_id": "c142792a-b1a0-5d5c-9a64-4a89db4d6b67",
          "kind": "llm_prompt",
          "event_id": "7d131ad3-d5e9-4aee-86bc-5f1288328761",
          "size_bytes": 5144,
          "actual_bytes": 5144,
          "hash_match": true
        },
        {
          "run_id": "c142792a-b1a0-5d5c-9a64-4a89db4d6b67",
          "kind": "llm_response",
          "event_id": "7d131ad3-d5e9-4aee-86bc-5f1288328761",
          "size_bytes": 629,
          "actual_bytes": 629,
          "hash_match": true
        },
        {
          "run_id": "c142792a-b1a0-5d5c-9a64-4a89db4d6b67",
          "kind": "report_html",
          "event_id": "fc27d118-cea2-4ad9-a00c-fdfacc5a22d8",
          "size_bytes": 4135,
          "actual_bytes": 4135,
          "hash_match": true
        },
        {
          "run_id": "c142792a-b1a0-5d5c-9a64-4a89db4d6b67",
          "kind": "report_markdown",
          "event_id": "fc27d118-cea2-4ad9-a00c-fdfacc5a22d8",
          "size_bytes": 2946,
          "actual_bytes": 2946,
          "hash_match": true
        }
      ],
      "actions": [],
      "executed": [],
      "report": "# 自动 Graph / Deep 调查\n\n> PARTIAL — 调查未完成；下方原模型判断不代表已验收结论。\n\n- Deep truncated: True\n\n# Incident Report — 775bf856-91e9-413b-8777-f2366f27102b\n\n## Summary\n\n| Field | Value |\n|-------|-------|\n| Verdict | confirmed_incident |\n| Confidence | 0.94 |\n| Status | completed |\n| Topology | automatic_graph |\n\n## Triage Rationale\n\n- triage prior=0.94\n- (triage) vendor risk_score=0.92\n- (triage) high-severity keyword match in alert text\n- (triage) 2 IOC field(s) present\n\n## Findings\n\n- Auto-triage: verdict=true_positive, confidence=0.95, latency=2907ms\n- Auto-triage rationale: The alert correctly detected a service account performing a bulk read of sensitive financial data (/srv/finance-demo) and generating an archive without an approved export job record. The high vendor risk score (0.92), the presence of data exfiltration indicators (bulk read + archive creation), and the specific MITRE technique T1560.001 (Archive Collected Data) confirm this is malicious activity. The lack of an approved record and the high ML priority rank strongly indicate an unauthorized data theft attempt rather than authorized administrative work.\n- Escalating to full pipeline — TP verdict\n- Triage severity: high (risk_score=0.92)\n- Extracted 2 IOCs for enrichment: [&#x27;10.78.30.13&#x27;, &#x27;198.51.100.43&#x27;]\n- MITRE kill chain: {&#x27;Unknown&#x27;: [&#x27;T1560.001: Unknown&#x27;]}\n- Triage verdict: true_positive (confidence=0.94)\n- Triage phase complete — proceeding to enrichment\n- Enrichment complete: 0 IOCs enriched, none flagged as malicious\n- No strong threat actor attribution possible with current intelligence\n- Graph context: host:DEMO-DATA-13: 0 nodes (depth=2)\n- Graph context: user:demo.export: 0 nodes (depth=2)\n- [{&quot;type&quot;: &quot;ip&quot;, &quot;value&quot;: &quot;10.78.30.13&quot;}]\n- Investigation depth: 4 distinct pivots across 6 reasoning steps (strategy: endpoint-suspicious-process) — entity_timeline, extract_iocs, lookup_technique, process_activity.\n- Coverage gap: the following data classes are not ingested, so this investigation could not check them — historical_execution, network_connections, process_tree. Treat them as unknown rather than clear.\n- Sources consulted beyond the AiSOC event lake: The customer has no SIEM connected to AiSOC, so nothing in this investigation searched their SIEM. Treat their SIEM&#x27;s contents as unknown. The customer has no EDR, identity provider or cloud audit connector that AiSOC can read, so this investigation could not consult any vendor directly.\n- Investigation hit its 6-step cap; the line of enquiry was not exhausted.\n- Attack stages observed: Unknown. This indicates a single-stage attack.\n- Investigation verdict: confirmed_incident (confidence=0.94)\n- Investigation complete. Total proposed actions: 0\n\n## MITRE ATT&CK Mappings\n\n- `T1560.001`\n\n_Generated by AiSOC router on 2026-10-24 03:59 UTC_\n",
      "stop": "已达到 Deep 轮次上限（本次 6 轮），调查尚未收束；保留已取得的结果。",
      "rawStopReasons": [
        "Deep truncated: True"
      ],
      "input": {
        "id": "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
        "title": "服务账号批量读取并生成归档 [DEMO-DATA-13]",
        "rule_id": "AUTO-SHOWCASE-20261024-3-rule-1",
        "rule_name": null,
        "severity": "high",
        "src_ip": "10.78.30.13",
        "dst_ip": "198.51.100.43",
        "hostname": "DEMO-DATA-13",
        "username": "demo.export",
        "file_hash": null,
        "domain": null,
        "url": null,
        "mitre_techniques": [
          "T1560.001"
        ],
        "risk_score": 0.92,
        "raw_event": {
          "full_log": "demo.export read 120 files under /srv/finance-demo on DEMO-DATA-13 and archive-demo created /tmp/finance-demo.tar (12 MiB). File names and contents are synthetic. No approved export job record supplied.",
          "approval_status": "not_supplied"
        },
        "confidence": 0.7952,
        "fusion_decision": "new_incident",
        "connector_id": null,
        "connector_type": null,
        "source_event_ids": [
          "0880e7fe-9a4f-4930-a16f-b1f29e36de80"
        ]
      },
      "input_summary": "服务账号批量读取并生成归档 [DEMO-DATA-13] — **High** alert: 服务账号批量读取并生成归档 [DEMO-DATA-13] on **10.78.30.13** from `showcase-security-sensor`.\n\nWhy we believe it:\n- + **ML priority rank** — 1.00\n- + **Alert severity** — high\n- + **Upstream vendor risk score** — 0.92\n- − **ML anomaly score** — 0.35\n- Confidence: **high** (80/100)\n\nCorrelated activity: this is the **first** alert on a newly opened incident.\n\nRecommended next step:\n- Triage the process tree and quarantine the binary if it is unsigned or rare.",
      "calls": 7,
      "tokens": 23351
    },
    {
      "id": "78144611-32a4-56b9-bbc8-917d7900ed68",
      "alertIds": [
        "ef9c21f4-d703-5be8-a6d2-63195e09da36"
      ],
      "title": "归档进程向文档地址上传字节 [DEMO-DATA-13]",
      "recorded": true,
      "sourceEnvironment": "aisoc20",
      "sourceTenantId": "00000000-0000-0000-0000-000000000001",
      "sourceCaseId": null,
      "status": "completed",
      "started": null,
      "ended": null,
      "completion": "not_escalated",
      "verdict": "benign",
      "confidence": null,
      "triage": {
        "verdict": "benign",
        "findings": [
          "Auto-triage: verdict=benign, confidence=0.95, latency=2338ms",
          "Auto-triage rationale: The raw event explicitly states that this is a 'synthetic demonstration, not a real breach,' indicating the activity is part of a controlled test environment rather than a genuine security incident. Although the alert has a high vendor risk score and correlates with other alerts, the context confirms the behavior is expected and non-threatening within this specific demo scenario. Therefore, it does not represent a valid threat requiring investigation or response.",
          "Auto-closed as benign (confidence 0.95 >= threshold 0.85, env)"
        ],
        "rationale": "LLM auto-triage verdict: benign · LLM confidence: 0.95 · Rationale: The raw event explicitly states that this is a 'synthetic demonstration, not a real breach,' indicating the activity is part of a controlled test environment rather than a genuine security incident. Although the alert has a high vendor risk score and correlates with other alerts, the context confirms the behavior is expected and non-threatening within this specific demo scenario. Therefore, it does not represent a valid threat requiring investigation or response.",
        "confidence": 0.95,
        "auto_closed": true
      },
      "findings": [
        "Auto-triage: verdict=benign, confidence=0.95, latency=2338ms",
        "Auto-triage rationale: The raw event explicitly states that this is a 'synthetic demonstration, not a real breach,' indicating the activity is part of a controlled test environment rather than a genuine security incident. Although the alert has a high vendor risk score and correlates with other alerts, the context confirms the behavior is expected and non-threatening within this specific demo scenario. Therefore, it does not represent a valid threat requiring investigation or response.",
        "Auto-closed as benign (confidence 0.95 >= threshold 0.85, env)"
      ],
      "steps": [
        {
          "seq": 0,
          "kind": "llm_call",
          "name": "auto_triage",
          "time": "2026-10-24T03:59:11.134377+00:00",
          "summary": "model call: triage.classify",
          "payload": {
            "model": "aisoc-triage",
            "purpose": "triage.classify",
            "duration_ms": 2338,
            "prompt_truncated": false,
            "response_truncated": false
          }
        },
        {
          "seq": 1,
          "kind": "triage_verdict",
          "name": "auto_triage:llm",
          "time": "2026-10-24T03:59:11.134377+00:00",
          "summary": "verdict=benign confidence=0.95",
          "payload": {
            "verdict": "benign",
            "findings": [
              "Auto-triage: verdict=benign, confidence=0.95, latency=2338ms",
              "Auto-triage rationale: The raw event explicitly states that this is a 'synthetic demonstration, not a real breach,' indicating the activity is part of a controlled test environment rather than a genuine security incident. Although the alert has a high vendor risk score and correlates with other alerts, the context confirms the behavior is expected and non-threatening within this specific demo scenario. Therefore, it does not represent a valid threat requiring investigation or response.",
              "Auto-closed as benign (confidence 0.95 >= threshold 0.85, env)"
            ],
            "rationale": "LLM auto-triage verdict: benign · LLM confidence: 0.95 · Rationale: The raw event explicitly states that this is a 'synthetic demonstration, not a real breach,' indicating the activity is part of a controlled test environment rather than a genuine security incident. Although the alert has a high vendor risk score and correlates with other alerts, the context confirms the behavior is expected and non-threatening within this specific demo scenario. Therefore, it does not represent a valid threat requiring investigation or response.",
            "confidence": 0.95,
            "auto_closed": true
          }
        }
      ],
      "tools": [],
      "depth": null,
      "graphs": {},
      "artifacts": [
        {
          "run_id": "78144611-32a4-56b9-bbc8-917d7900ed68",
          "kind": "llm_prompt",
          "event_id": "5cc659e1-f711-41b2-a6f6-82bfd5d4d4ea",
          "size_bytes": 5179,
          "actual_bytes": 5179,
          "hash_match": true
        },
        {
          "run_id": "78144611-32a4-56b9-bbc8-917d7900ed68",
          "kind": "llm_response",
          "event_id": "5cc659e1-f711-41b2-a6f6-82bfd5d4d4ea",
          "size_bytes": 533,
          "actual_bytes": 533,
          "hash_match": true
        }
      ],
      "actions": [],
      "executed": [],
      "report": null,
      "stop": "自动分诊已关闭此告警，未进入 Graph / Deep 调查。",
      "rawStopReasons": [
        "自动分诊已关闭此告警，未进入 Graph / Deep 调查。"
      ],
      "input": null,
      "input_summary": null,
      "calls": 1,
      "tokens": 1443
    }
  ],
  "graph": {
    "generatedAt": "2026-10-24T04:15:20.198074+00:00",
    "edges": [
      {
        "id": "6b75ea5e-ce23-598c-9e63-90043bcb53f4|OBSERVED_ON|AUTO-SHOWCASE-20261024-1-host",
        "source": "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
        "target": "AUTO-SHOWCASE-20261024-1-host",
        "label": "OBSERVED_ON",
        "attributes": {}
      },
      {
        "id": "6b75ea5e-ce23-598c-9e63-90043bcb53f4|INVOLVES_USER|AUTO-SHOWCASE-20261024-1-user",
        "source": "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
        "target": "AUTO-SHOWCASE-20261024-1-user",
        "label": "INVOLVES_USER",
        "attributes": {}
      },
      {
        "id": "6b75ea5e-ce23-598c-9e63-90043bcb53f4|MAPS_TO|T1059.001",
        "source": "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
        "target": "T1059.001",
        "label": "MAPS_TO",
        "attributes": {}
      },
      {
        "id": "6b75ea5e-ce23-598c-9e63-90043bcb53f4|CONTAINS_IOC|198.51.100.41",
        "source": "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
        "target": "198.51.100.41",
        "label": "CONTAINS_IOC",
        "attributes": {}
      },
      {
        "id": "d71b5c96-361d-5c21-b234-0b9ad3f854b2|OBSERVED_ON|AUTO-SHOWCASE-20261024-1-host",
        "source": "d71b5c96-361d-5c21-b234-0b9ad3f854b2",
        "target": "AUTO-SHOWCASE-20261024-1-host",
        "label": "OBSERVED_ON",
        "attributes": {}
      },
      {
        "id": "d71b5c96-361d-5c21-b234-0b9ad3f854b2|INVOLVES_USER|AUTO-SHOWCASE-20261024-1-user",
        "source": "d71b5c96-361d-5c21-b234-0b9ad3f854b2",
        "target": "AUTO-SHOWCASE-20261024-1-user",
        "label": "INVOLVES_USER",
        "attributes": {}
      },
      {
        "id": "d71b5c96-361d-5c21-b234-0b9ad3f854b2|MAPS_TO|T1071.001",
        "source": "d71b5c96-361d-5c21-b234-0b9ad3f854b2",
        "target": "T1071.001",
        "label": "MAPS_TO",
        "attributes": {}
      },
      {
        "id": "d71b5c96-361d-5c21-b234-0b9ad3f854b2|CONTAINS_IOC|198.51.100.41",
        "source": "d71b5c96-361d-5c21-b234-0b9ad3f854b2",
        "target": "198.51.100.41",
        "label": "CONTAINS_IOC",
        "attributes": {}
      },
      {
        "id": "9181b087-c9e0-5318-990f-085681201a92|OBSERVED_ON|AUTO-SHOWCASE-20261024-2-host",
        "source": "9181b087-c9e0-5318-990f-085681201a92",
        "target": "AUTO-SHOWCASE-20261024-2-host",
        "label": "OBSERVED_ON",
        "attributes": {}
      },
      {
        "id": "9181b087-c9e0-5318-990f-085681201a92|INVOLVES_USER|AUTO-SHOWCASE-20261024-2-user",
        "source": "9181b087-c9e0-5318-990f-085681201a92",
        "target": "AUTO-SHOWCASE-20261024-2-user",
        "label": "INVOLVES_USER",
        "attributes": {}
      },
      {
        "id": "9181b087-c9e0-5318-990f-085681201a92|MAPS_TO|T1003.001",
        "source": "9181b087-c9e0-5318-990f-085681201a92",
        "target": "T1003.001",
        "label": "MAPS_TO",
        "attributes": {}
      },
      {
        "id": "9181b087-c9e0-5318-990f-085681201a92|CONTAINS_IOC|198.51.100.42",
        "source": "9181b087-c9e0-5318-990f-085681201a92",
        "target": "198.51.100.42",
        "label": "CONTAINS_IOC",
        "attributes": {}
      },
      {
        "id": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7|OBSERVED_ON|AUTO-SHOWCASE-20261024-2-host",
        "source": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7",
        "target": "AUTO-SHOWCASE-20261024-2-host",
        "label": "OBSERVED_ON",
        "attributes": {}
      },
      {
        "id": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7|INVOLVES_USER|AUTO-SHOWCASE-20261024-2-user",
        "source": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7",
        "target": "AUTO-SHOWCASE-20261024-2-user",
        "label": "INVOLVES_USER",
        "attributes": {}
      },
      {
        "id": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7|MAPS_TO|T1021.002",
        "source": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7",
        "target": "T1021.002",
        "label": "MAPS_TO",
        "attributes": {}
      },
      {
        "id": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7|CONTAINS_IOC|198.51.100.42",
        "source": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7",
        "target": "198.51.100.42",
        "label": "CONTAINS_IOC",
        "attributes": {}
      },
      {
        "id": "3c98c56d-5bde-570c-a0a1-1c4bef90d509|OBSERVED_ON|AUTO-SHOWCASE-20261024-3-host",
        "source": "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
        "target": "AUTO-SHOWCASE-20261024-3-host",
        "label": "OBSERVED_ON",
        "attributes": {}
      },
      {
        "id": "3c98c56d-5bde-570c-a0a1-1c4bef90d509|INVOLVES_USER|AUTO-SHOWCASE-20261024-3-user",
        "source": "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
        "target": "AUTO-SHOWCASE-20261024-3-user",
        "label": "INVOLVES_USER",
        "attributes": {}
      },
      {
        "id": "3c98c56d-5bde-570c-a0a1-1c4bef90d509|MAPS_TO|T1560.001",
        "source": "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
        "target": "T1560.001",
        "label": "MAPS_TO",
        "attributes": {}
      },
      {
        "id": "3c98c56d-5bde-570c-a0a1-1c4bef90d509|CONTAINS_IOC|198.51.100.43",
        "source": "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
        "target": "198.51.100.43",
        "label": "CONTAINS_IOC",
        "attributes": {}
      },
      {
        "id": "ef9c21f4-d703-5be8-a6d2-63195e09da36|OBSERVED_ON|AUTO-SHOWCASE-20261024-3-host",
        "source": "ef9c21f4-d703-5be8-a6d2-63195e09da36",
        "target": "AUTO-SHOWCASE-20261024-3-host",
        "label": "OBSERVED_ON",
        "attributes": {}
      },
      {
        "id": "ef9c21f4-d703-5be8-a6d2-63195e09da36|INVOLVES_USER|AUTO-SHOWCASE-20261024-3-user",
        "source": "ef9c21f4-d703-5be8-a6d2-63195e09da36",
        "target": "AUTO-SHOWCASE-20261024-3-user",
        "label": "INVOLVES_USER",
        "attributes": {}
      },
      {
        "id": "ef9c21f4-d703-5be8-a6d2-63195e09da36|MAPS_TO|T1041",
        "source": "ef9c21f4-d703-5be8-a6d2-63195e09da36",
        "target": "T1041",
        "label": "MAPS_TO",
        "attributes": {}
      },
      {
        "id": "ef9c21f4-d703-5be8-a6d2-63195e09da36|CONTAINS_IOC|198.51.100.43",
        "source": "ef9c21f4-d703-5be8-a6d2-63195e09da36",
        "target": "198.51.100.43",
        "label": "CONTAINS_IOC",
        "attributes": {}
      }
    ],
    "nodes": [
      {
        "id": "AUTO-SHOWCASE-20261024-1-host",
        "label": "DEMO-FIN-11",
        "kind": "host",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Host"
          ]
        }
      },
      {
        "id": "AUTO-SHOWCASE-20261024-1-user",
        "label": "demo.finance",
        "kind": "user",
        "riskScore": 0.0,
        "severity": null,
        "attributes": {
          "labels": [
            "User"
          ]
        }
      },
      {
        "id": "6b75ea5e-ce23-598c-9e63-90043bcb53f4",
        "label": "Office启动隐藏PowerShell [DEMO-FIN-11]",
        "kind": "alert",
        "riskScore": null,
        "severity": "high",
        "attributes": {
          "labels": [
            "Alert"
          ]
        }
      },
      {
        "id": "d71b5c96-361d-5c21-b234-0b9ad3f854b2",
        "label": "脚本进程向文档地址建立HTTPS连接 [DEMO-FIN-11]",
        "kind": "alert",
        "riskScore": null,
        "severity": "high",
        "attributes": {
          "labels": [
            "Alert"
          ]
        }
      },
      {
        "id": "AUTO-SHOWCASE-20261024-2-host",
        "label": "DEMO-APP-12",
        "kind": "host",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Host"
          ]
        }
      },
      {
        "id": "AUTO-SHOWCASE-20261024-2-user",
        "label": "demo.ops",
        "kind": "user",
        "riskScore": 0.0,
        "severity": null,
        "attributes": {
          "labels": [
            "User"
          ]
        }
      },
      {
        "id": "9181b087-c9e0-5318-990f-085681201a92",
        "label": "进程读取LSASS内存 [DEMO-APP-12]",
        "kind": "alert",
        "riskScore": null,
        "severity": "high",
        "attributes": {
          "labels": [
            "Alert"
          ]
        }
      },
      {
        "id": "198.51.100.42",
        "label": "198.51.100.42",
        "kind": "asset",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "IOC"
          ]
        }
      },
      {
        "id": "306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7",
        "label": "同账号发起SMB远程服务访问 [DEMO-APP-12]",
        "kind": "alert",
        "riskScore": null,
        "severity": "high",
        "attributes": {
          "labels": [
            "Alert"
          ]
        }
      },
      {
        "id": "AUTO-SHOWCASE-20261024-3-host",
        "label": "DEMO-DATA-13",
        "kind": "host",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Host"
          ]
        }
      },
      {
        "id": "AUTO-SHOWCASE-20261024-3-user",
        "label": "demo.export",
        "kind": "user",
        "riskScore": 0.0,
        "severity": null,
        "attributes": {
          "labels": [
            "User"
          ]
        }
      },
      {
        "id": "3c98c56d-5bde-570c-a0a1-1c4bef90d509",
        "label": "服务账号批量读取并生成归档 [DEMO-DATA-13]",
        "kind": "alert",
        "riskScore": null,
        "severity": "high",
        "attributes": {
          "labels": [
            "Alert"
          ]
        }
      },
      {
        "id": "198.51.100.43",
        "label": "198.51.100.43",
        "kind": "asset",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "IOC"
          ]
        }
      },
      {
        "id": "ef9c21f4-d703-5be8-a6d2-63195e09da36",
        "label": "归档进程向文档地址上传字节 [DEMO-DATA-13]",
        "kind": "alert",
        "riskScore": null,
        "severity": "high",
        "attributes": {
          "labels": [
            "Alert"
          ]
        }
      },
      {
        "id": "198.51.100.41",
        "label": "198.51.100.41",
        "kind": "asset",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "IOC"
          ]
        }
      },
      {
        "id": "T1071.001",
        "label": "T1071.001",
        "kind": "technique",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Technique"
          ]
        }
      },
      {
        "id": "T1003.001",
        "label": "T1003.001",
        "kind": "technique",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Technique"
          ]
        }
      },
      {
        "id": "T1021.002",
        "label": "T1021.002",
        "kind": "technique",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Technique"
          ]
        }
      },
      {
        "id": "T1560.001",
        "label": "T1560.001",
        "kind": "technique",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Technique"
          ]
        }
      },
      {
        "id": "T1041",
        "label": "T1041",
        "kind": "technique",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Technique"
          ]
        }
      },
      {
        "id": "T1059.001",
        "label": "T1059.001",
        "kind": "technique",
        "riskScore": null,
        "severity": null,
        "attributes": {
          "labels": [
            "Technique"
          ]
        }
      }
    ]
  },
  "provenance": {
    "environment": "aisoc20",
    "inputKind": "synthetic",
    "capturedAt": "2026-10-25T03:18:12.296817+00:00",
    "collectedAt": "2026-10-27T23:54:11+00:00"
  }
};
