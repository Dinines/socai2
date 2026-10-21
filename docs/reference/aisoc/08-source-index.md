# 08 源码、接口与测试索引

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。此处是固定版本的源码/测试定位索引，文件存在和路由数量不等于服务已迁入或接口已验收。 当前职责见[范围](../../operations/alert-processing-scope.md)，阶段退出见[路线](../../operations/service-roadmap.md)，执行批次见[依赖计划](../../operations/dependency-migration-plan.md)。

返回[总入口](README.md)。此索引按实际本地文件生成；符号行号只辅助定位，更新后以函数名和快照为准。

源码 revision：`34ca18c57dd4175539e5c6dd3d04a72dc057306b`。快照覆盖 199 个被引用文件/代表测试；不表示逐行审计这些文件的所有分支。

## 1. 关键调用位置

| 文件 | 本次重点符号与行号 |
| --- | --- |
| [services/ueba/app/services/feature_extraction.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/app/services/feature_extraction.py) | `flat_fields:76`, `_entity:161`, `_features:192`, `extract:255` |
| [services/ueba/app/services/kafka_consumer.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/app/services/kafka_consumer.py) | `_process_message:110`, `run:181` |
| [services/ueba/app/services/baseline.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/app/services/baseline.py) | `_welford_update:25`, `compute_z_score:79`, `BaselineService:128`, `update:160`, `score_features:182` |
| [services/ueba/app/services/scoring.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/app/services/scoring.py) | `_composite_score:38`, `ScoringService:57`, `score_event:63` |
| [services/ueba/app/services/peer_group.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/app/services/peer_group.py) | `PeerGroupService:21`, `update:52`, `deviation_score:71` |
| [services/fusion/app/services/first_seen.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/first_seen.py) | `FirstSeenStore:93`, `observe:104`, `derived_fields:141` |
| [services/fusion/app/services/baselines.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/baselines.py) | `derived_fields:386` |
| [services/fusion/app/services/entity_risk.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/entity_risk.py) | `EntityRiskEngine:106`, `observe:135` |
| [services/api/app/services/incident_context.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/incident_context.py) | `IncidentContext:88` |
| [services/api/app/services/context_import.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/context_import.py) | `import_context:117` |
| [services/api/app/services/alert_priority.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/alert_priority.py) | `score_alert_priority:132` |
| [services/api/app/services/business_context/engine.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/business_context/engine.py) | `BusinessContextEngine:267`, `evaluate:323` |
| [services/api/app/services/detection_tuner.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/detection_tuner.py) | `suggest_tuning:55` |
| [services/agents/app/investigator/deep_investigation.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/deep_investigation.py) | `_record_tool_calls:347`, `run_deep_investigation:421` |
| [services/fusion/app/models/alert.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/models/alert.py) | `RawAlert:50`, `deterministic_id:99`, `fingerprint:109`, `correlation_key:125`, `FusedAlert:162`, `IncidentSummary:228` |
| [services/fusion/app/workers/consumer.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/workers/consumer.py) | `_consume_loop:229`, `_process_message:311`, `_fuse_and_persist:451` |
| [services/fusion/app/services/fusion_engine.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/fusion_engine.py) | `FusionEngine:115`, `process:149` |
| [services/fusion/app/services/alert_sink.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/app/services/alert_sink.py) | `PersistOutcome:37`, `PersistResult:52`, `persist:311` |
| [services/api/app/services/alert_queue.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/alert_queue.py) | `QueueItem:112` |
| [services/api/app/services/case_orchestration.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/case_orchestration.py) | `resolve_queue:110`, `sla_targets:123`, `escalation_due:165` |
| [services/api/app/api/v1/endpoints/cases.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/cases.py) | `reopen_case:635`, `update_case:746`, `case_investigate:1569` |
| [services/agents/app/workers/fused_alert_consumer.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/workers/fused_alert_consumer.py) | `build_state:242`, `_process_with_retry:488`, `_send_to_dlq:536`, `triage:583`, `_maybe_escalate:1180` |
| [services/agents/app/graph/workflow.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/graph/workflow.py) | `build_investigation_graph:93`, `build_escalation_graph:124` |
| [services/agents/app/graph/runner.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/graph/runner.py) | `default_budget:45`, `_budget_exhausted:53`, `_run:72` |
| [services/agents/app/api/investigate.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/api/investigate.py) | `_investigate_stream:136`, `_run_and_store:263` |
| [services/agents/app/investigator/orchestrator.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/orchestrator.py) | `_build_graph:118`, `_apply_groundedness:150`, `InvestigatorOrchestrator:216` |
| [services/agents/app/orchestrator/router.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/orchestrator/router.py) | `classify_signals:218`, `_join_states:292`, `RouterOrchestrator:617` |
| [services/agents/app/investigator/recon_agent.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/recon_agent.py) | `run_recon:149` |
| [services/agents/app/investigator/forensic_agent.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/forensic_agent.py) | `run_forensic:161` |
| [services/agents/app/investigator/ledger.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/ledger.py) | `get_pool:57`, `start_run:165`, `record_event:226`, `record_artifact:285`, `complete_run:338`, `persist_auto_triage:507`, `raise_approval:804` |
| [services/agents/app/context/bundle.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/context/bundle.py) | `ContextBundle:299`, `ContextBundleBuilder:492`, `build_context_bundle:862` |
| [services/agents/app/context/knowledge_base.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/context/knowledge_base.py) | `fetch_runbooks:287`, `citation_basis:485`, `unresolvable_citations:503` |
| [services/agents/app/llm/factory.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/llm/factory.py) | `llm_override:86`, `make_chat_model:162` |
| [services/agents/app/core/cost_telemetry.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/core/cost_telemetry.py) | `CostSummary:227`, `CostTracker:454`, `record_llm_call:676` |
| [services/agents/app/tools/mitre_full.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/tools/mitre_full.py) | `load_attck_corpus:275`, `embed_techniques_into_qdrant:366`, `semantic_technique_search:447` |
| [services/api/app/services/semantic_memory.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/services/semantic_memory.py) | `embed:195`, `index_item:276`, `search:362`, `remember_closed_case:414` |
| [services/threatintel/app/feeds/pipeline.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/threatintel/app/feeds/pipeline.py) | `ThreatIntelPipeline:30`, `ingest_iocs:53` |
| [services/threatintel/app/storage/qdrant.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/threatintel/app/storage/qdrant.py) | `QdrantStore:59`, `semantic_search:180`, `_embed:212` |
| [services/agents/app/playbook/engine.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/playbook/engine.py) | `_suspend_for_approval:811`, `resume_after_approval:955`, `PlaybookEngine:1973` |
| [services/api/app/api/v1/endpoints/approvals.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/approvals.py) | `decide_approval:233`, `_dispatch_decision:301` |
| [services/actions/app/services/action_store.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/services/action_store.py) | `save:84`, `_report_degraded:122`, `get:145` |
| [services/actions/app/api/router.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/api/router.py) | `submit_action:54`, `approve_action:184` |
| [services/actions/app/live_actions/dispatcher.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/live_actions/dispatcher.py) | `_verify_effect:363`, `dispatch:437` |
| [services/actions/app/services/verification.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/services/verification.py) | `PostActionVerifier:593` |
| [services/actions/app/services/rollback.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/services/rollback.py) | `reverse_action:160` |

## 2. 路由声明

以下提取模块内 router prefix 和装饰器中的字面路径；API 主路由挂载、反向代理、权限 dependency 与请求/响应 schema 仍须结合入口核对。HTTP 路由存在不证明已部署或业务通过。

### services/actions/app/api/live_actions_router.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/api/live_actions_router.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/live-actions` | `discover_live_actions:87` |
| GET | `/live-actions/by-capability/{capability}` | `vendors_for_capability:120` |
| GET | `/live-actions/by-vendor/{vendor_id}` | `capabilities_for_vendor:137` |
| POST | `/live-actions/dispatch` | `dispatch_live_action:160` |
| POST | `/live-actions/dry-run` | `dry_run_live_action:188` |

### services/actions/app/api/router.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/api/router.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/actions` | `submit_action:54` |
| POST | `/actions/{action_id}/approve` | `approve_action:184` |
| POST | `/actions/{action_id}/reject` | `reject_action:239` |
| GET | `/actions/{action_id}` | `get_action:271` |
| GET | `/chatops/callback` | `chatops_callback:333` |
| GET | `/health` | `health:433` |

### services/agents/app/api/investigate.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/api/investigate.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/api/v1/cases/{case_id}/investigate` | `launch_investigation:370` |
| GET | `/api/v1/investigations/{run_id}` | `get_investigation:396` |
| GET | `/api/v1/investigations/{run_id}/report.md` | `get_report_md:407` |
| GET | `/api/v1/investigations/{run_id}/report.html` | `get_report_html:418` |
| GET | `/api/v1/investigations/{run_id}/report.pdf` | `get_report_pdf:429` |
| WEBSOCKET | `/api/v1/investigations/{run_id}/stream` | `stream_investigation:463` |

### services/agents/app/api/router.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/api/router.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/agent-runs` | `start_investigation:90` |
| GET | `/agent-runs/{run_id}` | `get_investigation:116` |
| POST | `/hunt` | `run_nl_hunt:148` |
| GET | `/health` | `health:206` |

### services/agents/app/api/triage.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/api/triage.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/api/v1/cases/{case_id}/triage` | `launch_triage:273` |
| GET | `/api/v1/triage/{run_id}` | `get_triage:333` |

### services/api/app/api/v1/endpoints/agent_tools.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/agent_tools.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/agent-tools/backends` | `list_backends:102` |
| POST | `/agent-tools/siem-search` | `search_siem:146` |
| POST | `/agent-tools/vendor-read` | `vendor_read:206` |
| POST | `/agent-tools/hunt-plan/execute` | `execute_hunt_plan:266` |

### services/api/app/api/v1/endpoints/alerts.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/alerts.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/alerts/submit` | `submit_alert:539` |
| GET | `/alerts` | `list_alerts:782` |
| GET | `/alerts/stats` | `get_alert_stats:911` |
| GET | `/alerts/queue` | `get_alert_queue:959` |
| GET | `/alerts/{alert_id}` | `get_alert:989` |
| PATCH | `/alerts/{alert_id}` | `update_alert:1081` |
| POST | `/alerts/{alert_id}/escalate` | `escalate_alert:1166` |
| POST | `/alerts/{alert_id}/claim` | `claim_alert_endpoint:1194` |
| POST | `/alerts/{alert_id}/snooze` | `snooze_alert:1221` |
| POST | `/alerts/bulk-close` | `bulk_close_alerts_endpoint:1294` |

### services/api/app/api/v1/endpoints/approvals.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/approvals.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/approvals` | `list_approvals:109` |
| GET | `/approvals/{approval_id}` | `get_approval:159` |
| POST | `/approvals` | `create_approval:178` |
| POST | `/approvals/{approval_id}/decide` | `decide_approval:233` |

### services/api/app/api/v1/endpoints/assets.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/assets.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/assets` | `list_assets:118` |
| POST | `/assets` | `create_asset:137` |
| GET | `/assets/vulnerabilities` | `list_vulnerabilities:155` |
| GET | `/assets/{asset_id}` | `get_asset:174` |
| PATCH | `/assets/{asset_id}` | `update_asset:186` |
| DELETE | `/assets/{asset_id}` | `delete_asset:206` |
| POST | `/assets/vulnerabilities` | `create_vulnerability:224` |
| GET | `/assets/{asset_id}/vulnerabilities` | `list_asset_vulnerabilities:246` |

### services/api/app/api/v1/endpoints/business_context.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/business_context.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/business-context/rules` | `get_rules:436` |
| POST | `/business-context/rules` | `replace_rules:469` |
| PUT | `/business-context/rules/{rule_id}` | `update_rule:518` |
| DELETE | `/business-context/rules/{rule_id}` | `delete_rule:587` |
| POST | `/business-context/rules/preview` | `preview_rules:619` |

### services/api/app/api/v1/endpoints/cases.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/cases.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/cases` | `list_cases:488` |
| POST | `/cases` | `create_case:533` |
| GET | `/cases/{case_id}` | `get_case:608` |
| POST | `/cases/{case_id}/reopen` | `reopen_case:635` |
| PATCH | `/cases/{case_id}` | `update_case:746` |
| POST | `/cases/{case_id}/alerts` | `add_alerts:980` |
| POST | `/cases/{case_id}/observables` | `update_observables:1019` |
| POST | `/cases/{case_id}/comments` | `add_comment:1067` |
| GET | `/cases/{case_id}/comments` | `list_comments:1118` |
| GET | `/cases/{case_id}/notes` | `list_notes:1138` |
| POST | `/cases/{case_id}/notes` | `add_note:1143` |
| GET | `/cases/{case_id}/evidence` | `evidence_report:1150` |
| GET | `/cases/{case_id}/timeline` | `case_timeline:1183` |
| GET | `/cases/{case_id}/tasks` | `list_tasks:1311` |
| POST | `/cases/{case_id}/tasks` | `create_task:1334` |
| PATCH | `/cases/{case_id}/tasks/{task_id}` | `update_task:1384` |
| POST | `/cases/{case_id}/investigate` | `case_investigate:1569` |
| GET | `/cases/{case_id}/investigations` | `list_case_investigations:1723` |
| GET | `/cases/{case_id}/investigations/{run_id}` | `case_investigation_run:1780` |
| GET | `/cases/{case_id}/investigations/{run_id}/report.md` | `case_investigation_report_md:1822` |
| GET | `/cases/{case_id}/summary` | `case_auto_summary:1924` |
| GET | `/cases/{case_id}/postmortem` | `case_auto_postmortem:1963` |
| GET | `/cases/{case_id}/investigations/{run_id}/report.pdf` | `case_investigation_pdf:2004` |
| GET | `/cases/{case_id}/related` | `list_related_cases:2032` |

### services/api/app/api/v1/endpoints/detection_proposals.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/detection_proposals.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/detection-proposals` | `list_proposals:415` |
| POST | `/detection-proposals` | `create_proposal:438` |
| GET | `/detection-proposals/baselines` | `list_baselines:470` |
| POST | `/detection-proposals/baselines` | `record_baseline:494` |
| GET | `/detection-proposals/{proposal_id}` | `get_proposal:527` |
| POST | `/detection-proposals/{proposal_id}/comment` | `comment_on_proposal:539` |
| POST | `/detection-proposals/run-eval` | `run_eval_harness:641` |
| POST | `/detection-proposals/{proposal_id}/evaluate-rule` | `evaluate_rule:742` |
| POST | `/detection-proposals/{proposal_id}/backtest` | `backtest_proposal:819` |
| POST | `/detection-proposals/{proposal_id}/eval` | `attach_eval_result:868` |
| POST | `/detection-proposals/{proposal_id}/decide` | `decide_proposal:931` |
| POST | `/detection-proposals/{proposal_id}/promote` | `promote_proposal:1030` |

### services/api/app/api/v1/endpoints/detection_rules.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/detection_rules.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/rules` | `list_rules:124` |
| POST | `/rules` | `create_rule:216` |
| GET | `/rules/{rule_id}` | `get_rule:243` |
| PATCH | `/rules/{rule_id}` | `update_rule:256` |
| DELETE | `/rules/{rule_id}` | `delete_rule:322` |
| POST | `/rules/{rule_id}/execute` | `execute_detection_rule:371` |
| POST | `/rules/hunt` | `hunt:457` |
| POST | `/rules/{rule_id}/backtest` | `backtest_detection_rule:514` |

### services/api/app/api/v1/endpoints/feedback.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/feedback.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/feedback/alert-override` | `submit_alert_override:200` |
| POST | `/feedback/redisposition/apply` | `apply_redisposition_endpoint:372` |
| GET | `/feedback/overrides` | `list_overrides_endpoint:414` |
| GET | `/feedback/summary` | `get_override_summary:436` |
| GET | `/feedback/context-statements` | `get_context_statements:489` |
| GET | `/feedback/recent-dispositions` | `recent_dispositions:630` |

### services/api/app/api/v1/endpoints/hunts.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/hunts.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/hunts` | `list_hunts:233` |
| POST | `/hunts` | `create_hunt:266` |
| GET | `/hunts/{hunt_id}` | `get_hunt:316` |
| PATCH | `/hunts/{hunt_id}` | `update_hunt:328` |
| POST | `/hunts/{hunt_id}/run` | `run_hunt:390` |
| GET | `/hunts/{hunt_id}/runs` | `list_runs:479` |
| POST | `/hunts/{hunt_id}/findings` | `add_findings:514` |

### services/api/app/api/v1/endpoints/identity_graph.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/identity_graph.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/identity-graph/nodes` | `list_nodes:103` |
| POST | `/identity-graph/nodes` | `create_node:125` |
| GET | `/identity-graph/nodes/{node_id}` | `get_node:138` |
| GET | `/identity-graph/nodes/{node_id}/edges` | `get_node_edges:150` |
| GET | `/identity-graph/edges` | `list_edges:173` |
| POST | `/identity-graph/edges` | `create_edge:189` |
| POST | `/identity-graph/alert-links` | `link_alert_to_identity:207` |
| GET | `/identity-graph/alert-links/{alert_id}` | `get_alert_identity_links:220` |

### services/api/app/api/v1/endpoints/investigations.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/investigations.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/investigations` | `list_runs:371` |
| GET | `/investigations/costs/aggregate` | `aggregate_costs:396` |
| GET | `/investigations/{run_id}` | `get_run:473` |
| GET | `/investigations/{run_id}/events` | `list_events:503` |
| GET | `/investigations/{run_id}/replay` | `replay_run:542` |
| GET | `/investigations/{run_id}/explain` | `explain_step:565` |
| GET | `/investigations/{run_id}/artifacts` | `list_artifacts:645` |
| GET | `/investigations/{run_id}/artifacts/{artifact_id}` | `get_artifact:667` |
| GET | `/investigations/{run_id}/timeline` | `get_timeline:833` |
| POST | `/investigations/{run_id}/close` | `close_investigation:977` |
| GET | `/investigations/{run_id}/summary.pdf` | `export_summary_pdf:1028` |
| GET | `/investigations/{run_id}/bundle` | `export_evidence_bundle:1157` |

### services/api/app/api/v1/endpoints/knowledge_base.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/knowledge_base.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/kb/ingest` | `ingest:231` |
| GET | `/kb/documents` | `list_documents:272` |
| GET | `/kb/documents/{doc_id}` | `get_document:288` |
| DELETE | `/kb/documents/{doc_id}` | `delete_document:302` |
| POST | `/kb/query` | `query_kb:324` |
| GET | `/kb/runbooks/for-triage` | `retrieve_runbooks_for_triage:528` |

### services/api/app/api/v1/endpoints/lake.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/lake.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/lake/sql` | `execute_lake_sql:245` |
| POST | `/lake/estimate` | `estimate_lake_sql:546` |
| POST | `/lake/query-jobs` | `submit_lake_query_job:574` |
| GET | `/lake/query-jobs` | `list_lake_query_jobs:656` |
| GET | `/lake/query-jobs/{job_id}` | `get_lake_query_job:690` |
| POST | `/lake/query-jobs/{job_id}/cancel` | `cancel_lake_query_job:714` |
| GET | `/lake/schema` | `get_lake_schema:739` |

### services/api/app/api/v1/endpoints/posture.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/posture.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/posture/findings` | `list_findings:119` |
| POST | `/posture/findings` | `ingest_finding:144` |
| GET | `/posture/findings/{finding_id}` | `get_finding:157` |
| POST | `/posture/findings/{finding_id}/suppress` | `suppress_finding:169` |
| POST | `/posture/findings/{finding_id}/resolve` | `resolve_finding:188` |
| GET | `/posture/summary` | `get_summary:204` |
| GET | `/posture/scans` | `list_scans:233` |
| POST | `/posture/scan` | `cspm_scan:266` |
| POST | `/posture/destinations/preview` | `destination_preview:289` |

### services/api/app/api/v1/endpoints/saved_hunts.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/saved_hunts.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| GET | `/saved-hunts` | `list_saved_hunts:333` |
| POST | `/saved-hunts` | `create_saved_hunt:355` |
| GET | `/saved-hunts/{hunt_id}` | `get_saved_hunt:414` |
| DELETE | `/saved-hunts/{hunt_id}` | `delete_saved_hunt:429` |
| POST | `/saved-hunts/{hunt_id}/run` | `run_saved_hunt:461` |

### services/api/app/api/v1/endpoints/semantic_memory.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/semantic_memory.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/memory/items` | `ingest_item:174` |
| GET | `/memory/items` | `list_items:287` |
| DELETE | `/memory/items/{item_id}` | `retire_item:304` |
| POST | `/memory/recall` | `recall:350` |
| GET | `/memory/conflicts` | `list_conflicts:426` |
| POST | `/memory/conflicts/{item_id}/resolve` | `resolve_conflict:460` |
| GET | `/memory/status` | `recall_status:554` |

### services/ueba/app/api/routes.py

[文件](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/app/api/routes.py)

| 方法 | 模块路径 | 处理函数 |
| --- | --- | --- |
| POST | `/api/v1/ueba/score` | `score_event:122` |
| GET | `/api/v1/ueba/anomalies` | `list_anomalies:140` |
| PATCH | `/api/v1/ueba/anomalies/{anomaly_id}/acknowledge` | `acknowledge_anomaly:170` |
| GET | `/api/v1/ueba/baselines` | `list_baselines:185` |
| GET | `/api/v1/ueba/peer-groups` | `list_peer_groups:201` |

## 3. 代表测试入口

下表只做源码发现与静态分类，本次没有执行上游测试集。测试函数名表达待核合同，是否使用真 PG/模型/厂商，应进一步阅读 fixture、monkeypatch 与 client 构造。

| 测试文件 | 代表节点（最多四项） |
| --- | --- |
| [services/actions/tests/test_action_store_columns.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_action_store_columns.py) | `test_an_enum_member_is_written_as_its_value`<br>`test_the_qualified_enum_name_never_reaches_the_column`<br>`test_a_plain_string_status_is_unchanged`<br>`test_the_graded_tier_reaches_its_own_column` |
| [services/actions/tests/test_approval_identity.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_approval_identity.py) | `test_a_mapped_slack_user_resolves_with_real_permissions`<br>`test_an_unmapped_user_resolves_to_nothing_rather_than_an_empty_principal`<br>`test_an_unknown_platform_is_refused_not_trusted`<br>`test_platform_matching_is_case_insensitive_but_user_ids_are_not` |
| [services/actions/tests/test_approval_matrix.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_approval_matrix.py) | `test_severe_and_irreversible_never_auto_execute`<br>`test_irreversible_is_prohibited_not_merely_gated`<br>`test_a_contract_demanding_a_human_survives_any_tier`<br>`test_a_prohibited_contract_survives_everything` |
| [services/actions/tests/test_live_action_dispatcher.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_live_action_dispatcher.py) | `test_dispatch_routes_to_registered_executor`<br>`test_dispatch_unknown_pair_returns_failed_not_exception`<br>`test_dispatch_unknown_pair_lists_no_alternatives_when_none_exist`<br>`test_dispatch_dry_run_propagates_to_executor` |
| [services/actions/tests/test_live_action_router_auth.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_live_action_router_auth.py) | `test_dispatch_rejects_a_caller_with_no_token`<br>`test_dispatch_rejects_a_wrong_token`<br>`test_dispatch_accepts_the_configured_token`<br>`test_unconfigured_token_fails_closed_in_production` |
| [services/actions/tests/test_rollback.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_rollback.py) | `test_isolate_reverse_calls_crowdstrike_when_credentialed`<br>`test_block_ip_reverse_calls_aws`<br>`test_disable_user_reverse_calls_okta`<br>`test_no_credentials_is_simulated_not_fake_success` |
| [services/actions/tests/test_tenant_scope.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_tenant_scope.py) | `test_valid_token_yields_its_tenant`<br>`test_unacceptable_tokens_are_refused`<br>`test_malformed_tokens_are_refused`<br>`test_no_secret_means_no_verification` |
| [services/actions/tests/test_verification.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_verification.py) | `test_verified_only_when_the_host_is_actually_contained`<br>`test_resolvable_host_that_is_not_contained_is_a_failure`<br>`test_containment_pending_is_not_verified`<br>`test_missing_host_is_indeterminate_not_failed` |
| [services/actions/tests/test_verification_coverage.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/tests/test_verification_coverage.py) | `test_every_declared_probe_is_registered`<br>`test_an_absent_probe_at_containment_impact_is_explained`<br>`test_every_dispatchable_verb_either_probes_or_says_why_not`<br>`test_a_capability_with_no_action_type_cannot_claim_a_probe` |
| [services/agents/tests/test_alert_triggered_playbooks.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_alert_triggered_playbooks.py) | `test_the_deployment_switch_is_off_by_default`<br>`test_no_playbook_is_live_by_default`<br>`test_disabled_says_how_to_enable_it`<br>`test_scoping` |
| [services/agents/tests/test_auto_triage_dispositions.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_auto_triage_dispositions.py) | `test_parser_accepts_benign_true_positive`<br>`test_parser_normalizes_synonym_and_spacing`<br>`test_parser_unknown_verdict_fails_safe_to_true_positive`<br>`test_normalize_bridges_deterministic_and_llm_vocabularies` |
| [services/agents/tests/test_auto_triage_injection.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_auto_triage_injection.py) | `test_prompt_injection_in_evidence_blocks_autoclose`<br>`test_clean_evidence_still_autocloses` |
| [services/agents/tests/test_auto_triage_ledger_records_the_prompt.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_auto_triage_ledger_records_the_prompt.py) | `test_a_model_call_leaves_a_replayable_record`<br>`test_both_hashes_are_present_and_differ`<br>`test_the_hash_covers_the_whole_prompt_not_the_truncated_copy`<br>`test_a_run_that_called_no_model_records_nothing` |
| [services/agents/tests/test_context_bundle.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_context_bundle.py) | `test_email_username_separation`<br>`test_freeform_summary_pulls_iocs`<br>`test_dedup_across_keys`<br>`test_summary_for_llm_only_emits_safe_keys` |
| [services/agents/tests/test_deep_investigation.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_deep_investigation.py) | `test_selection_discriminates`<br>`test_subtechnique_matches_its_parent_strategy`<br>`test_technique_outranks_keyword`<br>`test_no_match_falls_back_rather_than_returning_none` |
| [services/agents/tests/test_deep_investigation_customer_tools.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_deep_investigation_customer_tools.py) | `test_the_phase_4_acceptance_bar`<br>`test_a_failed_vendor_read_does_not_count_as_a_pivot`<br>`test_a_tenant_with_no_customer_tools_gets_the_gap_in_its_findings`<br>`test_an_unreachable_api_does_not_silently_shrink_the_investigation` |
| [services/agents/tests/test_graph_runner.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_graph_runner.py) | `test_runner_records_one_ledger_event_per_node`<br>`test_runner_budget_timeout_fails_safe_to_needs_review`<br>`test_runner_merges_node_outputs_into_final_state` |
| [services/agents/tests/test_investigate_router_flag.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_investigate_router_flag.py) | `test_flag_defaults_off_when_env_unset`<br>`test_flag_truthy_values`<br>`test_flag_falsey_values`<br>`test_flag_tolerates_whitespace` |
| [services/agents/tests/test_investigator_completion_bound.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_investigator_completion_bound.py) | `test_the_call_sites_exist_so_this_test_is_not_vacuous`<br>`test_every_investigator_llm_call_bounds_its_completion`<br>`test_the_bound_clears_the_longest_reply_the_agents_actually_write`<br>`test_the_default_applies_with_no_configuration` |
| [services/agents/tests/test_investigator_groundedness.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_investigator_groundedness.py) | `test_no_evidence_is_not_scored`<br>`test_an_unscored_run_reports_none_not_zero`<br>`test_a_grounded_analysis_keeps_its_confidence`<br>`test_an_invented_indicator_lowers_confidence_and_says_why` |
| [services/agents/tests/test_llm_contract.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_llm_contract.py) | `test_classify_message_flags_minimal_ocsf_json`<br>`test_llm_input_contract_rejects_raw_ocsf_json`<br>`test_validate_messages_accepts_summarized_structure`<br>`test_validate_messages_rejects_nested_json_string_with_class_uid` |
| [services/agents/tests/test_model_router.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_model_router.py) | `test_confident_deterministic_wins_and_llm_never_called`<br>`test_low_confidence_escalates_deterministic_to_ml_to_llm`<br>`test_ml_wins_when_confident_and_llm_not_reached`<br>`test_no_silent_llm_when_llm_tier_absent` |
| [services/agents/tests/test_orchestrator_router_stream.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_orchestrator_router_stream.py) | `test_stream_emits_step_events_per_stage_parallel`<br>`test_stream_emits_step_events_per_stage_sequential`<br>`test_stream_seq_is_monotonic`<br>`test_stream_done_carries_report_and_state` |
| [services/agents/tests/test_playbook_action_bridge.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_playbook_action_bridge.py) | `test_all_fifteen_response_verbs_dispatch`<br>`test_the_three_that_used_to_simulate_now_reach_an_executor`<br>`test_each_step_is_dispatched_separately_and_carries_its_own_id`<br>`test_a_step_that_did_not_execute_fails` |
| [services/agents/tests/test_playbook_bounds.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_playbook_bounds.py) | `test_min_timeout_is_positive`<br>`test_pydantic_field_cap_above_param_cap`<br>`test_param_cap_is_tighter_than_field_cap`<br>`test_defaults_within_absolute_bounds` |
| [services/agents/tests/test_playbook_pause_resume.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_playbook_pause_resume.py) | `test_a_pause_records_where_to_resume`<br>`test_the_context_is_stored_not_just_the_position`<br>`test_no_database_returns_none_rather_than_raising`<br>`test_a_pause_is_found_by_approval_id_from_a_cold_start` |
| [services/agents/tests/test_splunk_evidence.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_splunk_evidence.py) | `test_build_evidence_spl_is_time_and_entity_bounded`<br>`test_build_evidence_spl_none_without_pivot`<br>`test_spl_values_are_quote_escaped`<br>`test_time_window_is_bounded` |
| [services/agents/tests/test_tenant_scope.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_tenant_scope.py) | `test_valid_token_yields_its_tenant`<br>`test_unacceptable_tokens_are_refused`<br>`test_malformed_tokens_are_refused`<br>`test_no_secret_means_no_verification` |
| [services/agents/tests/test_triage_knowledge_base.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_triage_knowledge_base.py) | `test_the_block_is_fenced_with_the_run_nonce`<br>`test_the_boundary_sentence_is_stated_inline_as_well_as_in_the_system_rule`<br>`test_a_chunk_that_echoes_the_fence_markers_is_refused`<br>`test_a_leaked_nonce_is_stripped_even_when_the_guard_says_nothing` |
| [services/agents/tests/test_triage_structured_output.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/tests/test_triage_structured_output.py) | `test_json_output_reaches_the_request_payload`<br>`test_json_output_is_opt_in`<br>`test_json_output_preserves_the_other_parameters`<br>`test_json_output_does_not_discard_caller_model_kwargs` |
| [services/api/tests/api/v1/endpoints/test_realtime_ticket.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/api/v1/endpoints/test_realtime_ticket.py) | `test_secret_uses_configured_value_in_any_env`<br>`test_secret_does_not_fall_back_to_the_published_default_in_development`<br>`test_the_retired_dev_secret_is_refused_even_when_set_explicitly`<br>`test_secret_is_none_in_prod_when_unset` |
| [services/api/tests/test_alert_list_priority_sort.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_alert_list_priority_sort.py) | `test_the_critical_is_first_under_priority_sort`<br>`test_the_critical_is_not_on_page_one_by_default`<br>`test_priority_still_breaks_ties_by_recency`<br>`test_priority_changes_the_order_and_not_the_rows` |
| [services/api/tests/test_alert_priority.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_alert_priority.py) | `test_a_critical_asset_outranks_a_low_one_at_equal_severity`<br>`test_a_domain_admin_outranks_a_standard_user`<br>`test_a_kev_vulnerability_outranks_an_ordinary_one`<br>`test_break_glass_activity_is_notable_at_any_severity` |
| [services/api/tests/test_alert_queue.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_alert_queue.py) | `test_returns_defaults_when_no_tenant_overrides`<br>`test_tenant_override_wins`<br>`test_unknown_severity_override_is_ignored`<br>`test_multiple_overrides_apply_independently` |
| [services/api/tests/test_analyst_feedback.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_analyst_feedback.py) | `test_one_analyst_is_not_yet_a_pattern`<br>`test_the_second_analyst_makes_it_memory`<br>`test_corroboration_counts_analysts_not_rows`<br>`test_a_single_high_trust_reason_needs_no_corroboration` |
| [services/api/tests/test_approval_dispatch.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_approval_dispatch.py) | `test_an_approval_submits_then_approves`<br>`test_the_approval_id_is_reused_as_the_action_id`<br>`test_parameters_reach_the_actions_service`<br>`test_the_requester_is_the_agent_not_the_approver` |
| [services/api/tests/test_business_context.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_business_context.py) | `test_empty_yaml_returns_empty_list`<br>`test_single_rule_shorthand`<br>`test_rules_list_form`<br>`test_aggregator_all_any_not` |
| [services/api/tests/test_case_orchestration.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_case_orchestration.py) | `test_precedence_decides_between_two_matching_queues`<br>`test_the_name_breaks_a_precedence_tie`<br>`test_criteria_are_anded_not_ored`<br>`test_a_case_matching_nothing_gets_no_queue` |
| [services/api/tests/test_context_import.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_context_import.py) | `test_nothing_is_ever_deleted`<br>`test_records_are_merged_not_created`<br>`test_absent_fields_do_not_blank_existing_values`<br>`test_an_end_date_marks_the_employee_inactive` |
| [services/api/tests/test_detection_eval.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_detection_eval.py) | `test_good_rule_passes_its_own_fixtures`<br>`test_blind_rule_is_rejected`<br>`test_noisy_rule_is_rejected`<br>`test_no_positive_fixtures_is_rejected_not_vacuous` |
| [services/api/tests/test_detection_tuner.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_detection_tuner.py) | `test_low_fp_rule_gets_no_suggestion`<br>`test_entity_clustered_fps_suggest_exception`<br>`test_diffuse_fps_suggest_lower_severity`<br>`test_overwhelming_human_confirmed_fps_suggest_suppress` |
| [services/api/tests/test_detection_tuning_is_not_promotable_as_a_stub.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_detection_tuning_is_not_promotable_as_a_stub.py) | `test_a_comment_only_body_carries_no_detection_logic`<br>`test_a_body_with_real_logic_is_promotable`<br>`test_create_proposals_defaults_to_false`<br>`test_promotion_checks_for_detection_logic` |
| [services/api/tests/test_evidence_bundle.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_evidence_bundle.py) | `test_two_exports_of_one_run_are_identical`<br>`test_it_survives_a_json_round_trip_unchanged`<br>`test_event_order_does_not_depend_on_input_order`<br>`test_the_canonical_form_has_no_inserted_whitespace` |
| [services/api/tests/test_evidence_custody.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_evidence_custody.py) | `test_it_records_what_who_and_when`<br>`test_an_unknown_action_is_refused`<br>`test_every_declared_action_is_accepted`<br>`test_an_untouched_chain_verifies` |
| [services/api/tests/test_feedback_context_statements.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_feedback_context_statements.py) | `test_reads_host_and_user_from_the_denormalised_lists`<br>`test_falls_back_to_the_raw_event_when_the_lists_are_empty`<br>`test_recovers_the_process_and_hash_a_binary_scope_needs`<br>`test_carries_the_rule_identity_a_rule_scope_needs` |
| [services/api/tests/test_incident_context.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_incident_context.py) | `test_every_matched_variable_is_scoped_or_globally_exempt`<br>`test_global_labels_are_never_traversed_through`<br>`test_null_tenant_is_not_treated_as_readable`<br>`test_global_reference_labels_are_the_only_exemption` |
| [services/api/tests/test_investigation_payload.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_investigation_payload.py) | `test_the_raw_event_reaches_the_payload`<br>`test_alert_metadata_travels_with_it`<br>`test_every_correlated_alert_is_included`<br>`test_the_summary_describes_the_alerts_not_just_the_title` |
| [services/api/tests/test_investigation_replay.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_investigation_replay.py) | `test_steps_come_back_in_sequence_order_not_storage_order`<br>`test_the_emitted_statement_orders_by_seq_ascending`<br>`test_the_paginated_stream_is_ordered_too`<br>`test_a_replay_of_one_step_is_still_a_replay` |
| [services/api/tests/test_posture_store.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_posture_store.py) | `test_first_collection_becomes_the_live_version`<br>`test_unchanged_recollection_does_not_open_a_version`<br>`test_unchanged_recollection_still_records_a_newly_lost_read`<br>`test_a_changed_estate_opens_a_version_and_closes_the_old_one` |
| [services/api/tests/test_replay_frozen_context.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_replay_frozen_context.py) | `test_organisation_memory_is_sent`<br>`test_outcome_priors_are_sent_keyed_by_signature`<br>`test_the_business_context_rule_set_is_sent`<br>`test_a_context_block_is_sent_even_with_no_skills` |
| [services/api/tests/test_semantic_memory.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/tests/test_semantic_memory.py) | `test_the_author_is_the_principal_not_the_body`<br>`test_re_ingesting_the_same_content_is_idempotent_and_does_not_re_embed`<br>`test_a_contradiction_suspends_both_sides_and_recall_returns_neither`<br>`test_resolving_a_conflict_restores_exactly_one_side` |
| [services/fusion/tests/test_alert_sink.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_alert_sink.py) | `test_dsn_strips_sqlalchemy_driver`<br>`test_iocs_and_entities_extraction`<br>`test_duplicate_decision_is_never_persisted`<br>`test_new_alert_is_inserted_with_canonical_id_and_provenance` |
| [services/fusion/tests/test_alert_sink_issue_1244.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_alert_sink_issue_1244.py) | `test_affected_hosts_users_and_ips_are_persisted`<br>`test_absent_entities_persist_as_empty_lists_not_nulls`<br>`test_the_batch_path_writes_the_same_columns`<br>`test_a_dedup_hit_records_the_second_events_id` |
| [services/fusion/tests/test_baselines.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_baselines.py) | `test_a_principal_with_too_little_history_gets_no_rarity`<br>`test_a_routine_action_scores_near_zero_and_a_novel_one_near_one`<br>`test_rarity_is_per_principal_not_per_tenant`<br>`test_tenants_do_not_share_baselines` |
| [services/fusion/tests/test_confidence.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_confidence.py) | `test_score_attaches_complete_rationale`<br>`test_rationale_is_sorted_by_impact`<br>`test_rationale_weights_sum_to_one`<br>`test_score_is_deterministic` |
| [services/fusion/tests/test_consumer_dlq.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_consumer_dlq.py) | `test_valid_event_is_processed_and_not_dead_lettered`<br>`test_missing_ocsf_event_is_dead_lettered_not_dropped`<br>`test_unknown_schema_version_is_dead_lettered`<br>`test_non_uuid_tenant_is_dead_lettered_with_lineage` |
| [services/fusion/tests/test_detection_engine.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_detection_engine.py) | `test_positive_event_fires_matching_rule`<br>`test_benign_near_miss_does_not_fire`<br>`test_endpoint_rule_fires_on_recovered_raw_fields`<br>`test_build_alert_carries_rule_metadata` |
| [services/fusion/tests/test_entity_risk.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_entity_risk.py) | `test_observe_creates_record_for_each_entity`<br>`test_score_accumulates_additively`<br>`test_severity_weights_are_ordered`<br>`test_risk_score_amplifies_points` |
| [services/fusion/tests/test_event_schema.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_event_schema.py) | `test_valid_raw_event_passes_and_carries_lineage`<br>`test_non_object_payload_is_rejected`<br>`test_missing_ocsf_event_is_rejected`<br>`test_unknown_schema_version_is_rejected` |
| [services/fusion/tests/test_first_seen.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_first_seen.py) | `test_the_first_sighting_is_not_seen_before_and_the_second_is`<br>`test_tenants_do_not_share_sightings`<br>`test_an_unreadable_store_contributes_no_key`<br>`test_an_absent_subject_contributes_no_key` |
| [services/fusion/tests/test_sessions.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_sessions.py) | `test_a_vendor_session_is_upserted_with_its_kind`<br>`test_an_event_with_no_session_writes_nothing`<br>`test_a_kind_outside_the_closed_set_is_refused`<br>`test_the_derived_kind_is_marked_as_not_the_vendors_grouping` |
| [services/fusion/tests/test_sigma_correlation_replay.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_sigma_correlation_replay.py) | `test_all_four_correlation_types_are_covered`<br>`test_event_count_fires_at_its_threshold_and_not_one_short`<br>`test_value_count_needs_distinct_values`<br>`test_temporal_ordered_requires_the_order` |
| [services/fusion/tests/test_tenant_scope.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_tenant_scope.py) | `test_valid_token_yields_its_tenant`<br>`test_unacceptable_tokens_are_refused`<br>`test_malformed_tokens_are_refused`<br>`test_no_secret_means_no_verification` |
| [services/fusion/tests/test_tenant_tuning_overlay.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_tenant_tuning_overlay.py) | `test_a_disabled_rule_is_an_override`<br>`test_an_untuned_rule_produces_no_override`<br>`test_the_version_is_derived_from_the_rows`<br>`test_a_changed_row_changes_the_version` |
| [services/fusion/tests/test_windowed_detection.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_windowed_detection.py) | `test_bruteforce_fires_at_threshold_once`<br>`test_group_by_isolates_entities`<br>`test_non_matching_event_never_fires`<br>`test_build_alert_from_hit` |
| [services/fusion/tests/test_windowed_sequences.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/fusion/tests/test_windowed_sequences.py) | `test_the_sequence_fires_in_order`<br>`test_the_last_stage_alone_does_not_fire`<br>`test_out_of_order_by_event_time_does_not_fire`<br>`test_a_batch_delivered_out_of_arrival_order_still_fires` |
| [services/ueba/tests/test_baseline_scoring.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/tests/test_baseline_scoring.py) | `test_first_observation_has_no_variance_yet`<br>`test_mean_and_sample_std_match_textbook_values`<br>`test_constant_stream_keeps_std_at_zero`<br>`test_features_are_tracked_independently` |
| [services/ueba/tests/test_feature_extraction.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/tests/test_feature_extraction.py) | `test_recovers_vendor_fields_nested_under_raw_event`<br>`test_connector_normalized_keys_win_over_raw_vendor_values`<br>`test_parses_raw_data_when_it_is_a_json_string`<br>`test_non_dict_envelope_yields_nothing` |
| [services/ueba/tests/test_non_human_entities.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/tests/test_non_human_entities.py) | `test_non_human_principals_are_accepted`<br>`test_the_original_types_still_work`<br>`test_an_unknown_entity_type_is_still_refused`<br>`test_the_pattern_is_derived_from_the_list` |
| [services/ueba/tests/test_tenant_scope.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/ueba/tests/test_tenant_scope.py) | `test_valid_token_yields_its_tenant`<br>`test_unacceptable_tokens_are_refused`<br>`test_malformed_tokens_are_refused`<br>`test_no_secret_means_no_verification` |

其他运行入口：

- [golden pipeline](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/tests/e2e/golden_pipeline/run_golden_pipeline.py)：20 已有记录，范围见 07。
- [Realtime tenant push](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/realtime/test/push-tenant.test.ts)、[认证](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/realtime/test/auth.test.ts)：本轮未执行。
- [本地部署 embedding 合同](../../../deploy/aisoc20/embedding/test_embeddings.py)：此前三项通过，不替代上游知识/调查测试。

## 4. 与历史参考快照的差异

比较的是本次引用集合与 `告警处理分析/reference-snapshot.json` 的交集。变化表示不能沿用原文件对应的旧结论；不表示全部变更已逐行审计。

| 历史 ID | 文件 | 状态 |
| --- | --- | --- |
| AC03 | [services/actions/app/api/live_actions_router.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/api/live_actions_router.py) | changed |
| AC02 | [services/actions/app/api/router.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/api/router.py) | changed |
| AC04 | [services/actions/app/live_actions/dispatcher.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/live_actions/dispatcher.py) | changed |
| AC06 | [services/actions/app/live_actions/models.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/live_actions/models.py) | changed |
| AC01 | [services/actions/app/main.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/main.py) | changed |
| AC05 | [services/actions/app/models/action.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/models/action.py) | changed |
| AC11 | [services/actions/app/services/rollback.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/services/rollback.py) | changed |
| AC10 | [services/actions/app/services/verification.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/actions/app/services/verification.py) | changed |
| AG07 | [services/agents/app/api/router.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/api/router.py) | changed |
| AG06 | [services/agents/app/context/bundle.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/context/bundle.py) | changed |
| AG04 | [services/agents/app/graph/workflow.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/graph/workflow.py) | unchanged |
| AG03 | [services/agents/app/investigator/ledger.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/investigator/ledger.py) | changed |
| LM03 | [services/agents/app/llm/contract.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/llm/contract.py) | changed |
| LM01 | [services/agents/app/llm/factory.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/llm/factory.py) | changed |
| LM02 | [services/agents/app/llm/model_pins.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/llm/model_pins.py) | changed |
| FB01 | [services/agents/app/memory/manager.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/memory/manager.py) | unchanged |
| AG05 | [services/agents/app/orchestrator/router.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/orchestrator/router.py) | unchanged |
| PB01 | [services/agents/app/playbook/store.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/playbook/store.py) | changed |
| LM04 | [services/agents/app/security/llm_resolver.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/security/llm_resolver.py) | changed |
| Q01 | [services/agents/app/tools/mitre_full.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/tools/mitre_full.py) | changed |
| AG02 | [services/agents/app/workers/fused_alert_consumer.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/agents/app/workers/fused_alert_consumer.py) | changed |
| PV05 | [services/api/app/api/v1/endpoints/assets.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/assets.py) | changed |
| PV03 | [services/api/app/api/v1/endpoints/hunts.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/hunts.py) | changed |
| PV01 | [services/api/app/api/v1/endpoints/lake.py](https://github.com/beenuar/AiSOC/blob/34ca18c57dd4175539e5c6dd3d04a72dc057306b/services/api/app/api/v1/endpoints/lake.py) | changed |

完整当前 hash 与历史 hash 见 [source-snapshot.json](/Users/lychee/Documents/project/SOCAI/doc/beenuarsocai/source-snapshot.json)。当前源码事实优先于历史索引中的行号和行为摘要；部署 overlay 的证据独立见 05 与部署说明。
