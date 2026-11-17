# S01 Case：整事件与A01固定范围对照

2026-11-15，**两案持久受理及即时读回已通过：2次POST、5次GET，无鉴权。** 调查确认Case日志湖/知识实际profile ready、调度保持停止后，HTTP按冻结请求先验整事件案，再创建A01对照；两案受理时均为accepted、无attempt/Run/结果。受理原件保留；随后调查唯一执行器完成两案首轮，测试保存核对通过，[最终结果58次GET](../streaming-case-result-http-20261115-01/README.md)也已通过。

[固定请求](requests.json)包含两个独立operation_key、准确入口及来源映射摘要。入口都是`POST http://192.168.1.21:18424/api/v1/socai2/cases`，无鉴权，沿现有80操作合同与共享lifecycle：

1. 整事件案：选择I01 `263a1c58-e9c6-4ba4-9204-3b0568970551`，当前应纳入A01/A02/A03共3条，并成为该事件接收后续变化的案件。
2. 单告警对照案：仅选择A01 `09e85609-d734-5b2a-81ba-d086fc81b619`，不显式关联事件，不改变整事件案接收目标。

单A01案首轮C1仍可以参考A01所属I01的诊断；这不等于显式关联整个事件。验证时应见`linked_from_case=false`，I自身原选入/覆盖3条保持，本Case的`case_selected_alert_ids/case_covered_alert_ids`只含A01，并保留`diagnosis_scope_extends_beyond_case`。不能把C1出现I判成错误，也不能把I的其他成员加入本案。此边界已在后续实际执行的冻结C1原件读回中核对；本目录受理原件保持原时点。

当前单案容量100，实际各返回1个独立Case及1条initial任务，scope_revision均为1。整事件案Case为`58194401-03ca-5383-83b4-ac82886a5acd`、task为`413e6f0e-1dad-4750-8fa4-152344eb1438`；A01对照Case为`bad63e2a-9f03-547b-8a0c-243347807c41`、task为`26a4fa49-3351-47eb-93fb-40c6b9528c4e`。详情成员/显式I分别为3/1和1/0，continuation为各自独立根。受理时current_assessment为空、任务source=case_create/intent=initial、0attempt/Run/results。最后I01 GET确认active_case_id仍为整事件案，can_receive_automatically=true。

详见[本步实施和验收安排](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#s01整事件及单告警case受理与首轮http安排2026-11-15)。复用[同批真实入站映射](../test-streaming-s01-ingress-20261115-02/readback/identity-map.json)及[A/I保存和62次读取](../streaming-ai-http-20261115-01/README.md)，不重投Kafka、不重跑A/I、不投S04。上游正文质量NOT_PASSED保持。

本步骤没有修改业务代码、合同或运行环境，没有构建镜像、重启HTTP/Swagger、启动调度/模型或推送Git。仅通过现有业务HTTP完成创建与读回，不直接写数据库；后续执行及结果读回另见上述新批证据，不改本目录受理快照。

[离线请求核对](preparation-01.json)已通过现有CaseCreate校验及80合同的201分配回执检查，OpenSpec严格校验通过。准备时实际HTTP请求数为0；此历史离线记录不能代替下述实际创建回执，更不代表首轮已通过。


实际证据：

- [Case/task真实映射和完整分配](actual-case-map-01.json)、[受理验收](acceptance-01.json)、[来源就绪引用](readiness-references.json)。
- [整事件201](post-whole_incident.json)、[Case/task读回](read-whole_incident.json)、[逐项核对](verification-whole_incident.json)。
- [单A01的201](post-single_alert_a01.json)、[Case/task读回](read-single_alert_a01.json)、[逐项核对](verification-single_alert_a01.json)。
- [I01接收者读回](receiver-read-01.json)、[执行脚本](create_cases.py)。

requests.json及preparation-01.json保留准备时原件和操作键，其中prepared_not_submitted/0请求只表示准备时点。当前受理状态以实际映射/acceptance为准，不能重跑创建脚本或换key重复建案。原受理快照保持，后续执行状态另存新回执。
