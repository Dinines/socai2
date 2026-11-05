# Case 范围变化与基础调查执行记录（2026-11-03）

用户明确要求：更新 Case 范围后，在调查执行表中新增或更新一条“待更新”的基础调查记录。连续修改且未开始执行时更新同一条；开始后冻结，后续范围变化另建一条。本次按该要求实现，取代此前“仅在 Case 上记录待更新状态”的设计建议。

实现分支 `codex/case-baseline-history-20261103`，基线 `39f4033663bf478c7a8e8af2adb8333b45a6eb41`；独立目录 `E:/aisoc/socai2/.local/worktrees/case-baseline-history-20261103`。设计原型仍在 `codex/functional-alignment-20261103`，本次未修改页面。

## 行为与存储

复用 `investigation_runs`，不新建另一张执行主表。需要应用 [迁移 122](../../services/api/migrations/122_case_baseline_pending.sql)，本次尚未执行数据库迁移。

| 条件 | 表中行为 |
| --- | --- |
| 新建带成员的 Case | 新建 baseline / pending_update 记录 |
| 已有 Case 的成员集合变化，尚无待更新记录 | 新建待更新记录，保存变更前成员和当前范围 |
| 待更新期间再次增删成员 | 更新同一 ID，scope_revision 加 1，保留最初 requested_at |
| 仅成员顺序、重复项变化或无实际变动 | 不新增记录、不增加版本 |
| 成员被全部移除 | 保留空范围待更新记录；可查看，不能启动 |
| 修改后又恢复最初集合 | 保留该待更新记录；净新增和净移除可为空，不自动删除 |
| 明确启动 | 同一记录改为 running，填写 started_at，冻结执行范围与来源元数据 |
| 已开始后再次改变成员 | 已开始记录保持原范围，另建/更新下一条待更新记录 |
| 当前同案已有活跃 case_analysis.v1 执行 | 下一条可以待更新，但启动返回 409 |

本次“范围”指 `aisoc_cases.alert_ids` 的成员集合。时间窗口与问题在明确启动时提供，不根据页面状态自动猜测。修改范围不调用模型、不自动调度。数据库 trigger 覆盖现有 v1 创建/加成员、v2 创建/关联和合并目标的成员写入；并未增加新的移除或移动成员 API。

| 字段 | 用途 |
| --- | --- |
| investigation_kind（新增，可空） | 新记录为 baseline；旧记录保留空值 |
| scope_revision（新增，默认 0） | 新待更新记录从 1 开始；每次实际成员变化递增 |
| scope_updated_at（新增，可空） | 最新范围准备时间；开始后固定 |
| status（已有） | pending_update → running → completed / failed，沿用原执行器终态 |
| created_at / requested_at | 请求记录的首次创建时间；读取时 requested_at 映射 created_at |
| started_at（已有，改可空） | 待更新为 NULL，真正开始才填写；不能把创建当成已执行 |
| raw_alert.baseline | schema、initial_member_ids、requested_at、trigger、added_member_ids、removed_member_ids、updated_at |
| raw_alert.scope | 待更新保存完整成员范围，read_member_ids 为空；启动补实际读取成员、start、end |
| raw_alert.intent | 启动者、请求、expected_scope_revision；开始时保存，供重试核对 |

新增/移除是相对本条记录首次准备前范围的净变化，不是逐次操作日志。未补造变更操作者；完整成员操作审计仍属于后续合同。历史 Run 不回填为 baseline，历史 Case 不批量补待更新记录；无 tenant 的历史 Case 跳过。已有 Case 后续发生实际成员变化时才进入新逻辑。

## 竞争控制

1. Case 成员 UPDATE 持有行锁，AFTER trigger 在同一事务内更新/创建待更新 Run；Case 写入失败或回滚时，执行记录一起回滚。
2. 所有当前 `start_analysis` 入口按 **Case → Run** 顺序加锁，读取锁后最新状态。合并多个 Case 按 ID 排序锁定 Case，随后修改成员。
3. 两个部分唯一索引分别限制每个 `(tenant_id, case_id)` 最多一条待更新 baseline、最多一条活跃 baseline（queued/running/unknown/awaiting_human），不靠“先查再插”保证唯一。可以有一条活跃记录和一条下一次待更新记录，但不能同时执行两条基础调查。
4. 启动必须携带 `expected_scope_revision`。加锁后版本不符或成员与准备范围不符均返回 409；不静默使用旧范围。显式选成员时必须等于准备的完整成员集合。
5. 同一 Run、同一操作者和相同启动请求重复提交，读回同次执行，不再次派发；不同参数返回冲突。
6. 启动先提交 running 与冻结数据，再调用执行器第一步和模型/Tool；不是由执行器第一步才改状态。提交失败则不调用执行器。不在模型调用期间持有 Case 锁。另一次成员变更可建立下一条待更新记录；同案已有活跃执行时不能再次启动。未来即使用 queued 交接异步执行，queued 也已占活跃位置并冻结范围。
7. 数据库 BEFORE UPDATE trigger 禁止已开始 baseline 回退 pending，或改其 Case、租户、kind、范围版本、范围更新时间、scope、baseline 来源元数据；运行状态、费用与结果仍可更新。

先发生成员变更时，旧版本启动请求冲突；先发生启动时，之后成员变更创建下一条记录。当前 `case_analysis.v1` 启动路径另检查同案活跃执行；数据库单活跃约束针对 investigation_kind=baseline，不把所有历史/外部执行器都重新标为基础调查。后续新启动入口也必须沿用同一锁协议。没有新增进程崩溃恢复或自动重试执行框架。

用户已明确确认保留手动启动逻辑，页面交专门人员后续讨论和实现。当前没有周期领取、结束后自动接续或后台排队执行模块。A 执行中产生的 B 是“待更新记录”，A 结束不会自动运行 B；需明确调用启动入口。有活跃调查时拒绝本次启动，B 仍为待更新，不写failed、不自动重试。

## 读取与启动接口

Case 调查历史、统一执行索引、告警/事件关联调查读取均增加 kind、scope_revision、scope_updated_at、requested_at 和 baseline 信息。pending 无报告和证据，保持已有“尚未产生结果”的处理。未开始记录用 created_at 排序，已开始记录用 started_at；跨请求列表是实时数据，不保证分页快照不变化。

启动入口：`POST /api/v2/investigation/cases/{case_id}/investigations/{run_id}/start`。

```json
{
  "expected_scope_revision": 2,
  "start": "2026-11-02T00:00:00Z",
  "end": "2026-11-03T00:00:00Z"
}
```

使用现有显式 Bearer、`investigation:run`、`cases:read`、`alerts:read` 权限。不需要另传 operation_key，本条待更新 Run 的 ID 就是启动身份。沿用现有带时区且最长 7 天的窗口限制。现有普通调查接口保留；要消费待更新基础调查，调用这个新入口。旧普通接口不会自动消耗待更新记录。

## 验证结果与未完成项

- 本地相关测试共 78 个不同用例：最新 **53 通过、25 跳过**，另有原分析测试的 16 个子场景通过。
- 第一次为 38 通过、2 失败、6 跳过；两项失败是新测试替身未识别“排除当前 Run”的活跃查询。修正替身后定向及关联回归 20 通过、18 跳过；没有放宽业务活跃检查，未重复运行未变通过项。
- 新增 11 个 API 用例覆盖待更新读取、版本冲突、同 ID 启动/重复提交、参数冲突、成员冲突、空范围、跨 Case、已有活跃执行、权限/必填版本，以及执行器第一步之前已经提交 running、提交失败不调用执行器。最后两项针对用户补充的领取竞争场景定向运行，2 项通过。使用模型/湖/数据库替身，非真实业务执行。
- 新增 7 个 PostgreSQL 事务用例：创建/更新/无变化/回滚，双成员写入，启动先行，修改先行，重复启动，唯一/冻结约束，以及领取为 queued 但尚未执行第一步时新增成员必须另建记录且不能抢占活跃位置。须显式设置本机 `AISOC_BASELINE_TEST_DSN`，测试自行创建并清理独立临时数据库，不使用业务 DATABASE_URL。这 7 项因本机无可用 PostgreSQL 引擎而跳过；另外 18 项为既有 case_depth 数据库测试跳过。
- Python 静态解析通过；SQLglot 仅识别顶层语句，两段 PL/pgSQL 被当作不透明 Command，**不算迁移或触发器语法验证通过**。新增 3 个 Python 文件 Ruff 通过；修改旧文件有 10 项与基线相同的既存诊断，无新增诊断。

交付仍需在可用本机/测试 PostgreSQL 上执行迁移与 7 个事务测试，并验证现有 RLS/权限及完整服务接入；目前不能声称真实数据库并发验收通过。迁移须先于新 API/ORM 上线，仅 `metadata.create_all` 不会安装这些 trigger。当前代码未部署、迁移未应用、无真实业务 Run/模型/Tool 调用，未提交/推送。界面接入及自动调度仍未实施，报告修复继续暂停。

测试原输出与文件指纹见 [本批回执](../operations/case-baseline-history-20261103.json)。旧分析、证据和报告保持原件。
