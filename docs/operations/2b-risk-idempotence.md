# 2B-01 风险累计验收

范围：核对现有Fusion评分组成及运行RBA配置，复现并修复同一规范告警ID重复增加实体风险的问题。只用独立测试tenant和实体，不改已有告警、权重、检测或自动分诊开关。

验收：真实HTTP→Kafka→Fusion→PG/API投递及移除本批单个去重key后的重投；风险hash、贡献、计数、关联和持久材料保持；直接调用当前源码连接真实Redis验证并发、超过50条展示上限、tenant隔离和TTL。先保留修复前结果，再使用新样例验证修复。相关上游测试保留。

方案：以实体hash和完整贡献ID集合为WATCH/MULTI事务边界，累计、贡献标记、队列和首次promotion一起提交；失败不提前标记已贡献。重复输入不刷新TTL或last_seen。原hash最后50条可见贡献作为迁移兼容，旧的不可见贡献无法追溯，不回写历史分数。

边界：集合随实体活跃期保留，实体连续无新告警达到现有24小时TTL后过期；持续活跃实体的集合会增长，需另做容量测量。完整Redis丢失后的重建、持久风险账本及跨实体全有或全无不在本批。处理规则版本/实际自动分诊消费仍属2B后续，不能用预览通过代替消费通过。

## 实际结果

2B-01限定验收通过，整个2B仍未完成。结构化回执见[JSON](2b-risk-idempotence.json)，源码差异见[清单](../handoff/2b-risk-source-manifest.json)和[补丁](../../deploy/aisoc21/patches/2b-entity-risk.patch)。历史回执、旧分数和材料均保留。

| 检查 | 实际输入 → 中间产品 → 结果 |
| --- | --- |
| 修复前真实链 | high、risk_score0.5、同UUID → 首次/warm/cold三次HTTP及Kafka → 首次30分/1次；warm不变；移除本批dedup key后接近60分/2次，PG仍1行 |
| 修复后真实链 | 新UUID/新实体，同样三次投递 → Kafka坐标、PG/API材料、RBA hash → 始终30分/1次；同一输入另一tenant独立30分/1次，跨tenant读404 |
| 真实Redis并发 | 同一告警32次并发 + 64条不同告警并发 → 完整贡献集合65、累计65、high1/low64、约212分、首次promotion返回1次；仅最后50条ID和25条详情显示，重投最早ID仍不变 |
| TTL与兼容 | 重投不刷新last_seen/TTL；独立测试engine使用2秒窗口 → hash/seen都过期；缺seen的旧hash仅用仍可见贡献兼容并补集合 |
| 相关测试 | 保留原断言，扩展Redis测试替身的事务接口；5项回归在旧实现4失败/1通过，修复后原entity_risk/confidence/process_endpoint及5项回归共40通过 |
| 部署与恢复 | 仅更新/重启Fusion，env、挂载和API镜像保持 → 58个运行app文件及52项锁依赖匹配，风险hash/config及3条API材料重启回查不变 |
| 保留与收尾 | 19条旧告警材料hash不变，新增3行，总22行；134迁移、其他35容器/18卷保持；7次受理及相关回查共20项HTTP检查，2测试key已停用401，Kafka三分区lag0，网关调用数不增 |

本批真实HTTP样例tenant为`d6b1cbd2-cc2d-5e13-81e8-8459462282dd`；最终告警ID、消息partition/offset/hash、incident及风险变化逐项在JSON的deliveries记录。风险层promotion是原版Redis标记，不等于新建持久Case。

## 分数分别表示什么

同一实际样例的Fusion anomaly=0.15、priority=0.85；两值与固定源码启发式一致。confidence七因子为`0.5 + Σ(weight × contribution) = 0.572`，label=medium，API持久confidence取整为57。RBA是实体累计点数：high权重20 × (1+0.5)=30。API详情的存储priority仍是50；Fusion的0—1优先级与API按上下文动态排序的0—1000分不是同一个字段。本批没有用一个分值替代另一个。

真实RBA配置：启用，threshold80，idle TTL86400秒，半衰期14400秒，critical/high/medium/low/info权重40/20/8/3/1，top100；配置规范JSON SHA256为`4dfa5aceadbca627de38080c479d4661f5f4df9b35f1e658e22d6baf5cd61426`。源码hash及镜像对应见清单；配置未变，不重算历史分数。无TI/UEBA/memory消费，样例中的“no TI match”只是原版缺材料默认值，不能解释为真实TI查询后无命中。

`/ml/status`实际返回503：Fusion租户认证材料尚未配置，保留原版拒绝，未因测试放宽认证。因而不声称已直接观察运行模型训练状态。该项及处理规则实际采用版本/消费路径是后续2B-02的检查输入；Agents自动worker仍关闭，不能用规则预览代表真实自动分诊。

## 限制与运行

当前Fusion为`sha256:6ff2a029253adc4301ee8e645ae9fecea218bd592078caf70c94b7de1b3fa3fd`。正常启动需在identity层之后再加[风险层](../../deploy/aisoc21/compose.risk-2b.yml)，完整命令见[操作说明](../../deploy/aisoc21/README.md#当前fusion2b-01风险累计)。无DDL、无新增依赖、评分权重未改。

风险仍为Redis状态，没有持久贡献账本；完整缓存丢失、持续活跃实体集合容量、自然24小时后的跨窗重投、跨实体全有或全无、队列读取时衰减及promotion队列时效未验。可见旧50条之外的历史贡献不能恢复，旧的重复分数不改写。WATCH最多重试32次；原Fusion对RBA失败仍fail-soft，不能把本批理解为风险失败后的持久重试保证。真实Redis的2秒TTL探针只影响本批fixture tenant，也会过期其测试队列索引，不作为队列完整性验收。

首次缺来源引用的探针未保存实际HTTP状态/ack，保留原输入且后续核PG无该样例行；已修正后在main/独立检查点运行。首次测试收集/路径错误及ML状态503的收尾中断均保留，未覆盖失败回执。

回退前停新输入并核消费进度，保留新seen集合和告警；退回identity镜像会恢复重复加分缺陷，不回写/减去已冻结分数。批次prepare/deploy/acceptance/verify/finish均有状态，完成后不直接重跑；新批次使用新tenant/标记。

**下一单项：2B-02处理规则配置与实际运行版本、消费及恢复边界。** 本批无模型/厂商动作，费用unknown。
