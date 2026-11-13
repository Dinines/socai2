# 列表查询设计与合同增量

状态：2026-11-13负责人已确认仅HTTP封套新增两个字段，尚未实施。前置的[对外HTTP边界重构](../archive/2026-11-13-separate-investigation-http/validation.md)已完成两端发布、限定独审及归档；本项查询功能尚未实施。

## 1 范围与用途
F01-02/03/09、F06-01/07、F09-03/08的完整筛选和排序。保留E26告警、E27事件、E02调查列表；每页限制仍1–50，默认20。列选择、导出已加载记录由调用方处理；完整CSV导出和统一归并统计另批实施。

## 2 参数及实际语义

| 主体 | 筛选 | 排序 |
| --- | --- | --- |
| 告警 | `q`名称包含/精确UUID；`severity`、`handling_status`、`owner_id`、`assignment_state`；`time_from/time_to`按真实`event_time` | `sort_by=ingested_at/event_time/severity`，默认ingested_at；`sort_order=asc/desc`，默认desc |
| 事件 | 同样的名称/UUID、状态、负责人、分配状态；severity按人工覆盖优先、否则成员最大等级；时间窗口内至少有一条成员告警真实event_time | `created_at/last_activity_at/severity`，默认created_at；last_activity_at为成员最晚真实发生时间 |
| Case | 原q、状态、等级、负责人、分配状态、metric、classification全部保留；time_from/time_to按业务更新时间 | `business_updated_at/created_at/severity`，默认business_updated_at；升/降序均支持 |

时间参数必须含时区，采用`[from,to)`，可单边；起点不得晚于或等于终点。无真实告警时间的数据不会用入库时间补齐；在明确时间筛选时不命中。等级info<low<medium<high<critical，未知等级/排序时间排最后。相同排序值按同方向UUID决胜。分配给我使用现有owner_id传实际登录用户UUID，不以显示姓名匹配。搜索中的%和_按普通字符处理。

## 3 需要负责人确认的告警交接增量

依据根AGENTS：“确需调整这些合同时，先列出原因、受影响字段与页面、数据兼容方案，取得项目负责人明确确认并记录范围。”

| 新增返回字段 | 类型及含义 | 原因 |
| --- | --- | --- |
| `filtered_total` | 非负整数，本次全部筛选命中数，不受当前页/游标影响；无筛选时等于total | 让页面知道搜索结果总数，同时不改变原total全租户总数的含义 |
| `next_cursor` | 字符串或null，下一页的不透明游标；null表示到末页 | 绑定筛选和实际排序值，防止把UUID顺序当成时间/等级顺序 |

受影响页面为告警列表及事件列表。原`items`中的facts、owner_name、derived、material、triage、feedback及关联URL不改；total/overall_stats语义不改、默认排序不改；原`next_before_id/before_id`在不使用新增查询条件时继续可用。新增查询使用cursor；不混用cursor与before_id，也不将before_id用于新增筛选/排序，混用返回422。旧调用方可以继续原参数和字段；对JSON字段严格拒绝未知键的调用方需接收上述两键。

Case无需增加返回字段，原total已经表示筛选总数，next_cursor已有。新参数均可选；旧默认查询的游标指纹和v1结构保留，新排序/日期走新的内部游标版本，旧请求不因新增默认字段导致旧游标失效。

## 4 实现与直接验收

在现有只读快照中计算筛选命中数、当前页与整体统计；不写数据库、不触发分析。游标保存当前排序值、UUID及租户/主体/条件/排序指纹，改变条件必须从第一页开始；非法或跨条件游标422。每页是实时读取快照，不承诺在两次请求间有业务修改时仍提供整个查询的冻结快照。

使用独立新合成批次：名称字面匹配、等级/状态/负责人、真实时间窗口、同值排序和未知值、正反向翻页不漏重、条件变更拒绝、事件覆盖等级与成员时间、默认旧参数/旧Case游标兼容；直接HTTP及PG结果核对，读取前后目标行保持。复用既有回归，只补受影响路径；不调用模型，不做权限专项、全仓回归或性能工程。

## 5 确认记录
- 2026-11-13负责人回复“确认，按这个方案继续”：仅告警/事件HTTP返回JSON新增 `filtered_total` 和 `next_cursor`，数据库表结构、每条记录字段及旧接口调用保持；不扩大为其他告警合同调整。
- 同日负责人强调整个对外HTTP与内部调查调用分开，内部必要HTTP保留；先行边界重构在 `separate-investigation-http` 维护，本项不复制该任务树。
