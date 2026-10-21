# 09 UEBA：从行为特征到异常信号

> 用途：固定上游源码与历史证据分析（2026-10-20对齐）。本轮消费已有UEBA/行为信号作为上下文，不建设独立UEBA生产或行为基线训练；下文为上游能力分析。 当前职责见[范围](../operations/alert-processing-scope.md)，阶段退出见[路线](../operations/service-roadmap.md)，执行批次见[依赖计划](../operations/dependency-migration-plan.md)。

返回[总入口](README.md)或[模块总览](01-system-map.md)。模块编号 **M13**；对应正常链路中的并行行为分析支路，不是 Case 调查结束后才使用的附属功能。

<a id="m13"></a>

## M13.1 职责、入口与上下游

UEBA 回答“实体现在的行为是否偏离自己或同类的历史”，不是直接判断恶意，也不是 LLM。它独立消费事件，形成行为基线和异常；Fusion 可以消费异常给后续告警加权，调查可以读取基线作为证据上下文。

```text
采集后的规范化事件 aisoc.raw_events
  ├→ Fusion 单事件/窗口检测 → 告警
  └→ UEBA 特征提取 → 旧个人基线评分 → 更新个人基线
                    + 可选 peer-group 对照
                    → PG 异常 → ueba.anomalies
                                   ↓
                         Fusion 实体异常缓存
                                   ↓
                         同实体后续告警加权
```

旧分析写的 `security.events` 默认输入与“没有特征桥接”已过时：当前 [config.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/ueba/app/core/config.py) 默认输入 `aisoc.raw_events`，并有 [feature_extraction.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/ueba/app/services/feature_extraction.py)。本次是源码复核，没有在 20 启动 UEBA 或证明真实事件已跑过这条支路。

## M13.2 输入模型与实体归一

两类输入：当前接入 envelope `tenant_id + ocsf_event`，以及原预提取的 `tenant_id/entity_type/entity_id/event_type/features` 形态。

| 输入组 | 当前处理 | 对后续结果的影响 |
| --- | --- | --- |
| tenant | 解析 UUID，按 tenant/实体读取和更新 | 无效 tenant 跳过；作用域仍需由可信入口保证 |
| 原始字段 | 从 OCSF、raw_data JSON、nested raw_event 恢复扁平视图 | connector 已归一字段优先，避免被厂商原值覆盖 |
| 实体 | 优先 user，再 device/host，最后 src IP | 当前普通事件通常选一个主实体，不是同时给全部实体建基线 |
| 时间 | epoch 秒/毫秒或 ISO 时间 | 派生小时/星期；当前实现不是自动理解业务时区 |
| 来源 | source_event_id 等 | 用于异常回链；Kafka 输出是否完整携带要独立核对 |
| peer_group | 调用方提供 group ID | 不会自动用 HR/组织关系发现同岗群体 |

HTTP API 支持 user/device/ip/service_account/ai_agent/mcp_server 等类型；普通 OCSF 提取路径的默认实体选择不意味着已自动识别所有非人实体。账号重名、大小写、域前缀、DHCP/NAT 和账号改名都会影响归一，需要在目标模型中明确。

## M13.3 特征工程

当前可从单事件派生：`hour_of_day/day_of_week/is_failure/severity_id`，以及 bytes、duration、file/request/response size、packet count 等允许字段。bool 不直接当任意浮点特征；缺身份或没有可提取特征可正常跳过。

关键区别：

- 一条失败登录可产生 `is_failure=1`，不是“十分钟失败次数”。频率必须经过窗口聚合，不能从单事件捏造。
- `hour_of_day` 和 weekday 被当普通数值，23 点与 0 点的周期距离没有专门编码；这是一种统计取舍，不能据此宣称具备完整时间行为模型。
- 数值存在不等于语义可比较。bytes 的单位、duration 秒/毫秒、severity_id 来源尺度都影响基线。
- 冷启动、字段缺失和零方差不是“正常”；它们表示未能评分或覆盖不足。

## M13.4 个人基线与异常评分

源码：[baseline.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/ueba/app/services/baseline.py)、[scoring.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/ueba/app/services/scoring.py)。

每个 tenant/entity_type/entity_id 的 `feature_stats` 保存 mean/M2/std/count。Welford 在线更新的主要关系：

```text
n' = n + 1
mean' = mean + (x - mean)/n'
M2' = M2 + (x - mean) × (x - mean')
std = sqrt(M2/(n'-1))
z = abs(x-mean)/std
composite = min(sqrt(sum(valid_z²)), 10)
```

ScoringService 先按旧个人基线评分，再更新该实体。样本不足（默认 30）、没有特征历史或 std 接近 0，z_score 为 `None`；复合分跳过这些项，日志记录不可评分特征。全不可评分时内部复合分为 0、不会产生 anomaly，不能对外解释成已证明安全。

baseline_window_days 默认 30，但当前 `update` 是累计 Welford，更新 window_end；本次检查没有看到按天淘汰老样本的真正滑动窗口重算。因此不能把“配置 30 天”写成已严格只使用最近 30 天样本。

当前 Welford helper 返回新的内部字典，避免 JSONB 原地修改不被 ORM 跟踪的旧问题。需要验证的是数据库 count/mean 实际增长，不是消费者日志显示 processed。

## M13.5 同类群体与合成风险

[peer_group.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/ueba/app/services/peer_group.py) 按外部提供的 group ID 维护统计并计算 peer deviation。当前 Kafka 路径先更新 group，再执行评分，所以 peer 分布可能已包含当前观测；个人基线则先评分后更新。二者时序不相同。

peer 结果存在时 composite 取 `(personal + peer)/2`。risk 默认区间：≥6 critical、≥4 high、≥anomaly_threshold medium，其余 low；默认 anomaly_threshold=3。达到阈值才保存异常。

需特别核对两处语义：group 的 member_count 由特征观测 count 推导，不一定是独立成员数；group ID 是表主键，虽查询含 tenant，跨租户使用相同裸 ID 的存储冲突仍需定向验证。移植不要从变量名反推真实 HR 群体规模或全租户唯一性。

## M13.6 存储、发布和 API

模型：[models/ueba.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/ueba/app/models/ueba.py)。三张核心表为 `ueba_entity_baselines`、`ueba_peer_groups`、`ueba_anomalies`。

消费者在 PG 事务中更新基线/群体并保存达阈值异常，事务退出后通过 `send_and_wait` 发布 anomaly。Kafka 消费当前配置 `enable_auto_commit=True`。这不是 PG Outbox，基线更新、anomaly 和 Kafka offset/发布没有跨系统原子保证。

anomaly 消息包含 anomaly ID、tenant、实体、event_type、score、risk、逐特征值/均值/std/z、peer 及 detected_at。PG 有 source_event_id，当前构造的 Kafka payload 未包含它；需要完整回链时不能仅依赖消息内容。

API：[routes.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/ueba/app/api/routes.py)，带服务认证与租户 scope：

| 路由 | 输入/输出 | 业务用途 |
| --- | --- | --- |
| `POST /api/v1/ueba/score` | 显式行为特征 → anomaly 或 null | 直接评分入口；不把 null 当完整安全证明 |
| `GET .../anomalies` | 实体/过滤 → 异常列表 | 调查和分析员读取 |
| `PATCH .../anomalies/{id}/acknowledge` | 异常 ID → acknowledged 状态 | 已读/确认不等于误报或风险消除 |
| `GET .../baselines` | 实体 → baseline | 检查样本和历史分布 |
| `GET .../peer-groups` | 群体 → stats | 查看群体对照；解释 member_count 语义 |

main 的 health/readiness 检查消费者仍 attached，优于固定 200；但 attached 不证明有输入、样本增长或异常输出。

## M13.7 与 Fusion/调查的对接

[ueba_signal.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/fusion/app/services/ueba_signal.py) 按 tenant/entity type/entity ID 保存最新风险与分数，默认 TTL 86,400 秒；告警用 username、hostname、src/dst IP 查最大信号，更新 anomaly/confidence 并增加解释因子。非人实体类型与告警实体映射是否匹配要单独检查。

异常先到、告警后到才能直接获得这个缓存增强。当前不是“UEBA 一异常就主动创建 Alert”，也未证明自动回算既有告警。异步消费者时序不同会改变首次融合时可见的信号；调查读取历史 anomaly 是另一条补充路线。

## M13.8 测试、缺口与采用

| 测试场景 | 输入 → 中间 → 最终判据 | 测试源码 |
| --- | --- | --- |
| 主输入接线 | 接入 OCSF、nested vendor fields → entity/features → 单位、字段优先和来源正确 | `test_feature_extraction.py` |
| 冷启动/零方差 | 少量或常数样本 → z=None → 不冒充已评为正常 | `test_baseline_scoring.py` |
| 统计增长 | 一组已知不同数值 → Welford 结果 → count/mean/std 正确且原字典不被改写 | 同上；真 PG 持久增长另验 |
| 非人实体 | 显式 service/AI/MCP 类型 → 评分/读取 → 作用域和类型接受正确 | `test_non_human_entities.py` |
| 跨租户 | 同 entity/group 名 → 分别存取 → 无串读，裸 group ID 冲突需额外定向核对 | UEBA `test_tenant_scope.py` |
| 联动 Fusion | 固定 anomaly → 缓存 → 后到告警解释/分数提高，其他 tenant 不变 | Fusion UEBA 信号相关测试需定位并执行选定节点 |

本轮没有运行 UEBA 测试或建立样本基线。移植时优先复用目标已有 UEBA，只引入必要特征、解释字段和 Provider 查询；不把参考 Redis/Kafka 接线直接替换目标 HTTP/权威存储合同。高并发和通用重建后置，冷启动诚实性、来源引用、真实新发生与租户隔离是本批正确性。

## M13.9 CORE 行为基线：另一条实际路径

不能把本章独立服务误认为上游唯一行为分析。新版 [Fusion baselines.py](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/fusion/app/services/baselines.py) 将部分行为信号放进 CORE，配合 [FirstSeenStore](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/fusion/app/services/first_seen.py) 在检测前生成规则字段。

| 对比 | CORE 行为模块 | 独立 UEBA 服务 |
| --- | --- | --- |
| 输入入口 | Fusion `DetectionEngine.evaluate_async` 调用绑定的 store | Kafka 规范化事件或 HTTP score |
| 关注内容 | principal 的属性/动作稀有度、小时量、自身/peer volume 等 typed signals | 单事件数值特征的个人 Welford 和 peer 偏离 |
| 存储 | Redis 计数/分布；有最大 distinct 等限制 | PostgreSQL baseline/group/anomaly |
| 冷启动 | 默认 principal 至少 20 observations 等要求，不足不输出相应 key | 默认至少 30 feature samples 等要求，z=None |
| 输出 | derived fields，供规则和 threat condition 组合 | 达阈值异常，可进入 Fusion UEBA signal cache |
| 告警生成 | 规则消费字段后才可能命中 | anomaly 不自动反向新建 Alert |
| 部署 | CORE 可绑定，不需要独立 UEBA 容器 | Compose full profile；20 未启用 |

CORE baseline 的 TTL 默认 90 天；这不自动证明具备严格逐样本滑动重算。稀有度接近 1 表示历史上少见，不等于恶意概率。未读到状态不输出字段，不能填 0 后冒充常见。

移植时先确定已有目标 UEBA/first-seen/行为 Provider 哪个负责同一信号，避免为兼容参考引入两份权威基线、双重计分。Fusion `test_baselines.py` 与独立服务同名测试分别属于不同实现，源码索引会分别列出。
