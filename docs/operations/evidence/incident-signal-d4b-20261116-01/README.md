# D4b：事件终结材料到 Case

本批只验证当前 I 终结回执的选择、Case 更新/分配门控、C1 冻结和实际 C3 业务输入构建。没有完整 Case 模型执行、Result、HTTP 请求、Redis 派发或部署。本步复用 [D4a](../ai-unit-continuation-d4-20261116-01/README.md) 两次真实模型调用所保存的完整/部分/空答母本；**本批新增模型生成 0 次**，不重投 Kafka，不重跑原任务。

## 实现与当前验证

- 当前入口为 `case_incident_material.source_sql/freeze`，嵌入 C1 同一 SQL Statement。只选当前输入、task 已终结、attempt 本地结束且完整回执/接收结果/原件实际保存的 I。优先最新可用核心，其次非空部分，最后 none；不跨 Run 拼接、不回落旧 stale 指针。
- `follow_current` 和 `business_view/unchanged` 共用冻结材料。新输入 none 可形成新信号；运行/待重试不提前触发；同输入空失败保留旧核心或部分材料。执行工件、别名及错误不构成业务变化；真实正文、范围、来源业务值变化仍能识别。
- C1 固定源 incident/task/attempt/Run、严格 receipt、input/response/原件身份和摘要及逐单元范围；`selected_refs` 收录准确来源。Case 工件仍通过本案 manifest→baseline-context 读取，源 I 工件属于源 I Run。新字段不改公共 DTO；旧冻结 Context 仍可解析，新 capture 不另设旧版执行路径。
- C3 读取实际保留的分析，角色始终为 prior_analysis；范围保留，后台 receipt/错误/ID/hash 不进入正文。无分析时使用 Case 原告警并给必要缺口。完整事件成员分配不受 I 选入或保留条数缩窄。
- 生命周期/关闭/单告警晚到 A 不直接触发 Case 等既定规则保持；未创建 D5 网络回执或展开 D4c 整链。

[直接最终检查](direct-final.txt) **60 项通过**。此前 direct-01 44、direct-02 59 是本步渐进验证，不累计为额外用例。独立测试去重后 **30 项直接检查通过**（原28；最后13项定向中含11项复验和2项新增），原三分支保存/读取106项、最终完整分支定向55项及当前三candidate复算9项通过，见[独立批次](../test-incident-signal-d4b-20261116-01/result.json)。106与55有重叠，不累加作独立用例数。HTTP 原[33组](http-c1-source-review-01.json)和最终完整分支[11组定向](http-c1-source-review-02.json)均通过，都是同包离线复核、0 HTTP请求。末补前后的源码和保存证据按下节分别保留。

## 唯一 PG 组件执行及读回

显式配置采用 `deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml` 及其包内当前 A/I/Case profiles，容量配置没有改动。私密连接在 `.local/incident-signal-d4b-20261116-01/verification.json`；本机隔离 `v12_upgrade_dev`，仅新测试租户。驱动为 [verify_pg.py](verify_pg.py)，不是生产执行器；以新身份导入已保存依赖，并经过实际 SQL 门控、follow 分配、claim 保存 C1 和 read_context。

| 分支 | 最终回执 | 事件总数 / I选入 / 保留业务单元 / Case成员 | 直接结果 |
| --- | --- | --- | --- |
| 完整核心，随后部分/空失败 | [pg-complete-08](pg-complete-08/result.json) | 4 / 4 / 10 / 4 | 最终版本6项存取复验；原07另保留9项动态门控断言 |
| 部分分析，随后空失败 | [pg-partial-02](pg-partial-02/result.json) | 4 / 3 / 1 / 4 | 10 个断言；Case 由 1 分配至 4，C3只给实际一成员分析 |
| 无可用单元 | [pg-none-01](pg-none-01/result.json) | 4 / 4 / 0 / 4 | 9 个断言；原告警仍可供 Case，I 缺口不伪装结论 |

三分支均验证 running、合法 retry 等待不提供信号；任务终结但未产生新回执不会替换旧可用内容；同信号 unchanged；新增告警使旧 I stale 且不自动分配；已保存 C1 读回保持原来源。complete 续验的 `allocation.json=[]` 表示已经分配过，首次实际 1→4 分配在 [pg-complete-05/allocation.json](pg-complete-05/allocation.json)，同一个 Case，不能把空列表当新分配证据。

**4/3/1 是明确的受控依赖变体。** 它保留 D4a 已保存的原答/received_analysis，按新身份派生三成员 selection（被遗漏成员在当前事件仍存在）；测试请求 body 标明 `unsent D4b dependency; no generation`，原请求 body 单独保存在 `mother_request_body`。该变体没有发给模型，不能声称真实模型在三条输入上生成了它。原 D4a 全四条输入、原答和旧失败文件未修改。本组件只验证门控、来源合同和范围，不据此评价新模型内容质量。

[原三分支只读回执](final-readback-01/result.json)及[最终完整分支只读回执](final-readback-02/result.json)由 [readback.py](readback.py)生成。每个分支保存实际 PG 的 `source-artifacts-readback.json`（所选 I 的五份 input/response/receipt/原件）、`database-readback.json`（17 表）、新增告警后 `frozen-context-after-new-alert.json` 及 `read-only-counts.json`。三组严格来源 span/hash/value 均可复算；读前后行数和摘要一致，运行中 Run/attempt 均为 0。各 C1-only Run（含末补前的完整分支）均真实结束为 **failed / component_capture_only**，ended_at 非空；没有伪造模型成功或 Result。

## 最后归一化修正的证据边界

PG 三分支完成后，最终复核发现 paired A 推荐的 `source_refs` 仍可能带执行工件 ID 进入 I 来源业务摘要。最终实现对这一推荐引用字段做与 I change_view 一致的去除，保留推荐原文；只换工件不变化、推荐业务理由变化仍变化的正反例已加入 60 项直接检查。

[final-normalization-01](final-normalization-01/result.json)通过最终代码离线重放三组**实际 PG 读回 candidate**，没有新数据库或模型请求。partial/none 整份业务摘要与原 C1 相同；complete 只有该引用业务值 hash 按预期改变，其余原单元、正文、范围、receipt、来源身份完全相同，故 C3 业务正文不变。再次替换推荐中的工件 ID 后最终摘要保持一致。该目录是离线派生检查，不能冒称重新捕获/保存了完整分支 C1；原 pg-complete-07/C1 原封不动保留。随后只对受影响 complete 用新身份执行 [pg-complete-08](pg-complete-08/result.json)，当前归一化代码真实 capture→C1保存→read_context→C3业务消息六项通过；partial/none不重跑，running/retry已验分支也不重复。最终完整源行和C1见 [final-readback-02/complete](final-readback-02/complete/database-readback.json)，仍0模型/HTTP，17表读前后相同、无running。

`source-final.json` 是此两行补丁前的快照；最终冻结另见 `source-final-after-normalization.json`。旧独立直接检查的 185 文件未变只适用于其原运行时点，最终独立定向13项、完整分支保存55项与三candidate当前freeze→C1逐值9项均通过；最后185文件运行中未变只适用于最终定向批次。

## 失败和续验边界

所有失败是本组件驱动/夹具未满足当前合同，未放宽任何生产守卫。没有重写旧失败来追认通过。

| 尝试 | 原失败 | 已保存/回滚范围及后续 |
| --- | --- | --- |
| pg-complete-01 | attempt 插入时 task 不在 running | 来源导入事务整体回滚，没有该租户行；修驱动按真实依赖/终结顺序构造 |
| pg-complete-02 | Case 告警关联缺 source_operation_id | 新来源租户已提交；Case 创建事务回滚，后续 03–07 复用这个租户和映射 |
| pg-complete-03 | 事件来源命名空间与告警不一致 | 已存新 Case 1 成员及 running/retry/终结测试；分配事务回滚。后续只补新夹具来源绑定 |
| pg-complete-04 | Case 尚未绑定 source_namespace | 分配事务回滚，前面四类 gate 结论保持；补 Case 夹具字段 |
| pg-complete-05 | C1-only Run 缺 purpose | 1→4 分配已提交，Run 创建事务回滚；实际分配回执保留 |
| pg-complete-06 | C1-only Run 缺 scope_kind | Run 创建事务回滚；未留下运行中的 Run |
| pg-complete-07 | 通过 | 同 Case 续验保存 C1 和实际 C3 输入，结束组件 Run，再加入新测试告警检查 stale/冻结保护 |
| pg-partial-01 | 去掉旧完成候选后未同时清夹具完成时间 | 新来源导入整体回滚；partial-02 是新的隔离身份 |
| pg-complete-08 | 通过 | 仅末补影响的完整分支重新做组件保存/读回，独立新身份；07旧C1保留，未重跑模型或其他分支 |
| pg-partial-02、pg-none-01 | 通过 | 分别独立新租户；组件 Run 均结束，源依赖、C1 和读回保留 |

本步不把受控依赖、C3 消息准备或 HTTP 同包读取称为完整 A/I→Case 任务链通过。D4c、D5、D6 和 change 最终验收/发布仍未完成。
