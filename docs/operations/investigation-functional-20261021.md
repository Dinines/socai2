# 调查模块本地功能实测与逐步案例（2026-10-21）

本批已经实际调用21模型网关及只读工具；**Router选域与结果交付可运行，默认四节点交付了带兜底的报告，Deep完成了真实查询循环但未产出最终叙述。不能把三条路径整体写成全部通过。** 仅修两处使查询固定失败的接口合同，不部署、不启常驻、不重调旧Run。原理见[调查逐调用说明](../architecture/investigation.md)及[预处理/模型/工具专篇](../architecture/investigation-preprocessing-tools.md)。

## 1. 实测范围与来源

本地运行当前Agents源码，连接21 LiteLLM、API、enrichment、UEBA。实际模型均由网关别名路由到43的 `aisoc-test-investigation`；未调用外部厂商动作。每条路径串行开始，原Router内部仍按默认并行执行选中的领域。SDK本地观察进程设retry=0/45秒；默认四节点completion保留2048，Router各角色保留原上限；Deep保留6轮/120秒，并设置本批20k token停止边界。

| 输入 | 来源与可证明的范围 | 处理 |
| --- | --- | --- |
| 20截图Golden pipeline | 20仅有这1条告警，已关联调查Run；不是已证实的真实入侵 | 只读盘点/历史对照，未重调 |
| Router第一例 | 新的公开事件派生**实验输入**，明确注明synthetic/no observed local compromise | 首次分诊提前关闭；结果保留 |
| Router第二例 | 对微软公开事件叙述本身作分析，账号/应用为脱敏别名，Case/Run/tenant和告警包装是本地测试元数据 | 新输入、新Run；用于观察专业领域分支，不重写第一例结果 |
| 默认四节点 | 新写的Office→编码PowerShell合成告警，主机/账号/父子进程均为测试字段 | 不含可执行载荷，不重放截图告警 |
| Deep | 基于公开密码喷洒叙述建立新隔离账号/主机；没有植入正向查询行 | 查询的是21测试租户，不能称查到了公开事件的原始日志 |

公开事实来源是[Microsoft Threat Intelligence，2024-01-25](https://www.microsoft.com/en-us/security/blog/2024/01/25/midnight-blizzard-guidance-for-responders-on-nation-state-attack/)：其描述了无MFA的旧测试账号遭密码喷洒及随后OAuth应用权限滥用。没有取得该事件原始日志、精确时间或实际账号/IP；本批不据此虚构原始遥测。

本地组件测试在导入前移除数据库DSN。Case/Run ID仅作本地关联，不创建线上Case/Run、关闭线上告警或验证新的Kafka自动触发。成本/ledger不写业务PG；默认人工原tracker的日志仍显示 `persisted=true`，它只表示原tracker开关，缺DSN时没有成本落库，不能据日志字样称已持久。已有自动主链和报告持久证据仍见[原B4回执](integrity-autonomy-r01.md)，不由本批代验。只读API可能沿原逻辑记录查询审计，不声称所有基础设施均零写入。

## 2. 验证结果总表

| 路径 | 模型尝试 / 收到回复 | 已知usage | 实际结果 | 尚未证明 |
| --- | --- | --- | --- | --- |
| Router实验输入 | 1 / 1 | 1,361 tokens | FP 0.95，原阈值分支提前关闭，模板Markdown保存 | 未进入专业分支；不作真实检测准确率样例 |
| Router公开叙述 | 3 / 3 | 2,917 tokens | NR→Identity/Cloud→TP 0.95→模板Markdown | 无工具取证、无完整响应计划；Phishing/Insider未作真实模型实测 |
| 默认四Agent | 4 / 3 | 6,177 tokens | Recon、Responder、Report有回复；Forensic连接错误后走原兜底；Markdown保存 | 四次模型全部成功、完整取证或质量通过 |
| Deep组件 | 6 / 6 | 21,540 tokens | 7次真实工具执行；2个不同成功工具名；预算触发停止 | 无最终narrative，非完整报告/完成调查 |
| 合计 | 14 / 13 | **31,995 tokens** | 全部原输出保留 | Forensic未收到回复，其实际提供方执行/用量未知，不能计为0或当成功 |

本批共78项直接测试通过，其中已有Router12项、Deep8项直接测试通过，模型/部分服务是替身；它们证明开关、接线、循环和返回序列，不能当真实来源/模型证据。另两处最小合同修正的直接验证见第6节。没有做压力、恢复、退出顺序或多模型比较矩阵。

## 3. Router：每一步做了什么

第二例本地Run：`ad4f47e3-7f81-4008-9c68-22af7e6ef3be`。

| 步骤 / 目的 | 实际输入 | 实际输出 / 交接 | 模型与查询 |
| --- | --- | --- | --- |
| 接入投影 | 摘要＋顶层username/mfa_status/cloud_provider/permissions等；原始日志未提供 | 原样创建本地state；未做ContextBundle预取 | 无模型/数据库读取 |
| 初次分诊：判断能否直接关闭 | 分诊system规则＋公开事件叙述、缺原始时间/IOC的边界 | `needs_review`，0.95；缺少实例证据，继续调查 | `aisoc-triage`，1,415 tokens |
| 代码选域 | 摘要、分诊理由、findings及raw顶层字段名 | `identity, cloud` | 规则关键词/字段存在性，0模型 |
| Identity：身份专业分析 | 身份system提示＋用户名别名、MFA disabled、OAuth权限及Additional fields | TP 0.95，`attack_type=privilege_escalation`，5个指标 | `aisoc-investigation`，725 tokens；无查询工具 |
| Cloud：云专业分析 | 云system提示＋Azure、服务/权限/应用别名及Additional fields | TP 0.95，`risk_category=iam_anomaly`，4个指标 | 同别名，777 tokens；无查询工具 |
| Join：汇合 | 两份领域输出 | 选出的整体结论TP 0.95，保两份findings；confidence_basis主要来自Identity | 确定性代码 |
| Responder：dry-run摘要 | 汇合结论/分数/待办动作 | `actions_pending=0`，未映射MITRE；没有生成完整隔离/根除/恢复计划 | 0模型、0动作执行 |
| 报告 | state/findings/confidence_basis | 模板Markdown（Summary、Triage Rationale、Findings） | 0报告模型 |

Identity真实可见回复的关键字段：

```json
{"verdict":"true_positive","confidence":0.95,"attack_type":"privilege_escalation","indicators":["legacy_nonproduction_account","MFA_disabled","password_spray_compromise","OAuth_permission_grant","privilege_escalation_to_app"]}
```

这些指标来自输入叙述与模型分析，不是工具查得的新证据。比如模型称“disabling of MFA”，而输入仅说“MFA未开启”，是否发生了禁用动作并未证明。领域schema没有NR选项，这次领域TP不等于解决了首分诊提出的缺证。**Router能把专业判断汇合并展示，但没有替你完成取证。**

第一例实验输入Run `cdd00f7c-d20a-4133-aed1-f8b6152b0cca` 只收到一次分诊回复：模型识别其明确的实验/合成说明，判FP 0.95；原策略因此提前结束。没有人为改判或强制让它继续。

## 4. 默认人工四Agent：输入如何交接

本地Run：`0834699d-b58e-409a-8166-d82efd7031ec`。

合成输入核心是 `WIN-LAB-MANUAL-20261021` 上 `winword.exe → powershell.exe -EncodedCommand <payload-not-provided>`，用户 `lab-manual-20261021`，T1059.001仅作标签。未提供载荷、实际事件时间、目标地址或成功执行证据。

| 步骤 | 模型看见的材料与目的 | 本次真实返回 / 下一步采用 |
| --- | --- | --- |
| 固定预处理/Bundle | 提取主机、用户、文本候选IOC；查询可用上下文 | 将两个exe名误提为domain；bulk增强200但sources为空；用户UEBA200未匹配新实体，设备UEBA500；图/记忆不可用原因进入bundle |
| Recon | system侦查提示＋原摘要/告警＋bundle/KB状态，抽取IOC、ATT&CK、攻击面 | 1,072 tokens。模型称未提取具体IOC、无归因，但确定性提取结果仍将两个exe补入IOC列表；固定逐项增强各HTTP400 |
| Forensic | system取证提示＋原材料、Recon、增强结果及上下文；形成时间线/工件/范围假设 | 调用尝试后247ms出现OpenAIConnectionError，**没有模型回复**。原兜底：timeline/artefacts空、confidence0.1、root cause未知、人工复核；这些不是模型答案 |
| Responder | system响应提示＋此前调查结构与取证兜底；提出处置建议 | 1,517 tokens。建议隔离主机、采内存、审计账号等，`dry_run=true`；没有执行这些动作 |
| ReportWriter | system报告规则＋原告警、Recon/Forensic/Responder、增强/知识/审计材料 | 3,588 tokens，生成Markdown；明确合成告警、未确认入侵、取证不可用、处置未执行 |
| 结束 | 原groundedness/ledger出口 | 本地原status为completed，报告可读，但这是**带Forensic兜底的完成**；不等于四模型全部成功或质量验收通过 |

预处理的限制要分别归因：本地测试租户不在所选旧身份reader映射中，所以图未发HTTP；本批未注入KB reader、未配置DB记忆读取。它们是**本地测试配置/覆盖边界**，不是本批证明迁移漏了图或知识库源码。UEBA设备查询500已查到失效连接，见第7节。

最终Markdown实际说明“no confirmed compromise”“Automated forensic analysis was unavailable”，并把两个exe作为domain判为分类错误。报告正文仍把无显式时区的处理审计时间写成UTC，且默认完成标签掩盖节点兜底；这些质量/状态表达问题保留，不追认通过、不重调模型。

## 5. Deep：模型怎样决定用工具

本地Run：`9e0b1ae9-e0d1-4b9e-aeea-29d85c3f851e`。原策略匹配 `identity-account-takeover`，模型实际获得原告警投影、策略和16个工具schema。没有客户SIEM/EDR/身份/云审计连接，MCP registry未配置专用服务身份，采用原工具集；未另造这些后端。

| 模型轮次 | 目的及实际工具请求 | 实际执行返回 | 下一轮采用 / 结果 |
| --- | --- | --- | --- |
| 1（3,023 tokens） | `authentication_events(user_name=lab-deep-20261021,hours=90)` | `available=false`，LakeQueryError | 第2轮承认lookup failed，改查后续活动 |
| 2（3,223 tokens） | `oauth_grants(user_name=...)`、`mailbox_activity(user_name=...)` | 两者原占位 `not_ingested` | 第3轮将其说成visibility gaps |
| 3（3,490 tokens） | `entity_timeline(user_name=...,hours=90)`、`process_activity(hostname=LAB-IDENTITY-DEEP-20261021,hours=90)` | 均 `available=true,row_count=0` | 第4轮引用返回，继续查主机 |
| 4（3,780 tokens） | `entity_timeline(hostname=...,hours=90)` | 成功0行 | 第5轮转查持久化 |
| 5（3,929 tokens） | `persistence_mechanisms(hostname=...)` | 原占位 `not_ingested` | 第6轮承认缺源 |
| 6（4,095 tokens） | `network_connections(hostname=...,hours=90)` | **未执行**：回复后用量越界，循环先停止 | 没有第8次工具执行/网络查询/下一轮 |

7个实际工具调用的call_id均与下一轮真实模型请求中的 `ToolMessage.tool_call_id` 一致；模型收到的内容与原4000字符renderer对真实返回的渲染逐字一致。一次回复可请求多个工具，所以“6轮”不等于“6个步骤/6次查询”。最后一个工具请求没有执行，不能只看tool_calls就记查询成功。

本次 `narrative=""`、`truncated=true`、`stop_reason="token budget exhausted (21540 of 20000)"`。Deep findings Markdown只保存深度/缺源/停止信息，不是完整Case报告。`reached_depth=true`仅因两个不同成功工具名达到min_pivots=2；三次成功查询全为0行，不是两类新实证。

模型第4轮把空结果称为“genuine evidence of absence”，受原提示词空结果规则影响。但API的available=true仅证明SQL成功，不证明该测试实体的来源已充分入湖，不能推成账号安全/没有攻击。另hours=90是**模型本次参数**，不是90天或固定事件窗口；没有原始event_time时模型选出的回看范围没有告警时间锚点。这些均记录后续取舍，未调整算法/提示词或放宽预算重跑。

## 6. 两处最小本地修正

| 问题 | 证据与归属 | 本地改动 | 最少验证 / 发布状态 |
| --- | --- | --- | --- |
| 认证查询固定失败 | 真实CH `source_ip:IPv6`，原SQL `source_ip != ''`，既有query_log异常676/CANNOT_PARSE_IPV6；文件匹配固定原版 | API过滤改 `source_ip != toIPv6('::')`，保tenant/user/time/limit参数 | 对应API原测试文件51项通过；本地原typed函数经真实只读API/sql→CH返回200/available=true/0行。仅替换测试传输为真实HTTP，未伪造结果；原typed API端点尚未部署修正 |
| 单项IOC增强固定400 | 本次两次真实HTTP400：`ioc_type is required`；原Agents包装器发送type | 请求字段仅改为ioc_type，保工具签名/端口/提取算法/失败返回 | 两份相关测试7项通过；本地原函数对保留example域名真实调用返回原JSON、sources=null/零分；不作安全判断。未部署，旧调查400保持 |

认证真实验证未复制湖仓凭据：自动审批拒绝远端lake.env完整导出，未执行；改用已授权的只读API token。SQL使用原driver参数转义，再由原API SQL入口做租户重写并发往真实CH。它验证修正后的SQL可执行，不能代验更新后的线上typed endpoint或新模型消费。

## 7. 后续问题与判断

| 项目 | 本批定位 | 当前处理 |
| --- | --- | --- |
| Forensic无回复 | 本地OpenAIConnectionError；21网关相应窗口无日志，无法确认远端收到请求/执行 | 保留未知，不算零用量、不自动重试；连接/可用性专项后置 |
| UEBA设备baseline 500 | UEBA既有日志为asyncpg `connection is closed`，非device参数错误；连接关闭原因未定 | 记录连接复用问题，按用户要求后置，不扩恢复测试 |
| 进程名被当IOC域名 | 原确定性域名正则把 `.exe` 匹配为domain，非模型成功提取 | 后续讨论IOC类型边界；本轮不改提取算法 |
| Router领域判断与缺证 | NR在专业分支被TP替换，专业schema无NR、无工具取证；本次还有MFA状态/动作措辞过度推断 | 不将领域模板当完整调查或事实核验，后续选型讨论 |
| Deep缺源与结束 | OAuth/mailbox/persistence原占位；空结果/深度指标不证明覆盖；后置token检查有越界 | 缺源能力、结果边界和预算语义均保留；不新增采集后端/质量矩阵 |
| 图/KB/历史经验 | 当前本地样例没有匹配reader/KB配置，DB记忆显式关闭；自动AttackPath本批未测 | 沿既有图/知识与full证据，不记本批新通过；下批有针对性接材料即可 |

当前可以继续按模块讨论取舍，不能据此宣称调查全部验收：**Router更适合领域快速判断；默认四节点能交付结构化分析与报告但要检查兜底；Deep已经能根据真实工具返回改变下一步，但缺源和停止条件会让它只交付部分结果。** 不决定删除哪套，不自动发布或归档未完成change。

逐模型实际消息、可见回复、工具返回、节点状态和Markdown在本地 `.local/aisoc21/investigation-functional-20261021/`；公开机器摘要见[本批回执](../handoff/investigation-functional-20261021.json)。完整私有证据保留且不提交，公开记录不含密钥/隐藏推理。结束独审与本地版本结果在OpenSpec execution及PROGRESS记录。

结束独审：未参与源码/报告实现的case_source_review已限定ACCEPT，0本批阻塞；核对数值、真实调用/工具交接、两处修正、来源/持久边界与敏感字段，未追加模型或业务查询。本地增量版本已实际保存在`.local/versions/investigation-functional-20261021/`（13份文件及Git基线/hash，无凭据；不是部署镜像）。原change5/15保持，不归档未完成产品工作。
