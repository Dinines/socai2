# 限定发布结束审计

2026-11-12。审计者未参与本 change 的实现或发布；本次只读核对仓库保存回执及当前交接文字，写入本文。未重跑测试、模型、数据库查询、网络请求、浏览器或部署。原 [audit.md](audit.md) 保持为发布前本地截止审计，本文补充此后发生的发布与读回，不覆盖原失败或未验结论。

**结论：限定发布验收通过（RELEASE_ACCEPTED），本 change 具备归档条件；模型质量仍为 NOT_PASSED。** 保存证据支持 `v1.2-20261112-r3`／`processing-20261112-r2` 的实际发布、配置加载、三目的生产检索及静态页面读回。归档、最终 Git 推送与父项目引用尚未发生，不在本结论中预报成功。

## 发布与实际切换

依据 [交付汇总](../../../../docs/operations/evidence/knowledge-selection-20261112-01/delivery-summary.json)、[发布读回](../../../../docs/operations/evidence/knowledge-selection-20261112-01/release-readback.json)及原 `unified-*` 回执核对：

- 首个冻结计划 `v1.2-20261112-r2` 已上传／构建，但 [02:02:46 preflight](../../../../docs/operations/evidence/knowledge-selection-20261112-01/unified-preflight-20261112T020246916612Z.json) 以 `runtime_image_drift_api`、exit 1 失败。原因是预期 API 镜像／Compose 来源仍指向旧基线；[更正记录](../../../../docs/operations/evidence/knowledge-selection-20261112-01/release-plan-correction.json)保留旧失败和旧冻结目录，明确更正前 rollout 为 0。不能把这次失败写成成功或另一次实际发布。
- 根据 [实际基线](../../../../docs/operations/evidence/knowledge-selection-20261112-01/release-baseline.json)修正为 r3 后，upload／build／preflight／prepare／activate 均保存成功回执，最终清单 hash 为 `bce977ca1577aa9383cf49417530cdf50d9092450664351594d2dc2d34cce6d6`。处理镜像复用本批 `processing-20261112-r2` 的成功构建，未据此前 r2 预检失败重做业务流程。
- 保存的 rollout 仅 [API 一次](../../../../docs/operations/evidence/knowledge-selection-20261112-01/unified-rollout-20261112T020632826161Z.json)及[工作台一次](../../../../docs/operations/evidence/knowledge-selection-20261112-01/unified-rollout-20261112T020700064569Z.json)。读回中二者容器 ID 改变；工作台沿用原镜像、切换绑定源码。fusion、agents、projection、litellm 的容器 ID 与镜像逐项和发布前一致，六服务均记录 healthy。后续静态发布的 `containers_unchanged=true` 只限定静态步骤，不否认此前这两次切换。
- 当前指针与处理入口均读回 r3，自动消费者仍关闭；未增加调查 DDL 或告警交接合同变更。

[实际加载配置](../../../../docs/operations/evidence/knowledge-selection-20261112-01/loaded-selection.json)显示 C3／C6 三目的、Deep 方法／历史，知识字符上限 12,000／8,000／8,000，各目的候选上限 8。Case profile hash `81bdc248f81477b56ff028551f4b9b9636dcfe4557b85092e50735e88e7d0858` 对应本地审计后的最终配置；knowledge profile hash `712f70ff2786c7be9bf9b834031c441c8d0145a74d857f937ff6accf1cdaaf8e` 与仓库配置、发布读回及两个生产检索回执一致。证明新选择配置已实际加载，不等于在生产重新执行了完整模型调查。

发布后收尾另发现仓库 `deploy/aisoc21/release-v1.2.json` 的描述字段 `processing.image` 仍是旧 `704344…`。限定复读确认：`release_12.py` 的 `configure_processing()` 和 `verify()` 通过 `processing.profile` 调用 `production_processing.py`；后者从 profile 的 `image.id/tag` 选择并核实镜像，不消费上述描述字段。原生产 profile 与处理构建回执均为 `sha256:fc646d523577e884696eb5ddc85d064b0d2afef3d5d7f8950cb8df8b0adeccfd`，当前仓库字段已对齐。该[元数据修正](../../../../docs/operations/evidence/knowledge-selection-20261112-01/release-metadata-correction.json)保留冻结 r3 的 release／manifest 和原回执；当前仓库清单因此与原冻结清单存在已记录的单字段差异，不能声称冻结工件被重新生成或服务再次发布。此差异不改变上述实际加载依据。

## 生产知识与凭据回执

| 范围 | 实际核对结果 |
| --- | --- |
| 历史知识 | [HTTP](../../../../docs/operations/evidence/knowledge-selection-20261112-01/production/history/http.json) 为显式导入／索引／GET 3 次，均 200；[只读检索](../../../../docs/operations/evidence/knowledge-selection-20261112-01/production/history/retrieval.json) 1 个历史目的查询返回 1 行。文档 `5837d5c7-2c53-53dc-9923-d75487f25c46` 的导入来源、GET 卡片、检索原正文一致，索引／检索／按保存原字段重算的 content hash 一致；`source_version_state=current`、适用条件 applicable，已保存分诊为 usable、人工反馈未记录。对象是已有演练告警，不是新增生产调查真值。 |
| 技术／方法知识 | [HTTP](../../../../docs/operations/evidence/knowledge-selection-20261112-01/production/method/http.json) 共 4 次：导入 201、索引 200、两块元数据 GET 各 200；一份资料形成两块。 [只读检索](../../../../docs/operations/evidence/knowledge-selection-20261112-01/production/method/retrieval.json) 的技术解释／取证指导各返回两行，合计 4 行、2 唯一块。两块原正文／元数据重算 hash 与索引及检索一致；另有 4 次 `comparable_topic_missing` 候选排除，不能当成查空或返回知识。 |
| 合计与边界 | **7 次业务 HTTP、3 个目的查询、5 返回行、3 唯一知识块。** 两个检索为只读 adapter 探针，使用保存查询及配置时间边界；没有生产新 Case、Run 写入或分析模型调用。导入与索引确实写入知识并调用现有嵌入／向量服务，不能把“分析模型 0”写成没有嵌入调用或全程只读。 |
| 临时凭据 | [签发](../../../../docs/operations/evidence/knowledge-selection-20261112-01/credential-issue.json)与[撤销](../../../../docs/operations/evidence/knowledge-selection-20261112-01/credential-revoke.json)的 ID、租户和用户对应；撤销后实际 HTTP 状态为 401，账号角色未变。没有保留未撤销临时 key 的交付条件。 |

## 4177 与交接

[静态发布](../../../../docs/operations/evidence/knowledge-selection-20261112-01/static-publication.json)记录正式 4177 **38→39 条，仅追加 1 条**，原记录、原文件及无关内容保持，未刷新旧批次；79 文件和 80 HTTP 读回通过。保存的 [static-manifest.json](../../../../docs/operations/evidence/knowledge-selection-20261112-01/static-manifest.json) 确有 79 文件，其原文件 SHA-256 与发布回执的 `ca2a525ba14711050b75837494a1221dee434acf7596ed0e8233234a32f25ea1` 一致。新索引 hash 为 `fac81eb59fd1caa51d761da49907caab8a6a5b5e38394134f471d827c9b95ba4`。本地 67 条与正式 39 条是不同记录集合，不混计。

[浏览器读回记录](../../../../docs/operations/evidence/knowledge-selection-20261112-01/ui-readback.json)保存了经本机 SSH 转发查看正式 4177 的结果：知识 5 行及 data／filtered／empty、候选身份／条件／hash、两次去重与 canonical 引用、合并用途及原路径可见，输入存在与原答结构化引用、校验错误分别显示。此项只覆盖知识及 C3 inspector，没有承诺完整产品 UI 回归，也没有新增模型或数据库写入。

已补读 PROGRESS、前后端交接、OpenSpec 导航及主调查记录、调查导航／两份知识交接／问题清单、两份部署 README 和本 change 的 validation。当前文字与 r3、7 次业务 HTTP／3 目的查询／5 行、正式 39 条和质量 NOT_PASSED 一致；归档及最终 Git／父引用仍明确处于后续收尾，不提前核销主调查开放项。

## 质量与后续收尾边界

本地原流程仍为 **6 次模型、119,412 reported tokens**；Result `0b4a01c6-8bdd-4046-8644-11760a43e5d7` 保持 **partial／rejected、conclusion_state=unavailable、conclusion=null**。C3 的 `source_member_mismatch` 及纠正后部分接受时的 `observed_original_fields_exceed_statement_contract`、C6 的 `duplicate_source` 及纠正后的 `delivery_source_coverage_missing` 均保留，生产发布成功不核销这些失败。

原流程后 null 判断资格与 Deep 目的筛选修正仅由对应直接检查支持，原流程未重跑；知识依赖恢复、较窄问题范围的选择未在本次被接受真实模型结果中获得整链验证。最终目录／token 容量限制、知识正文相关性及合理采用、自动导入／消费、A/I 新检索、Deep 动态检索等限制继续沿 [本地审计](audit.md)和[验收记录](validation.md)保留。

本地直接验收、独立审计与本次限定发布读回已形成闭环，可据此执行归档及一次最终 Git／父项目引用收尾。该收尾须以之后真实提交、远端和 gitlink 回执为准；本文不声明归档、推送或父项目更新已经完成。
