# 独立结束审计

## 初轮实现审查（2026-11-13）

审计者未参与实现，仅只读审查代码、规格、候选和证据并运行离线定向检查；没有发起业务 HTTP、数据库、模型或部署请求，仅维护本审计文件。

**阶段结论：暂不能宣称附件引用存取通过。** 原 59 合同及离线边界通过，但首轮本机真实登记暴露活动目标列错误，必须修正并完成新的直接验收。此状态由后续修后审计更新，不抹去首轮失败。

- 独立执行 `test_socai2_case_attachments.py` 和 `test_socai2_http_boundary.py` 共 6 项通过；OpenSpec strict 校验通过。候选原 59 操作路径定义与 Schema 保持，仅增加 3 个附件引用操作和 3 个 Schema。当前源码、冻结候选及 manifest 的 8 文件摘要相符；修正后需重新冻结。
- 新用例按认证租户/Case 保存引用，Case 行锁内核对操作回执及同案 `file_id` 重复；查询使用只读一致事务。DTO 拒绝空白/控制字符、非法大小/哈希以及客户端作者/下载 URL 字段；返回声明文件元数据和 `managed_by_backend`，没有文件读取、上传、下载或模型调用。
- 写入只使用既有 artifacts 的 attachment 类型及明确 schema/blob_ref；不自动进入 Run、证据目录、案件判断或人工任务结果。旧工件读取对于外部内容仍返回 `external_content_not_loaded`，不伪造文件正文。业务后端文件 ID 是本批合成引用，不能证明真实文件已上传、存在或可下载。
- **已定位阻断：** 初版 `case_attachments.py` 调用 `store.event` 时传入 `artifact_id` 目标，而 `ActivityTargets` 没有该列，真实 POST 触发 CompileError。首轮 HTTP 未形成登记成功证据；必须保留原意图/失败，并只读核查事务回滚。主执行者拟仅保存 Case 活动目标，附件 ID 和完整返回放已有 `operation_receipt.outcome`，不增加迁移；应同步设计、目标数量及 SQL 核对，再使用新批次完成直接存取。

本审计不覆盖业务后端上传/下载实现、附件编辑删除、采用/调度和并行模型工作。发布及归档仍待修后直接 HTTP/SQL、交接文档和两端实际读回完成。

## 修后本机直接验收复核（2026-11-13）

**实现与本机直接存取限定通过，初轮存储阻断已解除。** 可以继续 docs12 交接与发布准备；文档尚未完成本审计，不能据此宣称两端已发布或可以归档。未重复业务请求。

- 修后 `store.event` 仅保存既有 Case 目标，附件 ID 和完整登记值在该目标的 `operation_receipt.outcome`；规格设计已同步，没有新增列或迁移。独立重跑两份定向测试共 6 项通过，OpenSpec strict 通过。修后源码、冻结目录和新 manifest 的 8 文件摘要一致。
- 首轮[回滚核查](../../../../docs/operations/evidence/case-attachments-20261113-01/candidate/rollback-check.json)记录 0 附件、0 登记活动和 Case 原值保持。首轮失败说明保留 CompileError，并明确旧核验器解析非 JSON 错误时失败、未捕获原始 HTTP 错误正文；不把该失败追认为成功或伪造完整响应。第二次 candidate-02 仅启动过早的 OpenAPI GET 失败，没有业务请求；新 candidate-03 使用独立批次。
- [candidate-03](../../../../docs/operations/evidence/case-attachments-20261113-01/candidate-03/verification.json)的 25 次真实 HTTP 覆盖新登记两条、同键重放、改意图/重复文件 409、非法大小/空白 422、分页、单项、跨案 404、其他 Case 空目录及活动。原 59 操作和 Schema 仍逐项相同；新服务共 62 操作。
- 从[SQL 原行](../../../../docs/operations/evidence/case-attachments-20261113-01/candidate-03/sql-after.json)独立重新组装返回，两个附件的全部 11 个输出字段与 HTTP 相同。Case 仅业务时间/版本变化且版本增加 2；2 个 pending Run、1 任务/修订和 0 结果保持。2 活动/2 Case 目标的登记回执与两个附件返回完全相同；活动读取可以定位附件 ID 和原元数据。
- artifacts 仅绑定该 Case，run/step/alert/incident/content_json/content_text 均为空；blob_ref 是指定前缀加原 file_id。原始大小/哈希保留声明，retained 大小/哈希为 null、reason 为 `business_backend_reference_only`；第二项零字节和缺哈希正确保留。以上只证明合成引用登记与读取，**不证明业务后端真实上传、文件内容核验或下载成功**。

后续需审 docs12 的 F24-02/03 状态和业务后端上传后登记/按 file_id 下载说明；两端发布后再核实际版本、8 文件、配置、HTTP/SQL 及 Swagger。已结案追加分支当前由代码审查覆盖，未扩大声明已做该分支真实 TCP 验收。

## docs12 发布前复核（2026-11-13）

**文档与本机验收限定通过，无本批发布阻断项，可继续已授权的统一两端发布。** 本结论不表示已发布，也不替代两端实际读回与发布后审计；归档条件仍未全部满足。本阶段仅读取候选与仓库文件，并离线校验，没有业务请求或部署操作。

- 复核 `/private/tmp/socai2-attachments-docs12` 及 build/catalog/publish：E01–E59 顺序保持，E60 登记、E61 分页目录、E62 单项信息归入调查分类。共 62 操作、59 已实现/3 预留、135 Schema；125 功能按告警 22/事件 15/调查 88 分类。固定输出位置为原 576 加登记 11、目录封套 4/列表项 11、单项 11，共 613，CSV 104 列保持。
- 独立将新接口参数、请求体及 3 个新 DTO 去除说明/示例后，与 candidate-03 实际 OpenAPI 比对，结构和约束一致。docs11 全部旧 Schema 逐项保持。独立校验全部 532 响应示例（529 JSON、3 CSV）符合对应 Schema，与[文档回执](../../../../docs/operations/evidence/case-attachments-20261113-01/docs-check.json)相符。最终候选 OpenAPI SHA256 为 `1a05526f7daf24b11fcb09ff2b97d8a48cf25cac21c8dd9cee2eeb60a693e735`。
- F24-02/03 明确“本服务已实现”的范围是目录、单项和关联登记，上传/存储/下载由业务后端负责；没有把本次合成 file_id 验收扩写成文件端完整流程通过。指南说明先保存取得 file_id、再登记、读取目录/单项、业务后端按 file_id 下载及处理失效；附件关联 id 与文件 ID 明确区分。
- 元数据字段保留业务后端声明来源；`sha256=null` 表示未提供，`size_bytes=0` 允许，`availability=managed_by_backend` 不证明文件存在或可下载。说明了同键重放、改意图/同案重复文件 409、跨案/不存在 404、非法参数 422、分页和登记活动，以及不改变任务/Run/判断、不自动分析、不提供修改删除的范围。活动回执使用现有 Case 目标，未再描述不存在的附件目标列。

统一发布后需核两端实际基底与 8 文件、版本/配置、HTTP/SQL 及 docs12 内容；根当前部署入口、实施计划和交接状态由主执行者按真实发布结果原位收口。首轮失败、回滚及 candidate-02 的零业务失败仍保留，不被新文档追认为成功。

## 两端发布后结束审计（2026-11-13）

**最终限定通过，无本 change 剩余阻断项；可勾选 1.4、1.5 并归档。** 本结论取代上文各阶段的待验收/待发布状态，首轮失败和修复记录仍保留。审计者未参与实现，发布后仅读取既有证据、本地源码/冻结目录和文档并离线比对，没有新发业务 HTTP、数据库、模型或部署请求。Git 提交、双分支推送和父项目引用以主执行者后续实际回执为准，不在此提前确认。

1. **实际发布与限定源码一致。** [本机回执](../../../../docs/operations/evidence/case-attachments-20261113-01/local-api-release.json)记录正式 18024 为 `case-attachments-20261113-r1-local`、PID 80726、`v12_upgrade_dev`；[21 发布](../../../../docs/operations/evidence/case-attachments-20261113-01/21-api-release.json)和[运行读回](../../../../docs/operations/evidence/case-attachments-20261113-01/21-runtime.json)一致，为 `case-attachments-20261113-r1`、`aisoc`、镜像 `sha256:d0bb509983c04ba1e322f374f0d31dc23c8cd443a5193671097a8f0ff4fd8566`。8 文件当前源码、冻结目录、manifest、发布 overlay 和 21 实际摘要一致；根 local/aisoc21 profile 与本批 profile 一致。独立比较前版评论和本版本机冻结目录的全部 Python/JSON 源码，仅这 8 文件改变，未带入并行模型实现。运行核对脚本及回执支持其他 36 容器身份/镜像/启动时间保持。
2. **本机正式读取与候选保持。** [8 次正式 GET](../../../../docs/operations/evidence/case-attachments-20261113-01/local-http/verification.json)均成功，未重复登记。[正式 SQL 原行](../../../../docs/operations/evidence/case-attachments-20261113-01/local-http/sql-after.json)与 candidate-03 全部相同。两端实际 OpenAPI 仍保留原 59 操作路径定义与 Schema，仅增加本批 3 操作。
3. **21 登记、读取和 SQL 相符。** [26 次 HTTP](../../../../docs/operations/evidence/case-attachments-20261113-01/21-http/verification.json)使用本批明确合成 Case，主案 `c1c9c7bb-2da6-5d17-aa7f-e83761063c66`。从[SQL 原行](../../../../docs/operations/evidence/case-attachments-20261113-01/21-http/sql-after.json)独立重新组装两附件的全部 11 字段，与 HTTP 完全相同；重放/冲突/重复文件及非法输入、分页/单项/跨案等结果与合同一致。2 活动/2 Case 目标的 outcome 与附件返回一致；Case 仅版本增加 2 及业务时间变化，2 个 pending Run、1 项 not_started 任务及修订、0 结果保持。附件仅绑定 Case，文件正文和 run/step/alert/incident 字段为空，retention 如实保留后端声明而不伪称本服务保存字节。
4. **Swagger 内容一致。** 两端[docs12 回执](../../../../docs/operations/evidence/case-attachments-20261113-01/swagger-release.json)的 9 入口均 200、摘要相同；8 个 handoff 载荷与仓库、冻结挂载和已审候选逐字节相同。版本/统计为 62 操作、59 已实现/3 预留、135 Schema、613 固定输出字段位置；OpenAPI 摘要保持 `1a05526f7daf24b11fcb09ff2b97d8a48cf25cac21c8dd9cee2eeb60a693e735`。本机 aarch64、21 x86_64 与显式配置相符，当前部署回执和批次回执相同。
5. **交接与失败边界明确。** README/HANDOFF/PROGRESS、功能清单、实施计划、表职责、联调及部署说明已更新本批状态。三份共享文档的临时提交候选相对 HEAD 仅纳入本轮 HTTP 差异，未混入当前并行模型改写；此检查不代表已提交。首轮 CompileError/原错误正文未完整捕获、回滚核查、候选过早 GET 失败和启动端口暂占均在验收记录中保留，不把首次失败改成成功。正式两端直接存取通过后没有复写旧批次记录。

本次完成范围是 F24-02/03 中调查服务负责的附件关联登记、分页目录和单项元数据。**合成 file_id 不代表真实文件平台上传、下载、文件存在或内容/哈希验证通过**；这些职责仍由业务后端承接。已结案追加只做代码审查，未宣称该分支真实 TCP 验收；采用/Q02、任务调度、自动消费及模型质量仍按各自未完状态维护。表结构保持 28 表/450 列，没有迁移、新表或文件字节存储。汇总见[交付回执](../../../../docs/operations/evidence/case-attachments-20261113-01/delivery-summary.json)。

## 归档收口记录（主执行者）

已归档至2026-11-13-link-case-attachments，补齐主规格Purpose并修正相对链接；全量strict30/30、归档任务检查通过，新归档链接存在。此为文档收口，不新增业务验收；Git及父项目结果以固定skill实际回执为准。
