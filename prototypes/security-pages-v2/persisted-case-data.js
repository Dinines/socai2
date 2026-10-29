/* Historical persisted Case and joint Run; no live calls. */
window.persistedCaseData = {
  "cases": [
    {
      "id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
      "title": "Attack context corrected local case 6d0adf",
      "description": "Three synthetic reports sharing one user and host: login, PowerShell, then outbound TLS. Correlation is a hypothesis; no confirmed attack or actual response is requested.",
      "recordedCase": true,
      "sourceEnvironment": "socai2-21",
      "sourceCaseId": "82b1246f-9f34-463c-8c2d-27d2b075c741",
      "sourceTenantId": "5594ae90-f57c-50f5-8332-328b3cad1679",
      "alertIds": [
        "a7f2d535-f009-462f-b52f-a8178c774c8b",
        "8113e8fa-8fee-40a4-967f-80aa5987be50",
        "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5"
      ],
      "sourceRunIds": [
        "e998308a-a353-4647-99f6-10f94ced0ecf"
      ],
      "created": "2026-10-21T11:51:16.007978Z",
      "updated": "2026-10-21T11:51:16.007978Z",
      "owner": "未分配",
      "status": "New",
      "severity": "高",
      "priority": null,
      "classification": "Not set",
      "tags": [],
      "tasks": [],
      "incidentId": null,
      "due": null,
      "sourceRecord": {
        "id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
        "case_number": null,
        "title": "Attack context corrected local case 6d0adf",
        "description": "Three synthetic reports sharing one user and host: login, PowerShell, then outbound TLS. Correlation is a hypothesis; no confirmed attack or actual response is requested.",
        "severity": "high",
        "status": "new",
        "assignee": null,
        "mitre_techniques": [
          "T1078",
          "T1059.001",
          "T1071.001"
        ],
        "alert_ids": [
          "a7f2d535-f009-462f-b52f-a8178c774c8b",
          "8113e8fa-8fee-40a4-967f-80aa5987be50",
          "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5"
        ],
        "observable_graph": {},
        "evidence_chain": [],
        "compliance_frameworks": [],
        "opened_at": "2026-10-21T11:51:16.007978Z",
        "triaged_at": null,
        "resolved_at": null,
        "closed_at": null,
        "reopened_at": null,
        "reopen_count": 0,
        "reopen_reason": null,
        "created_at": "2026-10-21T11:51:16.007978Z",
        "updated_at": "2026-10-21T11:51:16.007978Z",
        "created_by": "1f-20261020-a@test.invalid",
        "tags": {
          "fixture": "attack-context-20261021",
          "evidence": "synthetic"
        },
        "sla_due_at": null,
        "fanout_results": null
      }
    }
  ],
  "runs": [
    {
      "id": "e998308a-a353-4647-99f6-10f94ced0ecf",
      "agentRunId": "12522217-c0ef-4222-8522-ee0fb680c0e6",
      "sourceCaseId": "82b1246f-9f34-463c-8c2d-27d2b075c741",
      "sourceEnvironment": "socai2-21",
      "sourceTenantId": "5594ae90-f57c-50f5-8332-328b3cad1679",
      "title": "Attack context corrected local case 6d0adf",
      "recorded": true,
      "alertIds": [
        "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
        "8113e8fa-8fee-40a4-967f-80aa5987be50",
        "a7f2d535-f009-462f-b52f-a8178c774c8b"
      ],
      "input": {
        "case_id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
        "alerts": [
          {
            "id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
            "title": "Attack context fixture 3: Outbound TLS connection reported",
            "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
            "severity": "high",
            "source": "attack-context-functional-fixture",
            "affected_ips": [
              "203.0.113.77"
            ],
            "affected_hosts": [
              "LAB-ATTACKCTX-20261021-6D0ADF"
            ],
            "affected_users": [
              "lab_attackctx_v2_6d0adf"
            ],
            "event_time": "2026-10-21T11:46:04.491307+00:00",
            "full_log": ""
          },
          {
            "id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
            "title": "Attack context fixture 2: PowerShell execution reported after account login",
            "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
            "severity": "high",
            "source": "attack-context-functional-fixture",
            "affected_ips": [
              "192.0.2.50"
            ],
            "affected_hosts": [
              "LAB-ATTACKCTX-20261021-6D0ADF"
            ],
            "affected_users": [
              "lab_attackctx_v2_6d0adf"
            ],
            "event_time": "2026-10-21T11:38:04.491307+00:00",
            "full_log": ""
          },
          {
            "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
            "title": "Attack context fixture 1: Unusual account login reported",
            "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
            "severity": "high",
            "source": "attack-context-functional-fixture",
            "affected_ips": [
              "192.0.2.50"
            ],
            "affected_hosts": [
              "LAB-ATTACKCTX-20261021-6D0ADF"
            ],
            "affected_users": [
              "lab_attackctx_v2_6d0adf"
            ],
            "event_time": "2026-10-21T11:30:04.491307+00:00",
            "full_log": ""
          }
        ],
        "attack_context_preparation": {
          "status": "success",
          "source": "postgres_alert_projection",
          "error": null,
          "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
          "case_id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
          "alert_id": null,
          "scope": "case",
          "source_alert_ids": [
            "a7f2d535-f009-462f-b52f-a8178c774c8b",
            "8113e8fa-8fee-40a4-967f-80aa5987be50",
            "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5"
          ],
          "truncated": false,
          "evidence_semantics": "source_alert_reported_association; not independently verified attack causality",
          "reason": "source_alerts_projected"
        }
      },
      "input_summary": "Local synthetic functional case. Read-only investigation; shared entities imply candidates, not confirmed causality.\n\nAttack context corrected local case 6d0adf\nThree synthetic reports sharing one user and host: login, PowerShell, then outbound TLS. Correlation is a hypothesis; no confirmed attack or actual response is requested.\n3 correlated alert(s) on this case:\n  - [high] Attack context fixture 1: Unusual account login reported (source: attack-context-functional-fixture)\n  - [high] Attack context fixture 2: PowerShell execution reported after account login (source: attack-context-functional-fixture)\n  - [high] Attack context fixture 3: Outbound TLS connection reported (source: attack-context-functional-fixture)",
      "status": "completed",
      "completion": null,
      "verdict": null,
      "confidence": 0.1,
      "confidenceLabel": "取证分析置信度",
      "findings": [
        "This is a synthetic functional case containing three correlated alerts (unusual login, PowerShell execution, outbound TLS) on a lab environment. While the alerts map to MITRE ATT&CK technique T1071.001 (Application Layer Protocol: Web Protocols) and involve IPs 203.0.113.77 and 192.0.2.50, the source explicitly states these are fixtures for context handoff. No actual intrusion, malware, or successful data access has been confirmed; all observed activity is hypothetical and part of a test scenario.",
        "Analysis of the provided data confirms a synthetic test scenario involving three correlated alerts (login, PowerShell, outbound TLS) on a designated lab host. Due to the explicit 'synthetic functional fixture' labeling and lack of concrete forensic artefacts (files, registry keys, logs), no actual attack causality or harm can be established.",
        "This incident is a synthetic functional test case designed to validate alert correlation logic, not a real security breach. No containment, eradication, or recovery actions are required as no actual intrusion or harm was confirmed."
      ],
      "started": "2026-10-21T11:52:23.080625Z",
      "ended": "2026-10-21T11:53:54.296066Z",
      "steps": [
        {
          "seq": 0,
          "kind": "tool_call",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:23.663922Z",
          "summary": "knowledge_base.fetch_runbooks(tenant_id, query) [FAILED]",
          "payload": {
            "args": {
              "query": "Attack context fixture 3: Outbound TLS connection reported",
              "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679"
            },
            "tool": "knowledge_base.fetch_runbooks",
            "result": {
              "as_of": null,
              "cache": {
                "source": "none",
                "freshness": "not_available",
                "age_seconds": null,
                "ttl_seconds": 120.0
              },
              "limit": 3,
              "query": "Attack context fixture 3: Outbound TLS connection reported",
              "budget": {
                "body_chars": 0,
                "max_body_chars": 3000,
                "max_chunk_chars": 900,
                "truncated_count": 0,
                "dropped_for_budget": 0,
                "encoded_body_chars": 0,
                "max_envelope_chars": 3400
              },
              "reason": "not_configured",
              "source": "api.kb.runbooks.for-triage",
              "status": "unavailable",
              "read_at": "2026-10-21T11:52:23.663670+00:00",
              "runbooks": [],
              "citations": [],
              "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
              "http_status": null,
              "valid_count": 0,
              "adopted_count": 0,
              "prompt_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
              "received_count": 0,
              "model_citations": [],
              "requested_as_of": null,
              "injection_signals": [],
              "without_timestamp": 0,
              "dropped_for_injection": 0,
              "excluded_after_cutoff": 0,
              "excluded_after_update": 0,
              "unresolvable_citations": [],
              "excluded_after_cutoff_total": 0
            },
            "success": false
          }
        },
        {
          "seq": 1,
          "kind": "llm_prompt",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:23.699563Z",
          "summary": "recon: extract IOCs, MITRE techniques, and threat actors",
          "payload": {
            "model": "aisoc-recon",
            "purpose": "recon: extract IOCs, MITRE techniques, and threat actors"
          }
        },
        {
          "seq": 2,
          "kind": "tool_call",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:30.942509Z",
          "summary": "knowledge_base.model_citations(agent)",
          "payload": {
            "args": {
              "agent": "ReconAgent"
            },
            "tool": "knowledge_base.model_citations",
            "result": {
              "cited_sources": [],
              "model_citations": [],
              "unresolvable_citations": []
            },
            "success": true
          }
        },
        {
          "seq": 3,
          "kind": "llm_response",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:30.942552Z",
          "summary": "LLM response (3689 tokens)",
          "payload": {
            "model": "aisoc-recon",
            "cost_source": "gateway",
            "tokens_used": 3689
          }
        },
        {
          "seq": 4,
          "kind": "tool_call",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:32.738384Z",
          "summary": "enrich_ioc(value, type)",
          "payload": {
            "args": {
              "type": "ip",
              "value": "203.0.113.77"
            },
            "tool": "enrich_ioc",
            "result": {
              "value": "203.0.113.77",
              "is_bot": false,
              "is_tor": false,
              "is_vpn": false,
              "sources": null,
              "ioc_type": "ip",
              "confidence": 0,
              "reputation": 0,
              "risk_score": 0,
              "enriched_at": "2026-10-21T11:45:18.265134597Z",
              "is_datacenter": false,
              "total_engines": 0,
              "classification": {},
              "harmless_votes": 0,
              "malicious_votes": 0
            },
            "success": true
          }
        },
        {
          "seq": 5,
          "kind": "tool_call",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:32.995554Z",
          "summary": "enrich_ioc(value, type)",
          "payload": {
            "args": {
              "type": "ip",
              "value": "192.0.2.50"
            },
            "tool": "enrich_ioc",
            "result": {
              "value": "192.0.2.50",
              "is_bot": false,
              "is_tor": false,
              "is_vpn": false,
              "sources": null,
              "ioc_type": "ip",
              "confidence": 0,
              "reputation": 0,
              "risk_score": 0,
              "enriched_at": "2026-10-21T11:45:18.265528286Z",
              "is_datacenter": false,
              "total_engines": 0,
              "classification": {},
              "harmless_votes": 0,
              "malicious_votes": 0
            },
            "success": true
          }
        },
        {
          "seq": 6,
          "kind": "evidence_cited",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:32.995668Z",
          "summary": "ioc: 203.0.113.77",
          "payload": {
            "ref": "203.0.113.77",
            "weight": 1.0,
            "enrichment": {
              "value": "203.0.113.77",
              "is_bot": false,
              "is_tor": false,
              "is_vpn": false,
              "sources": null,
              "ioc_type": "ip",
              "confidence": 0,
              "reputation": 0,
              "risk_score": 0,
              "enriched_at": "2026-10-21T11:45:18.265134597Z",
              "is_datacenter": false,
              "total_engines": 0,
              "classification": {},
              "harmless_votes": 0,
              "malicious_votes": 0
            },
            "evidence_kind": "ioc"
          }
        },
        {
          "seq": 7,
          "kind": "evidence_cited",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:32.995693Z",
          "summary": "ioc: 192.0.2.50",
          "payload": {
            "ref": "192.0.2.50",
            "weight": 1.0,
            "enrichment": {
              "value": "192.0.2.50",
              "is_bot": false,
              "is_tor": false,
              "is_vpn": false,
              "sources": null,
              "ioc_type": "ip",
              "confidence": 0,
              "reputation": 0,
              "risk_score": 0,
              "enriched_at": "2026-10-21T11:45:18.265528286Z",
              "is_datacenter": false,
              "total_engines": 0,
              "classification": {},
              "harmless_votes": 0,
              "malicious_votes": 0
            },
            "evidence_kind": "ioc"
          }
        },
        {
          "seq": 8,
          "kind": "evidence_cited",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:32.995738Z",
          "summary": "mitre_technique: T1059",
          "payload": {
            "ref": "T1059",
            "weight": 0.8,
            "evidence_kind": "mitre_technique"
          }
        },
        {
          "seq": 9,
          "kind": "evidence_cited",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:32.995754Z",
          "summary": "mitre_technique: T1071.001",
          "payload": {
            "ref": "T1071.001",
            "weight": 0.8,
            "evidence_kind": "mitre_technique"
          }
        },
        {
          "seq": 10,
          "kind": "recon",
          "name": "ReconAgent",
          "time": "2026-10-21T03:52:32.995893Z",
          "summary": "Found 2 IOCs, 2 MITRE techniques in 9332ms",
          "payload": {
            "ioc_count": 2,
            "input_hash": "1b3f5cf68ec6307a2c301d1d9f91f72d3ba65224b3153f9bf448c3fbbca11760",
            "duration_ms": 9332,
            "output_hash": "a424506d935f3a226c01e8ead0d55b2bc02f8a21c63904bd8f95d3b90b9d2afa"
          },
          "adopted": {
            "iocs": [
              {
                "type": "ip",
                "value": "203.0.113.77"
              },
              {
                "type": "ip",
                "value": "192.0.2.50"
              }
            ],
            "related_incidents": [],
            "threat_actors": [],
            "attack_surface": {
              "affected_systems": [
                "LAB-ATTACKCTX-20261021-6D0ADF"
              ],
              "data_at_risk": "Unknown; no confirmed data access or exfiltration observed."
            },
            "mitre_techniques": [
              "T1059",
              "T1071.001"
            ],
            "summary": "This is a synthetic functional case containing three correlated alerts (unusual login, PowerShell execution, outbound TLS) on a lab environment. While the alerts map to MITRE ATT&CK technique T1071.001 (Application Layer Protocol: Web Protocols) and involve IPs 203.0.113.77 and 192.0.2.50, the source explicitly states these are fixtures for context handoff. No actual intrusion, malware, or successful data access has been confirmed; all observed activity is hypothetical and part of a test scenario."
          }
        },
        {
          "seq": 11,
          "kind": "llm_prompt",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:43.116546Z",
          "summary": "forensic: timeline, artefacts, root cause, blast radius",
          "payload": {
            "model": "aisoc-investigation",
            "purpose": "forensic: timeline, artefacts, root cause, blast radius"
          }
        },
        {
          "seq": 12,
          "kind": "tool_call",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:55.352100Z",
          "summary": "knowledge_base.model_citations(agent)",
          "payload": {
            "args": {
              "agent": "ForensicAgent"
            },
            "tool": "knowledge_base.model_citations",
            "result": {
              "cited_sources": [],
              "model_citations": [],
              "unresolvable_citations": []
            },
            "success": true
          }
        },
        {
          "seq": 13,
          "kind": "llm_response",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:55.352156Z",
          "summary": "LLM response (4650 tokens)",
          "payload": {
            "model": "aisoc-investigation",
            "cost_source": "gateway",
            "tokens_used": 4650
          }
        },
        {
          "seq": 14,
          "kind": "evidence_cited",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:55.352473Z",
          "summary": "artefact_hypothesis: LAB-ATTACKCTX-20261021-6D0ADF",
          "payload": {
            "ref": "LAB-ATTACKCTX-20261021-6D0ADF",
            "weight": 0.1,
            "evidence_kind": "artefact_hypothesis"
          }
        },
        {
          "seq": 15,
          "kind": "evidence_cited",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:55.352497Z",
          "summary": "artefact_hypothesis: 192.0.2.50",
          "payload": {
            "ref": "192.0.2.50",
            "weight": 0.1,
            "evidence_kind": "artefact_hypothesis"
          }
        },
        {
          "seq": 16,
          "kind": "evidence_cited",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:55.352512Z",
          "summary": "artefact_hypothesis: 203.0.113.77",
          "payload": {
            "ref": "203.0.113.77",
            "weight": 0.1,
            "evidence_kind": "artefact_hypothesis"
          }
        },
        {
          "seq": 17,
          "kind": "evidence_cited",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:55.352526Z",
          "summary": "artefact_hypothesis: lab_attackctx_v2_6d0adf",
          "payload": {
            "ref": "lab_attackctx_v2_6d0adf",
            "weight": 0.1,
            "evidence_kind": "artefact_hypothesis"
          }
        },
        {
          "seq": 18,
          "kind": "decision_reason",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:55.352546Z",
          "summary": "root_cause_hypothesis (conf=0.10)",
          "payload": {
            "reason": "The observed sequence of alerts represents a synthetic functional fixture designed to test correlation logic, rather than a confirmed active intrusion or successful data exfiltration.",
            "decision": "root_cause_hypothesis",
            "confidence": 0.1,
            "alternatives": []
          }
        },
        {
          "seq": 19,
          "kind": "forensic",
          "name": "ForensicAgent",
          "time": "2026-10-21T03:52:55.352639Z",
          "summary": "Timeline: 3 events, confidence 10%",
          "payload": {
            "input_hash": "a424506d935f3a226c01e8ead0d55b2bc02f8a21c63904bd8f95d3b90b9d2afa",
            "duration_ms": 12238,
            "output_hash": "52bba307c10dd61b13f3ceb6f95b37364b4ef1e9660a43bf6b559bf25ca6501d"
          },
          "adopted": {
            "timeline": [
              {
                "ts": "2026-10-21T11:30:04.491307+00:00",
                "event": "Unusual account login reported for user lab_attackctx_v2_6d0adf on host LAB-ATTACKCTX-20261021-6D0ADF.",
                "src": "raw_alert.alerts[2]"
              },
              {
                "ts": "2026-10-21T11:38:04.491307+00:00",
                "event": "PowerShell execution reported on host LAB-ATTACKCTX-20261021-6D0ADF by user lab_attackctx_v2_6d0adf.",
                "src": "raw_alert.alerts[1]"
              },
              {
                "ts": "2026-10-21T11:46:04.491307+00:00",
                "event": "Outbound TLS connection reported from host LAB-ATTACKCTX-20261021-6D0ADF to IP 203.0.113.77.",
                "src": "raw_alert.alerts[0]"
              }
            ],
            "artefacts": [
              "LAB-ATTACKCTX-20261021-6D0ADF",
              "192.0.2.50",
              "203.0.113.77",
              "lab_attackctx_v2_6d0adf"
            ],
            "root_cause_hypothesis": "The observed sequence of alerts represents a synthetic functional fixture designed to test correlation logic, rather than a confirmed active intrusion or successful data exfiltration.",
            "blast_radius": "Supplied-alert observed scope (bounded provided fields, not an exhaustive incident scope):\nsupplied_alert_scope.provided_alert_payloads: 3\nsupplied_alert_scope.supplied_scope_fields: list[3 items]\nsupplied_alert_scope.supplied_scope_fields[0].affected_hosts: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[0].affected_hosts[0]: LAB-ATTACKCTX-20261021-6D0ADF\nsupplied_alert_scope.supplied_scope_fields[0].affected_ips: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[0].affected_ips[0]: 203.0.113.77\nsupplied_alert_scope.supplied_scope_fields[0].affected_users: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[0].affected_users[0]: lab_attackctx_v2_6d0adf\nsupplied_alert_scope.supplied_scope_fields[0].id: b940b6ec-766f-4ab9-ade1-d6fa3767e6a5\nsupplied_alert_scope.supplied_scope_fields[1].affected_hosts: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[1].affected_hosts[0]: LAB-ATTACKCTX-20261021-6D0ADF\nsupplied_alert_scope.supplied_scope_fields[1].affected_ips: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[1].affected_ips[0]: 192.0.2.50\nsupplied_alert_scope.supplied_scope_fields[1].affected_users: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[1].affected_users[0]: lab_attackctx_v2_6d0adf\nsupplied_alert_scope.supplied_scope_fields[1].id: 8113e8fa-8fee-40a4-967f-80aa5987be50\nsupplied_alert_scope.supplied_scope_fields[2].affected_hosts: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[2].affected_hosts[0]: LAB-ATTACKCTX-20261021-6D0ADF\nsupplied_alert_scope.supplied_scope_fields[2].affected_ips: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[2].affected_ips[0]: 192.0.2.50\nsupplied_alert_scope.supplied_scope_fields[2].affected_users: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[2].affected_users[0]: lab_attackctx_v2_6d0adf\nsupplied_alert_scope.supplied_scope_fields[2].id: a7f2d535-f009-462f-b52f-a8178c774c8b\nUnverified model scope assessment (a claim, not a confirmed scope boundary):\nLimited to the single lab host LAB-ATTACKCTX-20261021-6D0ADF and the associated user account; no confirmed data loss or lateral movement observed.\nWider extent: unknown beyond supplied or separately verified observations. Available alerts or graph results alone do not establish exhaustive coverage.",
            "confidence": 0.1,
            "summary": "Analysis of the provided data confirms a synthetic test scenario involving three correlated alerts (login, PowerShell, outbound TLS) on a designated lab host. Due to the explicit 'synthetic functional fixture' labeling and lack of concrete forensic artefacts (files, registry keys, logs), no actual attack causality or harm can be established.",
            "groundedness": null
          }
        },
        {
          "seq": 20,
          "kind": "llm_prompt",
          "name": "ResponderAgent",
          "time": "2026-10-21T03:53:08.336316Z",
          "summary": "responder: containment/eradication/recovery plan",
          "payload": {
            "model": "aisoc-investigation",
            "purpose": "responder: containment/eradication/recovery plan"
          }
        },
        {
          "seq": 21,
          "kind": "tool_call",
          "name": "ResponderAgent",
          "time": "2026-10-21T03:53:29.818940Z",
          "summary": "knowledge_base.model_citations(agent)",
          "payload": {
            "args": {
              "agent": "ResponderAgent"
            },
            "tool": "knowledge_base.model_citations",
            "result": {
              "cited_sources": [],
              "model_citations": [],
              "unresolvable_citations": []
            },
            "success": true
          }
        },
        {
          "seq": 22,
          "kind": "llm_response",
          "name": "ResponderAgent",
          "time": "2026-10-21T03:53:29.818993Z",
          "summary": "LLM response (3479 tokens)",
          "payload": {
            "model": "aisoc-investigation",
            "cost_source": "gateway",
            "tokens_used": 3479
          }
        },
        {
          "seq": 23,
          "kind": "decision_reason",
          "name": "ResponderAgent",
          "time": "2026-10-21T03:53:29.819188Z",
          "summary": "risk_level=low (conf=0.10)",
          "payload": {
            "reason": "Based on root cause 'The observed sequence of alerts represents a synthetic functional fixture designed to test correlation logic, rather than a confirmed active intrusion or successful data exfiltration.' with forensic confidence 10% and blast radius 'Supplied-alert observed scope (bounded provided fields, not an exhaustive incident scope):\nsupplied_alert_scope.provided_alert_payloads: 3\nsupplied_alert_scope.supplied_scope_fields: list[3 items]\nsupplied_alert_scope.supplied_scope_fields[0].affected_hosts: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[0].affected_hosts[0]: LAB-ATTACKCTX-20261021-6D0ADF\nsupplied_alert_scope.supplied_scope_fields[0].affected_ips: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[0].affected_ips[0]: 203.0.113.77\nsupplied_alert_scope.supplied_scope_fields[0].affected_users: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[0].affected_users[0]: lab_attackctx_v2_6d0adf\nsupplied_alert_scope.supplied_scope_fields[0].id: b940b6ec-766f-4ab9-ade1-d6fa3767e6a5\nsupplied_alert_scope.supplied_scope_fields[1].affected_hosts: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[1].affected_hosts[0]: LAB-ATTACKCTX-20261021-6D0ADF\nsupplied_alert_scope.supplied_scope_fields[1].affected_ips: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[1].affected_ips[0]: 192.0.2.50\nsupplied_alert_scope.supplied_scope_fields[1].affected_users: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[1].affected_users[0]: lab_attackctx_v2_6d0adf\nsupplied_alert_scope.supplied_scope_fields[1].id: 8113e8fa-8fee-40a4-967f-80aa5987be50\nsupplied_alert_scope.supplied_scope_fields[2].affected_hosts: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[2].affected_hosts[0]: LAB-ATTACKCTX-20261021-6D0ADF\nsupplied_alert_scope.supplied_scope_fields[2].affected_ips: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[2].affected_ips[0]: 192.0.2.50\nsupplied_alert_scope.supplied_scope_fields[2].affected_users: list[1 items]\nsupplied_alert_scope.supplied_scope_fields[2].affected_users[0]: lab_attackctx_v2_6d0adf\nsupplied_alert_scope.supplied_scope_fields[2].id: a7f2d535-f009-462f-b52f-a8178c774c8b\nUnverified model scope assessment (a claim, not a confirmed scope boundary):\nLimited to the single lab host LAB-ATTACKCTX-20261021-6D0ADF and the associated user account; no confirmed data loss or lateral movement observed.\nWider extent: unknown beyond supplied or separately verified observations. Available alerts or graph results alone do not establish exhaustive coverage.'.",
            "decision": "risk_level=low",
            "confidence": 0.1,
            "alternatives": []
          }
        },
        {
          "seq": 24,
          "kind": "responder",
          "name": "ResponderAgent",
          "time": "2026-10-21T03:53:29.819285Z",
          "summary": "Generated 3 recommended actions (risk=low, dry_run=True)",
          "payload": {
            "input_hash": "52bba307c10dd61b13f3ceb6f95b37364b4ef1e9660a43bf6b559bf25ca6501d",
            "duration_ms": 21485,
            "output_hash": "7bf120b482046b7d671c560a17667165b068d63a34abd9bb55b9c8f683b6a205"
          },
          "adopted": {
            "recommended_actions": [
              {
                "priority": 1,
                "action": "Verify synthetic fixture status and confirm non-production environment",
                "rationale": "The root cause explicitly states this is a 'synthetic functional fixture' designed to test correlation logic. Confirming the environment is a lab prevents unnecessary disruption to production systems.",
                "risk": "low"
              },
              {
                "priority": 2,
                "action": "Review user 'lab_attackctx_v2_6d0adf' and host 'LAB-ATTACKCTX-20261021-6D0ADF' metadata for lab-specific tags",
                "rationale": "Entity names containing 'LAB' and 'ATTACKCTX' strongly suggest a test environment. Validating these tags ensures the alerts are not misattributed to real assets.",
                "risk": "low"
              },
              {
                "priority": 3,
                "action": "Close incident as 'False Positive - Synthetic Test Data' with justification",
                "rationale": "The alert source is identified as 'attack-context-functional-fixture' and the confidence is only 10%. No actual intrusion, malware, or data exfiltration has been observed or confirmed.",
                "risk": "low"
              }
            ],
            "containment_steps": [
              "Step 1: No containment required; the environment is identified as a synthetic test fixture.",
              "Step 2: Verify no production data was inadvertently ingested into the test correlation engine."
            ],
            "eradication_steps": [
              "Step 1: No eradication required; no malware or unauthorized access was confirmed.",
              "Step 2: Ensure the synthetic fixture is scheduled for cleanup or archiving if no longer needed for testing."
            ],
            "recovery_steps": [
              "Step 1: Restore normal operations; no system recovery is needed.",
              "Step 2: Document the successful correlation test in the lab runbook."
            ],
            "estimated_effort_hours": 0.5,
            "risk_level": "low",
            "dry_run": true,
            "summary": "This incident is a synthetic functional test case designed to validate alert correlation logic, not a real security breach. No containment, eradication, or recovery actions are required as no actual intrusion or harm was confirmed."
          }
        },
        {
          "seq": 25,
          "kind": "llm_prompt",
          "name": "ReportWriterAgent",
          "time": "2026-10-21T03:53:33.179438Z",
          "summary": "report: synthesise final markdown incident report",
          "payload": {
            "model": "aisoc-report",
            "purpose": "report: synthesise final markdown incident report"
          }
        },
        {
          "seq": 26,
          "kind": "tool_call",
          "name": "ReportWriterAgent",
          "time": "2026-10-21T03:53:52.656136Z",
          "summary": "knowledge_base.model_citations(agent)",
          "payload": {
            "args": {
              "agent": "ReportWriterAgent"
            },
            "tool": "knowledge_base.model_citations",
            "result": {
              "cited_sources": [],
              "model_citations": [],
              "unresolvable_citations": []
            },
            "success": true
          }
        },
        {
          "seq": 27,
          "kind": "llm_response",
          "name": "ReportWriterAgent",
          "time": "2026-10-21T03:53:52.656210Z",
          "summary": "LLM response (6570 tokens)",
          "payload": {
            "model": "aisoc-report",
            "cost_source": "gateway",
            "tokens_used": 6570
          }
        },
        {
          "seq": 28,
          "kind": "report",
          "name": "ReportWriterAgent",
          "time": "2026-10-21T03:53:52.744667Z",
          "summary": "Report written (3549 chars, hash=b4a88775b291)",
          "payload": {
            "duration_ms": 19567,
            "report_hash": "b4a88775b2910a899f92c0e8a9aa78a2311d437c87e47107057c228663ce1333",
            "report_source": "model",
            "generation_status": "success"
          }
        }
      ],
      "tools": [
        {
          "name": "knowledge_base.fetch_runbooks",
          "args": {
            "query": "Attack context fixture 3: Outbound TLS connection reported",
            "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679"
          },
          "time": "2026-10-21T03:52:23.663922Z",
          "result": "{\n  \"as_of\": null,\n  \"cache\": {\n    \"source\": \"none\",\n    \"freshness\": \"not_available\",\n    \"age_seconds\": null,\n    \"ttl_seconds\": 120.0\n  },\n  \"limit\": 3,\n  \"query\": \"Attack context fixture 3: Outbound TLS connection reported\",\n  \"budget\": {\n    \"body_chars\": 0,\n    \"max_body_chars\": 3000,\n    \"max_chunk_chars\": 900,\n    \"truncated_count\": 0,\n    \"dropped_for_budget\": 0,\n    \"encoded_body_chars\": 0,\n    \"max_envelope_chars\": 3400\n  },\n  \"reason\": \"not_configured\",\n  \"source\": \"api.kb.runbooks.for-triage\",\n  \"status\": \"unavailable\",\n  \"read_at\": \"2026-10-21T11:52:23.663670+00:00\",\n  \"runbooks\": [],\n  \"citations\": [],\n  \"tenant_id\": \"5594ae90-f57c-50f5-8332-328b3cad1679\",\n  \"http_status\": null,\n  \"valid_count\": 0,\n  \"adopted_count\": 0,\n  \"prompt_sha256\": \"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\",\n  \"received_count\": 0,\n  \"model_citations\": [],\n  \"requested_as_of\": null,\n  \"injection_signals\": [],\n  \"without_timestamp\": 0,\n  \"dropped_for_injection\": 0,\n  \"excluded_after_cutoff\": 0,\n  \"excluded_after_update\": 0,\n  \"unresolvable_citations\": [],\n  \"excluded_after_cutoff_total\": 0\n}",
          "resultFormat": "saved_result",
          "success": false
        },
        {
          "name": "knowledge_base.model_citations",
          "args": {
            "agent": "ReconAgent"
          },
          "time": "2026-10-21T03:52:30.942509Z",
          "result": "{\n  \"cited_sources\": [],\n  \"model_citations\": [],\n  \"unresolvable_citations\": []\n}",
          "resultFormat": "saved_result",
          "success": true
        },
        {
          "name": "enrich_ioc",
          "args": {
            "type": "ip",
            "value": "203.0.113.77"
          },
          "time": "2026-10-21T03:52:32.738384Z",
          "result": "{\n  \"value\": \"203.0.113.77\",\n  \"is_bot\": false,\n  \"is_tor\": false,\n  \"is_vpn\": false,\n  \"sources\": null,\n  \"ioc_type\": \"ip\",\n  \"confidence\": 0,\n  \"reputation\": 0,\n  \"risk_score\": 0,\n  \"enriched_at\": \"2026-10-21T11:45:18.265134597Z\",\n  \"is_datacenter\": false,\n  \"total_engines\": 0,\n  \"classification\": {},\n  \"harmless_votes\": 0,\n  \"malicious_votes\": 0\n}",
          "resultFormat": "saved_result",
          "success": true
        },
        {
          "name": "enrich_ioc",
          "args": {
            "type": "ip",
            "value": "192.0.2.50"
          },
          "time": "2026-10-21T03:52:32.995554Z",
          "result": "{\n  \"value\": \"192.0.2.50\",\n  \"is_bot\": false,\n  \"is_tor\": false,\n  \"is_vpn\": false,\n  \"sources\": null,\n  \"ioc_type\": \"ip\",\n  \"confidence\": 0,\n  \"reputation\": 0,\n  \"risk_score\": 0,\n  \"enriched_at\": \"2026-10-21T11:45:18.265528286Z\",\n  \"is_datacenter\": false,\n  \"total_engines\": 0,\n  \"classification\": {},\n  \"harmless_votes\": 0,\n  \"malicious_votes\": 0\n}",
          "resultFormat": "saved_result",
          "success": true
        },
        {
          "name": "knowledge_base.model_citations",
          "args": {
            "agent": "ForensicAgent"
          },
          "time": "2026-10-21T03:52:55.352100Z",
          "result": "{\n  \"cited_sources\": [],\n  \"model_citations\": [],\n  \"unresolvable_citations\": []\n}",
          "resultFormat": "saved_result",
          "success": true
        },
        {
          "name": "knowledge_base.model_citations",
          "args": {
            "agent": "ResponderAgent"
          },
          "time": "2026-10-21T03:53:29.818940Z",
          "result": "{\n  \"cited_sources\": [],\n  \"model_citations\": [],\n  \"unresolvable_citations\": []\n}",
          "resultFormat": "saved_result",
          "success": true
        },
        {
          "name": "knowledge_base.model_citations",
          "args": {
            "agent": "ReportWriterAgent"
          },
          "time": "2026-10-21T03:53:52.656136Z",
          "result": "{\n  \"cited_sources\": [],\n  \"model_citations\": [],\n  \"unresolvable_citations\": []\n}",
          "resultFormat": "saved_result",
          "success": true
        }
      ],
      "graphs": {
        "attack_chain": {
          "data": {
            "case_id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
            "chain": [
              {
                "alert_id": "70ed4a43-fe58-459c-9140-835a5da8837d",
                "connector_type": "attack-context-functional-fixture",
                "distance": 1,
                "dt_seconds": 2112.44,
                "event_time": "2026-10-21T10:54:52.051159+00:00",
                "mitre_techniques": [
                  "T1078"
                ],
                "score": 0.9777,
                "severity": "high",
                "shared_entities": [
                  {
                    "kind": "Endpoint",
                    "value": "192.0.2.50"
                  }
                ],
                "source_event_ids": [
                  "attack-context-41207e-1"
                ],
                "title": "Attack context fixture 1: Unusual account login reported"
              },
              {
                "alert_id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                "connector_type": "attack-context-functional-fixture",
                "distance": 1,
                "dt_seconds": 480.0,
                "event_time": "2026-10-21T11:38:04.491307+00:00",
                "mitre_techniques": [
                  "T1059.001"
                ],
                "score": 0.9083,
                "severity": "high",
                "shared_entities": [
                  {
                    "kind": "Endpoint",
                    "value": "192.0.2.50"
                  },
                  {
                    "kind": "Endpoint",
                    "value": "LAB-ATTACKCTX-20261021-6D0ADF"
                  },
                  {
                    "kind": "Identity",
                    "value": "lab_attackctx_v2_6d0adf"
                  }
                ],
                "source_event_ids": [
                  "attack-context-6d0adf-2"
                ],
                "title": "Attack context fixture 2: PowerShell execution reported after account login"
              },
              {
                "alert_id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                "connector_type": "attack-context-functional-fixture",
                "distance": 1,
                "dt_seconds": 960.0,
                "event_time": "2026-10-21T11:46:04.491307+00:00",
                "mitre_techniques": [
                  "T1071.001"
                ],
                "score": 0.9067,
                "severity": "high",
                "shared_entities": [
                  {
                    "kind": "Endpoint",
                    "value": "LAB-ATTACKCTX-20261021-6D0ADF"
                  },
                  {
                    "kind": "Identity",
                    "value": "lab_attackctx_v2_6d0adf"
                  }
                ],
                "source_event_ids": [
                  "attack-context-6d0adf-3"
                ],
                "title": "Attack context fixture 3: Outbound TLS connection reported"
              },
              {
                "alert_id": "1eaeefc4-d553-46a7-b987-1aabefd33e4b",
                "connector_type": "attack-context-functional-fixture",
                "distance": 1,
                "dt_seconds": 1632.44,
                "event_time": "2026-10-21T11:02:52.051159+00:00",
                "mitre_techniques": [
                  "T1059.001"
                ],
                "score": 0.9043,
                "severity": "high",
                "shared_entities": [
                  {
                    "kind": "Endpoint",
                    "value": "192.0.2.50"
                  }
                ],
                "source_event_ids": [
                  "attack-context-41207e-2"
                ],
                "title": "Attack context fixture 2: PowerShell execution reported after account login"
              },
              {
                "alert_id": "051f2e00-bc7c-46aa-b62a-681b7ce93f37",
                "connector_type": "attack-context-functional-fixture",
                "distance": 2,
                "dt_seconds": 1152.44,
                "event_time": "2026-10-21T11:10:52.051159+00:00",
                "mitre_techniques": [
                  "T1071.001"
                ],
                "score": 0.631,
                "severity": "high",
                "shared_entities": [],
                "source_event_ids": [
                  "attack-context-41207e-3"
                ],
                "title": "Attack context fixture 3: Outbound TLS connection reported"
              }
            ],
            "chain_signature": "a137bdd5d672db1306cdf64278832a8f",
            "confidence": 0.9777,
            "entity_graph": {
              "edges": [
                {
                  "kind": "TOUCHES",
                  "source": "alert:a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "target": "endpoint:192.0.2.50"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "target": "endpoint:LAB-ATTACKCTX-20261021-6D0ADF"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "target": "identity:lab_attackctx_v2_6d0adf"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:70ed4a43-fe58-459c-9140-835a5da8837d",
                  "target": "endpoint:192.0.2.50"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:8113e8fa-8fee-40a4-967f-80aa5987be50",
                  "target": "endpoint:192.0.2.50"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:8113e8fa-8fee-40a4-967f-80aa5987be50",
                  "target": "endpoint:LAB-ATTACKCTX-20261021-6D0ADF"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:8113e8fa-8fee-40a4-967f-80aa5987be50",
                  "target": "identity:lab_attackctx_v2_6d0adf"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                  "target": "endpoint:LAB-ATTACKCTX-20261021-6D0ADF"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                  "target": "identity:lab_attackctx_v2_6d0adf"
                },
                {
                  "kind": "TOUCHES",
                  "source": "alert:1eaeefc4-d553-46a7-b987-1aabefd33e4b",
                  "target": "endpoint:192.0.2.50"
                }
              ],
              "nodes": [
                {
                  "event_time": "2026-10-21T11:30:04.491307+00:00",
                  "id": "alert:a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "kind": "Alert",
                  "label": "Attack context fixture 1: Unusual account login reported",
                  "severity": "high"
                },
                {
                  "id": "endpoint:192.0.2.50",
                  "kind": "Endpoint",
                  "label": "192.0.2.50"
                },
                {
                  "id": "endpoint:LAB-ATTACKCTX-20261021-6D0ADF",
                  "kind": "Endpoint",
                  "label": "LAB-ATTACKCTX-20261021-6D0ADF"
                },
                {
                  "id": "identity:lab_attackctx_v2_6d0adf",
                  "kind": "Identity",
                  "label": "lab_attackctx_v2_6d0adf"
                },
                {
                  "event_time": "2026-10-21T10:54:52.051159+00:00",
                  "id": "alert:70ed4a43-fe58-459c-9140-835a5da8837d",
                  "kind": "Alert",
                  "label": "Attack context fixture 1: Unusual account login reported",
                  "severity": "high"
                },
                {
                  "event_time": "2026-10-21T11:38:04.491307+00:00",
                  "id": "alert:8113e8fa-8fee-40a4-967f-80aa5987be50",
                  "kind": "Alert",
                  "label": "Attack context fixture 2: PowerShell execution reported after account login",
                  "severity": "high"
                },
                {
                  "event_time": "2026-10-21T11:46:04.491307+00:00",
                  "id": "alert:b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                  "kind": "Alert",
                  "label": "Attack context fixture 3: Outbound TLS connection reported",
                  "severity": "high"
                },
                {
                  "event_time": "2026-10-21T11:02:52.051159+00:00",
                  "id": "alert:1eaeefc4-d553-46a7-b987-1aabefd33e4b",
                  "kind": "Alert",
                  "label": "Attack context fixture 2: PowerShell execution reported after account login",
                  "severity": "high"
                },
                {
                  "event_time": "2026-10-21T11:10:52.051159+00:00",
                  "id": "alert:051f2e00-bc7c-46aa-b62a-681b7ce93f37",
                  "kind": "Alert",
                  "label": "Attack context fixture 3: Outbound TLS connection reported",
                  "severity": "high"
                }
              ]
            },
            "generated_at": "2026-10-21T11:52:21.219467+00:00",
            "seed_alert_id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
            "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
            "window": "24h"
          },
          "error": null,
          "query": {
            "anchor": "seed_event_time_plus_minus_window",
            "window": "24h"
          },
          "source": "postgres",
          "status": "success",
          "queried_at": "2026-10-21T11:52:21.089171+00:00"
        },
        "attack_path": {
          "data": {
            "case_id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
            "edge_count": 15,
            "edges": [
              {
                "source": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                "target": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                "type": "CONTAINS_ALERT"
              },
              {
                "source": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                "target": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                "type": "CONTAINS_ALERT"
              },
              {
                "source": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                "target": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                "type": "CONTAINS_ALERT"
              },
              {
                "source": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                "target": "98030d89-b43b-5adf-bba9-85b0ddbd3a48",
                "type": "CONTAINS_IOC"
              },
              {
                "source": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                "target": "T1071.001",
                "type": "MAPS_TO"
              },
              {
                "source": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                "target": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                "type": "INVOLVES_USER"
              },
              {
                "source": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                "target": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                "type": "OBSERVED_ON"
              },
              {
                "source": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                "target": "7d8d1b7b-54fd-5511-85c2-c1fd3cf17d3c",
                "type": "CONTAINS_IOC"
              },
              {
                "source": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                "target": "T1059.001",
                "type": "MAPS_TO"
              },
              {
                "source": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                "target": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                "type": "INVOLVES_USER"
              },
              {
                "source": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                "target": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                "type": "OBSERVED_ON"
              },
              {
                "source": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                "target": "7d8d1b7b-54fd-5511-85c2-c1fd3cf17d3c",
                "type": "CONTAINS_IOC"
              },
              {
                "source": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                "target": "T1078",
                "type": "MAPS_TO"
              },
              {
                "source": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                "target": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                "type": "INVOLVES_USER"
              },
              {
                "source": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                "target": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                "type": "OBSERVED_ON"
              }
            ],
            "node_count": 11,
            "nodes": [
              {
                "id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                "label": "Case",
                "properties": {
                  "created_at": "2026-10-21T11:52:15.234463+00:00",
                  "id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                  "severity": "high",
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                  "title": "Attack context corrected local case 6d0adf"
                }
              },
              {
                "id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                "label": "Alert",
                "properties": {
                  "created_at": "2026-10-21T11:52:14.932083+00:00",
                  "evidence_kind": "source_alert_reported_association",
                  "id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                  "severity": "high",
                  "source_alert_id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                  "title": "Attack context fixture 3: Outbound TLS connection reported"
                }
              },
              {
                "id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                "label": "Alert",
                "properties": {
                  "created_at": "2026-10-21T11:52:14.158197+00:00",
                  "evidence_kind": "source_alert_reported_association",
                  "id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                  "severity": "high",
                  "source_alert_id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                  "title": "Attack context fixture 2: PowerShell execution reported after account login"
                }
              },
              {
                "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                "label": "Alert",
                "properties": {
                  "created_at": "2026-10-21T11:52:13.786263+00:00",
                  "evidence_kind": "source_alert_reported_association",
                  "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "severity": "high",
                  "source_alert_id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                  "title": "Attack context fixture 1: Unusual account login reported"
                }
              },
              {
                "id": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                "label": "Host",
                "properties": {
                  "criticality": "medium",
                  "hostname": "LAB-ATTACKCTX-20261021-6D0ADF",
                  "id": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                  "ip_address": "",
                  "os": "",
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                  "updated_at": "2026-10-21T11:52:14.750359+00:00"
                }
              },
              {
                "id": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                "label": "User",
                "properties": {
                  "department": "",
                  "email": "",
                  "id": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                  "risk_score": 0.0,
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                  "updated_at": "2026-10-21T11:52:14.856869+00:00",
                  "username": "lab_attackctx_v2_6d0adf"
                }
              },
              {
                "id": "98030d89-b43b-5adf-bba9-85b0ddbd3a48",
                "label": "IOC",
                "properties": {
                  "id": "98030d89-b43b-5adf-bba9-85b0ddbd3a48",
                  "indicator_value": "203.0.113.77",
                  "source_alert_id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679"
                }
              },
              {
                "id": "T1071.001",
                "label": "Technique",
                "properties": {
                  "technique_id": "T1071.001",
                  "updated_at": "2026-10-21T11:52:15.098717+00:00"
                }
              },
              {
                "id": "7d8d1b7b-54fd-5511-85c2-c1fd3cf17d3c",
                "label": "IOC",
                "properties": {
                  "id": "7d8d1b7b-54fd-5511-85c2-c1fd3cf17d3c",
                  "indicator_value": "192.0.2.50",
                  "source_alert_id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679"
                }
              },
              {
                "id": "T1059.001",
                "label": "Technique",
                "properties": {
                  "technique_id": "T1059.001",
                  "updated_at": "2026-10-21T11:52:14.410368+00:00"
                }
              },
              {
                "id": "T1078",
                "label": "Technique",
                "properties": {
                  "technique_id": "T1078",
                  "updated_at": "2026-10-21T11:52:13.915456+00:00"
                }
              }
            ]
          },
          "error": null,
          "fallback": false,
          "source": "neo4j",
          "status": "success",
          "queried_at": "2026-10-21T11:52:21.089171+00:00"
        },
        "alert_graph": {
          "data": {
            "blast_radius": {
              "affected_nodes": [
                {
                  "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "label": "Alert",
                  "properties": {
                    "created_at": "2026-10-21T11:52:13.786263+00:00",
                    "evidence_kind": "source_alert_reported_association",
                    "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                    "severity": "high",
                    "source_alert_id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "title": "Attack context fixture 1: Unusual account login reported"
                  }
                },
                {
                  "id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                  "label": "Case",
                  "properties": {
                    "created_at": "2026-10-21T11:52:15.234463+00:00",
                    "id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                    "severity": "high",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "title": "Attack context corrected local case 6d0adf"
                  }
                },
                {
                  "id": "7d8d1b7b-54fd-5511-85c2-c1fd3cf17d3c",
                  "label": "IOC",
                  "properties": {
                    "id": "7d8d1b7b-54fd-5511-85c2-c1fd3cf17d3c",
                    "indicator_value": "192.0.2.50",
                    "source_alert_id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679"
                  }
                },
                {
                  "id": "T1078",
                  "label": "Technique",
                  "properties": {
                    "technique_id": "T1078",
                    "updated_at": "2026-10-21T11:52:13.915456+00:00"
                  }
                },
                {
                  "id": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                  "label": "User",
                  "properties": {
                    "department": "",
                    "email": "",
                    "id": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                    "risk_score": 0.0,
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "updated_at": "2026-10-21T11:52:14.856869+00:00",
                    "username": "lab_attackctx_v2_6d0adf"
                  }
                },
                {
                  "id": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                  "label": "Host",
                  "properties": {
                    "criticality": "medium",
                    "hostname": "LAB-ATTACKCTX-20261021-6D0ADF",
                    "id": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                    "ip_address": "",
                    "os": "",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "updated_at": "2026-10-21T11:52:14.750359+00:00"
                  }
                },
                {
                  "id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                  "label": "Alert",
                  "properties": {
                    "created_at": "2026-10-21T11:52:14.932083+00:00",
                    "evidence_kind": "source_alert_reported_association",
                    "id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                    "severity": "high",
                    "source_alert_id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "title": "Attack context fixture 3: Outbound TLS connection reported"
                  }
                },
                {
                  "id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                  "label": "Alert",
                  "properties": {
                    "created_at": "2026-10-21T11:52:14.158197+00:00",
                    "evidence_kind": "source_alert_reported_association",
                    "id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                    "severity": "high",
                    "source_alert_id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "title": "Attack context fixture 2: PowerShell execution reported after account login"
                  }
                },
                {
                  "id": "1eaeefc4-d553-46a7-b987-1aabefd33e4b",
                  "label": "Alert",
                  "properties": {
                    "created_at": "2026-10-21T11:45:12.604926+00:00",
                    "evidence_kind": "source_alert_reported_association",
                    "id": "1eaeefc4-d553-46a7-b987-1aabefd33e4b",
                    "severity": "high",
                    "source_alert_id": "1eaeefc4-d553-46a7-b987-1aabefd33e4b",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "title": "Attack context fixture 2: PowerShell execution reported after account login"
                  }
                },
                {
                  "id": "70ed4a43-fe58-459c-9140-835a5da8837d",
                  "label": "Alert",
                  "properties": {
                    "created_at": "2026-10-21T11:45:11.775312+00:00",
                    "evidence_kind": "source_alert_reported_association",
                    "id": "70ed4a43-fe58-459c-9140-835a5da8837d",
                    "severity": "high",
                    "source_alert_id": "70ed4a43-fe58-459c-9140-835a5da8837d",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "title": "Attack context fixture 1: Unusual account login reported"
                  }
                },
                {
                  "id": "98030d89-b43b-5adf-bba9-85b0ddbd3a48",
                  "label": "IOC",
                  "properties": {
                    "id": "98030d89-b43b-5adf-bba9-85b0ddbd3a48",
                    "indicator_value": "203.0.113.77",
                    "source_alert_id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679"
                  }
                },
                {
                  "id": "T1071.001",
                  "label": "Technique",
                  "properties": {
                    "technique_id": "T1071.001",
                    "updated_at": "2026-10-21T11:52:15.098717+00:00"
                  }
                },
                {
                  "id": "T1059.001",
                  "label": "Technique",
                  "properties": {
                    "technique_id": "T1059.001",
                    "updated_at": "2026-10-21T11:52:14.410368+00:00"
                  }
                },
                {
                  "id": "75a43d25-97f3-4709-b48a-f21c8fbae56b",
                  "label": "Case",
                  "properties": {
                    "created_at": "2026-10-21T11:45:13.709734+00:00",
                    "id": "75a43d25-97f3-4709-b48a-f21c8fbae56b",
                    "severity": "high",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "title": "Attack context functional case 41207e"
                  }
                },
                {
                  "id": "ac878f84-66f3-59ab-9a38-1866bc40de48",
                  "label": "User",
                  "properties": {
                    "department": "",
                    "email": "",
                    "id": "ac878f84-66f3-59ab-9a38-1866bc40de48",
                    "risk_score": 0.0,
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "updated_at": "2026-10-21T11:45:13.143598+00:00",
                    "username": "lab.attackctx.20261021.41207e"
                  }
                },
                {
                  "id": "fe751fe1-d180-5ada-abd0-18a07d10cdfc",
                  "label": "Host",
                  "properties": {
                    "criticality": "medium",
                    "hostname": "LAB-ATTACKCTX-20261021-41207E",
                    "id": "fe751fe1-d180-5ada-abd0-18a07d10cdfc",
                    "ip_address": "",
                    "os": "",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "updated_at": "2026-10-21T11:45:13.101781+00:00"
                  }
                }
              ],
              "blast_radius_score": 9.0,
              "entity_id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
              "entity_type": "alert",
              "hops": 3,
              "total_affected": 16,
              "type_breakdown": {
                "Alert": 5,
                "Case": 2,
                "Host": 2,
                "IOC": 2,
                "Technique": 3,
                "User": 2
              }
            },
            "neighbors": {
              "entity_id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
              "entity_type": "alert",
              "neighbor_count": 5,
              "neighbors": [
                {
                  "id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                  "label": "Case",
                  "properties": {
                    "created_at": "2026-10-21T11:52:15.234463+00:00",
                    "id": "82b1246f-9f34-463c-8c2d-27d2b075c741",
                    "severity": "high",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "title": "Attack context corrected local case 6d0adf"
                  },
                  "rel_type": "CONTAINS_ALERT"
                },
                {
                  "id": "7d8d1b7b-54fd-5511-85c2-c1fd3cf17d3c",
                  "label": "IOC",
                  "properties": {
                    "id": "7d8d1b7b-54fd-5511-85c2-c1fd3cf17d3c",
                    "indicator_value": "192.0.2.50",
                    "source_alert_id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679"
                  },
                  "rel_type": "CONTAINS_IOC"
                },
                {
                  "id": "T1078",
                  "label": "Technique",
                  "properties": {
                    "technique_id": "T1078",
                    "updated_at": "2026-10-21T11:52:13.915456+00:00"
                  },
                  "rel_type": "MAPS_TO"
                },
                {
                  "id": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                  "label": "User",
                  "properties": {
                    "department": "",
                    "email": "",
                    "id": "8ef6b319-1b3f-544e-880b-0267a983bbe6",
                    "risk_score": 0.0,
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "updated_at": "2026-10-21T11:52:14.856869+00:00",
                    "username": "lab_attackctx_v2_6d0adf"
                  },
                  "rel_type": "INVOLVES_USER"
                },
                {
                  "id": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                  "label": "Host",
                  "properties": {
                    "criticality": "medium",
                    "hostname": "LAB-ATTACKCTX-20261021-6D0ADF",
                    "id": "a9edc374-b1f4-58bb-a8ad-bd1246132d1b",
                    "ip_address": "",
                    "os": "",
                    "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                    "updated_at": "2026-10-21T11:52:14.750359+00:00"
                  },
                  "rel_type": "OBSERVED_ON"
                }
              ],
              "source": {
                "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                "label": "Alert",
                "properties": {
                  "created_at": "2026-10-21T11:52:13.786263+00:00",
                  "evidence_kind": "source_alert_reported_association",
                  "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "severity": "high",
                  "source_alert_id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
                  "tenant_id": "5594ae90-f57c-50f5-8332-328b3cad1679",
                  "title": "Attack context fixture 1: Unusual account login reported"
                }
              }
            }
          },
          "error": null,
          "source": "neo4j",
          "status": "success",
          "queried_at": "2026-10-21T11:52:21.089171+00:00"
        }
      },
      "artifacts": [
        {
          "id": "9ff9f357-be32-46af-a73e-67f80cc75e58",
          "kind": "attack_chain",
          "sha256": "8816c1d41801df1f3c53ea10421747732c0c6a73e0309ae46e6336bbe7373999",
          "size_bytes": 10105,
          "event_id": null,
          "created_at": "2026-10-21T11:52:23.373049Z"
        },
        {
          "id": "2ebc5d27-121e-495f-8ec1-9d7de797c0a6",
          "kind": "attack_path",
          "sha256": "1b8109971214cafa7fbb8ce8c86682bb8a7616b47b911b988bb6a42469d5062c",
          "size_bytes": 9576,
          "event_id": null,
          "created_at": "2026-10-21T11:52:23.570167Z"
        },
        {
          "id": "2a4f7bc7-4d52-43a7-b0a9-94ad30f59c6a",
          "kind": "alert_graph",
          "sha256": "72fe656327eed230bc5c268ca5c8099a1c2c4ae7c0d012f6b6a45d2138a73ff5",
          "size_bytes": 11817,
          "event_id": null,
          "created_at": "2026-10-21T11:52:23.692324Z"
        },
        {
          "id": "f0a33ff6-b423-4d0a-bf62-a4ef2bcf3e38",
          "kind": "report_md",
          "sha256": "67465c1a3f3e100e7d7bee475ed78cdb62a20616cffb5e32bb5cbdb33137d077",
          "size_bytes": 3551,
          "event_id": null,
          "created_at": "2026-10-21T11:53:54.192588Z"
        }
      ],
      "report": "# Incident Report — 82b1246f-9f34-463c-8c2d-27d2b075c741\n\n## Executive Summary\nThis case represents a **synthetic functional test** designed to validate alert correlation logic, not a confirmed security breach. Three alerts (login, PowerShell, outbound TLS) were generated on a designated lab host (`LAB-ATTACKCTX-20261021-6D0ADF`) to simulate an attack chain. No actual intrusion, malware execution, or data exfiltration has been observed. The incident is classified as a **False Positive - Synthetic Test Data**.\n\n## Timeline of Events\n*   **2026-10-21T11:30:04+00:00**: Alert generated: Unusual account login reported for user `lab_attackctx_v2_6d0adf`.\n*   **2026-10-21T11:38:04+00:00**: Alert generated: PowerShell execution reported on the same host by the same user.\n*   **2026-10-21T11:46:04+00:00**: Alert generated: Outbound TLS connection reported to IP `203.0.113.77`.\n*   **2026-10-21T11:52:23+00:00**: Investigation processing logged; knowledge base lookup failed (expected in test environment).\n\n## IOC Analysis\n| Indicator | Type | Context | Status |\n| :--- | :--- | :--- | :--- |\n| `192.0.2.50` | IP Address | Internal Lab Host | Synthetic Fixture |\n| `203.0.113.77` | IP Address | Outbound TLS Destination | Synthetic Fixture |\n| `lab_attackctx_v2_6d0adf` | User Identity | Lab Account | Synthetic Fixture |\n\n## MITRE ATT&CK Mapping\n*   **T1059 (Command and Scripting Interpreter)**: Mapped via PowerShell execution alert.\n*   **T1071.001 (Application Layer Protocol: Web Protocols)**: Mapped via outbound TLS alert.\n*   *Note*: Mappings are based on alert titles and detector logic; no actual technique execution was verified.\n\n## Forensic Findings\n*   **Environment**: Confirmed synthetic lab environment based on host naming (`LAB-ATTACKCTX`) and alert descriptions (`attack-context-functional-fixture`).\n*   **Causality**: Chronological ordering of alerts does not prove malicious causality; shared entities are part of the test design.\n*   **Evidence Gap**: No source-system historical logs, file artifacts, or registry keys were provided to confirm successful access or harm.\n*   **Confidence**: Low (10%) regarding any real-world threat; High confidence regarding the synthetic nature of the data.\n\n## Response Plan\n*   **Containment**: No action required. The environment is identified as a non-production test fixture.\n*   **Eradication**: No malware removal or account revocation needed.\n*   **Recovery**: No system restoration required.\n*   **Closure**: Close incident as \"False Positive - Synthetic Test Data\" with justification citing the `attack-context-functional-fixture` source label.\n\n## Recommendations\n1.  **Verify Environment**: Confirm the host `LAB-ATTACKCTX-20261021-6D0ADF` is tagged as a non-production asset to prevent future production impact.\n2.  **Metadata Review**: Ensure user `lab_attackctx_v2_6d0adf` has appropriate lab-specific tags to suppress or route alerts correctly.\n3.  **Documentation**: Document this successful correlation test in the lab runbook to validate the detection pipeline's logic.\n\n## Appendix: Enrichment Data\n*   **Graph Status**: Attack path and alert graph queries returned successfully within the test scope.\n*   **Enrichment Limitations**: Threat intelligence lookups and host neighbor graphs returned timeouts or unavailable status. This is a coverage limitation of the test environment, not evidence of missing malicious activity.\n*   **Knowledge Base**: Runbook fetch failed (`not_configured`); no operational procedures were adopted for this specific synthetic case.",
      "stop": null,
      "calls": 4,
      "tokens": 18388,
      "unpriced": 0,
      "actions": [
        {
          "description": "Verify synthetic fixture status and confirm non-production environment",
          "rationale": "The root cause explicitly states this is a 'synthetic functional fixture' designed to test correlation logic. Confirming the environment is a lab prevents unnecessary disruption to production systems.",
          "priority": 1,
          "risk": "low"
        },
        {
          "description": "Review user 'lab_attackctx_v2_6d0adf' and host 'LAB-ATTACKCTX-20261021-6D0ADF' metadata for lab-specific tags",
          "rationale": "Entity names containing 'LAB' and 'ATTACKCTX' strongly suggest a test environment. Validating these tags ensures the alerts are not misattributed to real assets.",
          "priority": 2,
          "risk": "low"
        },
        {
          "description": "Close incident as 'False Positive - Synthetic Test Data' with justification",
          "rationale": "The alert source is identified as 'attack-context-functional-fixture' and the confidence is only 10%. No actual intrusion, malware, or data exfiltration has been observed or confirmed.",
          "priority": 3,
          "risk": "low"
        }
      ],
      "executed": [],
      "remediation": "dry_run=true · 仅生成响应建议",
      "triage": null,
      "timeNote": "过程记录的原始时间与 Run 起止时间存在 8 小时差异；按来源原值展示，未推测修正。"
    }
  ],
  "alerts": [
    {
      "id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
      "title": "Attack context fixture 3: Outbound TLS connection reported",
      "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
      "persistedRecord": true,
      "sourceEnvironment": "socai2-21",
      "sourceTenantId": "5594ae90-f57c-50f5-8332-328b3cad1679",
      "severity": "高",
      "status": "Unknown",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "—",
      "source": "attack-context-functional-fixture",
      "entityIds": [
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:device:LAB-ATTACKCTX-20261021-6D0ADF",
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:user:lab_attackctx_v2_6d0adf",
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:ip:203.0.113.77"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-21T11:46:04.491307+00:00",
      "first": "2026-10-21T11:46:04.491307+00:00",
      "last": null,
      "incidentId": null,
      "caseId": "82b1246f-9f34-463c-8c2d-27d2b075c741",
      "comments": [],
      "disposition": null,
      "hostNames": [
        "LAB-ATTACKCTX-20261021-6D0ADF"
      ],
      "tactics": [],
      "iocKeys": [
        "ip:203.0.113.77"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-21T11:46:04.491307+00:00",
            "title": "告警发生",
            "description": "Attack context fixture 3: Outbound TLS connection reported"
          }
        ],
        "runs": [],
        "caseInvestigation": {
          "caseId": "82b1246f-9f34-463c-8c2d-27d2b075c741",
          "runId": "e998308a-a353-4647-99f6-10f94ced0ecf",
          "inputCount": 3
        },
        "tenantName": "5594ae90-f57c-50f5-8332-328b3cad1679",
        "techniques": [
          "T1071.001"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": null
        },
        "risk": null,
        "raw": {
          "id": "b940b6ec-766f-4ab9-ade1-d6fa3767e6a5",
          "title": "Attack context fixture 3: Outbound TLS connection reported",
          "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
          "severity": "high",
          "source": "attack-context-functional-fixture",
          "affected_ips": [
            "203.0.113.77"
          ],
          "affected_hosts": [
            "LAB-ATTACKCTX-20261021-6D0ADF"
          ],
          "affected_users": [
            "lab_attackctx_v2_6d0adf"
          ],
          "event_time": "2026-10-21T11:46:04.491307+00:00",
          "full_log": ""
        },
        "responseRecommendations": []
      }
    },
    {
      "id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
      "title": "Attack context fixture 2: PowerShell execution reported after account login",
      "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
      "persistedRecord": true,
      "sourceEnvironment": "socai2-21",
      "sourceTenantId": "5594ae90-f57c-50f5-8332-328b3cad1679",
      "severity": "高",
      "status": "Unknown",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "—",
      "source": "attack-context-functional-fixture",
      "entityIds": [
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:device:LAB-ATTACKCTX-20261021-6D0ADF",
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:user:lab_attackctx_v2_6d0adf",
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:ip:192.0.2.50"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-21T11:38:04.491307+00:00",
      "first": "2026-10-21T11:38:04.491307+00:00",
      "last": null,
      "incidentId": null,
      "caseId": "82b1246f-9f34-463c-8c2d-27d2b075c741",
      "comments": [],
      "disposition": null,
      "hostNames": [
        "LAB-ATTACKCTX-20261021-6D0ADF"
      ],
      "tactics": [],
      "iocKeys": [
        "ip:192.0.2.50"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-21T11:38:04.491307+00:00",
            "title": "告警发生",
            "description": "Attack context fixture 2: PowerShell execution reported after account login"
          }
        ],
        "runs": [],
        "caseInvestigation": {
          "caseId": "82b1246f-9f34-463c-8c2d-27d2b075c741",
          "runId": "e998308a-a353-4647-99f6-10f94ced0ecf",
          "inputCount": 3
        },
        "tenantName": "5594ae90-f57c-50f5-8332-328b3cad1679",
        "techniques": [
          "T1059.001"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": null
        },
        "risk": null,
        "raw": {
          "id": "8113e8fa-8fee-40a4-967f-80aa5987be50",
          "title": "Attack context fixture 2: PowerShell execution reported after account login",
          "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
          "severity": "high",
          "source": "attack-context-functional-fixture",
          "affected_ips": [
            "192.0.2.50"
          ],
          "affected_hosts": [
            "LAB-ATTACKCTX-20261021-6D0ADF"
          ],
          "affected_users": [
            "lab_attackctx_v2_6d0adf"
          ],
          "event_time": "2026-10-21T11:38:04.491307+00:00",
          "full_log": ""
        },
        "responseRecommendations": []
      }
    },
    {
      "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
      "title": "Attack context fixture 1: Unusual account login reported",
      "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
      "persistedRecord": true,
      "sourceEnvironment": "socai2-21",
      "sourceTenantId": "5594ae90-f57c-50f5-8332-328b3cad1679",
      "severity": "高",
      "status": "Unknown",
      "investigation": "Completed",
      "owner": "未分配",
      "category": "—",
      "source": "attack-context-functional-fixture",
      "entityIds": [
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:device:LAB-ATTACKCTX-20261021-6D0ADF",
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:user:lab_attackctx_v2_6d0adf",
        "raw:5594ae90-f57c-50f5-8332-328b3cad1679:ip:192.0.2.50"
      ],
      "tags": [],
      "classification": "Not set",
      "event_time": "2026-10-21T11:30:04.491307+00:00",
      "first": "2026-10-21T11:30:04.491307+00:00",
      "last": null,
      "incidentId": null,
      "caseId": "82b1246f-9f34-463c-8c2d-27d2b075c741",
      "comments": [],
      "disposition": null,
      "hostNames": [
        "LAB-ATTACKCTX-20261021-6D0ADF"
      ],
      "tactics": [],
      "iocKeys": [
        "ip:192.0.2.50"
      ],
      "detailMaterial": {
        "timelineVersion": 2,
        "history": [
          {
            "time": "2026-10-21T11:30:04.491307+00:00",
            "title": "告警发生",
            "description": "Attack context fixture 1: Unusual account login reported"
          }
        ],
        "runs": [],
        "caseInvestigation": {
          "caseId": "82b1246f-9f34-463c-8c2d-27d2b075c741",
          "runId": "e998308a-a353-4647-99f6-10f94ced0ecf",
          "inputCount": 3
        },
        "tenantName": "5594ae90-f57c-50f5-8332-328b3cad1679",
        "techniques": [
          "T1078"
        ],
        "explanation": {
          "generatedAt": null,
          "summary": "",
          "suggestedActions": []
        },
        "confidence": {
          "score": null
        },
        "risk": null,
        "raw": {
          "id": "a7f2d535-f009-462f-b52f-a8178c774c8b",
          "title": "Attack context fixture 1: Unusual account login reported",
          "description": "Synthetic functional fixture: this alert reports activity for chain/path context handoff only. Shared entities and chronological order do not prove causality, maliciousness or a real intrusion. No source-system historical logs are asserted.",
          "severity": "high",
          "source": "attack-context-functional-fixture",
          "affected_ips": [
            "192.0.2.50"
          ],
          "affected_hosts": [
            "LAB-ATTACKCTX-20261021-6D0ADF"
          ],
          "affected_users": [
            "lab_attackctx_v2_6d0adf"
          ],
          "event_time": "2026-10-21T11:30:04.491307+00:00",
          "full_log": ""
        },
        "responseRecommendations": []
      }
    }
  ],
  "assets": [
    {
      "id": "raw:5594ae90-f57c-50f5-8332-328b3cad1679:device:LAB-ATTACKCTX-20261021-6D0ADF",
      "type": "device",
      "name": "LAB-ATTACKCTX-20261021-6D0ADF",
      "tags": [],
      "inventory": false,
      "sourceEnvironment": "socai2-21"
    },
    {
      "id": "raw:5594ae90-f57c-50f5-8332-328b3cad1679:user:lab_attackctx_v2_6d0adf",
      "type": "user",
      "name": "lab_attackctx_v2_6d0adf",
      "tags": [],
      "inventory": false,
      "sourceEnvironment": "socai2-21"
    },
    {
      "id": "raw:5594ae90-f57c-50f5-8332-328b3cad1679:ip:203.0.113.77",
      "type": "ip",
      "name": "203.0.113.77",
      "tags": [],
      "inventory": false,
      "sourceEnvironment": "socai2-21"
    },
    {
      "id": "raw:5594ae90-f57c-50f5-8332-328b3cad1679:ip:192.0.2.50",
      "type": "ip",
      "name": "192.0.2.50",
      "tags": [],
      "inventory": false,
      "sourceEnvironment": "socai2-21"
    }
  ]
};
