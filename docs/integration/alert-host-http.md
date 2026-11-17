# 告警详情：同主机最近告警

E71供告警详情→概况→相关告警区域使用。查看当前告警涉及的主机最近还发生了什么，返回最近7条其他告警；7是条数，不是7天。

`GET /api/v1/socai2/alerts/{alert_id}/same-host-alerts`

唯一输入是路径里的真实告警UUID `alert_id`。不接受查询参数，不要求Case。不调用模型，不改变告警判定、处理状态或关联。打开返回的告警用E28；核对主机材料用E31。

## 查询规则

- 起点和候选只取各自最新材料的`host`对象。多个主机取并集，候选告警只显示一次，保留全部匹配对象对。
- 同租户、同告警`source_namespace`，对象`namespace`和`normalized_value`完全相同。不要求战术相同，不根据IP、资产ID、主机名相似或别名推断。
- 从数据库已保存且真实`event_time`已知的记录中，按`event_time`倒序、告警ID倒序取最近7条；排除当前告警。没有额外时间窗，可包含当前告警之后发生的记录。
- 候选发生时间未知时排除，不用入库时间替代。起点时间未知仍可查；没有当前材料或主机时返回空列表。
- 已关闭、已判误报的告警仍保留原状态和判定。共享主机只说明关联，不证明共同攻击。

默认上限7由`alert-host-query.json`的`display_limit`配置，`SOCAI2_ALERT_HOST_CONFIG_FILE`可指定文件；允许1–100，错误返回503。HTTP调用方不能传limit改变上限，本功能没有续页；`total`说明全部匹配数，`limit`说明本次实际上限。

## 输出字段

| 字段 | 含义与使用 |
| --- | --- |
| `items[].alert` | 原AlertFacts；显示title、severity、event_time，原状态和判定保持；点击id调用E28打开详情 |
| `items[].matches[].seed` | 起点最新材料中的主机对象；id、alert_id、material_id、object_type、namespace、object_key、raw_value、normalized_value、source_path，algorithm为null |
| `items[].matches[].candidate` | 对应候选主机对象，字段同seed；沿alert_id/material_id调用E31，再按source_path回查原文 |
| `total` | 全范围去重匹配告警数，可大于items长度 |
| `limit` | 实际配置的返回上限，当前7 |
| `source_alert_id` | 当前查看的告警，它本身不在结果中 |
| `source_material_id` | 实际查询的起点最新材料ID；没有材料时null |
| `source_namespace` | 本次告警来源范围 |
| `source_hosts` | 起点实际参与匹配的主机对象；为空时items和total均为空/0 |
| `observed_at` | 单次数据库只读快照时间；再次查询可能读取到新增数据 |

成功有值/空值完整JSON例子和嵌套字段见Swagger E71。无匹配返回`items=[]、total=0`，仍返回起点及主机范围；空结果不表示主机安全。

## 错误和与其他接口的关系

| HTTP | 情况 |
| --- | --- |
| 404 | `alert_host_source_not_found`：起点不存在或不属于当前租户 |
| 422 | 路径UUID非法；或`alert_host_query_parameter_not_supported`：传入了查询参数 |
| 503 | `invalid_alert_host_configuration`：配置文件或上限不合法；`socai2_page_read_not_enabled`：现有页面读取开关未开启 |

E70“相似历史复核”仍按同主机且同战术、同IP或哈希查询，默认起点前30天，支持分页，用于人工判定时对照。E71仅提供同主机最新7条，两个接口用途和条件各自保持。查询都不会自动提交人工反馈、关联Case或启动调查；E30的一般对象关系读取保持原合同。

本轮直接验收见[回执](../operations/evidence/alert-host-20261113-01/README.md)；仅交付后端HTTP，未修改测试页面，暂不提交或推送Git。
