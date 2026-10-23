# v1.0.0 两例真实流程及数据落地核验

状态：两个新例子已实际执行，已完成只读落库核对；v1_two_examples_audit结束独审限定ACCEPT、0本轮测试收口阻塞。完整逐步骤原文留存及调查质量不通过。用户明确允许正式服务上运行1—2例，并要求盘点表/数据方便后端对接。本轮正好2条新raw Kafka输入，不重跑旧canary、不改模型/业务代码/服务配置/预算、不执行真实厂商动作。

[后端盘点入口](../integration/v1/data-inventory.md) · [实际字段](../integration/v1/table-fields.md) · [机器盘点](../integration/v1/data-catalog.json) · [只读SQL](../integration/v1/examples/production-two-examples.sql)

PG补查采集：`2026-10-22T22:56:23.350081+08:00`。模型执行于17:09—17:10，数小时后仍能从新进程读回；不通过进程内缓存判断持久化。上次补充只读查询因自动审批额度错误未执行；用户要求继续后本次只读盘点成功。原失败记录保持，不把它当产品功能失败。

## 两例结果

| 项目 | 例1 | 例2 |
| --- | --- | --- |
| canonical Alert | `bc625c39-56af-5403-a378-9bfb99c610d2` | `e5f593f0-b328-59c3-8238-379db33d8bfe` |
| Run | `4f5a0a57-050a-57a4-8443-504550fbc5fd` | `bdccd907-7f36-558f-8ed4-4be2e417b101` |
| 首次结果 | benign_true_positive/0.95，resolved | needs_review/0.85，triaged |
| 事件/工件 | 3/7 | 18/14 |
| 模型回复/tokens | 1/2033 | 7/29755（分诊2058＋graph27697） |
| 调查 | 自动关闭，未升级，不要求MD | 自动升级，6轮Deep/10工具，partial |
| 直接Neo4j关系 | 3条 | 5条 |

PG生产总计3Alert/3Run/36事件/35工件，含上一轮canary；本轮仅2Alert/2Run/21事件/21工件。两例21工件正文实际读出，UTF-8字节数和SHA256逐份重算全部匹配，21份event_id均非空。`aisoc_run_costs`对应3行，8个回复、31788tokens，与Run/usage吻合，全部unpriced，美元值0不表示实测免费。

Kafka新生产组在两例观察后committed=`{0:31,1:33,2:40}`并追平当时end；只读消费者未提交offset。Fusion Redis4个dedup/delivery键及2个incident键在17:11观察时存在，delivery快照真实restore校验通过；它们有TTL，不作长期数据库。两个Alert在Neo4j真实存在，同tenant直接关系已读回。未改旧租户/group/unknown/旧预算或清理历史记录。

## 例2各工具实际输出

| seq | 工具 | 实际参数 | 已保存结果 |
| --- | --- | --- | --- |
| 10000 | `process_activity` | `{"hours": 24, "hostname": "v1-functional-host-2"}` | {'tool': 'process_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'processes on v1-functional-host-2 in the last 24h'} |
| 10001 | `process_tree` | `{"hostname": "v1-functional-host-2"}` | {'tool': 'process_tree', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Parent-process lineage is not stored: aisoc.raw_events has process_name but no parent_process_name or process_guid.  |
| 10002 | `network_connections` | `{"hours": 24, "hostname": "v1-functional-host-2"}` | {'tool': 'network_connections', 'available': False, 'row_count': 0, 'rows': [], 'reason': 'Lake query failed (LakeQueryError). This is a lookup failure, not an absence of evidence.', 'query': 'connect |
| 10003 | `entity_timeline` | `{"hours": 24, "hostname": "v1-functional-host-2"}` | {'tool': 'entity_timeline', 'available': True, 'row_count': 0, 'rows': [], 'query': 'timeline for v1-functional-host-2 over the last 24h'} |
| 10004 | `authentication_events` | `{"hours": 24, "user_name": "v1-functional-user-2"}` | {'tool': 'authentication_events', 'available': True, 'row_count': 0, 'rows': [], 'query': 'authentication events for v1-functional-user-2 in the last 24h'} |
| 10005 | `enrich_ioc` | `{"ioc_type": "ip", "ioc_value": "192.0.2.82"}` | {'ioc_type': 'ip', 'value': '192.0.2.82', 'risk_score': 0, 'confidence': 0, 'malicious_votes': 0, 'harmless_votes': 0, 'total_engines': 0, 'reputation': 0, 'classification': {}, 'is_bot': False, 'is_t |
| 10006 | `lookup_technique` | `{"technique_id": "T1059.001"}` | {'id': 'T1059.001', 'name': 'Unknown', 'tactic': 'Unknown'} |
| 10007 | `technique_activity` | `{"days": 24, "technique_id": "T1059.001"}` | {'tool': 'technique_activity', 'available': True, 'row_count': 0, 'rows': [], 'query': 'activity mapped to T1059.001 in the last 24d'} |
| 10008 | `historical_execution` | `{"days": 24, "process_name": "v1-functional-host-2"}` | {'tool': 'historical_execution', 'available': True, 'row_count': 0, 'rows': [], 'query': 'executions of v1-functional-host-2 across the fleet, last 24d'} |
| 10009 | `historical_execution` | `{"days": 24, "process_name": "v1-functional-user-2"}` | {'tool': 'historical_execution', 'available': True, 'row_count': 0, 'rows': [], 'query': 'executions of v1-functional-user-2 across the fleet, last 24d'} |

Markdown工件：`72e0c864-41a0-4096-bfa2-8aa0ebe3a641`，6413字节；Alert/Run/events/artifact目录/Markdown详情GET均200。生产reader、tenantheader及读取路径见生产接入文档；内容在JSON的content字段。

## 留存与功能限制

- 3个graph_step仅保存node，input/output_hash均null；无每个节点独立完整state快照。
- 模型回复8个均有记录且完整；首次分诊和Deep后4轮的持久prompt副本有截断，不能还原所有实际请求原文。
- 工具仅保存最多200字符result_preview，graph_result.messages为空，不能承诺完整ToolMessage归档。
- 例2外层Run completed，但graph/report running、completion partial；六轮上限且软预算27697/20000，attack_path节点未到达。现有attack_path工件来自Bundle上下文，非该节点执行证明。
- depth.tokens=0/over_budget=false与外层graph_usage不一致，narrative是末条historical_execution工具JSON；报告中的缺证据/良性prior表述仍有质量问题，不能作为调查质量通过。
- 五类资料读取200/no_match，租户相关资料表为0；TI归因401、部分processing-context四维BufferError、process_tree缺父进程字段、network_connections查询失败（LakeQueryError）、其他查询零行均按真实来源记录，不写成所有模块正常。
- 工具seq10000+先写、graph_result低seq后写；API since按seq筛选，不是严格写入游标。后端需要最终从首页分页补齐/去重，详见数据盘点指引。

本轮结论：主链自动关闭/自动调查、相关落库及读取通过；每步完整原文留存不通过，调查质量未验收。问题登记在已有upstream-issues，不另开架构改造/无限回归；原迁移5/15不变。

## 后端SQL执行与交付核对

`production-two-examples.sql`替换既定UUID变量后，在21真实只读事务（transaction_read_only=on）执行9个SELECT，全部成功，不返回/修改其他租户业务资料。字段字典25表428字段、成本3行、21个事件与21个工件关联、发送/读取坐标已由独立审查者对照原始回执核实；机器字典未包含凭据或prompt正文。脚本未创建表/视图或改动业务配置。
