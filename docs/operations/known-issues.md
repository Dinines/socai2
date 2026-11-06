# 已知问题与适配边界

先保留原版进行实际验证；以下用于选测试和记录缺陷，不自动触发大规模架构改造。

以[当前服务端范围](alert-processing-scope.md)筛选直接风险。独立UEBA训练/特征生产、原始事件检测和前端展示相关条目仅保留上游事实；本轮只验证告警处理及已有上下文的读取/消费，不将所有风险自动列为实施任务。

## 21 分步测试问题清单 · 签名暂存机 · 2026-11-06

本轮逐步登记告警、事件和 Case 的实测问题，待整轮执行结束后统一处理。

| 编号 | 发现步骤 | 问题与影响 | 后续复核 | 状态 |
| --- | --- | --- | --- | --- |
| F01 | A1 创建 E1，A2、A3 依次并入 E1 | 正式租户中，Fusion 和调查模块均已记录三条告警的归属。首条新建与后两条归并的数据库关联理由均为空。 | A2、A3 的运行日志均记录了合入已有事件。后续需让查询方能从持久化记录读取匹配依据。 | 三条均已核验，待整轮结束后处理 |
| F02 | 第 2 步，E1 首次事件诊断 | 正式处理入口的事件诊断整轮限时 120 秒，共用网关默认 45 秒。首次在 45.01 秒返回 HTTP 408，诊断记录为 `unknown`。 | 整轮结束后统一处理生产调用的超时参数和整轮时间预算。 | 已在同一输入上验证单次 300 秒可以收到原答，生产默认值待处理 |
| F03 | 第 2 步，复核 A1 的平台侧消费 | 本轮使用调查工作台默认租户，但[正式 Kafka 接入约定](../integration/v1/production.md)为原平台 Agents 指定了另一租户。调查同步服务已处理 A1；复查时原平台消费组的下一条仍是 A1。 | 发送后续测试告警前先对齐测试租户和主题。仅凭位点不能确定 Agents 停留的原因。 | 测试接入待确认 |
| F04 | 第 2 步，E1 重跑后的引用校验与展示 | 模型有完整回复，6 处成员或发现的局限说明均只填了同一事件级来源编号。执行器拒收，第 2 版诊断记录为 `failed`。事件的当前诊断指针和正式摘要均为空。 | 核对模型输出约定，并验收页面在拒收时能同时展示失败原因、模型原答入口和正式结果状态。 | 待整轮结束后处理 |
| F05 | 第 2 步，E1 模型原答内容 | 模型将原始进程日志的 `Informational` 描述为整个事件的严重性，又对规则的 TA0009、T1005 给出了输入没有提供的权限提升和凭据访问释义。 | 分别核对事件、告警和原始日志的严重性来源，以及模型对检测标签的解释。 | 原答已留存，待复核 |
| F06 | 正式租户重新开始，第 1 条告警发送前后 | 平台 Agents 的就绪检查返回 HTTP 503，报告与融合通知主题的订阅已断开。正式 A1 已由 Fusion 落库并由调查同步服务消费，平台组在查回时尚未提交该条通知。 | 整轮结束后排查消费者脱离订阅的原因，核实恢复后的处理结果。 | 已留健康检查和位点，原因待核 |
| F07 | 正式租户从事件手动建案 | 21:14 预检时，该租户有三条告警和一个事件，租户内操作员数为 0，无法记录正式建案人。 | 本轮专用操作员通过正式入口建案，调查结束后已停用。创建人和 Run 发起人均可追溯，活跃凭据为 0。 | 本轮身份与收尾已核实 |
| F08 | 正式入口和单次模型时限 | 21 的正式 Case 入口给整轮 120 秒，网关转发至 43 时默认等待 45 秒。 | 对照作业仅给本轮 1,260 秒、单次请求 300 秒。C3、C6 都在约 59 秒收到回复，均因输出截断而失败。 | 测试作业时限已验；常驻服务时限待处理 |
| F09 | C3 请求能否发出 | 原案为 C6 预留额度后跳过 C3。 | 同材料复验时 C3 实际发送 17,467 字节，含 38 个证据来源；43 已返回原答。回复完整性见 F12。 | 此案例的发送前预算问题已验证 |
| F10 | C6 模型报告的完整性 | 3,000 输出 tokens 的两次测试均截断。 | 长输出复跑收到完整 JSON（3,527 输出 tokens），执行器以 F14 的成员范围问题拒收，系统保存兜底报告。 | 此案的截断原因已验证；模型报告采用待验 |
| F11 | C3 的补查主机和工具 | 原案的裁剪排除了三条湖日志所属源主机。 | 对照案实际发给 43 的三个查询全部指向正确源主机；C3 没有生成可接收的整份回答，C4 未查询 ClickHouse。 | 模型输入已验；本轮补查与最终引用待验 |
| F12 | C3 模型回复的完整性 | 3,000 输出 tokens 时截在第二条后续建议。 | 长输出复跑正常结束，实际输出 3,254 tokens。接收程序读到完整回复后报 F14，四类分派各为 0。 | 此案的截断原因已验证；有效派单待验 |
| F13 | 后续问题与所选工具的能力 | C3 原答第一条建议选择认证活动查询 B1，却想用它找审批记录。该查询能返回登录活动，审批记录另需来源。 | 后续取证需分别验证“查到了什么”和“它能回答什么”；这一建议只出现在被拒收的原答中。 | 已记录，未实际派发 |
| F14 | C3 与 C6 回复中的发现归属 | 首次长输出复跑有 2/11 条引用越界。修订提示后的 43 实测中，C3 有 5/7 条、C6 有 1/4 条越界。 | 两次实际请求均包含修订提示。逐条对照领域声明的告警与它所引用发现的告警，仍有不匹配。正式接收程序这次先报 F15。 | 同材料实测仍复现 |
| F15 | C3 与 C6 第六题的来源 | 两份回复都把“三条告警是否已覆盖”标为已回答，证据编号却填了空数组。每次请求均包含 38 项可引用来源。 | 保存原答并回放接收程序。需区分成员材料已读取、覆盖情况有据可查、已形成有效调查结论这三种状态。 | 本轮直接拒收原因，待处理 |
| F16 | C6 时间线的登录时间 | C6 把北京时间 20:50:10 的关联告警时间写成登录发生时间。认证原件记录为 20:49:45。 | 当前输入中的时间字段标记为告警时间。需要精确登录时间时，应读取认证记录；只有告警时间时应明确其含义。 | 仅出现在拒收原答，待处理 |

F01 于北京时间 20:09:22 在生产库 `aisoc` 查回。告警 `9cef967a-ce7d-52c2-93ee-c156b7473e67` 关联事件 `0db85fb6-a92c-46c6-8952-d2afb0f305c5`，当时成员数为 1。`socai2.incident_alerts` 的 `membership_source=fusion`、`basis_version=unrecorded`、`correlation_basis.method=fusion_basis_not_recorded`，`reason` 为空。Fusion 原始快照中读取的 `correlation_basis` 也为空。可按同租户工件 ID `3f6fb5d6-b994-51d4-8094-e09992cc03ff` 复查。[本机 PG 回查记录](../../.local/stepwise-nov06/pg-after.json)

F02 的首次 Run 为 `c16f922f-cc46-5af4-8ab9-149ebf5cd37b`，按本次授权以现有处理模块数据库角色调用事件诊断，`requested_by` 为空。北京时间 20:19:14 发出 1 份模型请求，20:19:59 保存错误回执。网关报告本次超时时限 45 秒、耗时 45.01 秒。Run 的停止原因为 `incident_execution_uncertain`，诊断尝试为第 1 版。请求包含 A1 的主机、账号、清单枚举进程及来源 ID。同案另外两条湖日志未进入本轮模型请求。[首次诊断输入和网关回执](../../.local/stepwise-nov06/i1-readback.json)

F02 按确认另建 Run `9ef83fed-3c03-58b3-b978-4ae5b0c4a2a2`，仍由 21 的 LiteLLM 请求 43。此前三案的 300 秒设置用于直连 43 的测试程序。本次在原网关上为这一个请求指定 300 秒，单次任务整轮留 360 秒。两轮冻结输入相同，实际模型请求逐字段比较，仅增加 `request_timeout=300`。北京时间 20:32:29 至 20:33:18，调用 1 次，48.779 秒后返回 HTTP 200，输入 2,458 tokens、输出 2,478 tokens，结束标记为 `stop`。[单次调用与时限回执](../../.local/stepwise-nov06/i1-r300-run.json)

F04、F05 来自该次原答。编号 `N1_S13` 指向冻结输入的 `$.parent`（事件基本信息），关联告警列表为空。A1 的局限说明和 5 条发现各自的局限说明都只写了这个编号，产生 6 条 `incident_answer_prose_source_wrong_member`；事件整体局限中的同一编号产生 1 条展示警告。E1 只有 A1 一个成员。请求工件为 `297d0b22-2982-43cb-9865-a9f528cad218`，含完整原答的回复工件为 `96c82a50-e5de-4c97-a46d-57b3cb63786a`。第 2 版诊断 `4b2f2d67-6299-5e58-8ed9-c68c6426e98f` 和两条执行步骤均记为失败，查询时 `incidents.latest_diagnosis_id`、正式诊断摘要均为空。[重跑完整输入、原答、逐项校验与发布状态](../../.local/stepwise-nov06/i1-r300-readback.json)

F03 于北京时间 20:21 复核。A1 的融合通知位于 `socai2.alerts.fused` 分区 1、位点 37，已按租户、告警和事件 ID 比对。调查同步组已提交 38，原平台 Agents 组已提交 37，分区末端为 38。本次使用只读查询。[本机 Kafka 位点回执](../../.local/stepwise-nov06/i1-kafka-readback.json)

20:44 再核：上述两个位点仍分别为 38 和 37。21 运行中的 Fusion 读取 `socai2.alerts.raw`，写入 `socai2.alerts.fused`，调查同步服务订阅该输出。E1 的 Redis 索引当时指向 E1，摘要中只有 A1，索引剩余 1,505 秒。此时尚未发送 A2。继续同一个 E1 需要沿用其测试租户；按平台正式接入约定验收常驻链路，则应从正式租户的新事件开始。[21 只读预检](../../.local/stepwise-nov06/a2-preflight-124402.json)

### 正式租户首条告警 · 2026-11-06 北京时间 20:56

按确认从正式租户 `stingaisoc-prod` 重新测试。主机 `sigstage-lab-41e7ab` 的登录、进程启动、网络连接 3 条原始日志已在 ClickHouse `aisoc.raw_events` 分别查回，原始字段逐项一致。A1 直接引用其中的进程启动记录。首轮取证 SQL 将 UUID 列转成字符串后复用同名别名，返回空；按原生 UUID 核查后证实 3 条均在 20:53:33 入库，全程只投递一次。[上下文查回](../../.local/stepwise-prod-nov06/lake-proof.json)

正式 A1 `792740a8-f423-5992-be2e-6d637c93b597` 的输入坐标为 `socai2.alerts.raw/1/27`。Fusion 在 `socai2.alerts.fused/0/34` 发出已落库通知。原始告警和调查同步记录均指向正式 E1 `2ee03cc3-5105-4dbb-87f9-6fbda229fe33`，成员精确为 A1。材料完整，告警分诊及事件诊断 Run 各为 0。F01 在正式租户也可复现，成员关系有记录，关联理由字段仍为空。[正式告警和事件查回](../../.local/stepwise-prod-nov06/pg-after.json)

F06 在投递正式告警前已观察到。20:56:39 核对通知所在分区，调查同步组的下一位点为 35，平台 Agents 组为 34。该观察只说明取证时的消费进度，两个组各自独立。本步仅发送正式 A1。[发送前服务状态](../../.local/stepwise-prod-nov06/services-before.json) · [融合通知及组位点](../../.local/stepwise-prod-nov06/fused-after.json)

### 正式租户第二条告警 · 2026-11-06 北京时间 21:03

A2 `0bc24333-64fd-5989-a3fb-b0c6b289e65f` 的规则“签名作业登录后枚举发布清单”引用了同一主机会话的登录和进程启动两条湖日志。发送前按租户和原始事件 ID 核对两条材料，并用 21 运行中的 Fusion 对 A1 和 A2 分别计算关联键：租户、主机 `sigstage-lab-41e7ab` 和首个战术标签 `TA0009` 相同。发送前该键仍指向 E1，索引剩余 3,194 秒。[A2 输入](../../.local/stepwise-prod-nov06/a2.json) · [发送前关联状态](../../.local/stepwise-prod-nov06/a2-send-intent.json)

A2 通过 `socai2.alerts.raw/1/28` 投递一次。Fusion 日志记录了合入已有事件，通知 `socai2.alerts.fused/2/42` 记录 `inserted`。原始告警、调查成员表和关联缓存均确认 E1 `2ee03cc3-5105-4dbb-87f9-6fbda229fe33` 的成员从单独 A1 变为 A1、A2。事件行版本从 2 升到 3，业务更新时间为北京时间 21:03:10，事件诊断运行数仍为 0，最新诊断指针为空；两条告警各自的分诊运行数也为 0。A2 的成员关系已落库，`basis_version=unrecorded` 且 `reason=null`。复查时调查同步组已提交 43，平台 Agents 报告订阅断开、该分区位点仍为 42。[发送前数据库记录](../../.local/stepwise-prod-nov06/a2-e1-before.json) · [归并后数据库记录](../../.local/stepwise-prod-nov06/a2-pg-after.json) · [运行日志匹配、缓存和消费回执](../../.local/stepwise-prod-nov06/a2-checked.json)

### 正式租户第三条告警 · 2026-11-06 北京时间 21:09

A3 `fd503979-0b4b-5e78-b169-e57f3df52a03` 使用已入湖的两条原始日志。同一主机和发布会话在 20:50:10 启动清单枚举进程，20:50:35 连接元数据端点 `198.51.100.81:8443`，使用 TCP。上游主机侧合成规则按这两项活动的先后关系生成 A3，实际建立连接的进程和传输内容待核实。发送前 E1 的成员为 A1、A2，现网 Fusion 对 A1、A3 算出的关联键相同，仍指向 E1。[A3 告警输入](../../.local/stepwise-prod-nov06/a3.json) · [证据和关联窗口预检](../../.local/stepwise-prod-nov06/a3-preflight.json)

A3 的 Kafka 输入坐标为 `socai2.alerts.raw/1/29`，融合通知为 `socai2.alerts.fused/0/35`。日志记录了合入已有事件，Fusion 原始记录和调查成员表中的正式 E1 `2ee03cc3-5105-4dbb-87f9-6fbda229fe33` 均恰好包含 A1、A2、A3。事件行版本从 3 升至 4，业务更新时间为 21:09:44。21:10 查回时，三条告警分诊运行数各为 0，E1 的事件诊断运行数为 0，按三条告警和该事件查询的显式关联 Case 数为 0。F01 在 A3 仍可复现，`basis_version=unrecorded`、`reason=null`。调查同步组已提交本分区位点 36，平台 Agents 仍报告订阅断开，位点为 34（F06）。[发送前数据库记录](../../.local/stepwise-prod-nov06/a3-e1-before.json) · [发送后数据库记录](../../.local/stepwise-prod-nov06/a3-pg-after.json) · [运行日志、通知和订阅状态](../../.local/stepwise-prod-nov06/a3-checked.json)

F07 的建案前核对限定正式租户和 E1。21:14 查得租户用户数及绑定有效建案用户的凭据数均为 0。21:17 用独立只读角色再次核对：E1 的三条告警齐全，与 E1 或其三条成员显式关联的 Case 数为 0，本次建案键对应的 Case、Run、步骤、模型请求和结果数均为 0。只读预检保留了建案计划及操作键。[操作员与范围预检](../../.local/stepwise-prod-nov06/case-create-preflight.json) · [建案前数据库记录](../../.local/stepwise-prod-nov06/case-create-before.json)

### 正式租户从 E1 人工建案 · 2026-11-06 北京时间 21:33

经用户确认，专用操作员 `stepwise-case-41e7ab` 通过 21 的 `case-create` 从事件 `2ee03cc3-5105-4dbb-87f9-6fbda229fe33` 建立“签名暂存机发布清单活动调查”。Case ID 为 `a88226ca-bf68-5b27-9c21-cb1af39712f1`，范围版本为 1。只读核验确认 E1、Case、待执行 Run 的成员集合逐项相同，均为 A1、A2、A3。基础调查 Run `3e68b2a9-d154-475b-a15e-09206afad193` 为 `pending_update`，开始时间为空，执行步骤、模型请求、结果数均为 0。[建案回执](../../.local/stepwise-prod-nov06/case-create-receipt.json) · [建案后数据库记录](../../.local/stepwise-prod-nov06/case-create-after.json)

创建人和 Run 申请人均为此次操作员 `5f16c011-dcdc-5926-9898-3ed3da2b9c49`。唯一凭据的权限为 `cases:write`，本轮于 21:51 收回。29 表只读快照登记在正式租户工作台，固定入口按 Case ID 打开最新导出的详情。[权限核验](../../.local/stepwise-prod-nov06/case-create-actor-audit.json) · [本机正式租户 Case 工作台](../../.local/processing-workbench/aisoc/f6a5c700-69b8-44fc-8238-609362fb1a9f/site/index.html#live/a88226ca-bf68-5b27-9c21-cb1af39712f1)

### 正式租户 Case 启动预检 · 2026-11-06 北京时间 21:45

分别核对了 21 已部署处理镜像的启动策略和运行中 LiteLLM 的路由。正式入口的 120 秒覆盖整轮 Case。网关把调查请求转到 43，本次路由默认 45 秒，显式请求可选 300 秒，配置的自动重试次数为 0。取证只查镜像、路由及业务记录。21:47 回查时，该 Run 仍为 `pending_update`，步骤、工件和结果各为 0。[生产镜像与网关](../../.local/stepwise-prod-nov06/case-start-inspect.json) · [正式库的待执行记录及三条成员](../../.local/stepwise-prod-nov06/case-run-before.json) · [单次测试作业预检](../../.local/stepwise-prod-nov06/case-start-check.json)

### 正式租户 Case 执行结果 · 2026-11-06 北京时间 21:48:53–21:49:53

对上述既有 Run 执行一次。测试作业给单次模型调用 300 秒、整轮 1,260 秒，使用 21 的调查网关和 43 的模型。PG `aisoc` 中的最终记录有 14 个执行步骤、29 个本轮工件、1 个结果，所有非空步骤工件指针均可查回。窗口为北京时间 20:49–20:51，含三条已入湖的上下文。

| 阶段 | 实际输入与处理 | 可查回的输出 |
| --- | --- | --- |
| C1 冻结范围 | 从 E1 取 A1、A2、A3，将三份告警材料、范围版本 1、时间窗和执行额度冻结到本轮 | 输入快照和执行计划；三个成员最终均为已读、未分析 |
| C2 补背景 | 用两个 IP 查 PG 威胁情报，用账号 `svc_release_catalog` 查 PG 用户风险。资产、历史和知识查询因给后续取证预留工具次数而跳过，外部图源未连接 | 两个查询均成功返回 0 行；其余四个来源分别记录跳过理由 |
| C3 初步分析 | 执行器在发模型请求前检查请求大小及 C6 预留空间，记录 `final_model_tokens_reserved` | 初步分析为空，四个领域未分析。此阶段实际模型调用数为 0 |
| C4 材料与分派 | 已处理三份冻结材料。C3 没有提出后续问题，分派记录中的清单为空 | 查询、深入分析、图谱补查、人工四种派单各 0 条。此次 Case 从 ClickHouse 取回 0 行 |
| C5 关系图 | 从冻结材料整理对象和已有关系 | 关系图有 15 个节点、11 条边，覆盖三条告警，可从最终结果打开 |
| C6 最终交付 | 通过 21 调用 43 一次，已核对数据库请求体与实际发送请求的散列。输入 3,139、输出 3,000 tokens，原答以 `length` 结束 | 留存模型回复和 `model_response_not_complete`。Run 为 `failed`，系统报告为 `partial`。三条告警均在结果成员表内 |

这次模型消息包含告警材料中提取的登录、进程启动、网络连接、命令行、目标 IP 和端口 8443。三条 ClickHouse 原始事件的 ID 均未进入模型消息，登录的原始时间也未进入。告警自身引用湖数据和 Case 运行时重新查询原始日志应分别验收。

结果 `514be4a0-e24d-4785-8c37-296719a8c7c4` 保存的系统结论为“案件性质待核实。本案涉及 3 条告警，当前调查尚不足以确认行为性质和影响范围，需继续核查。”当前判断 `498b0397-49e2-4a3f-b0c0-f2cbd13d75f0` 已关联该结果。工作台可查看模型原答、兜底报告和图。专用操作员和唯一凭据已停用，21 上的临时密钥文件已删除，创建人和发起人关联仍在。[网关调用回执](../../.local/stepwise-prod-nov06/case-start-timed.json) · [按步骤和工件核对的数据库摘要](../../.local/stepwise-prod-nov06/case-run-outcome.json) · [身份收尾核验](../../.local/stepwise-prod-nov06/case-operator-retire-verified.json)

### 同一份 Case 材料的本地复核

本轮只读使用 21:50:15 的正式租户快照。线上记录仍是上述一次执行；以下数据来自原答分析或本地重建，分别说明。

- **F09 初步分析请求。** 原 Run 有三条成员、38 个可引用来源。按实际模型协议和测试用的 `request_timeout=300` 重建 C3 时，原请求为 17,696 字节，可用上限为 17,641。展开仅引用一次的 Schema 定义后降至 17,471 字节，余 170 字节。消息及全部来源逐值一致，解引用后的输出约束相同，C6 留足原先的 27,103 个保守计量单位。此检查只证明新请求可进入发送步骤，旧 Run 的 C3 没有模型原答。
- **F10 最终报告。** 原答的可见正文有 6,854 个字符、7,866 个 UTF-8 字节，截断在 `impact.cannot_generalize` 的第二项中。两个通用限制码各重复了 15 次和 12 次，供应方上报的推理用量为 0。已经输出的 `comparison.summary` 也填入了正文，而首轮调查要求为 `null`。本地改为要求单行 JSON，各项用短句写具体缺口；对没有基线的首轮，在发送给模型的 Schema 中直接限定 `kind=initial`、`summary=null`、`support_ids=[]`。后续比较仍按所选基线处理；接收方继续拒绝截断答案。
- **F11 补查来源。** 完整的 6 个候选占 1,449 字节，均通过 1,800 字节目录上限。与当前案例资料合并后，消息为 13,190 字节，超过 12,288 字节的消息上限。按现有顺序从末尾裁剪，留下的网络和进程查询都指向 A3 的目的主机 `catalog-metadata-41e7ab.test`。库中登录、进程和网络三条原始日志的来源主机均为 `sigstage-lab-41e7ab`。下轮先验在相同额度下实际给了模型哪些主机选项，再核对工具返回。旧 Run 没有执行这些查询。[三条湖记录](../../.local/stepwise-prod-nov06/lake-proof.json)

使用相同的 C6 用户消息重建后，完整请求从 19,018 降至 18,915 字节，仍在原先 23,847 字节的请求额度内。另构造一份明确标记为测试数据的短答，覆盖三条成员、六个问题、四个领域，按实际 Schema 和既有接收程序校验通过。样例为 2,599 个 UTF-8 字节，未测该模型的输出 token 数。它没有写入 Case。原截断回复继续被拒收。实际运行时，若 C3 成功，会有新的初步分析和补查材料进入 C6，这部分需要另一次执行验收。[原件及本地候选的对账结果](../../.local/stepwise-prod-nov06/f09-f10-replay.json) · [本机只读复放脚本](../../.local/stepwise-prod-nov06/replay_f09_f10.py)

此次定向运行的 70 项离线测试通过，涵盖 C3 容量、发送约束、Deep/C6 调用路径、首轮及后续轮比较、非法输出和成员范围。测试中补齐了既有成员范围用例缺失的领域适用性字段，继续检验发现不能继承另一条告警的对象。此次没有部署或新增模型调用，21 的正常 Case 入口仍使用原有时限。

### F11 源主机选择与 21 工具核验 · 2026-11-06

C4 三种湖工具按租户、`src_hostname`、事件类型和冻结时间窗读取 `aisoc.raw_events`。C3 现在优先提供与成员材料中已核实源主机相符的查询，再按对应活动类型和成员覆盖数排序。主机取值沿用 Fusion 的 `device.name`、`src_endpoint.hostname` 顺序；缺失或冲突的来源字段不作为匹配依据。等义缩短 C3 的工具说明后，同一份材料能列出源主机 `sigstage-lab-41e7ab` 的三项工具。完整模型请求为 17,446 字节，距 17,641 字节上限尚余 195。38 个证据来源、全部 6 个原始绑定及 C6 的 27,103 单位预留均已核对。[同案选择和预算回放](../../.local/stepwise-prod-nov06/f11-replay.json)

北京时间 22:14，在 21 用已部署的 `LakeGateway` 和 `socai2_prod_lake_reader` 对三个源主机绑定分别实查。时间窗固定为 20:49 至 20:51，查询未按期望的事件 ID 预筛。返回后按事件 ID 对账，三项均恰好返回一条。

| 工具 | 返回时间（北京时间） | 活动 | 实际返回的原始事件 ID |
| --- | --- | --- | --- |
| `authentication_activity` | 20:49:45 | 登录 | `f04c6cbb-0fd1-55ef-81d8-f985ff5022ff` |
| `process_activity` | 20:50:10 | 启动进程 | `656f6690-a9ed-5684-919b-a2844300c960` |
| `network_connections` | 20:50:35 | 网络连接 | `505690c5-5270-5127-b139-0b50e608cb7b` |

这些是三个独立只读查询，有各自的 ClickHouse 查询 ID。原 Run 的 C4 派单数仍为 0，本次也没有模型请求。真实执行时，若 C2 同样用掉两次工具额度，C4 最多还能执行两次。验收应逐项比较“提供给模型的查询、实际派单、返回事件 ID、C6 最终使用的材料”。定向测试 78 项通过，1 项历史回放因本机缺少所需导出文件跳过。[21 的三份查询回执](../../.local/stepwise-prod-nov06/f11-live-lake-receipt.json)

22:18 预检确认 E1 仍恰好包含 A1、A2、A3，三份材料的版本、ID 和内容指纹与原 Run 一致。旧案的系统结果和当前判断均可查回，计划中的独立对照 Case 尚未创建。正式租户内活跃用户及绑定用户的有效建案凭据数均为 0。后续按步骤确认，先以新的受限测试身份从同一 E1 建案，再确认启动修后的一次性调查作业。[对照案只读预检与计划](../../.local/stepwise-prod-nov06/f11-comparison-preflight.json)

22:24:41（北京时间），21 的正式建案入口从 E1 建立对照 Case `63619fe9-e39a-50bf-9875-8d8b5613a404`，名称为“签名暂存机发布清单活动调查（同材料复验）”。沿用 E1 中已有的三条告警，建案时使用的临时操作员凭据仅有 `cases:write`，有效至北京时间 11 月 7 日 22:22，本轮复验结束后停用。[正式建案回执](../../.local/stepwise-prod-nov06/f11-case-create-receipt.json)

22:25:13 从 `aisoc` 独立只读复查。新案范围版本为 1，恰好关联 E1 和 A1、A2、A3。三份告警材料的 ID、版本、SHA-256 以及分诊和反馈引用均与原案一致。建案生成一条待启动 Run `64906750-4dc6-42cf-9312-d11daefc811b`（`pending_update`），三条成员记录均待分析，整轮输入工件尚未生成。步骤、工件、模型请求、模型回复和结果各 0 条。原案 13 类记录共 64 行与建案前快照逐值一致。下次确认启动后，再核对模型获得的查询选项、C4 的执行回执和 C6 的最终结果。[独立数据库核验](../../.local/stepwise-prod-nov06/f11-created-readback.json)

工作台已收录新案。页面显示“待启动 · 无交付”，详情仍可展开 A1、A2、A3 的三份告警原件；这些材料来自告警处理，在本次调查开始前就已存在。新案与原案都已在浏览器里按 Case ID 打开核对。[新案工作台](../../.local/processing-workbench/aisoc/f6a5c700-69b8-44fc-8238-609362fb1a9f/site/index.html#live/63619fe9-e39a-50bf-9875-8d8b5613a404) · [工作台与数据库快照回执](../../.local/stepwise-prod-nov06/f11-pending-workbench.json)

### 同材料对照案执行 · 2026-11-06 北京时间 22:46:00–22:48:00

在 21 仅启动上述对照 Run 一次。一次性容器实际加载了六份修后模块并逐一核对内容指纹。两个模型请求通过 21 的网关到 43，各发一次，每次等待上限 300 秒、最多输出 3,000 tokens。两份数据库请求正文的 SHA-256 均与对应 HTTP 发送正文一致。运行策略只作用于本次作业。[容器预检](../../.local/stepwise-prod-nov06/f11-start-check.json) · [原始作业回执](../../.local/stepwise-prod-nov06/f11-start-receipt.json) · [逐次请求对账](../../.local/stepwise-prod-nov06/f11-calls-vs-database.json)

| 环节 | 数据库记录与处理结果 |
| --- | --- |
| C1 输入和 C2 背景 | 冻结 E1 的三条成员材料、范围版本 1 和 20:49–20:51 的窗口。威胁情报、用户风险均成功返回 0 行。资产、历史、知识因给补查预留额度而跳过，外部图来源未连接。 |
| 材料读取和 C3 初步分析 | 三份成员材料已读。实际请求 17,467 字节，含 38 个证据来源，三个工具均指向 `sigstage-lab-41e7ab`（B1 登录、B2 网络、B3 进程）。43 用时 59.558 秒，HTTP 200，输入 3,464、输出 3,000 tokens，结束原因为 `length`。回复在第二条建议的第一个对象值中途结束。三条成员均保持已读、未分析。 |
| C4 后续分派 | 执行器记录了空清单。查询、深入分析、图谱补查、人工四个分支各 0 条，本轮从 ClickHouse 取回 0 行。上文 22:14 独立查询的三条回执可验证湖里有数据。 |
| C5 案件关系图 | 由三份冻结材料生成 15 个节点、11 条边。图工件 ID 为 `4b097082-79ba-4537-8379-ab6fdbf20319`；生成这张基础图不依赖 C4 的图谱补查。 |
| C6 最终交付 | 43 用时 59.366 秒，HTTP 200，输入 3,136、输出 3,000 tokens，结束原因为 `length`。单行 JSON 在 `impact.alert_ids[2]` 中途结束。系统完成报告落库，模型步骤标为失败；最终结果来源为 `system`，状态为 `partial`。 |

系统给出的当前结论为“案件性质待核实。本案涉及 3 条告警，当前调查尚不足以确认行为性质和影响范围，需继续核查。”结果 ID 为 `4d43ba09-b171-4679-afae-071ec8f25991`，由当前判断 `2d1246a0-988d-4a6a-910a-647e5a3a6bcc` 引用。21 的业务库已查回 15 条步骤、31 份本轮工件和 1 条结果，步骤上的非空工件指针可全部解析。此次通过了执行记录、基础图、兜底报告的工作台展示核验，完整模型结论和带湖证据的交付仍待验。[逐阶段数据库核验](../../.local/stepwise-prod-nov06/f11-terminal-audit.json) · [正式租户工作台](../../.local/processing-workbench/aisoc/f6a5c700-69b8-44fc-8238-609362fb1a9f/site/index.html#live/63619fe9-e39a-50bf-9875-8d8b5613a404)

工作台快照取于 22:48:58，已按 15 个步骤 ID 与数据库逐一核对。本机 4177 当前连接另一租户，正式租户请使用上面的工作台快照。测试操作员及唯一凭据已停用，21 上的临时密钥文件已删除，创建人与发起人仍可追溯。[工作台核验](../../.local/stepwise-prod-nov06/f11-terminal-workbench.json) · [身份收尾核验](../../.local/stepwise-prod-nov06/f11-identity-retired-verified.json)

### 43 原生最大输出窗口完整复跑 · 2026-11-06 北京时间 23:09:23–23:11:38

从同一 E1 新建 Case `64e28047-f69d-5116-a6fe-1c3ec67ff6c6`，Run `9e58d441-dd63-4e16-bef6-f21b6e9c134c` 从 C1 开始。三份告警材料的 ID、版本和 SHA-256 与前轮逐项相同，窗口仍为 20:49–20:51。[建案材料核验](../../.local/stepwise-prod-nov06/f14-case-create-readback.json)

43 的运行实例提供 65,536 tokens 的输入加输出总窗口。21 的一次性作业在原推理请求中省略两个显式输出长度字段，由 43 扣除本次输入后使用全部剩余额度。单次等待 1,800 秒，整轮 7,500 秒。为兼容执行器按请求字节与预留输出计算预算，本轮给整案 393,216 个保守计量单位；实际仍最多 4 次模型、4 次工具，每次工具最多 200 行。常驻服务策略沿用原配置。预检核了 21 的网关参数、43 的模型与运行配置。另用上一轮两份既有消息在同一 43 做无生成分词校核，得到的计数与当时上报用量相符。本轮的新消息只经原生成入口发送。[部署上限与网关验证](../../.local/stepwise-prod-nov06/f14-native-capacity-preflight.json) · [本轮作业预检](../../.local/stepwise-prod-nov06/f14-start-check.json)

| 模型步骤 | 输入 tokens | 可用输出 tokens | 实际输出 tokens | HTTP 耗时 | 结束与接收 |
| --- | ---: | ---: | ---: | ---: | --- |
| C3 初步分析 | 3,465 | 62,071 | 3,254 | 64.489 秒 | 200，`stop`，完整 JSON，领域引用范围校验失败 |
| C6 最终报告 | 3,139 | 62,397 | 3,527 | 69.713 秒 | 200，`stop`，完整 JSON，同一项范围校验失败 |

两阶段各调用一次。整轮 134.95 秒，数据库返回 `failed`，原因 `domain_finding_scope_mismatch`，结果交付为 `partial`。C4 没有收到可执行建议，C5 保存了基础关系图，C6 保存了系统兜底结果 `7ada3013-a6ac-468c-9767-c0d58884139e`。本轮专用操作员和凭据已停用，临时密钥已删除。[作业终态与用量](../../.local/stepwise-prod-nov06/f14-start-receipt.json) · [临时身份收尾](../../.local/stepwise-prod-nov06/f14-operator-retire.json)

完整原答均通过各自请求声明的 JSON Schema，随后在接收程序的跨字段校验被拒收。C3 的身份分析 `domains[0]` 只列 A2（登录后启动枚举进程），却引用了同时列 A1、A2、A3 的发现 F1。C6 的云分析 `analysis.domains[1]` 只列 A1、A3，却引用了其自身覆盖三条告警的 F1。两个 F1 分别出自两次模型回复。接收程序要求一个领域所引用发现涉及的告警均在该领域声明的范围内。[原答复查脚本](../../.local/stepwise-prod-nov06/f14_explain_rejection.py) · [领域范围接收规则](../../services/api/app/socai2/baseline_analysis_contract.py)

工作台已按 ID 对照 15 个执行步骤和 31 份工件。C4 的四类后续分派各为 0，C5 图有 15 个节点、11 条边。C6 系统报告覆盖三条告警，`cases.current_assessment_id` 指向 `b96d330a-e5a3-486f-b9f5-7da47970c7fb`。页面可同时打开未采用的完整模型回复和当前采用的系统报告。[本次 Case 工作台](../../.local/processing-workbench/aisoc/f6a5c700-69b8-44fc-8238-609362fb1a9f/site/index.html#live/64e28047-f69d-5116-a6fe-1c3ec67ff6c6) · [数据库、模型和页面逐项核验](../../.local/stepwise-prod-nov06/f14-terminal-audit.json)

#### F14 的本地修订与验收边界

用冻结的请求、原答和当时的解析规则检查了 8 个领域、11 条领域到发现的引用。越界的恰好是上文所列的 C3 身份和 C6 云领域两处。分别在内存副本中只移除越界的 F1 引用，两份副本均通过完整解析，全案仍保留发现 F1 和它关联的三条告警。另一组副本只把缺少的成员补到领域里，结构上也能通过；要采用这种做法，需要证据支持新加成员属于该领域。正式记录仍保存两份被拒收的原答和已采用的系统结果。[逐条引用与四份诊断副本的回放](../../.local/stepwise-prod-nov06/f14-scope-counterfactual.json)

C3 的原提示只说可以引用范围内的发现。C6 已要求领域覆盖所引发现的全部成员，但没有告诉模型遇到不匹配时如何填写。现在两阶段共用一条规则：先按证据确定领域的 `alert_ids`，发现涉及的每一条告警都在该范围内才列入 `finding_ids`，无合适发现可填 `[]`。补证后的 C3 再分析也使用这条规则。接收程序仍逐项检查范围；未给程序添加扩大成员或改写原答的处理。[C3 提示及接收规则](../../services/api/app/socai2/baseline_analysis_contract.py) · [C6 提示](../../services/api/app/socai2/baseline_delivery_contract.py)

按 F14 的实际协议重新装配请求，仅系统提示发生变化。C3 与 C6 各自的 38 项来源、字段值和输出 Schema 均与原请求逐值一致。C3 消息计 12,277 / 12,288 字节，保留源主机的登录、网络和进程三个补查选项；C6 消息计 11,764 / 12,288 字节，完整请求 18,956 字节，低于本案预留的 23,830 字节。新增的回归用例验证“领域只覆盖发现的部分告警时拒收、撤掉该引用后同一发现仍留在全案”。57 项定向测试通过。下节记录这项修订在 43 上的实际表现。[实际消息、来源和发送预算对账](../../.local/stepwise-prod-nov06/f14-scope-wire-revised.json)

### 修订领域提示后，按同一事件完整复跑 · 2026-11-07 北京时间 07:36:43–07:39:26

21 从事件 `2ee03cc3-5105-4dbb-87f9-6fbda229fe33` 新建 Case `47e1ed08-6414-5b80-960e-57a92e88ca0d`，执行 Run `81f2e9fb-854a-4ac4-be27-ad0a9bf8c10e`。三份冻结告警材料逐一核对一致。与前次对照作业相比，C3、C6 只换了模型提示，接收规则相同。本次作业使用 43 的 65,536 tokens 总窗口，单次等待 1,800 秒，整轮等待 7,500 秒。两次调用各发一次，均以 HTTP 200、`stop` 返回完整 JSON。整轮实际耗时 162.25 秒。[材料核对](../../.local/stepwise-prod-nov06/f15-comparison-preflight.json) · [实际作业配置](../../.local/stepwise-prod-nov06/f15-start-check.json) · [作业回执与用量](../../.local/stepwise-prod-nov06/f15-start-receipt.json)

| 阶段 | 实际执行与交付 |
| --- | --- |
| C1、C2 范围与背景 | 冻结同一事件的三条告警材料，均已读取。情报和用户风险查询各返回 0 行。资产、历史、知识查询因工具额度预留而跳过，外部图数据源未连接。 |
| C3 初步分析 | 模型用时 68.091 秒，输入 3,478、输出 3,435 tokens。六道题中，第六题 `questions[5]`（`coverage`）回答“三个告警成员已覆盖”，`state=answered`，但 `evidence_ids=[]`。本次正式校验在此报 `answered_question_needs_sources`。 |
| C4 分派与补查 | 系统保存了空分派清单。查询、深入分析、图谱补查、人工四条分支各 0 项。被拒收的原答中有查认证和深入分析的建议，均未执行，本轮无数据湖回执。其 B1 查询只能取登录活动，不能据此确认审批工单，见 F13。 |
| C5 关系图 | 用三份冻结材料生成了 15 个节点、11 条边，并保留三个告警锚点。无须等待 C4 查湖便可显示这张基础图。 |
| C6 最终交付 | 模型用时 93.396 秒，输入 3,157、输出 4,729 tokens。其独立回答的 `analysis.questions[5]` 同样声明已覆盖且证据编号为空。模型步骤失败，系统收尾步骤完成并写入报告。 |

第六题是两阶段各自唯一“已回答却无来源”的题。两次输入各有 38 个来源，三份材料均在。如果回答“三条材料已覆盖”，应给出支持覆盖声明的成员来源。授权或外传仍无法确认时，应单独说明未知之处。[两份原答的六道问题及接收程序回放](../../.local/stepwise-prod-nov06/f15-response-replay.json)

两份原答中的领域引用也逐项核过。C3 身份领域只列 A2，却引用了跨三条告警的 F1。云和内部风险领域各有两处类似越界，共 5/7 条。C6 的云领域列 A1、A3，却引用了涵盖 A2 的 F1，共 1/4 条越界。修订提示在两次实际请求中均已生效，F14 仍复现。C6 对登录时刻的混用另记为 F16。[实际请求、原答工件及逐项领域核验](../../.local/stepwise-prod-nov06/f15-terminal-audit.json)

业务库保存 15 个步骤、31 份工件、1 条结果。运行状态为 `failed`，交付状态为 `partial`。结果 `9195cff0-2a8e-4ea0-973a-ee8c232a9b1f` 为系统兜底，当前判断 `cb35f64e-45fb-4dde-a94a-53e169e483c9` 引用它，结论为“案件性质待核实”。三条成员状态均为已读、未形成有效分析。正式租户工作台的 15 条步骤和 31 份工件均已逐项对上。先前的三个 Case 已核对库内数据与工作台详情。本轮专用操作员和凭据已停用，临时密钥文件已删除。[打开本次 Case 工作台](../../.local/processing-workbench/aisoc/f6a5c700-69b8-44fc-8238-609362fb1a9f/site/index.html#live/47e1ed08-6414-5b80-960e-57a92e88ca0d) · [身份收尾回执](../../.local/stepwise-prod-nov06/f15-operator-retire.json)

## 已修复的 20 部署阻塞

| 问题 | 已有适配 | 使用前要核对 |
| --- | --- | --- |
| 三条 embedding 默认模型/维度不一致 | 统一到本地 qwen0.6b 原生1024维，新建独立集合 | source hash、模型指纹和当前集合，不能混写旧向量空间 |
| Qdrant 进程 nofile1024 导致集合创建失败 | Compose soft/hard65536 | 重建容器后核实际进程 limit，不只是 shell 值 |
| SDK1.19.1 无上游调用的 search | 两处检索改用服务端 HTTP points/search | 仅当前实际操作已测，不宣称所有版本/API兼容 |
| 旧 TI 向量抽查为全零 | 1,748公开记录重新嵌入，原payload/ID保留 | 没有原始输入文件时不能盲跑 reindex |

## 当前迁移计划的直接检查项

以下按固定源码核对；1B/1C、1F、1D及1E实际结果已补充，其余仍为静态检查/待验。分别进入[批次执行卡](dependency-migration-plan.md)，不把规划写成通过证据。

| 批次 | 源码现状/风险 | 计划处理与通过判据 |
| --- | --- | --- |
| 1B | 原initdb脚本缺SQL挂载/空目录时可退出0；134份SQL有同编号不同文件 | 1B使用受控共享库执行器，134/134原SQL及ledger集合一致；原init脚本仍保留，不将其退出0单独视为成功 |
| 1B | `20_runtime_role_password.sh` 的psql `SELECT set_config(...)` 返回密钥值，默认输出可能进入初始化日志 | 1B原版哨兵输出→补丁静默→原版负对照通过；真实凭据补丁输出不含密码。原件保留，生成副本及差异记录见[1B回执](1b-shared-services.md) |
| 1B/1F | runtime角色非superuser不等于tenant隔离；原RLS保留未绑定上下文的跨tenant worker语义 | 1B实际确认绑定读写/越权拒绝，未绑定仍可跨tenant读取。1F受理HTTP身份/权限、跨tenant拒绝及两租户读隔离已实测；不外推所有路由或broker权限 |
| 1C/1F | 21现有Kafka只有PLAINTEXT，无认证；原resolver拒绝production/staging明文 | 1F新增19093 SSL listener，CA/IP验证及无CA拒绝通过；production无豁免。旧9092保留，broker仍无客户ACL，单节点无高可用背书 |
| 1C/1G | Agents worker默认group_id为aisoc-agents-triage，main只传topic/地址，没有group环境接线 | 1G已显式传项目group_id；worker关闭，实际Kafka消费留3A，不能用静态接线代替消费验收 |
| 1F | API迁移器默认可汇总SQL失败但不失败退出，严格模式需显式开启 | 1F REQUIRED/STRICT独立owner迁移检查通过，134文件/134ledger/0pending。首次macOS伴随文件导致268计数已阻断并修正打包，失败日志保留 |
| 1F | `POST /api/v1/alerts/submit` 为直写库快路径，明确绕过Kafka/Fusion | 1F新认证alert-ingress已实现并实测主链；原submit仍为直写快路径，不算Fusion链验收 |
| 1F/1G | 事件检测/lake与部分后台任务默认启用；Agents可自动消费/升级/记忆写回 | 按执行卡显式关闭范围外/尚未验能力，并检查实际订阅和启动任务；所需能力到对应子批再开启 |
| 1D/1G/3C | 共享Qdrant1.7.0有API key；20生成的部分HTTP/SDK调用没有向21传递密钥 | 1D用受控key和REST验结构/恢复，原20 overlay未挂载；未来业务路径需实际传递密钥、独立集合名并核SDK1.19.1，不能只改QDRANT_URL就宣称接通 |
| 1E/1G | LiteLLM1.106.0在无虚拟密钥DB时，错误master key请求返回400/no_db_connection，非401 | 1E真实拒绝已验；保留原版行为及首次探针判据失败，不以加匿名绕过或额外数据库掩盖。服务key不等于tenant/BYOK隔离 |
| 1G | 原服务可能向缺失的Realtime发送非必要进度；未证明无Realtime仍能交付 | 1G两Run无Realtime均完成，重启后API账本/报告hash保持；Agents本身缓存易失，其他入口未验 |

1F还补齐API startup对已有图/湖禁用配置的判断，新增war-room worker开关（默认保留上游开启）；本批12项后台worker关闭。未知schema DLQ会在解析tenant/source前拒绝，记录可通过broker坐标取回；不得假设其一定有tenant/source字段。

## 源码事实/待验证风险

- 1F已实际确认：同指纹而event_time/external_id/source不同的发生归入同一canonical Alert；新增来源ID保留，原event_time/raw_event为首条。独立发生语义不宣称通过，2A继续核。
- Fusion PG fail-soft 与 Kafka 发布分离；自动分诊 DLQ 失败可被吞掉，不能假定可靠处置后才确认。
- Case 发起调查只选择/裁剪有限告警材料；报告覆盖不能宣称整个 Case 全量。
- Recon 的非空增强 error dict 可能被后续判断当作有材料；这是静态风险，需实际定向复现。
- Ledger 无 DSN 可 no-op，Actions 保存失败可降级内存；状态完成不证明持久证据齐全。
- `max_tool_calls` 的部分检查实际比较模型调用；不能据名称推断严格工具预算。
- UEBA window_days 不自动实现逐样本淘汰；peer member_count 不一定是人数；CORE 行为模块与独立 UEBA 要分开测。
- ATT&CK 语义函数在已检查的 agents/app 未见调用方；索引可检索不证明调查已用。
- Live effects 验证有条件，其他动作/入口不保证已回读；awaiting_completion 不当 succeeded。

完整逐项定位与测试入口见 [数据/风险分析](../reference/aisoc/07-data-tests-porting.md)、[源码索引](../reference/aisoc/08-source-index.md)。实际可复现缺陷进入新项目问题表后再限定修复，保留原测试与结果。

1G实测缺陷及限制见[回执](1g-service-baseline.md)：缓存读跨tenant及外Case发起缺口已加约束；工具error字典成功标记、同响应usage重复计数已修复并独立复验。首次错误账本保留；API聚合numeric0需结合unpriced provenance解读，费用unknown。报告token上限和可选增强依赖未接保留，未宣称完整调查质量。较大模型和旧数据按[计划](knowledge-data-reuse-plan.md)比较，不混用向量空间。

2A新增[实测回执](2a-dedup-correlation.md)：2A-01不同发生的event_time/raw_event/external_id未独立持久，仍阻塞；需明确独立告警或聚合+发生记录合同。2A-02已修复既有incident成员重投重复计数和容量边界，25项测试及真实3投递通过；完整Redis丢失重建、并发及RBA重投累计不在本次通过范围。保留首次错误快照；只重建Fusion，实际镜像采用2A叠加层。

2A-01后续已按[独立身份合同](2a-source-identity.md)通过限定验收：新source-v1不再按内容合并不同上游UUID；旧legacy事实/历史缺口保留，可匹配旧HTTP及旧Kafka保持ID。无DDL；持久身份/关联存现有enrichment_data项目命名空间，后续增强写入须保留。PG不可用不伪称新身份duplicate持久，但只做故障分支替身检查。完整Redis丢失、并发与风险支路重投到后续，不将正常/单键丢失通过当全面恢复通过。

## 2B-01风险实测与后续边界

- 已修复：Fusion dedup key失效后相同规范ID重复增加RBA分数/计数；改为实体hash+完整贡献集合WATCH/MULTI，promotion同事务，40项测试及限定真实链/Redis并发通过，见[回执](2b-risk-idempotence.md)。旧多计分数不回写。
- 保留：风险非PG持久账本，完整Redis丢失/跨实体原子性/持续活跃实体集合容量/队列时效未验；原fail-soft行为及32次冲突重试上限不等于持久重试保证。
- 实测：Fusion `/ml/status`因租户认证材料未配置返回503；保持拒绝，不将source-consistent启发式值写成直接观察到训练状态。2B-02核所需身份接线。
- 静态后续：业务上下文API的内存snapshot版本、PG的yaml/enabled/updated_at、Agents的tenant缓存并非已证实同一持久版本；自动worker关闭。后续2B-02已对存储指纹/实际方法采用/TTL/恢复与失败缓存作限定验收，见下节；不能以preview代替消费或外推自动worker。

## 2B-02规则实测及限制

已复现原版重复GET的进程version递增、缺少可跨进程对应的内容身份；新增policy_revision与实际采用来源/状态，保留version兼容。保存失败污染缓存、冷依赖故障被报告成空规则已修复，83项测试与所列真实链通过，见[回执](2b-policy-versions.md)。

保持30秒缓存，故障stale_cache无最大陈旧期限；API行缺失可返回missing_row_cache，多副本/CAS/持久版本历史未验。原抑制在ledger写入前返回，自动worker仍关闭，持久抑制结果必须在3A开启前补验。Fusion状态接口认证503仍保留，2B-02未改该服务。

## 2C-01IOC路径

原matcher连接/查询失败返回[]且连接失败永久丢弃DSN；新生产消费改用带matched/no_match/unavailable/not_requested的lookup，失败保留可重试配置并限时。旧match列表接口为兼容仍保留原限制，其他调用方不能据此判“查过无匹配”。sink/API新增首次冻结lookup及来源/观测/衰减字段，见[回执](2c-ioc-consumption.md)。

仅一条历史参考，不证明实时信誉；来源原报告无数值置信，50只是默认。无外部增强、Go、模型或厂商调用。Agents旧enrich_ioc仍未接，完整上下文到2C-02；并发建池/负载、坏行转换、真实共享PG故障传播、公共IOC CRUD、Fusion ML认证503与旧风险限制未扩验。

## 2C-02当前PG上下文

静态核对：上游priority算法存在，但queue_priority没有传入真实PG资产/权限，build_queue仍用存储priority。本批保留队列行为，新增独立只读processing-context实际查询与评分解释，见[回执](2c-processing-context.md)。不把原算法单测写成队列已接上下文。

已有PG SAVEPOINT真实故障/同会话恢复、合成tenant隔离及时间边界通过；生产资料同步/有效时间/性能/全库故障未验。当前视图非持久历史快照，material_complete只指评分材料候选已解析；员工目录/普通事件日志/UEBA仍未接。下一2C-03核已有外部历史材料，不能用先前alerts当完整事件湖。

## 2C-03来源缺口与工具身份

[盘点与真实缺源回执](2c-event-ueba-sources.md)确认当前没有可接的AiSOC事件历史/UEBA来源；20仅一条未定性Kafka消息，不能当完整历史库。21 lake默认localhost、迁移启动关闭；Agents工具当前缺API调用凭据，空Bearer在发送前产生LocalProtocolError。独立进程用短时受限key收到API缺源结果，不代表生产工作负载身份已接。工具清单backed_by_data是7个静态SQL实现，不能作为runtime ready。后续实际工具接线须处理身份和清单语义，不能以开启采集/湖写入代替外部合同。

[3A-01](3a-triage-entry-plan.md)先处理business-context抑制在ledger前返回的持久性缺口；worker保持关闭，2C真实事件/UEBA消费仍开放。

## 3A-01抑制持久性已限定修复

先前business-context抑制在ledger前返回已由[本批](3a-policy-suppression.md)补规则事件；DLQ改为broker确认，双持久失败不提交并停订阅。新group仍默认latest，不能在未明确起点/控制器恢复/多分区语义前启常驻worker。已有completed Run会含policy标识的规则记录，统计调用方须按event kind/model_used区分模型verdict。来自故障探针的合成f-revision记录保留为probe-only，不代表实际规则采用；完整规则撤销/再分诊、上游可变材料等价性、真实模型/知识/事件源仍未验。

## 3A-02模型可见材料与质量限制

[3A-02实际回执](3a-model-triage.md)发现build_state缺失risk_score默认0.0，模型引用它当作零风险证据；后续[3A-03](3a-risk-score.md)已修缺失/null、显式0及来源语义，并验一次真实模型。旧已默认0不可反推，未知的内部数值特征基线与权重保持，不算重新校准评分。后续[3A-04](3a-org-memory.md)已接A/B组织记忆读取，成功/空结果与失败分开；后续[3A-05](3a-tenant-skill.md)已验技能Bearer/settings:read、读取/选择/失败来源及实际模型采用，重启回查保持；后续[3A-06](3a-kb-read.md)已接A/B KB认证读取、保守cutoff、实际采用文本与工件；后续[3A-07](3a-dispositions.md)已接近期处置认证读取及明确采用来源；后续[3A-08](3a-identity-read.md)已接身份读取及明确图源失败，五类reader接通，完整质量仍未过。

3A-03还保留原finding文字`confidence0.95 < threshold0.85`不准确的问题：needs_review分支实际要求升级，不是数值比较成立；自动graph仍关闭。新number|null消息不兼容旧float-only Fusion，不能直接撤层后继续消费积压，恢复步骤见回执。

3A-04组织记忆只有两个测试tenant配置了受控30天reader key，语句直接合成入PG，不等于真实多分析员编译写入或全tenant部署。默认缓存120秒内不重验服务端撤销/到期与编辑删除；逐条核缓存expires_at、映射移除/轮换在缓存前生效。真实撤销失败探针强制TTL0，不能宣称默认即时撤销。新first-write回执/工件原子性不外推原通用Run/alert重试更新。失败状态只验证实际读取→prompt投影→probe-only账本；只有正常材料调用了真实模型，完整质量未过。

首轮raw_event评分标签/synthetic来源污染已保留；另3条新告警盲测分类符合预期，但模型恶意回答有ATT&CK名称错配，授权只来自输入变更单，置信未校准。模型连接失败没有成功响应/成本行；cost日志persisted=True只表配置意图，不是行存在或零费用证明。完整模型质量、常驻自动分诊、多分区和崩溃中模型重复调用未验。

## 3A-05技能读取与保留边界

本批使用独立每tenant settings:read reader，保留组织记忆alerts:read的key/映射；仅A/B测试tenant配置，不代表全tenant部署。默认缓存120秒，映射移除/轮换在缓存前生效，API端单独撤销/到期、技能编辑/退休须刷新后生效；逐条检查缓存expires_at，刷新失败不采用旧材料。选择保留加法分数（rule20、technique10、source5、每keyword2，同分按ID），不是严格优先级。生产worker保留source，技能选择可回退原始MITRE标签，不代表已修复整体技术映射质量。

真实模型采用v2，事后合成头v3与历史v2工件分开；不外推deep investigation版本pin：原逻辑在指定旧版本不可得时仍可能落当前版本，graph保持关闭，列为3B开放前的检查/修复门槛。技能指导语的确切采用文本/hash、读取事件和工件同首次写入事务保存，不能据此宣称整个Run/alert完全不可变。

8条预激活样例及后续2条读取样例、版本轮换均为合成测试；4条replay行是failed/probe-only、无score/报告且未执行replay，仅满足原FK，不是实际编写/回测/激活流程通过。失败状态验证真实读取→prompt投影→独立probe-only账本，只有正常采用材料调用一次真实模型；347测试与1677 tokens不证明技能内容或完整调查质量。重启回查与身份生命周期已核，失败尝试按[回执](3a-tenant-skill.md)保留。

## 3A-06 KB读取与引用边界

KB内部GET已使用Bearer/knowledge_base:read及tenant交集；reader有独立受控映射，按tenant/地址/身份/query/limit/cutoff隔离缓存，失败不采用过期材料，禁用/无配置/无命中/失败分别记录。默认120秒缓存仍不能保证API端单独撤销、到期、文档删除或编辑即时生效；本批已实际验证撤销后仍命中有效缓存，强制刷新才401且无材料，不能写成默认即时撤销。仅A/B测试tenant，原org/skill权限与映射保持。

当前检索是aisoc_kb_documents的PG english全文content匹配，保留原query生成、kind和排序；不使用embedding或已有ATT&CK/TI向量索引。六条KB行、含必要检索词的正文及后续压缩均为本批合成资料，不是真实SOP、产品检索或知识质量。created/updated cutoff保守排除后来新增或修改的行，创建/修改拒绝数不双计；没有正文历史重建，不能还原被改旧文本。API文档详情只有200字符preview，核完整采用依据须看冻结工件。

守卫扫描、清理、JSON转义、UNTRUSTED_DATA与nonce边界保持；统一采用子集后保存文本、来源、引用表及hash。KB局部使用ensure_ascii=False避免中文经二次转义触发隐藏截断，编码体最多3400字符；inline boundary note等义精简，保留原“suspected prompt-injection attempt”措辞和原断言。字符预算不是token预算，也不代表注入守卫检测质量已全面通过。

首次完整literal prompt8717、第二次8105字符均在8000上限前预检停止，未调用模型；只改本批合成KB内容/标题并保留旧新hash与updated_at，另作等义note精简，从检查点恢复同一已受理告警。最终7861字符、一次真实模型2095 tokens未截断，提供KB1但model_citations与unresolvable_citations均为空；这是实际提供来源，不是已证明模型引用准确。中间prompt-v2测试197过/1措辞断言失败保留，恢复原短语后prompt-v3重测198过，未删断言。

新KB回执随verdict首次事务保存，真实PG故障/同Run恢复及重启回查已验，不外推整个Run/alert完全冻结。该批当时处置/身份reader401，处置后续见下文；deep investigation版本pin、真实事件/UEBA、宽样本质量和常驻消费仍未过；详见[回执](3a-kb-read.md)。


## 3A-07近期个人处置意见边界

近期处置GET已使用Bearer/alerts:read及tenant交集和显式RLS，独立每tenant凭据映射在缓存前选择。仅A/B测试tenant配置两枚30天reader，原org/skill/KB六枚凭据保持；alerts:read是已有较粗的只读scope，不是本接口专属权限。默认120秒缓存不即时重验服务端撤销/到期或反馈编辑删除；已实际复现撤销后缓存成功、强制TTL0刷新401且不采用旧材料，不能宣称默认即时撤销。闭合地址失败与恢复为真实reader证据，坏格式/缺时间/错误cutoff echo等为单元或投影证据。

五条反馈是直接合成PG读样例，alert_id为空且符合真实表约束，不是分析员实际结案、纠正、第二人佐证或编译组织记忆。保留同rule优先于仅entity匹配、再按created_at及ID排序；原prompt标题含newest first，实际是各优先级内时间顺序，不能解释成跨组全局最新。表只有created_at且非空，没有updated_at/历史或数据库禁止UPDATE；cutoff只能核记录创建时间，不能重建后来编辑的旧note。row_source_sha256是带tenant及请求匹配标记的当前API来源投影hash，不是完整DB行版本、历史证明或认证签名。

最多5条、note最多240字符，完整原heading与个人意见advisory共同受原3000字符上限约束；采用行、实际清理note、rendered文本/hash、完整prompt块/hash一致。本次3条意见/1336字符块进入7355字符的真实safe-call输入；一次模型needs_review/自报0.65、1909 tokens，未精确提及note或反馈ID，rationale仅概括参考过往意见，不证明因果采用、分类正确或引用质量。原org读取success，技能读取success但selection no_match、KB no_match是该新rule/entity的自然结果；另外用旧查询验证原三能力保持。

初394项测试通过后，收尾独立进程导入reader触发app.agents包初始化依赖环。保留失败证据，移除该包初始化依赖、使用固定的闭合词表并补两种新进程导入顺序核对，最终396项（API91/Agents305）通过；仅额外重建Agents，env/mount/依赖/DDL不变。最终镜像非root读取A/B处置及原三能力通过；唯一真实模型和原重启工件核对发生在首镜像，最终镜像没有重测模型。后半只读检查点恢复没有追加重启、key操作、输入或模型，不能写成全程首次通过。

真实PG工件INSERT除零回滚/同Run恢复/重复不追加保护的是首次读取事件与工件，不冻结通用Run/alert更新。生产SQL同会话SAVEPOINT故障恢复不是HTTP/共享PG故障或API503传播验收。该批当时身份reader401，现已由3A-08接通；旧增强/工具身份、事件/UEBA、完整知识/调查质量仍开放；常驻worker、graph、审批和真实响应关闭。详见[回执](3a-dispositions.md)，身份后续见下条，imported_at不能当HR有效期或完整历史。


## 3A-08身份读取的时间、权限与质量限制

五类reader已接通，但只验A/B合成资料。身份imported_at是Employee导入stamp，不是HR生效日；native cutoff先过滤再limit，7候选只1可采用（晚3、不可核3），所有采用行仍计业务历史未知。新样例部门/经理两属性v1→v2后旧split也读当前值，明确不能重建旧HR路径；is_active/职位不证明当前活动授权。

专用lazy READ_ACCESS不启通用图初始化/schema。Community共享高权限凭据不是数据库只读租户角色，原Bolt未新增TLS；隔离依赖本查询每节点严格tenant，不外推其他图接口。身份默认300秒缓存不即时感知撤销或图修改，刷新失败无stale。真实配置移除503、图查询错误及恢复与PG账本探针分别留证，不是共享服务outage。

唯一模型同最终镜像，身份1已提供、回复提到账户及通用service词，不证明因果采用或质量。来源ID未显示在prompt，仅供工件追溯；未提ID不列失败。初次operator成本表TEXT参数传UUID而失败，未发输入/模型；仅修字符串绑定并从已完成矩阵后恢复。初版operator未另存文件/hash，不能声称具备该版本冻结备份；失败日志/检查点保留。3A-09实际复验与阻塞见下条，常驻、graph和响应未开放。


## 3A-09历史复现与仍存准入阻塞

三例真实分类符合判据，但p01把11:01行为说成处于02:00批准窗口，且把缺少job当确认未授权；完整质量不通过。p02授权只来自合成CR，身份不是活动授权；p03的0.10已在Fusion叙事中，risk_score仍null。未追加模型改善成绩。

真实broker以模型方法替身复现：坏schema返回None，无DLQ却commit1；ledger返回False且PG零行，也commit1；冷进程重投已完成Run仍重入模型方法。暖重投原事件/工件保持，但通用Run/shadow行变化，不能宣称完整不可变或模型恰好一次。PG错误后的同进程暖恢复虽不重入模型，却将原先实际读取的五类回执全部写成not_requested，来源事实丢失；该历史事实保留，普通live路径的后续保护见3A-10-02。

真实工件错误与注入DLQ未确认时offset0，恢复后1；实际DLQ确认后才commit1。这是限定小边界，不抵消上述静默提交，也不是共享PG/broker outage。生产SDK根client默认retry2/timeout None，本批只在探针实例设0/45秒，生产仍未受该限制。静默提交的后续修复见下节；[总计划](3a-worker-reliability-plan.md)其余子项仍为规划。

首次broker工具在import前失败、无topic/消息，保留原脚本/log后只修操作工具。finish误要求measured1而实际unpriced1/measured0，保留原脚本与结构化失败；首次独立完整stderr未保存。只读恢复未重复撤销、输入、模型或重启，不能写成全首次通过。详见[回执](3a-triage-admission.md)。

## 3A-10-01修复范围与保留缺口

[本批回执](3a-triage-durability.md)限定通过：live writer只认明确True，False/None等为持久失败；Kafka入口先验证已JSON解码的schema，坏消息和无处理结果不再正常提交，DLQ未确认保留offset。只改两处运行源码，143项直接测试和真实broker/PG小边界已验；不覆盖非法wire JSON、直接triage/build_state或全部其他消费者。

有效UUID不证明tenant在PG存在或告警归属。3A-10-01当时未知tenant先进入模型方法替身，再因PG FK失败进入持久DLQ；后续普通live claim另核告警归属，不能外推所有入口授权。无pool样例仅恢复DLQ确认，pool仍为None，不是PG恢复成功。该批当时冷重投/来源恢复问题后续见下节；生产SDK retry2/timeout None及p01时间/授权理由错误仍保留。

初次测试136通过/7个新增替身失败，只修新测试后143通过，运行源码不变。首次部署已构建并重建Agents后因Env列表顺序断言停下；原脚本/log保留，改按排序hash核相同配置后只读verify-existing恢复，没有再次构建或重建。最终再做一次同容器重启回查，不能写成全首次通过。常驻worker/自动graph/审批/真实响应继续关闭。

## 3A-10-02保护边界及新增准入限制

[回执](3a-triage-recovery.md)限定普通Kafka live分诊：先核合法首次结果及来源工件，新处理持久claim/seq=-1后才进入方法；同worker保存恢复保留完整五来源/usage/原tuple，fresh进程遇已开始而无结果则unknown，不能靠TTL重调。三个真实broker样例及207项测试通过，但不是模型恰好一次、长期吞吐或rebalance保证；direct triage、replay、纯离线shadow和原policy/memory抑制入口不据此扩张。

默认事件时间线实际包含[-1,1]或仅[-1]；显式`events?since=-1`仍422，负开始事件增量cursor在修复前是准入限制。seq=-1只证明处理开始，不能写成模型请求已发送；unknown Run即使被reaper从running改failed也不授权自动重调。旧legacy首次结果只回可证明字段，原incident/shadow/规则/模型名等缺失保持unknown；p01只读lookup保留1687 tokens，没有worker或模型重放。

本批首轮测试、broker、部署与finish通过，无失败恢复或重跑。生产SDK预算、负cursor及3A-09 p01理由质量未修，完整worker准入仍false，下一3A-10-03见[总计划](3a-worker-reliability-plan.md)。十枚reader只核原文件/hash/metadata/scopes保持，未重测十枚各自旧查询，不能写成重启后完整reader查询矩阵通过。

## 3A-10-03-01请求界限与cursor修复，额度仍待验

[回执](3a-triage-request.md)的189项测试/71项HTTP限定通过：当前triage角色factory默认SDK retry0/timeout45，原auto-triage另有整次45秒截止；既有开始事件next_seq=-1可直接增量读取，-2仍422。客户端截止/取消不证明远端停止或零usage，其他角色/显式参数覆盖/原始HTTP及stream入口不外推。本批未新增模型调用，未验43真实超时。

仅API/Agents更新及重启、当前二十层，14表旧材料/十枚reader保持、三操作key401。当前仍无持久单tenant调用/tokens额度，跨进程并发、积压/停止恢复留03-02；完整质量和worker准入false。一次过早finish由部署检查点拒绝、无副作用，待部署成功后完整finish；无重复部署/模型。

## 3A-10-03-02持久预约/停止的限定边界

[回执](3a-triage-budget.md)的263项/137项HTTP、真实SSL Kafka/PG与模型HTTP替身已通过；只有普通live且配置policy的LLM尝试才受新表约束。call与固定预留token/未确认上限跨进程共享，quota claim失败保留offset，旧前置lookup仍沿原确认DLQ合同。一次20000为准入单位，非实际usage；出站16000 UTF-8字节/512输出/SDK0/45不外推任意tokenizer或厂商忽略参数。未知预约不自动过期，当前三份保留，A积压仍offset0/end1。

实际10.012917秒停止后任务清空、offset保持，fresh未知无新请求；显式调整测试policy后同group恢复没有退款或重发消息。初始import环、恢复校验身份、probe读取policy权限及operator屏障/快速拒绝断言失败均留证，故不是首轮全过。当前21层、原134迁移保持，另有一项目表；scope外模型入口、自然窗口过期、长期吞吐/rebalance、非协作取消、生产完整prompt覆盖和整体质量未验。下一为3A准入剩余阻塞复核，worker仍OFF。

## 3A-11-01最新只读准入复核

3A-11-01只读准入复核已完成，见[回执](3a-admission-review.md)：旧p01时间/授权错误未被indicator gate识别；常驻Agents审批提案guard实际True且缺Kafka bootstrap/TLS，旧调查工具身份仍缺。三未知预约及A积压保持，0模型/消息/offset提交/运行改动；完整准入未过。下一[3A-11-02配置补齐](3a-triage-admission-config-plan.md)，保持worker禁用，然后单独修提示词/复验质量。

审批提案guard未显式禁用、常驻Agents缺Kafka bootstrap/TLS；worker关闭使其未作为常驻消费者运行，隔离探针通过不证明这些环境项已接。五reader不替代旧工具service身份。旧回执保持；本批无运行改动，三未知预约及A积压不清理/重调。

## 3A-11-02最新配置验收

3A-11-02常驻分诊配置补齐已限定验收，见[回执](3a-triage-admission-config.md)：仅Agents同镜像重建一次，新增四项环境值，复用原只读CA；审批提案guard现False、Kafka SSL/主机名校验及六组offset读取通过。旧14表/三unknown/A积压/十reader/其他35容器/18卷/134迁移保持，0模型/消息/提交。当前22层、19源码层，worker仍OFF；下一[3A-11-03理由提示词修复](3a-triage-reasoning-plan.md)，完整准入/质量未过。

当前补齐的是transport及审批提案禁用，不含常驻topic/group/DLQ项目映射；五reader与通用工具身份仍分开。A积压与unknown不清理/重调；p01理由仍未修，不能将配置就绪当质量或常驻准入。

## 2026-10-20迁移正确性复核

[审核报告](migration-review-20261020.md)确认R1 Fusion保存/发布未确认仍提交、R2普通分诊丢description/event_time、R3 source-v1缺行修复保存空关联、R4 gate前缓存使下一新告警复用被拒绝的原结论、R5 consumer.stop报错漏任务清理。均待修，本轮使用原方法内存替身复现，未注入真实PG/Kafka故障或模型；不把既有局部通过外推。R6更正项目映射未配置的旧判断：1G已接topic/group，DLQ派生为项目topic，尚缺常驻准入证据。
