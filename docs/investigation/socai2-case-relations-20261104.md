# Case 事件关联与成员移动

2026-11-04，OpenSpec `complete-socai2-investigation-chain` 3.4。主目录分支 `codex/case-baseline-history-20261103`。实现只在新 `socai2` 链，沿用默认关闭的 Case API；页面和生产消费者未切换。

## 本次核对发现及表变更

原来 `case_alerts`、`case_incidents`、范围版本、pending Run 和冻结记录已经存在，但没有事件关联/移动的写入事务。Case 也缺少固定的来源命名空间：如果每次从当前成员推导，成员清空后就无法保留原边界。

增量迁移 [124](../../services/api/migrations/124_socai2_case_source_binding.sql) 给 `cases` 增加 `source_namespace text NULL`，本批从29表458列变为**29表459列**。这是唯一新增列；不增枚举、JSON公共合同或新表。原123迁移保持字节不变，不重新生成历史迁移。新 Case 首次写入成员时固定绑定，数据库触发器阻止后续改值或清空。空白不合法。

已有 Case 仅在当前成员、历次 Run 成员、显式事件链接及历史成员活动记录共同证明一个非空命名空间时回填。历史混合、无可验证来源的 Case 保持 NULL，读取仍可用，范围写入返回 `case_source_scope_unverified`，不把未知当通配符，不自动重新归属。本批迁移只应用于21的独立合成库 `socai2_schema_review_20261103_a1`，回填后有3个原合成 Case 未确定；不是业务数据质量统计。

**语义边界：** 告警/事件的 `source_namespace` 是数据身份空间；Fusion 新 writer 当前固定为 `fusion.v1`。对象/引用中的 `connector:...` 是接入链路，不是原厂，也不等于来源环境。因此本批保证认证租户和明确身份命名空间一致，**不能声称已经验证不同原始环境相同**。收到的数据没有独立来源环境标识时按输入限制记录，遵循用户要求不猜测、不追查或要求上游补数。未来若输入提供该标识，须独立定义环境边界，不能直接把 connector_id 当成环境。

## 完整流程

### 关联或从事件创建

1. 认证及 `cases:write`，服务核同租户真实用户；请求不能自带租户/操作者。
2. 创建使用原确定性 Case ID 与请求指纹；追加先锁 Case。已成功的相同操作返回原回执，事件后来增员不会改变重发结果。
3. 在单条 SQL 快照内读取所选事件、**完整成员**及各自命名空间。缺事件、空事件、不可用成员、跨租户或来源不符整体失败；不截掉成员后部分成功。
4. 直接选择的告警与事件成员取并集，再与已有 Case 成员取并集。最终最多200条，超出整体拒绝。添加不会从其他 Case 抢走告警。
5. 复用 `replace_members` 更新当前成员/范围/pending：连续更新尚未领取的同一条 pending；已领取的 running/unknown 不改，另建或更新下一 pending。不执行模型或自动开始下一轮。
6. 对每个显式事件保存独立 `case_incidents`，活动回执保存当次实际事件成员目录。仅链接新增而成员不变时只刷新 Case 业务时间及行版本，不增加范围版本，不创建基础调查。
7. 成员、链接、pending、活动整体提交。Case 详情新增独立事件目录，告警/事件页原关联读取可直接读这些关系。

事件成员是本次关联 SQL 快照中的成员，后来事件增员不会隐式修改 Case；用户用**新的操作键**再关联时才重新取成员。为避免与 Fusion 的 Alert→Incident 锁形成环，不在该快照后持有事件行锁再写 Alert 外键；Case 及其运行记录的变更仍受 Case 行锁串行化。

### 移动

1. 显式指定不同的目标 Case、所选告警、源/目标各自预期范围版本。
2. 两个 Case 始终按 UUID 顺序加行锁；重发先核原回执，随后检查两端版本、可编辑状态及固定来源绑定。
3. 所选告警必须全部是源 Case 当前成员；目标已有成员去重。源减少、目标并集、两边 pending 和活动在同一事务内保存。任一端失败全部回滚。
4. 源范围必变；目标只有实际新增成员才变版本及 pending。若目标本来已有全部所选告警，目标不制造额外调查。
5. 原显式事件链接保留在原 Case，不随成员移动转移或凭空生成。`run_members`、C1工件、历史 Result/引用/当前判断均不重写；现有读取会显示判断与当前范围的差异。
6. 源全部移空仍保留固定命名空间及空范围 pending；原手动启动规则拒绝空范围。已有活跃 Run 继续按冻结范围执行，下一 pending 仍需手动启动。已解决 Case 不隐式重开，沿用拒绝编辑政策。

## 字段及读取对照

| 项 | 语义/类型 | 保存位置或派生 | 实际出口 |
| --- | --- | --- | --- |
| R01 | Case固定身份命名空间 text/null | 新 `cases.source_namespace` | Case详情 `case.source_namespace` |
| R02 | 认证租户 uuid | 所有表 `tenant_id`，服务端提供 | 不允许请求注入 |
| R03 | 操作者 uuid/快照 | created/added/linked_by，activities.actor | Case成员、链接目录及活动 |
| R04 | 幂等操作 uuid | 确定性Case ID、操作指纹及活动回执 | 同键返回原 Mutation/Association/MoveReceipt |
| R05 | 直接告警 uuid[] | `case_alerts` | `members` |
| R06 | 显式事件 uuid[] | `case_incidents`，每Case/事件唯一 | `linked_incidents[].incident_id` |
| R07 | 链接时间 timestamptz | `case_incidents.linked_at` | 同名目录字段 |
| R08 | 链接人 uuid | `case_incidents.linked_by` | 同名目录字段 |
| R09 | 链接原操作 uuid | `case_incidents.source_operation_id` | 同名目录字段 |
| R10 | 事件标题 text及身份空间 | 读取当前 `incidents` | 同名目录字段；不冒充冻结事件标题 |
| R11 | 当次完整事件成员 uuid[] | case_associated活动的Case目标回执 `incident_member_snapshot` | 持久审计，不用当前事件成员替代重发结果 |
| R12 | 新增告警 uuid[] | 并集差集，随操作回执保存 | `added_alert_ids` |
| R13 | 新增显式链接 uuid[] | 未有关联差集，随回执保存 | `linked_incident_ids`，独立于R12 |
| R14 | 成员加入方式 enum | `case_alerts.membership_source` manual/incident_link/move | 成员目录；重复成员保原加入信息 |
| R15 | 范围版本 bigint | `cases.scope_revision` | MutationReceipt及Case详情 |
| R16 | 并发预期版本 int | 请求值与锁内现值比较 | 不符409，无部分写入 |
| R17 | 待更新基础记录 uuid/null | 新建或复用 `runs.pending_update` | pending_run_id、Case/history |
| R18 | 当前是否有成员变化 bool | 操作差集 | `changed`；链接新增不等于成员变化 |
| R19 | 显式源/目标Case uuid | 两个事务主体及回执 | MoveReceipt.source/target.case_id |
| R20 | 实际移出 uuid[] | 原源范围与选择一致 | `moved_alert_ids` |
| R21 | 目标实际新增 uuid[] | 选择减目标原成员 | `added_to_target_alert_ids` |
| R22 | 两端操作审计 | activities+activity_targets，原/新member值 | 明确主体/目标活动，不混入无关Case |
| R23 | 原轮冻结范围和材料 | 原 `run_members`+C1工件 | 旧Run、冻结材料读取保持原身份 |
| R24 | 链接总数/省略 | 独立总数，目录最多200 | linked_incident_count/linked_incidents_truncated |
| R25 | 业务时间、行版本 | 真正成员或链接变化更新 `cases` | business_updated_at/row_version；重复操作不刷新 |

内部成员子操作使用原操作键派生的 UUID，区分 associated-members、move-source、move-target；外层活动保存原请求键及完整双端回执，不是新执行任务。

## 接口

| 路径（前缀 `/api/v1/socai2/cases`） | 合同 |
| --- | --- |
| POST 空后缀 | 原CaseCreate增加可选incident_ids；alert_ids/incident_ids至少一种非空，响应增加两个新增ID列表 |
| POST `/{case_id}/associations` | operation_key、expected_scope_revision、alert_ids/incident_ids；只添加 |
| POST `/{case_id}/members/move` | operation_key、target_case_id、两端expected_scope_revision、alert_ids |
| GET `/{case_id}` | 原详情增加固定来源及显式事件目录/总数/截断 |

原 PUT members仍表示整体替换，新增来源校验同样覆盖该入口。旧的告警创建请求指纹保留，旧成功回执缺两个新增列表时按空列表兼容；不重执行旧操作。OpenAPI见[当前合同](../design/socai2-case-api-v1.openapi.json)。

## 例子

1. 事件E1有A、B，用户另勾A：创建Case后只有A、B两条成员，E1有一条显式链接；一个pending、范围版本1。A记录直接手动加入，B记录incident_link。
2. Case已有A、B且一轮正在执行，再显式关联E1(A、B)：新增链接数1、新增告警数0、范围版本不变，不创建下一轮；旧C1仍显示冻结时未显式链接E1。E1后来增加C，同请求重发不纳入C，新操作关联才纳入C。
3. Case X运行中冻结A、B，Case Y有C。将A移到Y：X当前B，原Run仍A、B，X新pending为B；Y当前A、C，复用Y未执行pending。下一次移B时只更新X/Y各自pending，不覆盖原Run。
4. X只有A，Y已有A。移动后X为空、范围递增，Y范围及pending不变。X仍绑定原来源，不能添加其他命名空间的告警。若目标已解决、跨租户、不匹配来源或会超200，整个移动失败，X不丢成员。

## 验证与剩余边界

本批使用既有独立PG、受限临时角色及合成数据，HTTP身份替身；不调用真实模型、湖或厂商。回执保存首次夹具/断言失败与定向复核，不把最新通过冒称全部首过。[本批汇总](../operations/socai2-case-relations-20261104.json)列出每项测试和源码指纹。

未改页面、未部署API、未切换业务库/Kafka/生产消费者，不迁移旧public告警。H人工任务、外部数据来源/响应实时状态、旧消费者迁移及真实语义质量仍在后续任务。Q只预留接口；旧r13暂停、5.3未完。
