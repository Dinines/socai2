# 独立结束审计

## 实现与候选 HTTP 复核（2026-11-13）

审计者未参与实现。本轮只读审查核心、DTO、外部路由、装配、发布清单和已有证据，并运行离线定向检查；未发起业务 HTTP、数据库或模型请求，未部署，未修改实现。

**当前结论：实现与本机直接验收限定通过，未发现阻断项；尚不能据此归档。** docs11、两端实际发布与发布后审计仍须完成。本结论不覆盖结果采用、任务调度、附件及并行模型修改。

- `case_comments.py` 先检查真实作者，再锁定同租户 Case；在锁内查询同 Case、同动作、同操作键的活动回执。同作者同正文重试返回原评论，意图改变返回 409。新增评论、Case 版本及业务时间、活动和两个目标在同一事务中保存；重放不再次写入。
- 正文校验拒绝空白、超过 20000 字符和客户端作者字段，保存和返回原文。作者与时间来自服务端；普通评论不成为人工任务结果、采用事实或模型输入。实现未因 Case 已关闭而拒绝追加，也不改变关闭状态。
- GET 按认证租户和明确 Case 读取，以 `created_at,id` 升序、`limit/offset` 分页；计数及条目处于同一次只读 repeatable-read 事务。不存在 Case、非法页参数和未知查询参数有明确错误。跨请求分页不承诺冻结快照。
- 外部路由只经 DTO、port 和 adapter 调用核心；未引入 SQL/Session 或内部调查 HTTP。发布 profile 仅覆盖 8 个文件；当前源码、冻结本机候选和 `local-source-manifest.json` 的 8 项摘要一致，未包含并行模型源码。
- 独立执行 `test_socai2_case_comments.py` 与 `test_socai2_http_boundary.py`：6 项通过；`openspec validate add-case-comments --strict --no-interactive` 通过。原 57 操作路径定义和原 Schema 均保持；仅增加 comments 路径的 GET/POST 与 3 个 Schema。
- 只读复核[候选回执](../../../../docs/operations/evidence/case-comments-20261113-01/candidate/verification.json)与原始 responses/fixture：21 次 TCP 请求包含两次新评论、相同请求重放、冲突/空白拒绝、分页、其他 Case 空集合、不存在 Case 及活动读取。独立比对原文和返回、两页结果、Case 版本仅增加 2，任务和待启动 Run 保持。此时回执仍明确要求另行 SQL 核验，不能以 HTTP 成功替代数据库保存证据。

随后复核[独立 SQL 快照](../../../../docs/operations/evidence/case-comments-20261113-01/candidate/sql-after.json)及只读采集代码：实际库为 `v12_upgrade_dev`。以快照原行独立重新投影，评论、Case、Run 与 HTTP 返回完全相同；两条评论均仅绑定目标 Case，两个活动及四个目标存在。两个待启动 Run、一项未开始任务及其一条修订、零结果与本批预期一致。此核查未新发数据库请求。已结案追加分支由实现审查覆盖，本机本批未另走该分支，不声明其已有直接 TCP 验收。

归档前还需完成当前交接文档和 Swagger 内容核对，以及限定 8 文件的两端实际发布、配置和读回复核；已完成业务写入无需为了本审计重复执行。

## docs11 发布前复核（2026-11-13）

**发布前限定通过，无本批阻断项。** 审查最终候选 `/private/tmp/socai2-comments-docs11`、生成器/目录、功能清单和[文档校验回执](../../../../docs/operations/evidence/case-comments-20261113-01/docs-check.json)。本结论允许继续本 change 已授权的统一发布，不表示两端已切换成功，也不代替发布后读回。

- E01–E57 编号顺序保持，E58 是 POST 评论、E59 是 GET 评论，同归调查分类。共 59 操作、56 已实现/3 预留、132 Schema、125 功能（告警 22/事件 15/调查 88）；固定输出字段位置为原 554 加 POST 9、GET 封套 4 和 items 9，共 576，CSV 104 列保持。
- 将新接口的参数、请求体及 3 个新 Schema 排除说明/示例后与实际候选 OpenAPI 比对，结构和约束一致。独立校验全部 508 个响应示例（505 JSON、3 CSV）符合对应 Schema。最终 OpenAPI SHA256 为 `00f19ca51200f7a69cd10f16ae13045a29e17c23c47898b0902e303bfd930979`。
- 已明确原文、服务端作者/时间、当前认证以登录邮箱保存名称快照、幂等重放/冲突、分页顺序/范围/非跨请求冻结快照，以及 404/422 等实际错误。普通评论不影响案件判断、成员、任务或 Run；已结案可追加的说明是行为合同，不伪称已有该分支 TCP 证据。
- F24-01 仅普通评论读写已实现；F24-02 仍仅已知工件读取，通用附件目录/下载未完成；F24-03 上传仍未实现。候选没有把评论提交成功写成附件保存、人工任务完成或调查结果采用。
- 生成器的旧“A/I 评论只读、没有 Case 写入”说明已定向修正为 Case 使用 E58/E59；不涉及业务源码。根当前部署入口仍按实际 docs10 状态保留，主执行者需在两端成功后原位更新相关计数、功能范围及后续计划，避免将已交付评论继续列为待实施。

待两端实际服务的版本/8 文件摘要/配置、HTTP 和 SQL 保存读回、docs11 字节及入口状态完成后，追加发布后审计再判断归档；当前不核销该待办。

## 两端发布后结束审计（2026-11-13）

**最终限定通过，无本 change 剩余阻断项；可据此勾选 1.4、1.5 并归档。** 此结论取代上文阶段性“待发布/不可归档”状态。审计仍仅读取现有证据及本地文件并做离线比对，没有新发业务 HTTP、数据库、模型或部署请求，也未修改实现。归档、Git 提交/推送及父项目同步由主执行者按实际授权收口，不以此审计冒称已完成。

1. **运行和源码范围相符。** [本机发布](../../../../docs/operations/evidence/case-comments-20261113-01/local-api-release.json)记录正式 18024 为 `case-comments-20261113-r1-local`、PID 69626、`v12_upgrade_dev`；[21 发布](../../../../docs/operations/evidence/case-comments-20261113-01/21-api-release.json)与[运行读回](../../../../docs/operations/evidence/case-comments-20261113-01/21-runtime.json)一致，为 `case-comments-20261113-r1`、`aisoc`、镜像 `sha256:4577b3f11125378c31e419961e68f2a5f462e7b30bc77981c4fe9ee5be3bd318`。8 文件的当前源、冻结目录、manifest、发布 overlay 和 21 实际摘要全部相同；根 local/aisoc21 profile 与本批 profile 相同。独立比较前版与本版本机冻结源码的全部 Python/JSON 文件，仅这 8 文件改变，没有带入并行模型修改。其他 36 容器的身份、镜像和启动时间保持，由实际核对脚本及回执支持。
2. **本机正式服务读取保持。** [6 次 GET](../../../../docs/operations/evidence/case-comments-20261113-01/local-http/verification.json)均成功；正式服务 OpenAPI 保持原 57 路径定义/Schema，新增评论 GET/POST。评论、Case、待启动 Run 与候选相同，[正式 SQL 原行](../../../../docs/operations/evidence/case-comments-20261113-01/local-http/sql-after.json)和候选 SQL 全部相同。本机发布后没有重复评论写入。
3. **21 正常提交、保存和读取相符。** [22 次 HTTP](../../../../docs/operations/evidence/case-comments-20261113-01/21-http/verification.json)仅为本批两份明确标记的合成 Case、一项任务及两条评论；新建评论、重放、409 冲突、422 空白、分页、其他 Case 空集合、错误 Case 404 和活动回查均有原始响应。[SQL 快照](../../../../docs/operations/evidence/case-comments-20261113-01/21-http/sql-after.json)独立重新投影后与 HTTP 评论/Case/Run 完全相同：2 条评论只绑定主 Case、2 活动/4 目标、2 个 pending Run、1 任务/修订、0 结果；评论使主 Case 版本仅增加 2，其他业务字段、任务及 Run 保持。没有启动调查、采用结果或模型。
4. **失败记录未追认。** 21 首次 `docker cp` 因只读 rootfs 失败，保留[失败说明](../../../../docs/operations/evidence/case-comments-20261113-01/21-http/sql-read-attempt.json)和零字节初次输出；当时 SQL 未运行。随后通过标准输入执行同一只读采集脚本才得到有效 SQL 证据，未重派业务写入或放宽服务配置。不能把首次失败当成 SQL 通过。
5. **Swagger 和交接状态一致。** 两端[Swagger 回执](../../../../docs/operations/evidence/case-comments-20261113-01/swagger-release.json)的 9 入口均 200，摘要完全相同；其中 8 个 handoff 载荷与仓库、冻结挂载及已审候选字节一致。docs11 仍为 59 操作、132 Schema、576 固定输出字段位置，OpenAPI 摘要保持 `00f19ca51200f7a69cd10f16ae13045a29e17c23c47898b0902e303bfd930979`；本机 `aarch64`、21 `x86_64` 分别符合 profile。根 README/HANDOFF/PROGRESS、功能清单、后续计划、部署说明及表职责已同步；发现的功能清单顶部旧 57/54 计数已改为 59/56。comments 纳入已有写路径表使数量为 25，仍为 28 表/450 列，没有迁移或新增表。

本次通过仅覆盖 F24-01 普通评论提交/分页和相应发布交接。附件上传/目录/下载闭环仍未交付；结果采用及 Q02、任务调度由其他模块推进；自动消费和模型质量未据此核销。已结案评论分支仍仅由实现审查覆盖，未扩大声称真实分支验收。完整交付范围见[汇总回执](../../../../docs/operations/evidence/case-comments-20261113-01/delivery-summary.json)。

## 归档收口记录（主执行者）

归档已执行，主规格Purpose和相对链接已补齐。首次归档后全量strict检查因Purpose少于50字符产生1项失败，已补足用途说明；最终全量29/29、归档28/28通过，新归档文档链接存在。此为文档校验修正，不代表新增业务测试。Git及父项目结果另按固定skill实际回执确认。
