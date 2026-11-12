# 限定结束审计

2026-11-12。审计者未参与本 change 的代码实现；只读复核当前工作树、OpenSpec、已保存直接检查与流程证据，独立写入本文。未运行测试、数据库查询、嵌入／模型、网络请求或部署，未读取私密 `.local`，未修改业务源码、根文档或 `tools/model-preflight/`。前序历史知识 change 已归档，本次不重新审计。

**结论：本地功能限定可交付（LOCAL_ACCEPTED）；未发现仍需处理的本范围功能阻断。模型质量仍为 NOT_PASSED。** 结论覆盖已验证的用途／条件筛选、同版本去重与原引用保留、历史当前资格和版本选择、正常 Case 保存／GET 及本地 4177 记录。它不是生产发布验收、知识合理采用或完整模型质量通过；发布读回、归档、Git／父项目回执仍待后续实际完成。

## 实现与保存证据

证据目录为 [knowledge-selection-20261112-01](../../../../docs/operations/evidence/knowledge-selection-20261112-01/)，主要核对 [真实数据库快照](../../../../docs/operations/evidence/knowledge-selection-20261112-01/local-flow/export/database.json)、原 HTTP／模型请求回执与 [流程汇总](../../../../docs/operations/evidence/knowledge-selection-20261112-01/local-flow-summary.json)，不只采用汇总文字作结论。

| 核对项 | 限定结论 |
| --- | --- |
| 用途与适用条件 | 三目的共用存储而分别保留资料类型／目的过滤。`knowledge_applicability.py` 只比较配置字段及原标签／历史观察；主题需明确匹配，已知冲突排除，必要条件未知排除，通用标记不绕过主题或冲突，历史无通用兜底。候选上限独立配置，无循环补搜。实际 9 查询：5 条全部筛除、1 条原始查空、3 条有数据；6 次 `applicability_conflict`、2 次 `history_superseded`、5 条选入与快照一致。 |
| 去重与原引用 | `knowledge_model_input.py` 按文档／内容版本及历史来源身份分组，按原角色与部分合并；原检索 5 行保存，模型为 3 唯一知识块、5 个角色来源。方法两块跨目的各合并一次，`origins` 保留原路径／用途／成员映射；canonical 引用仍指向真实冻结行。历史卡、分诊和人工正文分别保持 `source_label`、`prior_analysis`、`human_statement`，历史主体仍标为本案外，未改成本案观察。 |
| Deep／C6 选择与依赖 | `case_followup_input.py` 先恢复冻结前序引用，再选可选知识；引用历史部分时恢复同卡各角色，不查询最新正文。修正后 Deep 可选目的为方法／历史，coverage 不主动附加；C6 可选范围取未决问题；已引用依赖先于目的、范围和可选容量筛选。真实两个 Deep 及 C6 保存的前序映射均无缺失，但被接受结果没有知识结构化引用，因此知识依赖恢复分支由定向检查与代码支持，不能宣称本次真实模型流程已覆盖。 |
| 历史资格与修订 | `knowledge_history.py` 要求完整材料、事件时间和至少一份正文／verdict 存在且对应当前材料的保存判断；带来源 Run 的分诊还要求该告警 Run completed。回读同时核当前指针和内容，不回退旧卡。保存的显式重复导入保持同 ID；演练反馈修订产生新卡；旧卡两次 GET 内容一致，仍可追溯；实际候选排除了旧版本。反馈修订使用演练 SQL，不等同生产人工操作。 |
| 保存与读取 | 一案一 Run：Case `a1191380-a6ef-5c45-8fbf-70efb0eec214`，Run `0be3c4be-3b5a-4ded-afab-16f1e80f0a91`。5 次 Case HTTP 均为 200；Result 的 ID、来源 Run、交付／校验／结论状态和 conclusion 在保存快照与 GET 一致。知识 HTTP 回执成功包含资料创建的 201，不把所有业务响应笼统记成 200。 |
| 4177 | 本地索引由 66→67 条，原 66 条记录内容保持，新页对应本次 1 Run／21 步／51 工件及 partial 交付。inspector 代码和新静态页包含候选筛除、合并出处、知识未送入原因及结构化引用状态。本审计未启动浏览器或读取正式 4177；生产静态发布与读回尚未验收。 |

## 直接检查、审计发现与源码差异

- [direct-tests.xml](../../../../docs/operations/evidence/knowledge-selection-20261112-01/direct-tests.xml) 保存 16 项通过，errors／failures／skipped 均为 0；检查覆盖本次直接行为，未扩展全仓回归或模型采样。流程后的 [nullable-assessment-check.xml](../../../../docs/operations/evidence/knowledge-selection-20261112-01/nullable-assessment-check.xml) 和最终 [assessment-eligibility-final.xml](../../../../docs/operations/evidence/knowledge-selection-20261112-01/assessment-eligibility-final.xml) 各为同一资格检查的 1 项通过，保留先后回执，不当作新增独立场景。
- 审计初查发现 Deep 仅按成员／容量选择，纯技术可选知识仍可能进入，与 design §3 的方法／历史范围不一致。实施方已在 `case-input-v1.json` 增加 `stage_purposes`，由 `runtime_policy.py` 校验，`knowledge_model_input.choose()` 按合并出处的目的筛选；依赖分支仍在前。[audit-purpose-check.xml](../../../../docs/operations/evidence/knowledge-selection-20261112-01/audit-purpose-check.xml) 保存 1 项通过：同成员纯技术可选块排除，已引用的原值／原引用仍恢复。此发现已限定修复，不要求再运行真实模型。
- 流程后另有 rationale 可空的最小处理：`knowledge_history.py` 将 null 判为无可用判断正文，避免对 null 调用 `.strip()`。没有以此改写原流程、原计划或原答。
- 已复核 [post-flow-source-delta.json](../../../../docs/operations/evidence/knowledge-selection-20261112-01/post-flow-source-delta.json) 的四项文件：流程 hash 与冻结 `plan.json` 一致，最终 hash 与当前源码一致。上述空值及 Deep 目的修正没有重新走真实 Case；支持结论的是原流程加对应直接检查，不能把原流程声称为最终四文件版本的整链实测。
- C3 正文准备、Deep／C6 组装已有整条可选知识移除；C3 后续附加工具目录和实际 token 测量超限仍沿原显式失败，没有新增自动裁减。本次未触及这些容量限制。design §6 与 validation 已收紧表述，不据未测边界宣称容量保证。

复读后的 proposal、design、tasks、validation、知识交接及 PROGRESS 已区分当前本地实现与前批生产发布；过期“仅规划”及本地 66 条口径已修正。任务中的发布／归档／Git 回执仍保持未完成。

## 原失败与未验范围

六份真实调用回执 usage 合计 **119,412 reported tokens**，包括既有 C3／C6 各一次纠正，没有增加 Run 或采样。C3 首次 `source_member_mismatch`；纠正后部分接受并保留 `observed_original_fields_exceed_statement_contract`。C6 首次 `duplicate_source`，纠正后仍 `delivery_source_coverage_missing`。最终 Result `0b4a01c6-8bdd-4046-8644-11760a43e5d7` 为 **partial／rejected，conclusion_state=unavailable，conclusion=null**；Run completed 仅说明流程结束。

仅 C3 首次原答结构化引用了知识，其余原答未见结构化知识引用；进入输入、正文提及、合法引用和合理采用分别判断。两个 Deep 的冻结问题均涉及全案，实际仍各带 3 唯一块，不能称本次真实流程已经证明按问题缩小了知识范围。F02 召回正文相关性／合理使用及 M01／M02 质量问题继续开放，不由过滤与去重检查核销。

本次为真实本地 PostgreSQL、独立验收向量集合和真实模型的一次演练流程，身份及模型传输沿既有本地适配；不是生产完整调查或真实历史真值验证。审计截止时 21 仍为前批 `v1.2-20261112-r1`，本 change 尚未发布。未验生产新版本实际加载／检索读回、正式静态页面、自动入库／自动消费者、A/I 新检索、Deep 动态检索或语义准确率；没有据本地通过预报归档、推送或父项目引用成功。
