# C03-02C-02：授权事实澄清后的新代表样例复验

2026-10-21。执行前 freeze 候选，尚未执行本批 freeze/provision、HTTP、模型、broker 或业务写入。正式前由 root 审定并经独立审计；本稿不授予调用权限。承接 C03-02C-01 v4 小批，旧 C03-02/02B 两次质量失败与各自已执行 case01 不改写、不重调；两批各三条、共六条未执行输入继续保留。新四条输入与独立判据已经另行审查，本候选只移除 draft 状态/父尚未满足的过时标记，不改变实质。

## 固定版本与输入

- 父/本批候选镜像固定 `sha256:9ba6be09b682b451f6ce3b590c1e736e00b5baf1dcd13c00874781261ca8a3b3`，triage.system v4，26 Compose/23源码层；Agents184 Py、四服务769 Py及非Py lock。0app/prompt/schema/模型路由修改，0build/重启/DDL，worker/graph/审批/记忆写回仍OFF。
- 输入将存为 `docs/operations/c03-triage-authorization-quality-inputs.json`，batch `c03-triage-authorization-quality-20261021`；本 ignored freeze 候选 SHA `d2a34e447af666b1b51780fa62371f3b1f650b65f0de585cfc16e10838ba23f4`。A三条/B一条，新UUID/source/rule/account/host，与旧两次已执行输入不同；不放 expected/评分信息。
- 独立 `rubric.json` 候选 SHA `d10b8f95299c8d4a11812e4c10653e048f51d62df6499f0ee1c9df83456425f3`。只供审计者评分，不挂执行容器、模型或source目录，不由operator读取。
- 四例分别覆盖直接威胁行为与授权未知、当次完整范围授权及跨日offset、转移谓词无法核查且维护信息缺端点/时区/范围、event早于授权窗而created在窗内。分类与短理由分别核；任何自报日期/数值/offset关系必须正确，不凭历史背景或职位虚构本次批准/拒绝。

以上是代表性范围说明，不替代分离的独立评分标准，不把本卡或rubric正文额外送入模型。

## 父封包与保护基线

正式 freeze 必须验证 C03-02C-01 `acceptance.json` bounded_accepted、固定镜像/v4/26&23，以及predeploy、运行、closeout三份独立audit accepted；本批 `before.json` 使用新的真实只读observation，须等于父 `after.json`，不得复制旧观测冒充新基线。保存项目PG备份、实际env/容器、私密policy/reader映射的摘要、两类额外表/QA、主/raw/六预算组及两旧quality/DLQ metadata；不消费消息核验。

已知父7预约/140000固定预留单位，3旧unknown，实际freeze必须一致。A已有4条预约（2 unknown），B已有3条（1 unknown）。不退款、删除、自动过期或重发unknown，不清A旧积压；两旧质量批raw/回执/失败事实、C-01观测修订及其原件保持。

当前policy A6 calls/120000单位/max_unsettled3，B4/80000/2，window86400秒。本新卡明确授权使用未用A2+B1，再只增加A一call/20000容量：目标A7/140000/3，B保持4/80000/2。因此可容A3+B1四次串行新调用；本批最多4新预约/80000预留单位不是新增4份policy容量，也不是实际usage/费用。任一新unknown仍占槽，立即停止下一例。

## 数量与运行边界

| 对象 | 上限与合同 |
| --- | --- |
| 模型 | ≤4次实际SDK发送，每case≤1；保持0retry/整次45秒/输出512。没有自动loop或用旧case重试追分 |
| 数据 | ≤4 Alert/4 Run/4预算、12事件/28工件/4成本/4shadow；原QA策略不改，≤4新增pending QA，无reviewer/评分，QA实际incident/canonical/Run关系分别记录，不把原QA关联缺陷称已修 |
| broker | ≤2新单分区topic（quality/DLQ）、1新group，显式初始化commit0；≤12发送尝试(raw4/Fusion fused4/quality4，失败也计)；≤12交付边界，包含常驻Fusion raw4、原fused捕获4、qualityworker4。raw slot/metadata不冒称直接物理yield观测 |
| 观测 | 显式真实网络HTTP≤240，Mock另≤4；同一共享sequence准确计数。显式hostSQL/helper与独立审计分别记，不冒称全内部SQL统计；不额外读broker记录 |
| 凭据 | 仅3枚新≤3小时操作key，结束停用且逐枚实际API401；原10reader/key映射保持，不新增tenant或reader |
| 运行 | 同固定baked Agents候选做fresh临时worker，实际BusinessContext/LiveTriageWriter/LiveShadowPolicy及五reader从现有配置读取，不为结果关闭策略。常驻worker及真实响应保持OFF；其他35容器/18卷/134迁移不改 |

新对象：`socai2.c03.triage-authorization-quality.20261021`、其`.dlq`及group `socai2-c03-triage-authorization-quality-20261021`。两个旧quality组分别保留原02和02B end/commit1、DLQ end0，metadata-only快照独立保存并在finish复核。主fused end随真实Fusion新增，但主group commit保持；不reset任何旧group。

## 五算子与逐例门

只用新 `prepare/run/acceptance/snapshot/finish_triage_authorization_quality_c03.py`。quality专用算子间只引用本批prepare/runner；不导入旧quality模块来取常量。metadata脚本作为字面量数据复制，不能触发旧batch counter hooks。本批OFFSET_CODE从旧shared字面量本地去assign，旧shared代码不改；新group空topic的显式初始化提交仍是本卡唯一初始化写。新prepare的计数hooks只属新E，其他批次不得把它作为常量库导入。

1. `prepare freeze`：父封包门、真实只读保护基线/PG备份、三个仅private staged身份与policy候选；无PG key写/模型/输入发布。
2. `snapshot`：同prepare后的独占检查点采额外表、QA、Fusion metrics(1次共享HTTP)、raw/main/旧02+02B quality/DLQ metadata；用固定候选、networknone、UID10001、只读单operator文件做SHA/AST可读探针，无app/env/private挂载。
3. 独立source/输入/基线审查后 `prepare provision/topics/authorize`：一次受限key事务、只增加A容量、创建本批2topic/1group的空commit0；再经独立pre-exec审计绑定整个baseline和operator SHA后才允许业务phase。
4. 单case `run ingress`：单次真实HTTP→raw/Fusion→PG/fused捕获，绑定Alert/incident/tenant/source/ack。发送不明只回查，不重复POST/publish。
5. 单case `run preflight`：fresh进程、实际五reader及v4完整safe-call/egress/SDK Mock；无Invocation/PG claim，CostTracker persistFalse、cache fixture OFF。默认JSON literal≤8000字符、规范UTF-8≤16000字节，完整post-egress request可核。Mock只验证输入/传输，不是模型质量。
6. 独立preflight audit通过后 `run invoke`：单次复制原fused信封到新quality topic，实际live worker认领/预算/SDK/原策略/持久化；只保存可见request body和短content/usage/finishreason，不保存headers、rawkey、隐藏推理或完整provider body。真实阶段不以Mock预占预算。
7. `run verify`：只读PG/API/offset及Run/Alert/成本/预算工件关系；独立审计者按冻结rubric写该case gate，绑定本批输入SHA、completion及rawanswer SHA。只有该gate accepted且gate_eligible才可进下一case，不能自动循环四例。
8. 任unknown、长度/schema、来源漂移、分类或理由不合格，停止后三例。原schema不合格允许生产完成其自身处理后独立质量拒绝，不把已收到回复伪造为unknown。按实际passed或stopped依次finish inspect→独立结束audit→revoke/3个401→closeoutaudit→seal；保留全部原失败/预约/offset，不重调或删现场。

旧3A/02B的版本、基础设施和cached-unit证据只复用其未变合同，不新增全仓回归。当前仅准备五算子与freeze候选，尚无本批真实长度、reader结果、模型质量或运行变更证据；C03-02C-01四个构造Mock不替代本批真实五reader预检。四例全过也仅是本批限定质量，常驻准入仍需后续独立卡，整个迁移不因本卡完成。
