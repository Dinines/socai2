# 测试数据迁移逐步回执

2026-10-23。用户已授权按[修订计划](testdata-migration-plan-20261023.md)开始迁移；如必须调整后续调查设计，先停下讨论。本批只补测试工具和必要测试接线，保持现有模型职责、提示/输入输出合同、编排及业务算法。使用本地源码和隔离测试资源，不自动发布或提交/推送Git。原调查小修工作区与旧失败保留。

## 步骤记录

1. 执行前保留工具原件及Agents业务源码hash；原工具8项离线测试通过。记录位于`.local/verification/testdata-migration-20261023/before-manifest.json`与`baseline.json`。
2. 输入适配：新增按template-id选择且保留上游稳定场景ID/索引/材料；纯本地source-v1 wire转换直接复用Fusion RawAlert身份逻辑。答案文件不参与转换，原HTTP生成/发送兼容。12项直接检查通过，日志`step01-tests.txt`。
3. Kafka有界发送：显式Kafka transport、本批独立raw topic、预先保存wire/hash、逐条落unknown后发送、ACK仅受理、失败停止和拒覆盖。16项检查通过（包含上述12项，不累加），日志`step02-tests.txt`；此时未联网。
4. 结果观察工具已有12项离线合同和本地历史两例回读；21工件正文hash一致，例1自动关闭、例2调查partial，8条成本调用31788tokens。仅复用本地记录，不算本批新模型/业务执行。详细日志在`observer/`。

5. 真实Fusion：批次`migration-39ff8a2f78`，测试tenant `5594ae90-f57c-50f5-8332-328b3cad1679`。3条新wire经新发送器、真实raw Kafka、原Fusion方法、PG首次快照及fused通过；共6消息、3 Alert/new/无Case、关联Run0/模型0、Fusion DLQ0。全部原始字节/坐标、规范身份、快照与材料核验通过；两个观察消费者无group/offset提交，临时客户端清理无错误。`real-fusion/attempt01/`保留原回执，新增observer真实只读PG结果在`real-fusion/observed.json`，准确显示Alert present/Run missing。
6. 两例自动功能：新测试tenant `344dc4fb-5830-4677-9164-d2181d8fb618`、批次`functional-8099ed7fed`，独立raw/fused/Agents DLQ、消费组、Redis前缀。原Agents从新空topic位置0消费，逐条原分诊/实际升级后提交1→2；raw/fused各2消息，两类DLQ均0。未直接写fused或创建Run，Fusion仍为原处理方法，非其常驻消费循环专项。逐步证据见`functional/attempt01/`。
7. 独立直接测试：结束审阅者执行`pytest -q tools/testdata/tests`，44 passed、39 subtests passed（3条既有依赖弃用告警），无网络/业务/模型。原件6份hash保持，188个Agents业务源码与执行前hash一致；本批未修改调查实现。

## 两例实际结果与判定

| 样本 | 实际分诊/业务结果 | 调查与持久结果 | 已知用量 |
| --- | --- | --- | --- |
| A：有明确审批、账号/主机/命令/时间一致的资产盘点 | BTP 0.95，原0.85阈值自动关闭；判据来自提供的合成授权事实 | Run `b6f56c57-ad17-5d2a-bcd1-022faf83a9b6`，3事件/7工件；自动关闭不需要调查MD | 1回复，2361 tokens |
| B：PowerShell下载/执行表达式，缺授权及后续结果 | NR 0.85，告警未关闭，自动进入原graph/Deep | Run `a883e488-c091-5a0e-af6a-8c7d42d6951b`，16事件/22工件；4轮Deep、8工具；停止后MD8003 UTF-8字节可读，`completion=partial` | 分诊1＋Deep4回复，24131 tokens，其中调查21796 |

共6次出站/6个HTTP200可见回复，26492 tokens，全部unpriced；无本批未响应调用。实际模型工厂仍triage角色512、temperature0、JSON输出，investigation角色2048；6轮/180秒/原20k软预算不变。SDK测试包装器retry0/45秒，最多14次出站，未达上限；真实只读网关配置为retry0、fallbacks[]、45秒，网关内部provider尝试并非本工具逐次观察。

独立核29份工件正文的UTF-8字节/hash及event/Run关联通过。8个工具结果均逐次保留到tool_result工件，6项unavailable、2项error，没有有效取证pivot；报告显示缺源、材料ID和停止原因。Lake为实际查询失败、process_tree缺原字段、enrichment指向原禁用地址，不能写成真实数据检索命中或“没有异常”。本批验证的是已选“仅告警材料/缺源可交接”情形。

**内容检查限定：** A的授权采用与关闭成立；B原分诊理由引用`synthetic`/`CONTROL-B-MISSING-EVIDENCE`推断可能演练，说明测试标记影响推理，不能视为盲测或整条模型理由质量通过。B调查21796超过20000后按原轮后软预算停止，不能宣称严格20000硬限；报告Summary仍为running，而持久Run为completed/调查partial，提议隔离主机仅是原heuristic建议、未执行。保留这些原文/状态，不重投样本或修改prompt、模型职责、输入输出合同、预算算法和编排；后续设计按用户要求另讨论。问题同步原[登记](upstream-issues.md)，不另开任务树。

## 清理、失败与版本边界

- API/Agents临时进程已退出，runner清理无错误；专属SSH隧道已关闭。两枚本批4小时最小权限身份已停用，后续正确RLS上下文只读确认本测试tenant活跃key0、两笔预算均responded。旧tenant/key/unknown/积压/预算未改。新测试数据及topic保留，Redis按原TTL过期。
- 第一次基础设施只读直连被本机沙箱拒绝，未发业务；自动审批超时发生在命令启动前，后按获准方式完成执行。agents_probe离线检查中两次测试假设失败及修正日志保留。清理初次查询预算的第二事务遗漏RLS上下文而得空列表；原记录保留，后通过正确set_context的只读SSH补查确认为2 responded，没有据空列表修业务或重调模型。
- 本轮运行使用本地当前源码（含此前已验但未部署的调查小修）；不能将新tool_result/停止交接实证写成线上v1已更新。未启动生产worker变更、部署、Git提交或push。上述通过只限工具、接线、持久观察与partial交付，不代表调查质量、全部来源或完整change完成。原5/15保持。

## Git忽略检查

按用户追加要求，核132份本轮运行材料/本地快照均被根`/.local/`规则忽略，0份已被Git跟踪。补工具目录`generated/`、`runs/`、`private/`三个可选输出目录规则，并验证不会忽略工具源码、tests或upstream来源清单。凭据、wire/payload/expected批次、模型/工具逐次正文及PG快照保持本地；公开只交付代码、必要测试、固定上游原件和摘要文档。检查记录为`gitignore-check.json`，不将此范围外推为整个仓库的秘密扫描。

未参与实现的handoff_audit结束独审限定ACCEPT、0项本批必须修；结论仅限本批工具/接线/持久观察和partial交付，详见原change audit/execution。选定代码、文档、无凭据回执及审阅结论留存在`.local/versions/testdata-migration-20261023/`，不把其他会话修改算入本批。
