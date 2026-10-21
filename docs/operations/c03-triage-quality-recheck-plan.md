# C03-02B：新四例分诊理由复验

2026-10-21。**状态：执行前冻结候选，本批尚无真实模型或业务写；正式执行前须独立审计及明确执行授权。** 只承接C03-02 stopped后的新一批质量复验，不覆盖原输入/评分/失败/Run。当前仅在本地生成输入、分离评分标准及核字符串/时间关系，没有远端PG/Kafka/HTTP、模型、部署或app改动。

原C03-02真实执行仅case01、一次模型/1998 tokens；其needs_review未达原true_positive判据，后三例未执行。原场景的备份catalog删除/覆盖有破坏事实，但缺少在用业务环境及勒索等直接威胁事实，needs_review存在合理解释，不能为追旧标签修改prompt。原短理由借无关组织记忆断言明确授权的局限仍须保留；原质量失败不能改写为通过。新批改用新业务材料，不重调旧例、不编辑既有组织背景。

## 固定输入与独立判据

- [输入JSON](c03-triage-quality-recheck-inputs.json)：batch `c03-triage-quality-recheck-20261021`，SHA256 `fb3d14dbb424384a00d83e343f895f60d56b9f7f2e6634fd2fca013c3ab65e51`。四条新UUID、source/source_event_ids/rule/host/user；A三条、B一条。`risk_score=null`、`severity=medium`、中性title、`raw_event={}`；无expected/评分字段。description分别297/312/296/318个ASCII字符，均≤380，未含test/controlled/fixture字眼。
- `rubric.json`：SHA256 `8dc84bbc257656386631f0eff18bb80558cfbf81dc5bf8bf6b3cd914dd7e3a44`。独立文件、只供评分，**不挂至模型/执行容器，不放入prompt或输入附件**；正式运行前另经未参与编写者审查冻结，模型运行者不得据评分要求动态改写材料。
- case01给出同PID加密运行中账务服务正在使用的发票、原先成功读回随后失败、该PID写付款换解密密钥说明的可观测链；不以无批准/无job证明恶意。case02给出完全匹配的当次账户/源host/目标/action授权及跨日期offset；case03缺end/TZ/scope且没有直接威胁事实；case04发生时间早于窗口而created处于窗口内，均用新材料。 case01/03/04的来源时间与描述中日期均为2026-10-20；case02保留2026-10-21T00:22+08:00等于前日16:22Z的跨日例。case04明确为20日02:05Z事件、02:44Z创建、02:30–03:00Z授权窗口。
- 判分类与短理由分别核。接受明确且可独立核真的event与指定授权窗关系，不强制输出具体换算数值；只说authorized/有审批而没有event与该窗的关系仍不通过。任何自报数值、日期、offset或时差必须正确。B例须明确活动在所供窗口之前、created虽在窗内也不能授权该event，窗外不能推出从未授权或恶意。原p01错误“窗内”关系仍会被拒；本批只验证固定样例关系正确，不外推通用时区算力。不要求特定原文字串、编号或写作模板，严格评分详情只在rubric，勿复制入模型侧卡。

## 同一生产版本与实际长度门

保持Agents `sha256:039f2cb09684c29e170b8907572196ff5559c9d7991837fc431a12d113350985`、triage.system **v3**、184运行Py及非Py lock，25 Compose/22源码层；0源码/prompt/模型角色变更、0build/服务重启/DDL。worker、graph、审批提案、记忆写回和真实响应仍OFF。新的模型输入不能引用02评分或把旧无关组织材料当作本次授权。

当前旧case01的完整literal 7808字符只剩192字符余量，不据本地description长度直接声称安全。每例真实Fusion信封进入模型前，用相同v3、原五reader/egress处理及actual SDK MockTransport预检**完整messages**：账本literal≤8000字符，canonical UTF-8请求≤16000字节，输出512、retry0/45秒；保留完整消息hash和body hash。Mock无Invocation/claim/Run/成本/QA新写。任何限额/来源漂移即停，不能截旧材料、放大上限、换prompt或重用旧预检。无需全仓回归，复用同版C03-01/C02/SDK预算证据，仅核新operator的batch/输入绑定。

## 预算与数据保护

执行前从C03-02 **最终seal**重新只读核实际DB/私密policy/reader/旧14表与额外Case/source-links/QA/六预算组/主group None及topic边界，保存项目备份与全部父字节。已知应保留旧预算5行及C03-02新增1行；旧三unknown不退款、删除、自动过期或重调，原1998 tokens与其Run/成本/事件/工件不变。实际DB若不符合已知值先停，不强行按草案写policy。

当前02 policy A5 calls/100000单位/max_unsettled3、B4/80000/2中，原未用A2+B1须由本新卡明确重新授权，并核实际DB后才计入本批4次调用上限，不是退款或自动重分配；为本批A3+B1只额外增加A **1call/20000单位**：目标A6/120000/3，B仍4/80000/2，窗口86400秒。每次固定预约20000，本批最多4新预约/80000单位，不等于新增policy容量80000，也不等于实际tokens/费用。保留全部父预约、父policy hash和调整理由；串行一例一gate，未知请求仍占槽，不因额度不足清理旧现场。

| 对象 | 本批上限 |
| --- | --- |
| 模型 | ≤4次实际SDK发送、每例≤1；无自动retry/fallback再次发送，失败/未知/格式/理由未过立即停后续 |
| 数据 | ≤4新Alert/4Run/4预算、12事件/28工件/4成本/4shadow；原QA策略不变，≤4新A/B pending QA，无reviewer/评分；实际QA incident/canonical/Run关系分别报，Q2不宣称修复 |
| Kafka | ≤2新单分区topic（quality/DLQ）和1独立group，显式初始commit0；≤12发送attempt（raw4/Fusion fused4/quality4）及≤12交付上界。捕获/worker实际交付与常驻Fusion raw预留slot分开，不把slots当直接物理证据 |
| 读观测 | operator显式HTTP≤240，含每次metrics/API/metadata HTTP；Mock另≤4。显式host SQL计数，内部service SQL不冒称全计；独立审计另列，不额外读broker数据 |
| 凭据/运行 | ≤3枚新3小时操作key，最终撤销并逐枚401；十reader/映射保持。0新tenant/reader、0共享服务变更、0外部通知/真实动作/embedding |

raw/Fusion正常新增会增加主fused end，但主group仍不消费/提交/reset；历史边界应是旧83+02实际新增，再加本批实际输入，不预先声称旧四例都已发送。新topic/group/数据/失败现场保留，不清库/卷。控制PG新增表限额只针对命名的保护投影，不外推全PG；Fusion incident/membership为Redis，不虚构PG incident新增。

## 正式冻结后才可按例执行

1. 形成新的公开执行卡/安全输入及private评分冻结、operators/输入/plan/hash门、原版本与父closeout绑定，先过独立pre-exec审计。使用全新E/P/G/AUDIT路径和新broker对象；不能把02旧state/before/accepted路径改batch后原地复用。文件/目录owner与UID10001可读权限在Docker前核，旧启动前失败不删除。
2. 单例ingress独占started：真实API→raw/Fusion→PG/API及原fused capture；绑定新canonical/source/tenant/输入hash与坐标，遇非预期记录立即停，不扩大扫描。202或ack不明只回查，0重复POST/publish。
3. 单例preflight：实际完整源材料、nonce块/采用文本、actual SDK body与边界通过；确认PG/QA零增量。preflight Mock不是模型质量结果。
4. 单例invoke：复制该原fused信封一次至独立quality topic，fresh实际live worker继承默认business-context/reader/governor/shadow，真实PG claim/budget与SDK请求；保留短content/usage/finish reason和可见messages，不收隐藏推理/完整provider body/secret header。
5. 单例只读verify及**独立质量gate**：核原schema/分类/每个材料性理由、时间换算/授权范围及PG/API/成本/预算关联。gate绑定整批输入SHA及该case completion原文件SHA；只有其accepted且gate_eligible才可启动下一例。不得自动loop四例。
6. 任一质量或基础设施未过，停止后续、保留本批实际调用/预约/offset，不换答案或重复同例改善成绩。四例全过才满足本批限定质量；否则按实际stopped封存。最终运行审计、撤3key/401、closeout独审、seal分开，完整HTTP槽含收尾各阶段预留；正常/失败都不启resident。

这些步骤尚未执行。此候选仅在本地静态核description/枚举/新身份及两例时间关系；不能当作预执行审计、真实长度证明或调用授权。C03-03及整体迁移仍未完成；旧C03-02失败与理由局限不因本批新输入通过而消失。
