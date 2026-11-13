# 独立结束审计

审计日期：2026-11-12发布前；2026-11-13恢复核对候选并完成发布后复核。审计者：`subject_management_audit`，未参与本change实现；审计阶段只读代码、规格、回执和候选，未调用业务写入、模型或部署。本文件由主执行者明确授权写入。

## 发布前结论

**限定审计通过，当前发布前阻塞为零。** 本结论允许沿已获授权范围发布本机与21的独立API及Swagger；不代表发布已经发生，也不替代发布后实际服务和数据读回复核。

范围为告警人工判定、告警管理、事件管理各单条／批量，共E48–E53六操作。未扩大到页面、模型输入、自动消费者、问答、探索、资产平台或数据库迁移；主调查及模型质量未完项保持。

## 核对内容与证据

- 规格及实现：已读proposal、design、tasks和`alert-incident-management`规格，strict校验通过。核对新增合同、服务、路由、现有页面路由挂载与批量配置。
- 写入行为：人工反馈追加保存并绑定当前材料；D02关闭／反向恢复、人工关闭保留原判定、事件分配／解决／等级覆盖与现有规则一致。原模型分诊、材料和成员等级不被新接口覆盖，不自动启动Run或改变父Case处理状态。
- 事务：操作键事务锁，目标UUID排序行锁，逐项版本核对；整批成功或拒绝。哈希包含操作者、动作、明确字段和目标版本，同键同意图读原回执，不同意图409；管理无变化不增加主体版本。活动记录各实际目标的前后值。
- 原合同：独立比较HEAD基线与候选，原47操作的requestBody、responses、parameters及106个原Schema逐项不变；保留原路径／方法顺序。新六操作在末尾映射E48–E53，不错位旧编号。
- 本机真实验证：[local-http/verification.json](../../../../docs/operations/evidence/subject-management-20261112-01/local-http/verification.json)及原始回执共86次TCP HTTP（79次200、3次409、3次422、1次404），覆盖六入口、保存后GET、改判关闭／恢复、批量冲突整批拒绝、重放、未选对象和原分诊保留。
- SQL读回：[local-sql.json](../../../../docs/operations/evidence/subject-management-20261112-01/local-sql.json)核对6主体全部facts与HTTP最终值一致，原分诊及等级保持。此为本机隔离PG，不能替代21实际验证。
- 文档：候选`2026-11-12.docs7`共53操作、127类型、540个固定输出字段、125项功能；新增四项归告警、两项归事件。新六组请求和响应通过实际Pydantic合同校验，路径／参数／结果／状态对应一致。
- 交接：根指南、README、产品功能状态、D02记录、测试指南和后续计划同步本批范围；原七类规则没有重新扩展。
- 部署候选：基底固定`sha256:4a7bf9bde482bddbc3753a421e4991a98d572ed2663e8a2e464d67b9ead407b6`；仅覆盖页面路由、主体管理路由、服务、合同和批量配置五文件。独立核对manifest与候选文件哈希、候选与工作树五文件一致，manifest SHA-256为`d078788506e2f80fed0daa52d80c3ca9a6e4cbc135adce2183729b349559ad22`。
- 环境配置：21的AMD64配置明确`aisoc`、18024及`/app/app/socai2/subject_management.json`，Dockerfile复制位置一致；本机ARM64配置明确`v12_upgrade_dev`和18024，独立候选18026。私密环境中的批量配置路径实际存在且值为100，未输出凭据。根local/aisoc21配置与本批profiles逐值相同，指南启动入口一致。

## 审计发现及关闭情况

| 发现 | 修正与复核 |
| --- | --- |
| 反馈传播到关联事件时，较早取得的now可能覆盖另一并发更新后的较新business_updated_at | 改为`greatest(existing, now)`，版本继续递增；[monotonic-time.json](../../../../docs/operations/evidence/subject-management-20261112-01/monotonic-time.json)用独立新合成对象直接PG核对时间不倒退，通过 |
| E50/E51请求设置标签，响应示例仍为空数组 | 生成器修正并重建，候选响应与提交标签一致 |
| 新接口403示例误用旧Case错误码，六操作复制了不可达的owner／关闭理由错误 | 重建后403使用`subject_user_actor_required`；owner错误仅管理入口，关闭理由错误仅告警管理入口，批量选择错误仅批量入口 |
| 当前启动指南指向旧根profiles，功能清单仍保留“不修改业务代码”的旧阶段声明 | 根profiles已同步本批，清单声明改为六接口实际实施范围；复核一致 |

## 发布后结论（2026-11-13）

**限定结束审计通过，本change无剩余交付阻塞，已满足完成1.6及归档前检查的审计条件。** 此结论以主执行者保存的真实发布、HTTP及SQL回执为依据，审计者没有重复业务写入或发布；归档、Git提交／推送及父项目引用更新未由本审计执行。

- 实际运行来源：[本机发布回执](../../../../docs/operations/evidence/subject-management-20261112-01/local-api-release.json)、[21发布回执](../../../../docs/operations/evidence/subject-management-20261112-01/21-api-release.json)及[21运行核对](../../../../docs/operations/evidence/subject-management-20261112-01/21-runtime.json)对应本机`subject-management-20261112-r1-local`、21`subject-management-20261112-r1`，均挂载53操作。独立逐项比较两端记录的五文件SHA-256与当前源码，全部一致；21实际镜像为`sha256:8ebdf8ff7c727355cb0ec0a886f380eaf22056d9892d0f2b9244026d8045af1d`，保持发布前五文件覆盖范围。
- 环境配置：本机使用`v12_upgrade_dev`；21 reader、writer及实际写连接均为`aisoc`，实际writer为`socai2_prod_processor`。运行批量配置为100；根local/aisoc21 profiles仍与本批profiles一致，21路径对应`/app/app/socai2/subject_management.json`。部署回执确认其他既有容器保持。
- 直接业务验收：[本机最终HTTP](../../../../docs/operations/evidence/subject-management-20261112-01/local-release-http/verification.json)与[21 HTTP](../../../../docs/operations/evidence/subject-management-20261112-01/21-http/verification.json)分别使用新批合成对象。独立读取两份原始`responses.json`，各86次，均为79次200、3次409、3次422、1次404；写入路径只涉及本批管理及验收Case创建，没有调查启动或模型分析入口。六个单条／批量操作、保存后详情／活动、冲突整批拒绝、幂等、未选对象和原分诊保留均有直接回执。
- 数据读回：[本机SQL](../../../../docs/operations/evidence/subject-management-20261112-01/local-release-sql.json)及[21 SQL](../../../../docs/operations/evidence/subject-management-20261112-01/21-sql.json)各比较6个主体，全部facts与HTTP最终值一致，原分诊及成员等级保留。两端新Case分别为`83ceb088-ee3b-54e1-8fe3-8428c437dc15`、`0407cdc9-141c-5cb6-95a5-13ecfbfe62a3`，仅供关联活动验证，未启动Run。
- Swagger实际发布：[本机](../../../../docs/operations/evidence/subject-management-20261112-01/local-swagger.json)、[21](../../../../docs/operations/evidence/subject-management-20261112-01/21-swagger.json)六个入口均200且响应摘要逐项相同；OpenAPI、manifest、guide、examples、字段页摘要亦与仓库最终交付及本机实际挂载文件相同。[固定docs7回执](../../../../deploy/api-docs/receipts/20261112-docs7.json)与当前发布回执一致。最终OpenAPI SHA-256为`22f7825799ae872fb31c237b2dbd2016d79cb6680eb8351316e00f442b57a380`，共53操作、50已实现、3预留501，E48–E51归告警、E52–E53归事件。
- 最终合同复核：再次逐项核对原47公共操作的编号／顺序、请求／响应／参数和106个原始Schema不变；最终发布文件中的六组请求及响应均通过实际Pydantic合同校验，已修正的标签及403／各入口错误示例保留。早期`.local/subject-management-20261112-01/handoff`与最终发布的OpenAPI差异仅为54处说明文字的实际部署状态更新，guide同步操作总数及部署状态；请求、响应、Schema和示例不受影响。最终发布文件为本次复核依据。
- 交接与结束检查：验证记录、PROGRESS、主调查子项和接口计划已记入本批实际完成范围，保留并行模型质量及整体调查未完项。测试指南中的21只读告警／事件／Case ID与已完成fixture一致，并说明新写联调另用新批；部署指南已纠正替换容器后的回退方法，README使用“问答／采用操作”描述三项预留。再次执行`openspec validate manage-alert-incident-operations --strict --no-interactive`通过。

上述通过限定于本批六个管理操作及其发布／交接。未新增数据库迁移或表、未恢复自动消费者、未验证真实模型质量、未修改页面；既有模型失败和未实现功能不因本批通过而核销。汇总见[delivery-summary.json](../../../../docs/operations/evidence/subject-management-20261112-01/delivery-summary.json)。

## 归档操作与封后检查（主执行者记录）

2026-11-13在上述独立结束审计通过后完成1.6，运行`openspec archive manage-alert-incident-operations --yes`，实际归档到本目录，新增`alert-incident-management`主规格的4项要求。仅补齐生成的Purpose并更新当前文档及本目录证据链接，没有改变业务要求或重发服务。`openspec validate --all --strict --no-interactive`为24通过/0失败，`--archived --strict --no-interactive`为23通过/0失败；本批相关文档本地链接全部存在。Git提交、推送和父项目引用未由本批执行。
