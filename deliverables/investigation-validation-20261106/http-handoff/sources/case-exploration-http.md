# 案件关系图候选查询：后端调用指南

E66 `GET /api/v1/socai2/cases/{case_id}/exploration-candidates` 已实现。用途是从真实告警对象查一层关联候选，返回每一条为什么匹配及原材料出处。实现/发布证据见[本批验收](../operations/evidence/case-exploration-20261113-01/README.md)，实际部署见[交接入口](../../FRONTEND_BACKEND_HANDOFF.md)。查询不调用模型、不改图、不加入成员；AI对话继续暂缓。

## 从告警对象到候选

当前Fusion入库从明确字段提取主机、账号、IP、域名、URL和文件哈希，保留原值及来源。其他类型虽可存储，不据此声称已统一提取。本接口不会从自由文本推测对象。

| 类型 | 本接口实际匹配规则 | 结果能说明什么 |
| --- | --- | --- |
| host/user/ip/domain/url | 相同租户、Case告警来源范围、对象namespace、object_type及normalized_value完全相同；不追加大小写、IP格式别名、DNS或跨来源归并 | 两份来源记录报告了同类型同值对象；basis=same_source_value。不是统一资产身份或攻击因果证明 |
| hash | 相同来源范围和对象namespace，双方明确MD5/SHA1/SHA256/SHA512算法；算法忽略大小写及`-`、`_`，核16进制及算法长度，值忽略十六进制大小写 | 两份来源记录的算法和哈希值相同；basis=same_hash_algorithm_and_value。不自动合并图中的文件节点 |
| file/process/email/application/cloud_resource/technique/other | 本次不匹配 | 指定对象返回422；多对象起点在scope.excluded_objects逐项说明 |

哈希算法缺失、不支持或值格式不符时同样排除，不根据长度猜算法。原object_key、值、字段路径和材料保留；旧related_alerts及内部C5图的规则完全不变。

## 输入

```http
GET /api/v1/socai2/cases/<Case UUID>/exploration-candidates?object_id=<真实对象 UUID>&limit=20
```

| 参数 | 含义 |
| --- | --- |
| case_id | 当前案件ID，限定租户与案件绑定的告警来源范围 |
| alert_id | 可选，以这条告警最新材料的可用对象为起点；可用候选告警继续下一层查询 |
| object_id | 可选，E30 objects的id或E66 matches中的对象id；与alert_id互斥。必须属于同范围告警的最新材料，不是图内部节点ID |
| 两种起点均不传 | 使用案件当前成员的最新对象；不读取前端未保存画布或历史Run作为默认起点 |
| time_from/time_to | 同时给出带时区的时间；起点包含，终点不含。省略时以起点告警已知event_time的min/max各向外扩配置窗口，当前24小时。单告警/对象使用所属告警时间；全部未知须显式给范围。无可用对象可返回空结果 |
| limit | 默认20，1–100 |
| cursor | 上次next_cursor原样传回；查询起点、实际时间范围、Case成员版本或起点材料变更后清空。跨请求候选数据可能改变，需刷新 |

候选必须有真实event_time落入窗口，不以入库时间代替。排除作为起点的告警，其余本案成员可返回并标记。按共享对象数降序、距**实际匹配起点告警**最近的已知秒数升序（未知最后）、告警ID升序，SQL筛选聚合后再分页。没有威胁分数或攻击路径推断。

配置文件 `services/api/app/socai2/exploration-query.json` 的 `default_window_hours` 控制默认窗口；可用 `SOCAI2_EXPLORATION_CONFIG_FILE` 显式选其他文件。该配置独立于内部调查模型预算和时间窗口。

## 输出字段

| 字段 | 含义 |
| --- | --- |
| items / total / next_cursor | 本页候选、整个范围去重告警数、下一页游标（null结束） |
| observed_at | 本请求一致只读快照的观察时间 |
| scope.seed_kind / seed_alert_ids | case/alert/object起点模式及实际起点告警ID |
| scope.source_namespace / case_scope_revision | 案件绑定的告警来源范围及本次成员范围版本 |
| scope.time_from / time_to / window_basis | 实际窗口及explicit/seed_event_times/no_seeds依据；无对象且未给窗口时两端可null |
| scope.excluded_objects[].object_id / reason | 没有参与匹配的起点对象及unsupported_object_type或hash_algorithm_or_value_invalid原因 |
| items[].alert | 原AlertFacts，全部字段复用E28；不修改旧告警合同 |
| items[].shared_object_count | 去重后的共享对象数；相同对象在多个原字段出现不重复计数 |
| items[].time_delta_seconds | 距实际匹配起点最近已知发生时间的秒数；这些起点全无时间时null |
| items[].already_in_case / case_ids / incident_ids | 是否已在当前案件、全部当前案件归属、事件归属；可包含其他案件 |
| items[].matches[].basis | 同来源对象值，或同明确算法和哈希值；语义见上表 |
| matches[].seed / candidate | 起点与候选实际对象，每个对象均有下列字段 |
| 对象.id / alert_id / material_id | 对象原ID、告警ID、匹配时材料版本；材料可按E31回查 |
| 对象.object_type / namespace / object_key | 原对象类型、来源身份范围与对象键 |
| 对象.raw_value / normalized_value | 原收到值和原存储比较值，未改写 |
| 对象.source_path / algorithm | 原材料字段路径；hash显示本次核对的规范算法，其他类型null |

同一告警只返回一次，但matches保留所有匹配原字段对。**matches仅包含共同对象**；要画出该候选的所有对象，继续读E30 `/alerts/{alert.id}/records/objects`。完整合成响应、各错误示例和每个类型见Swagger E66 / Models。

## 调用顺序与结果

1. E66查询；用E28查看候选详情，用E31 `/alerts/{alert_id}/materials/{material_id}`核对每个source_path原值。
2. 预览、展开和撤销由调用方维护画布；下一次可传候选的真实alert_id/object_id。历史图对象先回查当前材料，旧版本不能直接冒充当前对象。
3. 需要加入本案时，E03读取最新scope_revision，用户明确提交E08 `/cases/{case_id}/associations`，携带operation_key、expected_scope_revision和alert_ids。
4. E03或E66读回成员变化；原事件/其他案件归属保留。调查仍需明确启动，查询不会启动Run。

本项不提供画布保存/恢复；E66不是内部调查工具接口，不会改变A/I/Case执行逻辑。

## 错误

| 状态 | detail / 条件 | 处理 |
| --- | --- | --- |
| 404 | case_not_found / exploration_start_not_found | 核对当前环境ID及Case来源范围 |
| 409 | exploration_start_material_changed | 对象属于旧材料，读取当前对象再查询 |
| 409 | exploration_cursor_scope_changed | 查询或起点范围变化，清空cursor重新读取 |
| 422 | exploration_unsupported_object_type / exploration_hash_algorithm_or_value_invalid | 更换明确可用对象；不猜对象或算法 |
| 422 | exploration_explicit_window_required | 起点无已知发生时间，明确提供time_from/time_to |
| 422 | invalid_exploration_cursor / exploration_query_parameter_not_supported | 损坏游标、未知或重复参数；修正请求 |
| 422 | 字段错误数组 | 非法UUID/分页、两个起点并传、缺一端时间、无时区或倒置窗口 |
| 503 | 对应读取开关未启用 | 检查服务读取配置 |

保存恢复现在使用 [E67–E69](case-exploration-save-http.md)：固定底图、展开来源和画布状态，不生成调查或加入成员。
