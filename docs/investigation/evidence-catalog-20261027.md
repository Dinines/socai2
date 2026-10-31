**2026-10-31实施证据：** [修复记录](audit-fixes-implementation-20261031.md)、[源码/测试/候选包回执](../operations/investigation-audit-fixes-20261031.json)、[阶段及最终原日志目录](../operations/evidence/investigation-audit-fixes-20261031/)；31个不同直接用例最终通过，保持此前静态审计和r1真实证据。

# 调查模块证据与文档目录

2026-10-31更新。先看[最新指南](audit-guide-20261031.md)与[当前设计](current-design-alignment-20261027.md)，再按以下当前材料进入。文件名保留原入口；底部137项为原6044615历史目录，范围不回填为新验证。

本地源码为5b95138；最新6项受影响直接用例通过记录属于本地修复。真实四案例为512c004/r1，原失败保留，r2常驻与真实复验待做。以下分类用于查找材料，不代表全部功能通过。

## 当前实施与验证说明

| 文档 | 入口 |
| --- | --- |
| 最新指南与审计步骤 | [2026-10-31指南](audit-guide-20261031.md) |
| 设计—实现详细审计 | [发现、功能对照与验证边界](design-implementation-audit-20261031.md) |
| 本次静态审计清单 | [源码/测试索引、路由及原件hash](../operations/investigation-static-audit-20261031.json) |
| 审计后OpenSpec规划 | [提案](../../openspec/changes/fix-investigation-audit-gaps/proposal.md)、[设计](../../openspec/changes/fix-investigation-audit-gaps/design.md)、[任务/验证](../../openspec/changes/fix-investigation-audit-gaps/tasks.md)（尚未实施） |
| 当前设计 | [职责与流程](current-design-alignment-20261027.md) |
| 当前接口合同 | [字段与错误](interface-contracts-20261027.md) |
| 告警、事件与Case调查结果的关联 | [alert-event-investigation-links-20261028.md](alert-event-investigation-links-20261028.md) |
| 调查功能基本运行测试（2026-10-28） | [basic-runtime-test-20261028.md](basic-runtime-test-20261028.md) |
| Case创建后的调查初版 | [case-first-version-20261028.md](case-first-version-20261028.md) |
| F4：告警和事件成员转入Case | [case-linking-20261028.md](case-linking-20261028.md) |
| 公共调查索引与证据跳转 | [execution-index-and-evidence-20261028.md](execution-index-and-evidence-20261028.md) |
| 事件→Case→AI概况基本运行验证（2026-10-28） | [incident-case-basic-flow-20261028.md](incident-case-basic-flow-20261028.md) |
| Case多告警综合分析：成员、关联、时间线与未决问题 | [multi-alert-synthesis-20261028.md](multi-alert-synthesis-20261028.md) |
| 多案例逐步HTTP测试（2026-10-28） | [multi-case-http-20261028.md](multi-case-http-20261028.md) |
| 调查模块后续功能规划 | [next-phase-plan-20261028.md](next-phase-plan-20261028.md) |
| Case产品HTTP Tool：主机详情 | [product-host-tool-20261028.md](product-host-tool-20261028.md) |
| 调查真实PG联调结果（2026-10-28） | [real-pg-test-20261028.md](real-pg-test-20261028.md) |
| 独立调查API与调用方接入（2026-10-28） | [resident-api-20261028.md](resident-api-20261028.md) |
| 调查功能逐步测试（2026-10-28） | [step-by-step-test-20261028.md](step-by-step-test-20261028.md) |

## 四案例逐步记录与报告

以下报告是当批保存内容，保留语义偏差与失败，不用最新修复改写。

| 文件 | 入口 |
| --- | --- |
| archive-upload-main-report.md | [查看](cases-20261028/archive-upload-main-report.md) |
| archive-upload.md | [查看](cases-20261028/archive-upload.md) |
| lsass-smb-subset-main-report.md | [查看](cases-20261028/lsass-smb-subset-main-report.md) |
| lsass-smb-subset.md | [查看](cases-20261028/lsass-smb-subset.md) |
| network-positive-reuse-followup-report.md | [查看](cases-20261028/network-positive-reuse-followup-report.md) |
| network-positive-reuse-main-report.md | [查看](cases-20261028/network-positive-reuse-main-report.md) |
| network-positive-reuse.md | [查看](cases-20261028/network-positive-reuse.md) |
| office-powershell-followup-report.md | [查看](cases-20261028/office-powershell-followup-report.md) |
| office-powershell-main-report.md | [查看](cases-20261028/office-powershell-main-report.md) |
| office-powershell.md | [查看](cases-20261028/office-powershell.md) |

## 后续机器回执

下表包括16份10月28日命名的回执；followup-fix-local随10月29日提交保存。各自基线、实际观察和限制在原文件内，测试数不累计为当前全量通过。

| 回执 | 入口 |
| --- | --- |
| investigation-api-entry-local-20261028.json | [查看](../operations/investigation-api-entry-local-20261028.json) |
| investigation-api-resident-20261028.json | [查看](../operations/investigation-api-resident-20261028.json) |
| investigation-basic-runtime-20261028.json | [查看](../operations/investigation-basic-runtime-20261028.json) |
| investigation-followup-fix-local-20261028.json | [查看](../operations/investigation-followup-fix-local-20261028.json) |
| investigation-followup-step1-20261028.json | [查看](../operations/investigation-followup-step1-20261028.json) |
| investigation-followup-step2-20261028.json | [查看](../operations/investigation-followup-step2-20261028.json) |
| investigation-followup-step4-20261028.json | [查看](../operations/investigation-followup-step4-20261028.json) |
| investigation-followup-step7-20261028.json | [查看](../operations/investigation-followup-step7-20261028.json) |
| investigation-followup-step8-input-20261028.json | [查看](../operations/investigation-followup-step8-input-20261028.json) |
| investigation-followup-step9-20261028.json | [查看](../operations/investigation-followup-step9-20261028.json) |
| investigation-incident-case-flow-20261028.json | [查看](../operations/investigation-incident-case-flow-20261028.json) |
| investigation-multi-case-budget-diagnosis-20261028.json | [查看](../operations/investigation-multi-case-budget-diagnosis-20261028.json) |
| investigation-multi-case-inputs-20261028.json | [查看](../operations/investigation-multi-case-inputs-20261028.json) |
| investigation-multi-case-summary-20261028.json | [查看](../operations/investigation-multi-case-summary-20261028.json) |
| investigation-real-pg-20261028.json | [查看](../operations/investigation-real-pg-20261028.json) |
| investigation-tool-schema-step5-20261028.json | [查看](../operations/investigation-tool-schema-step5-20261028.json) |

## 原件与当前工作文件

| 用途 | 文件 |
| --- | --- |
| 四案例实际脚本 | [冻结执行脚本](../operations/evidence/INVHTTP-20261028-01/investigation_http_cases.py) |
| 四案例实际输入 | [冻结cases.json](../operations/evidence/INVHTTP-20261028-01/cases.json) |
| 当批启动及哈希观察 | [启动脚本](../operations/evidence/INVHTTP-20261028-01/run_multi_case_http.py)、[execution-observation](../operations/evidence/INVHTTP-20261028-01/execution-observation.json) |
| 原批汇总与凭据收尾 | [batch.json](../operations/evidence/INVHTTP-20261028-01/results/batch.json)、[credential-receipt](../operations/evidence/INVHTTP-20261028-01/credential-receipt.json) |
| 后续复验工作文件 | [当前脚本](../../tools/testdata/investigation_http_cases.py)、[当前清单](../../tools/testdata/investigation-http-cases-20261028.json)，已增加必需Tool，与原批不同 |
| 最新Case测试源码 | [test_case_analysis_api.py](../../services/api/tests/test_case_analysis_api.py)，含必需Tool、复用及不可用/跳过场景 |
| 最新修复规格与状态 | [proposal](../../openspec/changes/fix-case-followup-gaps/proposal.md)、[design](../../openspec/changes/fix-case-followup-gaps/design.md)、[spec](../../openspec/changes/fix-case-followup-gaps/specs/case-followup/spec.md)、[tasks](../../openspec/changes/fix-case-followup-gaps/tasks.md) |
| 四案例测试任务状态 | [tasks](../../openspec/changes/exercise-investigation-http-cases/tasks.md)，记录测试工作完成，不表示全功能验收 |
| 常驻部署任务状态 | [tasks](../../openspec/changes/serve-investigation-api/tasks.md)，实际版本仍按部署回执解释 |

每个案例页面分别链接该案例全部请求/响应、步骤、证据及报告；完整原件位于docs/operations/evidence/INVHTTP-20261028-01，历史运行的哈希应与该目录冻结文件核对。

## 2026-10-27历史目录

以下保留原目录及早期F4补记；其中“当前”一词均指当时基线，不覆盖上述更新。

2026-10-28增补：[F4实现与直接验证](case-linking-20261028.md)、[F4用例源码](../../services/api/tests/test_case_links_api.py)。下方137项为2026-10-27基线目录，不把新验证回填为历史通过项。

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
