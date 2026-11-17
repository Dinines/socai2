# query-case-story 独立结束审计

审计日期：2026-11-13。审计者为未参与本项实现的独立代理；实际分支为 `V1.1`。本审计只修改本文件，保留工作树中并行调查模型改动；没有部署、提交、数据库写入或模型调用。

## 当前结论

**本 change 的实现、直接验收、交接及发布后限定复核通过，可以按 OpenSpec 流程归档。未发现未解决的交付阻断项。** 本结论仅覆盖 E65 普通故事查询及其 HTTP 接线、本机/21 指定 API 与 Swagger 发布，不扩大到 AI 对话、自动更新、产品页面或主调查模型质量。归档操作及其 CLI 校验由实施者继续完成；Git 提交、推送和父项目引用更新尚未执行，不在本审计中追认完成。

## 代码与范围

审阅了本 change 的 proposal、design、tasks、spec，以及 `case_story.py`、`case_story_contracts.py`、独立 story 路由、port/adapter/dependencies/main 接线及复用的只读事务、分页函数、源 DTO、表约束。

- 来源仅为同租户同 Case 的当前成员告警、baseline Run 和已完成 TaskRevision。告警对象搜索限定该告警的最新材料及 host/user 类型；Result 同时限定租户、Case、source_run_id 和 baseline 类型，未扩大到其他 Case 或 AI 对话。
- 告警使用 event_time；终态 Run 使用 ended_at，running/unknown 使用 started_at，pending_update 和缺失时间保持 null。排序为时间倒序、NULLS LAST、稳定类型/UUID 键倒序；复用 seek 分支覆盖同时间及空时间续页。
- q 按明确业务字段做不区分大小写的字面匹配，转义反斜线、`%`、`_`；各来源在数据库先筛选再分页。severity 仅约束告警；total 为全部命中条目数。游标绑定租户、Case 和规范化筛选，不把游标当授权；每次请求仍独立校验 Case 归属。
- 只有 completed/failed/cancelled 的 Run 读取其已存结果，活跃 Run 不展示提前结论。原结果的 conclusion/validation/delivery 等字段保持；没有把程序接受、执行完成或结果存在改写为模型质量通过。
- 人工完成修订按不可变版本读取，旧完成版本在任务重开后保留，并用 current_revision_id 明确标记是否当前；正文、范围、完成人及来源引用均复用原 TaskRevisionView。
- 新路由不含 SQL、内部实现或模型调用；经用例端口及适配器使用现有 Case 读取配置/身份。核心不反向导入对外 HTTP 包。查询处于 `REPEATABLE READ, READ ONLY` 事务，无迁移或源数据更新路径。

## 独立核验与证据限制

1. 执行 `openspec validate query-case-story --strict --no-interactive`：通过。
2. 执行现有 `services/api/tests/test_socai2_http_boundary.py`：**3 passed**。使用 `PYTHONDONTWRITEBYTECODE=1` 和 `-p no:cacheprovider`；未扩展为全仓回归。
3. 将[采用发布基底 OpenAPI](../../../../docs/operations/evidence/case-result-adoption-release-20261113-01/local-candidate/openapi.json)与[本批候选 OpenAPI](../../../../docs/operations/evidence/case-story-20261113-01/local-http/candidate-openapi.json)独立逐项比较：原 **64 个业务操作**保持；包括辅助入口在内为 69→70，仅新增 story GET。原 **130 个运行时 Schema**完全保持，仅增加 StoryEntry、StoryPage。告警 DTO 和原接口字段、类型、枚举、空值及关联合同未变。
4. 首次审阅独立核对[冻结源码清单](../../../../docs/operations/evidence/case-story-20261113-01/local-source-manifest.json)的 8 个文件 SHA-256，均与当时工作树文件一致。后续文档检查只为 `StoryPage.items` 补充 description；独立比较冻结候选与工作树，确认仅有此说明变化，类型、默认值及行为保持。原清单保留，最终发布已另存包含此说明的[最终源码清单](../../../../docs/operations/evidence/case-story-20261113-01/local-source-manifest-final.json)，未改写原验收版本。
5. 复核[30 次真实 TCP 回执](../../../../docs/operations/evidence/case-story-20261113-01/local-http/verify-http.json)并离线重做其中关键断言：6 条混合来源完整读取；同时间连续分页不重不漏；未知时间置后；主机/账号、字面特殊字符、调查结论及人工正文搜索；等级筛选保留调查/人工上下文；旧修订非当前；运行中无结果；筛选/跨 Case 游标及非法参数 422、缺 Case 404、另一 Case 来源隔离均符合设计。源记录详情回查的响应与故事 DTO 保持一致。
6. 首轮 30 请求后的 SQL 比较因脚本选择 ORM 对象而失败，不能据其 `sql-before/after.json` 宣称原行不变；[失败说明](../../../../docs/operations/evidence/case-story-20261113-01/local-http/initial-verification-failure.md)及原件保留。补验改取真实表行，在**一次额外故事 GET**前后保存 [before](../../../../docs/operations/evidence/case-story-20261113-01/local-http/snapshot-verify-sql-before.json)／[after](../../../../docs/operations/evidence/case-story-20261113-01/local-http/snapshot-verify-sql-after.json)：独立比较 **11 张表原行完全一致**；[补验回执](../../../../docs/operations/evidence/case-story-20261113-01/local-http/snapshot-verification.json)同时核对主要源值。本结论不把这次补验改写为首轮快照比较成功。

本机样本来自独立合成 Case/Run/Result 和人工任务流程，数据库为 `v12_upgrade_dev`；本审计核验现有回执，没有新建样本或重派执行。合成调查结果只验证查询，0 模型调用不代表真实模型质量通过；未新增生产业务写入。本审计未进行复杂故障、压力、恢复或多模型矩阵。

## 交接与发布复核

- 已复核[故事调用指南](../../../../docs/integration/case-story-http.md)、功能清单 F20/F22-08、HTTP 实施计划及根交接：severity 仅筛告警；q 限定标题、说明、最新主机/账号及明确的调查/人工结果字段；真实时间/空时间/游标分页、原始身份回查、旧人工完成版本与当前任务的区别、活跃 Run 不提前给结论均与实现一致。AI 对话仍全部暂缓，自动 C6 及模型质量未被核销。
- 已检查 docs14 候选包 `/tmp/socai2-story-docs14-preview` 及生成器 `build.py`、`catalog.py`、`publish.py`：[文档核验回执](../../../../docs/operations/evidence/case-story-20261113-01/docs-check.json)记录 65 操作、141 个文档 Schema、571 个 JSON 响应示例、3 个 CSV 示例、26 个请求示例和 13 个新字段说明；独立复核计数、StoryEntry/StoryPage 全部说明及 E65 示例顺序，OpenAPI SHA-256 与回执相同。运行时 132 个 Schema 与文档补充后的 141 个 Schema 口径分开，不混报。
- 候选阶段复核发现并由实施者修复两处旧口径：生成目录 F22-08 的“故事未接”，以及候选 HTTP README 仅介绍 docs13/64 操作。重建后已确认旧句不再出现在生成页，当时 README 明确 docs14/65 为候选、正式基底仍为 64；`guide.html` 可直接打开 `/handoff/sources/case-story-http.html`。候选阶段未冒称已发布；原快照脚本错误与补验的 1 次 GET/11 表核对分别记录。

## 发布后限定复核

本阶段只读核对已完成的发布回执、保存的 HTTP 响应和本机文件指纹，没有重复模型、数据库或业务请求。

- [本机运行回执](../../../../docs/operations/evidence/case-story-20261113-01/local-runtime.json)为 `case-story-20261113-r1-local`、18024、`v12_upgrade_dev`，正式 PID 11901；本轮 18026 预览 PID 8796 已停止。[21 运行回执](../../../../docs/operations/evidence/case-story-20261113-01/21-runtime.json)为 `case-story-20261113-r1`、18024、`aisoc`，入口为 `investigation_http.main:app`，镜像 `sha256:ae6e5181cd23d5e095e3dd545280b1297e6a471cb1e94828bf956cc36586418c`。独立比对最终清单、工作树、本机冻结运行目录和两端回执的 8 文件指纹，全部一致；21 回执记录除指定 API/Swagger 外 36 个容器的身份、镜像和启动时间保持。
- [本机正式读取](../../../../docs/operations/evidence/case-story-20261113-01/local-release-http/verification.json)与[21 正式读取](../../../../docs/operations/evidence/case-story-20261113-01/21-release-http/verification.json)各 7 次 GET。对保存的 `responses.json` 独立重做断言：状态均为 200、运行版本和 65 个业务操作正确、故事分别为 6/4 条、源告警/Run/结果/人工修订响应与条目一致、前后 Case 响应保持。21 使用已有合成 Case；0 新生产业务写入、0 模型调用。此发布读取不替代先前完整筛选/分页直验，也不冒称发布后重做了 11 表 SQL 快照。
- [最终 Swagger 聚合回执](../../../../docs/operations/evidence/case-story-20261113-01/swagger-release.json)与 `deploy/api-docs/deployment-receipt.json` 一致；两端 `*-swagger-final.json` 各 10 个入口为 200，所有对应内容指纹相同。最终挂载为 `20261113-docs14-final`。独立核对仓库交接目录、`/tmp/socai2-story-docs14-final2` 与本机实际挂载，**31 个文件完全一致**，记录的在线静态指纹与本机文件一致。
- docs14 最终 OpenAPI SHA-256 为 `ac4b581ec42679daed7224659a5682b914d3a09f9e468cc60f7e407b2eb84f60`；[最终文档检查](../../../../docs/operations/evidence/case-story-20261113-01/docs-check-final.json)仍为 65 操作、63 已实现、2 问答暂缓、141 文档 Schema、668 固定字段位置、35 动态组、571 JSON 响应示例、3 CSV、26 请求示例。AI 对话、模型质量及自动消费者的既有未通过/未开放边界保持。
- 发布后发现 HTTP README 接入表残留旧采用版本/64 操作，根交接和 PROGRESS 也有旧当前计数。实施者已修正，独立复核不再保留这些现时旧句。最终静态包相对首包仅 `README.md`/`guide.html` 改变，OpenAPI 不变；首包 `swagger-release-initial.json`、原两端回执均保留，最终两端静态读回另存，没有因此重启或重复验证业务 API。[validation.md](validation.md)、当前进展及交接已对应实际发布状态。

据以上结果，本项直接验收、交接、独立审计与指定发布读回已齐备，可完成任务 1.5 的归档步骤。本结论不要求扩大测试范围，也不核销其他 change 或主调查未完成项。

## 归档与封后校验

2026-11-13，独立发布后审计通过后由实施者完成归档，任务5/5按实际交付勾选；新主规格case-story-query同步，CLI自动生成的Purpose占位已替换为本次只读故事职责。当前导航和归档内相对链接已校正。封后strict：全部32通过、归档31通过，0失败，见本批openspec-all.txt/openspec-archived.txt。主调查仍31/41，Git提交/推送及父项目同步未执行。
