# 调查模块证据与历史文档全目录

2026-10-27，仓库基线`6044615`。从[审计导航](audit-guide-20261027.md)和[当前实现详解](current-implementation-reference-20261027.md)进入。此目录按当前仓库实际存在的相关文件生成，提供完整链接；分类不是通过/失败结论，本轮未执行任何probe或业务验证。

范围：`docs/investigation`的Markdown/场景JSON、相关架构、原需求Markdown及Word原件、`docs/operations`路径名包含investigation的文档/回执/原件、当前OpenSpec及调查归档、活动probe和当前直接用例源码。外部未提供文件、Git历史中已删除文件及原件JSON内部编码条目不逐项展开；完整原件应打开对应JSON。

审计时读取机器回执的baseline/status/limits、实际观察和failure originals等字段。各阶段测试数不累计为整体业务完成；旧fixed/program真实回执不能转作F3 Case真实验证。

## 1. 当前入口与F1–F3文档

当前说明；状态以当前设计对齐、审计导航及实现详解为准（9项）

| 文件 | 链接 |
| --- | --- |
| docs/investigation/README.md | [README.md](README.md) |
| docs/investigation/audit-guide-20261027.md | [audit-guide-20261027.md](audit-guide-20261027.md) |
| docs/investigation/case-investigation.md | [case-investigation.md](case-investigation.md) |
| docs/investigation/current-design-alignment-20261027.md | [current-design-alignment-20261027.md](current-design-alignment-20261027.md) |
| docs/investigation/current-implementation-reference-20261027.md | [current-implementation-reference-20261027.md](current-implementation-reference-20261027.md) |
| docs/investigation/incident-ai-overview.md | [incident-ai-overview.md](incident-ai-overview.md) |
| docs/investigation/incident-investigation-implementation-plan-20261025.md | [incident-investigation-implementation-plan-20261025.md](incident-investigation-implementation-plan-20261025.md) |
| docs/investigation/interface-contracts-20261027.md | [interface-contracts-20261027.md](interface-contracts-20261027.md) |
| docs/investigation/tool-onboarding-and-flow-verification.md | [tool-onboarding-and-flow-verification.md](tool-onboarding-and-flow-verification.md) |

## 2. 调查历史审计与场景

历史/场景；不自动代表当前F3（5项）

| 文件 | 链接 |
| --- | --- |
| docs/investigation/design-implementation-review-20261025.md | [design-implementation-review-20261025.md](design-implementation-review-20261025.md) |
| docs/investigation/examples/fixed-recon-published-20261024.md | [fixed-recon-published-20261024.md](examples/fixed-recon-published-20261024.md) |
| docs/investigation/independent-audit-20261024.md | [independent-audit-20261024.md](independent-audit-20261024.md) |
| docs/investigation/review-response-20261024.md | [review-response-20261024.md](review-response-20261024.md) |
| docs/investigation/scenarios/network-observation.v1.json | [network-observation.v1.json](scenarios/network-observation.v1.json) |

## 3. 架构、工具与原需求

总体规划或相应路径说明，注意日期与适用范围（16项）

| 文件 | 链接 |
| --- | --- |
| docs/architecture/alert-processing.md | [alert-processing.md](../architecture/alert-processing.md) |
| docs/architecture/attack-chain-path.md | [attack-chain-path.md](../architecture/attack-chain-path.md) |
| docs/architecture/fusion.md | [fusion.md](../architecture/fusion.md) |
| docs/architecture/incident-analysis-product-comparison-20261023.md | [incident-analysis-product-comparison-20261023.md](../architecture/incident-analysis-product-comparison-20261023.md) |
| docs/architecture/incident-investigation-flow-20261025.md | [incident-investigation-flow-20261025.md](../architecture/incident-investigation-flow-20261025.md) |
| docs/architecture/investigation-design-review.md | [investigation-design-review.md](../architecture/investigation-design-review.md) |
| docs/architecture/investigation-planning-design.md | [investigation-planning-design.md](../architecture/investigation-planning-design.md) |
| docs/architecture/investigation-preprocessing-tools.md | [investigation-preprocessing-tools.md](../architecture/investigation-preprocessing-tools.md) |
| docs/architecture/investigation-product-engineering-roadmap-20261022.md | [investigation-product-engineering-roadmap-20261022.md](../architecture/investigation-product-engineering-roadmap-20261022.md) |
| docs/architecture/investigation-product-research-20261023.md | [investigation-product-research-20261023.md](../architecture/investigation-product-research-20261023.md) |
| docs/architecture/investigation-tool-catalog.md | [investigation-tool-catalog.md](../architecture/investigation-tool-catalog.md) |
| docs/architecture/investigation-tool-data-plan.md | [investigation-tool-data-plan.md](../architecture/investigation-tool-data-plan.md) |
| docs/architecture/investigation.md | [investigation.md](../architecture/investigation.md) |
| docs/architecture/unified-investigation-design-20261023.md | [unified-investigation-design-20261023.md](../architecture/unified-investigation-design-20261023.md) |
| docs/requirements/ai-soc2-requirements.md | [ai-soc2-requirements.md](../requirements/ai-soc2-requirements.md) |
| docs/requirements/AI SOC2.docx | [AI SOC2.docx](../requirements/AI%20SOC2.docx) |

## 4. OpenSpec活动变更

规格/任务/实施/审计记录；2.2/2.3仍未核销（6项）

| 文件 | 链接 |
| --- | --- |
| openspec/changes/continue-isolated-investigation-v2/audit.md | [audit.md](../../openspec/changes/continue-isolated-investigation-v2/audit.md) |
| openspec/changes/continue-isolated-investigation-v2/design.md | [design.md](../../openspec/changes/continue-isolated-investigation-v2/design.md) |
| openspec/changes/continue-isolated-investigation-v2/execution.md | [execution.md](../../openspec/changes/continue-isolated-investigation-v2/execution.md) |
| openspec/changes/continue-isolated-investigation-v2/proposal.md | [proposal.md](../../openspec/changes/continue-isolated-investigation-v2/proposal.md) |
| openspec/changes/continue-isolated-investigation-v2/specs/investigation-v2/spec.md | [spec.md](../../openspec/changes/continue-isolated-investigation-v2/specs/investigation-v2/spec.md) |
| openspec/changes/continue-isolated-investigation-v2/tasks.md | [tasks.md](../../openspec/changes/continue-isolated-investigation-v2/tasks.md) |

## 5. OpenSpec历史归档

历史归档；不得据此恢复旧任务或宣称F3完成（11项）

| 文件 | 链接 |
| --- | --- |
| openspec/changes/archive/2026-10-21-plan-alert-investigation-migration/audit.md | [audit.md](../../openspec/changes/archive/2026-10-21-plan-alert-investigation-migration/audit.md) |
| openspec/changes/archive/2026-10-21-plan-alert-investigation-migration/design.md | [design.md](../../openspec/changes/archive/2026-10-21-plan-alert-investigation-migration/design.md) |
| openspec/changes/archive/2026-10-21-plan-alert-investigation-migration/proposal.md | [proposal.md](../../openspec/changes/archive/2026-10-21-plan-alert-investigation-migration/proposal.md) |
| openspec/changes/archive/2026-10-21-plan-alert-investigation-migration/tasks.md | [tasks.md](../../openspec/changes/archive/2026-10-21-plan-alert-investigation-migration/tasks.md) |
| openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/assessment.md | [assessment.md](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/assessment.md) |
| openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/audit.md | [audit.md](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/audit.md) |
| openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/design.md | [design.md](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/design.md) |
| openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/execution.md | [execution.md](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/execution.md) |
| openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/proposal.md | [proposal.md](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/proposal.md) |
| openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/specs/alert-investigation-integrity/spec.md | [spec.md](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/specs/alert-investigation-integrity/spec.md) |
| openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/tasks.md | [tasks.md](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/tasks.md) |

## 6. 运行与审计说明

实施/审计说明；按原基线读取（10项）

| 文件 | 链接 |
| --- | --- |
| docs/operations/data-investigation-integration-audit-20261024.md | [data-investigation-integration-audit-20261024.md](../operations/data-investigation-integration-audit-20261024.md) |
| docs/operations/integrity-investigation-r01.md | [integrity-investigation-r01.md](../operations/integrity-investigation-r01.md) |
| docs/operations/investigation-candidate-build-20261022.md | [investigation-candidate-build-20261022.md](../operations/investigation-candidate-build-20261022.md) |
| docs/operations/investigation-candidate-images-20261022.md | [investigation-candidate-images-20261022.md](../operations/investigation-candidate-images-20261022.md) |
| docs/operations/investigation-functional-20261021.md | [investigation-functional-20261021.md](../operations/investigation-functional-20261021.md) |
| docs/operations/investigation-result-handoff-20261023.md | [investigation-result-handoff-20261023.md](../operations/investigation-result-handoff-20261023.md) |
| docs/operations/investigation-stage-closeout-20261022.md | [investigation-stage-closeout-20261022.md](../operations/investigation-stage-closeout-20261022.md) |
| docs/operations/investigation-stage-handoff-20261022.md | [investigation-stage-handoff-20261022.md](../operations/investigation-stage-handoff-20261022.md) |
| docs/operations/investigation-tools.md | [investigation-tools.md](../operations/investigation-tools.md) |
| docs/operations/unified-investigation-implementation.md | [unified-investigation-implementation.md](../operations/unified-investigation-implementation.md) |

## 7. 阶段机器回执

机器回执；真实/替身及限定范围见内文（52项）

| 文件 | 链接 |
| --- | --- |
| docs/operations/integrity-investigation-r01.json | [integrity-investigation-r01.json](../operations/integrity-investigation-r01.json) |
| docs/operations/investigation-alert-projection-20261025.json | [investigation-alert-projection-20261025.json](../operations/investigation-alert-projection-20261025.json) |
| docs/operations/investigation-compatible-gateway-20261025.json | [investigation-compatible-gateway-20261025.json](../operations/investigation-compatible-gateway-20261025.json) |
| docs/operations/investigation-compatible-internal-api-20261025.json | [investigation-compatible-internal-api-20261025.json](../operations/investigation-compatible-internal-api-20261025.json) |
| docs/operations/investigation-compatible-offline-20261025.json | [investigation-compatible-offline-20261025.json](../operations/investigation-compatible-offline-20261025.json) |
| docs/operations/investigation-compatible-owned-reader-20261025.json | [investigation-compatible-owned-reader-20261025.json](../operations/investigation-compatible-owned-reader-20261025.json) |
| docs/operations/investigation-fixed-recon-20261024.json | [investigation-fixed-recon-20261024.json](../operations/investigation-fixed-recon-20261024.json) |
| docs/operations/investigation-fixed-runtime-controller-20261024.json | [investigation-fixed-runtime-controller-20261024.json](../operations/investigation-fixed-runtime-controller-20261024.json) |
| docs/operations/investigation-fixed-runtime-controller-race-20261024.json | [investigation-fixed-runtime-controller-race-20261024.json](../operations/investigation-fixed-runtime-controller-race-20261024.json) |
| docs/operations/investigation-fixed-runtime-seam-20261024.json | [investigation-fixed-runtime-seam-20261024.json](../operations/investigation-fixed-runtime-seam-20261024.json) |
| docs/operations/investigation-fixed-runtime-state-20261024.json | [investigation-fixed-runtime-state-20261024.json](../operations/investigation-fixed-runtime-state-20261024.json) |
| docs/operations/investigation-fixed-runtime-store-20261024.json | [investigation-fixed-runtime-store-20261024.json](../operations/investigation-fixed-runtime-store-20261024.json) |
| docs/operations/investigation-independent-audit-20261024.json | [investigation-independent-audit-20261024.json](../operations/investigation-independent-audit-20261024.json) |
| docs/operations/investigation-internal-read-api-20261025.json | [investigation-internal-read-api-20261025.json](../operations/investigation-internal-read-api-20261025.json) |
| docs/operations/investigation-material-projection-20261024.json | [investigation-material-projection-20261024.json](../operations/investigation-material-projection-20261024.json) |
| docs/operations/investigation-network-identity-20261024.json | [investigation-network-identity-20261024.json](../operations/investigation-network-identity-20261024.json) |
| docs/operations/investigation-optional-excerpt-20261024.json | [investigation-optional-excerpt-20261024.json](../operations/investigation-optional-excerpt-20261024.json) |
| docs/operations/investigation-owned-reader-20261024.json | [investigation-owned-reader-20261024.json](../operations/investigation-owned-reader-20261024.json) |
| docs/operations/investigation-profile-contract-20261024.json | [investigation-profile-contract-20261024.json](../operations/investigation-profile-contract-20261024.json) |
| docs/operations/investigation-profile-restore-20261024.json | [investigation-profile-restore-20261024.json](../operations/investigation-profile-restore-20261024.json) |
| docs/operations/investigation-program-admission-20261025.json | [investigation-program-admission-20261025.json](../operations/investigation-program-admission-20261025.json) |
| docs/operations/investigation-program-admission-pg-20261025.json | [investigation-program-admission-pg-20261025.json](../operations/investigation-program-admission-pg-20261025.json) |
| docs/operations/investigation-program-alert-projection-20261025.json | [investigation-program-alert-projection-20261025.json](../operations/investigation-program-alert-projection-20261025.json) |
| docs/operations/investigation-program-coordinator-20261025.json | [investigation-program-coordinator-20261025.json](../operations/investigation-program-coordinator-20261025.json) |
| docs/operations/investigation-program-material-20261025.json | [investigation-program-material-20261025.json](../operations/investigation-program-material-20261025.json) |
| docs/operations/investigation-program-profile-restore-20261025.json | [investigation-program-profile-restore-20261025.json](../operations/investigation-program-profile-restore-20261025.json) |
| docs/operations/investigation-program-publication-preparation-20261025.json | [investigation-program-publication-preparation-20261025.json](../operations/investigation-program-publication-preparation-20261025.json) |
| docs/operations/investigation-program-publication-store-20261025.json | [investigation-program-publication-store-20261025.json](../operations/investigation-program-publication-store-20261025.json) |
| docs/operations/investigation-program-recon-20261025.json | [investigation-program-recon-20261025.json](../operations/investigation-program-recon-20261025.json) |
| docs/operations/investigation-program-runtime-20261025.json | [investigation-program-runtime-20261025.json](../operations/investigation-program-runtime-20261025.json) |
| docs/operations/investigation-program-runtime-state-20261025.json | [investigation-program-runtime-state-20261025.json](../operations/investigation-program-runtime-state-20261025.json) |
| docs/operations/investigation-program-runtime-store-20261025.json | [investigation-program-runtime-store-20261025.json](../operations/investigation-program-runtime-store-20261025.json) |
| docs/operations/investigation-program-start-api-20261025.json | [investigation-program-start-api-20261025.json](../operations/investigation-program-start-api-20261025.json) |
| docs/operations/investigation-program-start-contract-20261025.json | [investigation-program-start-contract-20261025.json](../operations/investigation-program-start-contract-20261025.json) |
| docs/operations/investigation-program-start-gateway-20261025.json | [investigation-program-start-gateway-20261025.json](../operations/investigation-program-start-gateway-20261025.json) |
| docs/operations/investigation-program-start-offline-20261025.json | [investigation-program-start-offline-20261025.json](../operations/investigation-program-start-offline-20261025.json) |
| docs/operations/investigation-publication-pg-seam-20261024.json | [investigation-publication-pg-seam-20261024.json](../operations/investigation-publication-pg-seam-20261024.json) |
| docs/operations/investigation-publication-preparation-20261024.json | [investigation-publication-preparation-20261024.json](../operations/investigation-publication-preparation-20261024.json) |
| docs/operations/investigation-publication-store-20261024.json | [investigation-publication-store-20261024.json](../operations/investigation-publication-store-20261024.json) |
| docs/operations/investigation-request-budget-20261024.json | [investigation-request-budget-20261024.json](../operations/investigation-request-budget-20261024.json) |
| docs/operations/investigation-result-gateway-20261025.json | [investigation-result-gateway-20261025.json](../operations/investigation-result-gateway-20261025.json) |
| docs/operations/investigation-result-http-read-20261025.json | [investigation-result-http-read-20261025.json](../operations/investigation-result-http-read-20261025.json) |
| docs/operations/investigation-review-validation-20261024.json | [investigation-review-validation-20261024.json](../operations/investigation-review-validation-20261024.json) |
| docs/operations/investigation-start-contract-20261025.json | [investigation-start-contract-20261025.json](../operations/investigation-start-contract-20261025.json) |
| docs/operations/investigation-v2-isolation-20261024.json | [investigation-v2-isolation-20261024.json](../operations/investigation-v2-isolation-20261024.json) |
| docs/operations/investigation-v2-query-seam-20261024.json | [investigation-v2-query-seam-20261024.json](../operations/investigation-v2-query-seam-20261024.json) |
| docs/operations/investigation-window-policy-20261024.json | [investigation-window-policy-20261024.json](../operations/investigation-window-policy-20261024.json) |
| docs/operations/unified-investigation-clickhouse-20261023.json | [unified-investigation-clickhouse-20261023.json](../operations/unified-investigation-clickhouse-20261023.json) |
| docs/operations/unified-investigation-m0-source.json | [unified-investigation-m0-source.json](../operations/unified-investigation-m0-source.json) |
| docs/operations/unified-investigation-m3-20261023.json | [unified-investigation-m3-20261023.json](../operations/unified-investigation-m3-20261023.json) |
| docs/operations/unified-investigation-m4-20261023.json | [unified-investigation-m4-20261023.json](../operations/unified-investigation-m4-20261023.json) |
| docs/operations/unified-investigation-m4-20261024.json | [unified-investigation-m4-20261024.json](../operations/unified-investigation-m4-20261024.json) |

## 8. 失败、修前与完整原件

原始/失败材料；不可只看修后汇总（16项）

| 文件 | 链接 |
| --- | --- |
| docs/operations/evidence/investigation-design-implementation-review-20261025.json | [investigation-design-implementation-review-20261025.json](../operations/evidence/investigation-design-implementation-review-20261025.json) |
| docs/operations/evidence/investigation-program-admission-pg-20261025.json | [investigation-program-admission-pg-20261025.json](../operations/evidence/investigation-program-admission-pg-20261025.json) |
| docs/operations/evidence/investigation-program-start-offline-20261025.json | [investigation-program-start-offline-20261025.json](../operations/evidence/investigation-program-start-offline-20261025.json) |
| docs/operations/investigation-compatible-gateway-failure-20261025.json | [investigation-compatible-gateway-failure-20261025.json](../operations/investigation-compatible-gateway-failure-20261025.json) |
| docs/operations/investigation-program-admission-failure-20261025.json | [investigation-program-admission-failure-20261025.json](../operations/investigation-program-admission-failure-20261025.json) |
| docs/operations/investigation-program-admission-pg-failure-20261025.json | [investigation-program-admission-pg-failure-20261025.json](../operations/investigation-program-admission-pg-failure-20261025.json) |
| docs/operations/investigation-program-profile-restore-failure-20261025.json | [investigation-program-profile-restore-failure-20261025.json](../operations/investigation-program-profile-restore-failure-20261025.json) |
| docs/operations/investigation-program-publication-preparation-failure-20261025.json | [investigation-program-publication-preparation-failure-20261025.json](../operations/investigation-program-publication-preparation-failure-20261025.json) |
| docs/operations/investigation-program-publication-store-failure-20261025.json | [investigation-program-publication-store-failure-20261025.json](../operations/investigation-program-publication-store-failure-20261025.json) |
| docs/operations/investigation-program-runtime-store-failure-20261025.json | [investigation-program-runtime-store-failure-20261025.json](../operations/investigation-program-runtime-store-failure-20261025.json) |
| docs/operations/investigation-program-start-api-failure-20261025.json | [investigation-program-start-api-failure-20261025.json](../operations/investigation-program-start-api-failure-20261025.json) |
| docs/operations/investigation-program-start-gateway-failure-20261025.json | [investigation-program-start-gateway-failure-20261025.json](../operations/investigation-program-start-gateway-failure-20261025.json) |
| docs/operations/investigation-program-start-offline-failure-20261025.json | [investigation-program-start-offline-failure-20261025.json](../operations/investigation-program-start-offline-failure-20261025.json) |
| docs/operations/investigation-publication-seam-probe-failure-20261024.json | [investigation-publication-seam-probe-failure-20261024.json](../operations/investigation-publication-seam-probe-failure-20261024.json) |
| docs/operations/investigation-publication-store-sourcecheck-failure-20261024.json | [investigation-publication-store-sourcecheck-failure-20261024.json](../operations/investigation-publication-store-sourcecheck-failure-20261024.json) |
| docs/operations/investigation-result-http-probe-failure-20261025.json | [investigation-result-http-probe-failure-20261025.json](../operations/investigation-result-http-probe-failure-20261025.json) |

## 9. 其他原始辅助文件

辅助材料；不执行这些脚本（0项）

| 文件 | 链接 |
| --- | --- |

## 10. 活动变更中的直接probe源文件

源文件链接；本轮未运行（9项）

| 文件 | 链接 |
| --- | --- |
| openspec/changes/continue-isolated-investigation-v2/probes/compatible_result_offline_seam.py | [compatible_result_offline_seam.py](../../openspec/changes/continue-isolated-investigation-v2/probes/compatible_result_offline_seam.py) |
| openspec/changes/continue-isolated-investigation-v2/probes/design_audit_20261024.py | [design_audit_20261024.py](../../openspec/changes/continue-isolated-investigation-v2/probes/design_audit_20261024.py) |
| openspec/changes/continue-isolated-investigation-v2/probes/fixed_recon_publication_seam.py | [fixed_recon_publication_seam.py](../../openspec/changes/continue-isolated-investigation-v2/probes/fixed_recon_publication_seam.py) |
| openspec/changes/continue-isolated-investigation-v2/probes/fixed_recon_runtime_seam.py | [fixed_recon_runtime_seam.py](../../openspec/changes/continue-isolated-investigation-v2/probes/fixed_recon_runtime_seam.py) |
| openspec/changes/continue-isolated-investigation-v2/probes/program_admission_pg_seam.py | [program_admission_pg_seam.py](../../openspec/changes/continue-isolated-investigation-v2/probes/program_admission_pg_seam.py) |
| openspec/changes/continue-isolated-investigation-v2/probes/program_start_offline_seam.py | [program_start_offline_seam.py](../../openspec/changes/continue-isolated-investigation-v2/probes/program_start_offline_seam.py) |
| openspec/changes/continue-isolated-investigation-v2/probes/result_http_read_seam.py | [result_http_read_seam.py](../../openspec/changes/continue-isolated-investigation-v2/probes/result_http_read_seam.py) |
| openspec/changes/continue-isolated-investigation-v2/probes/review_material_contracts.py | [review_material_contracts.py](../../openspec/changes/continue-isolated-investigation-v2/probes/review_material_contracts.py) |
| openspec/changes/continue-isolated-investigation-v2/probes/v2_query_seam.py | [v2_query_seam.py](../../openspec/changes/continue-isolated-investigation-v2/probes/v2_query_seam.py) |

## 11. 当前直接验证源码

当前功能测试源码；不是本轮新测试结果（3项）

| 文件 | 链接 |
| --- | --- |
| services/api/tests/test_case_analysis_api.py | [test_case_analysis_api.py](../../services/api/tests/test_case_analysis_api.py) |
| services/api/tests/test_investigation_incident_api.py | [test_investigation_incident_api.py](../../services/api/tests/test_investigation_incident_api.py) |
| services/api/tests/test_investigation_incident_summary.py | [test_investigation_incident_summary.py](../../services/api/tests/test_investigation_incident_summary.py) |

## 12. 当前源码目录

- [API v2源码](../../services/api/app/investigation_v2)：F1/F2/F3及旧兼容网关。
- [Agents v2源码](../../services/agents/app/investigation_v2)：fixed/program/旧M1–M8合同与运行。
- [API v2说明](../../services/api/app/investigation_v2/README.md)。
- [Agents v2说明](../../services/agents/app/investigation_v2/README.md)。

本目录共链接137个不同文件；同一文件不重复计数。目录型链接和上述说明链接不计入文件清单数量。
