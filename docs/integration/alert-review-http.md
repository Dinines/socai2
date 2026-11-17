# 告警页：相似历史告警复核

E70 用于人工判定前后查找值得对照的历史告警。返回的是候选及匹配依据，不自动把当前判定应用到其他告警，不调用模型。

`GET /api/v1/socai2/alerts/{alert_id}/review-candidates`

| 输入 | 必填/默认 | 用途 |
| --- | --- | --- |
| `alert_id` 路径参数 | 必填 UUID | 当前查看的告警；候选排除它本身 |
| `time_from` / `time_to` | 可选，必须同时提供且带时区 | 按候选真实发生时间筛选，[起点,终点) |
| `limit` | 默认5，1–100 | 每页候选告警数量 |
| `cursor` | 默认不传 | 上页 `next_cursor` 原样续页；改变条件清空 |

未传时间窗时，以当前告警真实 `event_time` 为终点，默认向前30天。这个时长在 `alert-review-query.json` 的 `default_lookback_days` 配置，通过 `SOCAI2_ALERT_REVIEW_CONFIG_FILE` 可指定配置文件。当前告警没有真实发生时间时返回422，需明确选择时间窗，不用入库时间替代。显式窗口可包含当前告警之后的记录，响应标明 `window_basis=explicit`。

## 为什么匹配

三个规则取并集；一条告警只出现一次，同时保留所有依据。按候选发生时间倒序、告警 ID 倒序排列，优先查看最近记录。

| `matches[].rule` | 规则 | 返回依据 |
| --- | --- | --- |
| `same_host_and_tactic` | host对象值相同，且至少一个检测战术标签相同 | 双方主机对象与材料路径；共同标签及双方 `detection.tactics[index]` 路径 |
| `same_ip` | ip对象值相同 | 双方 IP 对象、值与材料路径 |
| `same_hash_algorithm_and_value` | 明确算法及有效哈希值相同 | 双方 hash 对象、算法、原值与材料路径 |

同租户、同告警 `source_namespace`，双方对象 `namespace` 也必须一致。只查双方最新材料。主机/IP按已存 `normalized_value` 精确匹配；战术按原字符串精确匹配，大小写、名称/编码不互转，不从技术编号推战术。单独同主机、单独同战术不命中。

哈希支持明确的 MD5/SHA1/SHA256/SHA512，规范化算法写法并核对十六进制长度；哈希值忽略大小写。不猜算法，不按文件名匹配。只有哈希来源时不额外推断文件名称或恶意性。战术是检测标签，共有对象也不是攻击因果。

可以返回已关闭、已有人工反馈，以及属于其他事件或 Case 的告警；保持原状态、判定和归属，逐条复核后再决定是否修改。发生时间未知的候选不进入时间窗。

## 输出字段

| 字段 | 含义与使用方式 |
| --- | --- |
| `items[].alert` | 原 `AlertFacts`；名称、严重程度、发生时间、状态、判定、版本及原关联 ID，字段不改写 |
| `items[].matched_rules` | 该候选满足的去重规则名称，不是风险评分 |
| `items[].time_delta_seconds` | 与当前告警真实发生时间相差的绝对秒数，起点时间未知时null |
| `items[].matches[].seed/candidate` | 实际对象 ID、告警/材料 ID、类型、namespace、原值/规范值、字段路径、哈希算法；沿 E31 回查对应版本 |
| `items[].matches[].shared_tactics` | 同主机规则的标签原值及双方数组路径；IP/哈希规则为空数组 |
| `items[].incident_ids/case_ids` | 当前所属事件/案件；点击后分别 E29/E03读取，不改变成员 |
| `total` / `next_cursor` | 全部去重匹配告警数/下一页；空页不表示告警安全 |
| `scope.source_alert_id/source_material_id/source_event_time/source_namespace` | 本次实际起点告警、最新材料、真实时间及来源范围 |
| `scope.time_from/time_to/window_basis` | 实际查询窗口及默认回看或显式窗口口径 |
| `scope.unavailable_rules` | 起点缺少所需对象或有效战术，哪些规则无法使用 |
| `scope.excluded_objects` | 本功能不支持的对象、缺少/非法算法或值的哈希对象及原因 |
| `observed_at` | 本次数据库只读一致快照时间；跨请求不冻结结果集 |

## 调用与跳转

1. 从告警详情取真实 `alert_id`，调用 E70。
2. 显示候选名称、等级、时间、当前判定/处理状态和 `matched_rules`；展开 `matches` 显示具体依据。
3. 点击候选 `alert.id` → E28告警详情；点击来源 → E31 `/alerts/{alert_id}/materials/{material_id}`。这两个 ID 必须来自同一 `seed` 或 `candidate`，不能混用。
4. 用户阅读理由后才决定反馈；E48单条或E49明确勾选批量提交时，重新取各目标当前 `row_version`。不因同IP或同哈希自动复制判定。

```http
GET /api/v1/socai2/alerts/<真实告警UUID>/review-candidates?limit=5
```

没有候选时 `items:[]`、`total:0`、`next_cursor:null`，仍返回scope说明窗口及规则可用情况。完整成功/空态结构及错误示例见 Swagger E70。

| 错误 | 调用方处理 |
| --- | --- |
| 404 `alert_review_source_not_found` | 告警不存在或不在当前租户，检查 ID |
| 409 `alert_review_cursor_scope_changed` | 起点材料/对象/战术或时间范围变化；清空游标重读 |
| 422 `alert_review_explicit_window_required` | 起点时间未知或默认窗口无法生成；明确时间范围 |
| 422 `invalid_alert_review_cursor` | 游标格式不合法，不自行拼接 |
| 422 字段校验 / `alert_review_query_parameter_not_supported` | 处理无时区、单边/逆向时间窗、非法limit、未知或重复查询参数 |
| 503 `invalid_alert_review_configuration` / `socai2_page_read_not_enabled` | 修正服务配置，不能将失败显示成无候选 |

本次实现 F03-05 的专项候选查询，人工反馈沿用 E48/E49。详情区域“同主机最近7条”由[E71](alert-host-http.md)独立提供，不要求战术相同；E30一般对象关联和E66案件探索保持各自原口径。没有新增表、写入、自动调查或AI对话。

本轮实际验证与发布状态见[验收记录](../operations/evidence/alert-review-20261113-01/README.md)。
