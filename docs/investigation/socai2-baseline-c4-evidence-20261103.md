# C4第一批：必要原始字段与确定查询

2026-11-03。本批补齐新socai2调查路径的**冻结材料语义读取、进程/网络确定查询、查询账本和有界模型输入视图**。这是C4的第一批，不是已完成Deep：问题级动态选择下一查、主机产品工具适配、认证工具、补证后再分析仍待接。

业务表沿用29表458列，无新增DDL。页面、旧v2调查入口与历史报告保持；本批没有模型调用、真实ClickHouse/厂商查询或业务部署。PG检查使用21原独立合成库，工具返回全部为明确替身。

## 1. 执行流程

1. Case手动启动时，C1已冻结成员、材料版本、对象、问题和时间窗，并提交Run为running。
2. `prepare_evidence`在Case→Run锁内读取**冻结material_id**，不跟随`latest_material_id`。选择明确OCSF字段，保存原路径、值、转换、冲突与遗漏；保存服务器生成的主机查询目录。C4.materials步骤及工件同事务提交。重复调用读取原工件。
3. 调用方选择目录中的binding_id及本轮question_id。目录只包含冻结host对象对应的process_activity/network_connections，不能提交SQL、任意主机、窗口或新成员。目录列出能力，不自动执行全部查询。
4. 同事务检查Run状态、已有未落定步骤及本Run总Tool额度，写C4.query、实际参数、query_id和tool_request；**提交后才派发**。查询SQL固定同租户、精确主机、绝对UTC窗口，先去重再排序/限量。
5. 保存tool_response原行、行数、截断与状态，再保存独立语义投影。每字段能回查到原行/材料路径。相同绑定只派发一次，后续读取该次回执；不同问题引用同一回执不变成第二份证据。
6. `prepare_evidence_view`按问题生成新快照，将原材料和新查询的字段按记录交错选取。保留全部成员覆盖、查询状态、遗漏、E来源映射和记录分组；8192字节正文/2048字节单字段及12KiB消息上限保持。视图准备不等于模型已分析。

本批没有修改C3初始输入或重跑初始分析。后续Deep与再次综合须使用这个新输入工件及新的步骤身份，不能覆盖旧C3请求、答复或领域结果。

## 2. 已补字段的准确来源

优先读取`alert_materials.ocsf_json`；仅其缺失时读取已知规范化信封`raw_json.ocsf_event`。不从任意raw_text、标题或存储preview猜字段。字段不存在就记录not_provided。

| 字段 | 明确源路径 | 读取与语义 |
| --- | --- | --- |
| 事件类别 | class_uid | 仅1007/4001/3002映射为process/network/authentication_activity；其他未知。此映射不是ATT&CK或攻击判定 |
| 目标进程 | process.name/pid/uid/cmd_line/file.path | PID为非负整数；命令行整值guard后整项保留或省略 |
| 父进程 | process.parent_process.pid/uid/name/file.path/cmd_line | 来源报告的父进程字段；不单凭PID建立跨记录因果链 |
| 操作者进程 | actor.process.pid/name/cmd_line/parent_process.pid | 单独命名，不与process混成同一进程 |
| 进程与操作者会话 | process.session.uid、process.session_uid、actor.session.uid、actor.session_uid | 四个来源分别保留，不自动认定等价或与Fusion会话关联 |
| 用户 | actor.user.name/uid | 明确用户名与源UID；缺失不从标题补 |
| 主机 | device.name、src_endpoint.hostname、dst_endpoint.hostname | 设备名与源/目标主机分开；查询目录仍仅由冻结对象表生成 |
| 网络完整端点 | src_endpoint/dst_endpoint的ip和port | IP文本校验；端口0–65535，原字段明确给出0可保留 |
| 协议、文件 | protocol、connection_info.protocol_name、file.path | 多个协议来源不一致时保留两者并标conflict |
| 动作、结果 | activity.action/outcome | 不从空返回或状态码推断动作结果 |
| Fusion/厂商会话 | activity.session.id/key/key_kind/originating_human | 内部会话ID、厂商键及键类型分开保留 |
| 信封activity | _socai2_storage.envelope_activity下相同字段 | 仅存储元数据明确activity来源时读取。与OCSF内值冲突并列，不拼成混合会话 |

每个选中字段为`{name:string,value:string|integer,source_path:string,transform:identity|explicit_class_mapping,conflict:boolean}`。每个遗漏为`{source_path:string|null,reason:string}`。state为available/unavailable；**available只表示结构可读，不代表字段齐全**。PID拒绝布尔值/负数，端口拒绝非法范围，字符串空值/危险原值/大于2048字节整项省略。

原始OCSF信封继续留在库内。语义投影是明确白名单和类型转换；逐个原值检查后才选取，并再次检查完整模型消息。没有关闭guard，也没有把整个原始日志删掉class_uid后送给模型；这仍不是通用提示注入或语义真实性证明。

## 3. 两个查询的合同变化

新查询合同为`socai2.c4-lake.v1`，不复用旧process.v3/network.v2结果。两类都读取：event_id、event_time、class_uid、src/dst_hostname、process_name、source/dest_ip、src/dst_port、protocol、file_path、hash_sha256、user_name、action、outcome、session_id/key/key_kind/originating_human、ocsf_json。

- PID、父进程、命令行从该行保留的OCSF读取；湖不需要为此新增列。
- 扁平列也完整保存在原回执。非空明确值可投影；空串、0端口及默认零地址单独不能当观察。明确OCSF中的0与扁平默认0分开处理。扁平列与OCSF冲突并列保留。
- event_id/event_time保存为原行身份/时间字段，模型中的record_key用于把同一行字段放在一起；E来源映射可回查实际工件、行号、字段路径与值hash。
- 相同tenant/event_time/class_uid/event_id按ingest_time选最新行，然后稳定按event_time/event_id排序，最多50行或Run更小上限，额外一行仅判断截断。进程查询不再以非空process_name过滤，避免丢失只有PID等字段的记录。
- 返回列、主机、类别、窗口、重复行和限量再次校验。时间窗为左闭右开，查询使用UTC；不把当前时间窗口偷偷扩成前后若干小时。
- **湖没有来源命名空间列可供精确过滤**：同租户同主机窗口可能含多个连接器来源，限制写入回执和模型视图。binding中的alert_ids只表示为何选择此主机，不证明每行属于所有相关告警；本批不自动构造跨记录归因或图边。

## 4. 表、字段、状态和已有合同

| 已有表/字段 | 本批写入/读取 | 保持的边界 |
| --- | --- | --- |
| alert_materials | 精确读取冻结版本原OCSF/已知信封 | 不更新原件、不切到最新版本 |
| run_members.read_state | 已检查选定字段的材料标read | 工件注明selected_source_fields_only；不表示全文审核或模型分析，analysis_state不变 |
| run_steps | stage=C4.materials；tool=C4.query，question_id、seq、actual_args、输入输出工件、行数/错误/时间 | 沿用同Run，材料步骤不计Tool，真实派发计全Run额度，失败/unknown也占已用额度 |
| artifacts.tool_request | tool_name/contract_version/scope/limit/parameters | 沿用tool_args；parameters含tenant/host/binding/related members/query_id，不含凭据 |
| artifacts.tool_response | state、rows、returned_rows、truncated、query_id、error、captured_at | 沿用tool_exchange；成功空查询rows=[]/0，未执行rows=null/行数null |
| artifacts.source_snapshot | materials、query_projection、model_view三种内容 | schema_version=socai2.baseline-evidence.v1，hash与字节数留存；内容由程序生成，未新增通用38合同或第二套结果表 |
| results/case_assessments | 本批不生成 | 工具回执和模型输入不是案件结论；不自动采用、结案 |

materials保存scope、逐成员语义/遗漏/材料ID、目录和captured_at。query_projection保存binding/question/相关成员/原回执ID、执行state/reason、有限fetch实见数量、截断/遗漏及逐行字段。model_view保存question、ready/reason、messages、source_map、coverage、omissions、bytes、input_artifact_ids；相同输入和问题复用同一视图，新证据产生新视图。

引用只允许materials/query_projection中实际存在的字段路径使用observation。原tool_response、model_view、根路径、执行状态不能冒充观察；发布时再次校验路径和角色。原始查询状态、来源报告、推断仍分开。

## 5. 失败、额度与并发

缺窗口、空窗口、未配置湖、缺额度、额度用尽或剩余时间不足1秒均记录skipped及原因，不派发。低于1秒不得传给旧CH助手变成服务端整数0秒（无时间上限）。C2/C3/C4共用Run已有额度和截止，不新发4次额度，不增加模型或Token预算。

同Case锁后检查同一绑定已有记录；running/unknown返回冲突，已完成/已跳过读取原结果。C4不在其他未落定步骤旁另开一个查询。请求提交失败时外部调用为0；不存在第一步尚未改running就覆盖执行范围的问题。

本地超时或取消不能证明同步ClickHouse线程已停止，因此查询步骤/Run保留unknown占槽，无自动重试或恢复任务。query_id已在派发前请求中保存，便于后续核实。返回合同异常或结果保存不确定也保守保留unknown；本批没有增加自动恢复模块。

原行保留上限64KiB（留出其余工件字段空间），语义工件上限128KiB；超限整行/整字段省略，记录有限fetch数量与截断原因。若材料/必需范围超出已有上限，明确拒绝准备；不裁剪成员或提高预算。模型输入按记录交错选取仍可能省略字段，不能宣称完整调查覆盖。

## 6. 具体例子

合成Case包含A1，冻结材料M1记录`process.pid=4209`、`parent_process.pid=20`、`cmd_line=worker --synthetic`。用户随后更新材料到M2（PID=999）并加入A2。

- 运行中的R1继续读取M1，仅含A1；新待更新R2由既有范围更新流程维护。本批不会将999或A2混入R1。
- R1选中“该主机/本轮窗口的进程查询”，先提交request/query_id和running，再执行。同一请求同时进入的第二个调用收到冲突；完成后再次调用只读原回执。
- 返回行中的PID、父进程和命令行按各自源路径进入语义工件，模型可见E编号与record_key。它们表示“来源记录报告这些值”，不能写成“Tool已证明恶意父子链”。
- 网络查询成功0行保存completed、[]、0；模型看到查空及覆盖未知，不能据此写“没有网络连接”或“削弱攻击关联”。
- 后续Deep应基于本次新视图判断是否需要认证或人工授权材料；当前尚未执行这个动态回合，也没有生成最终报告。

## 7. 本批验证与后续

明细和原始失败见[本批回执](../operations/socai2-baseline-c4-evidence-20261103.json)。真实PG只用于新socai2合成事务、冻结、RLS、并发、账本、引用和回滚；ClickHouse SQL/适配器与返回使用替身，不能当成真实湖/模型质量验收。

下一先接**问题级Deep与C3再分析的新回合身份**，沿用本批绑定、来源映射和全Run预算；补产品主机/认证能力时仍需精确来源实例、窗口和权限校验。再接C5有来源图与C6交付。业务HTTP、新表告警/事件writer、UEBA/知识/Graph适配与生产切换仍待。r13不重试，报告修复暂停，5.3未完。
