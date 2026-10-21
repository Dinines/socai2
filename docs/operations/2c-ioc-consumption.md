# 2C-01 历史IOC查询与告警持久消费

范围：从用户授权复用的旧SOCAI报告提取一个有日期/来源的历史指标，只放入独立测试tenant现有IOC表；使用Fusion实际查询、fused消息、PG/API告警元数据验证命中/无匹配/依赖失败及重启后冻结结果。不导入整个知识库，不建设采集/检测或新库存，不启Go增强或外部信誉渠道，不据历史命中提升评分。

改动前问题：现有matcher将连接/查询失败返回[]，与合法无匹配相同；sink不保存本地IOC证据。保留原match列表接口兼容，新消费使用带状态的lookup；结果携带查询范围/时间、IOC ID/来源引用/观测时间、衰减及外部未查询状态。测试仅操作标记数据，旧材料和回执保留。

验收：真实HTTP→Kafka→Fusion→PG→API，历史命中与另租户/无匹配分开；过期/停用不匹配；不可达依赖在独立探针进程验证不伪造空结果及恢复；重投和重启不改首次证据。资产/身份/漏洞/历史日志在后续2C-02接入。2C-01限定验收通过，整个2C尚未完成。实际结果见[JSON](2c-ioc-consumption.json)，来源见[差异清单](../handoff/2c-ioc-source-manifest.json)及[补丁](../../deploy/aisoc21/patches/2c-ioc-consumption.patch)。下一单项为2C-02已有资产/身份/漏洞及历史材料读取与消费。

## 实际数据与结果

历史指标来自用户提供的`../SOCAI/knowledge/2023/3cx-software-supply-chain-compromise.md`缓存，原报告发布日期2023-04-20；仅提取Table2中`journalide[.]org`于2022-04-08的历史观测。保留缓存文件SHA256、报告URL、原行及解混淆规则，见[来源样例](../../tests/porting/fixtures/historical-ioc-2c.json)。这不是2026年实时恶意信誉证明；不向该域名发起连接。

指标在独立tenant A=`b2696d2f-7632-5984-a5cd-119ecf38e628`的现有PG表中保存，IOC ID=`1faa0eb5-3aab-525c-a56e-48a1084e8dbb`，first_seen/last_seen均保留2022-04-08。confidence50只是原表默认值，原报告未提供数值概率；context记录该限制及来源hash。另有一条明确标记的合成过期指标用于边界。使用受控fixture SQL保留历史时间，不宣称IOC CRUD API已验。

| 输入/路径 | 实际结果 |
| --- | --- |
| 历史domain告警 → HTTP/Kafka/Fusion真实PG查询 | matched，携带IOC ID/报告引用/观测时间/tenant范围；约1656天、90天半衰期，effective_confidence四舍五入0.0且weak=true |
| A的不存在域名 | no_match，表示本租户存储确实查询过且未命中；外部渠道not_configured |
| B的相同历史域名 | no_match，不读取A的指标；B读A的告警404 |
| 已过期、已停用指标的新告警 | 均no_match，原过滤条件实际生效 |
| 指标停用后重投首次同UUID | duplicate，PG/API保留首次matched/checked_at/引用，不改写为当前no_match；新发生独立保存 |
| 独立探针闭合端口 → 实际PG | unavailable/database_unavailable与合法no_match分开；修复原永久丢弃DSN行为，探针保留可重试配置，切回真实PG后恢复；未停止共享PG |
| API/Fusion重启回查 | 6条投递引用的冻结IOC结果、原材料及incident关系均保持 |

共6次真实投递、5条新告警、21项HTTP检查（投递与查询13、重启6、停用key2），消息partition/offset/hash、API结果和PG关系在JSON逐项记录。62项相关测试通过（Fusion43/API19），3项新回归在旧实现均失败；首次新单元样例漏填FusedAlert必填decision的失败已保留，修正后通过，未改业务判据。两处原测试只补matcher.lookup接口或新增响应字段，原断言保留。

## 消费合同

生产Fusion调用新的`lookup()`，明确返回matched/no_match/unavailable/not_requested；旧`match()`列表接口保留兼容，其失败仍为空列表，不能拿它证明查询成功。查询连接/命令限3秒，连接失败不再永久删除DSN；并发建池/负载未验。

真实fused消息在`enrichments.ioc_lookup`交付证据，sink将同一观察首次写入`alerts.enrichment_data.socai2_fusion.ioc_lookup`，身份与incident字段保留。认证API详情新增`fusion_ioc_lookup`，重投不覆盖；旧告警该字段为null，含义是没有已记录观察，不能解读成安全/无匹配。

历史本地命中没有接入外部provider加权，TI contribution保持原-0.3，因子文字明确“tenant IOC match; not used in confidence weighting”；无匹配/不可用文字也区分来源及未查状态。没有把历史弱参考标成VirusTotal/实时信誉命中，没有调整权重或重算历史分数。源观测时间、当前checked_at和导入时间分别保留。

## 部署与保留

当前API=`sha256:53dd54d02169e41fc5d1ed21322c0d66594991d65712f9e0ad0122020ca3eda1`，Fusion=`sha256:106b290cd77ab08f8dfe84563b56e248235012c53ad38d0f639b9b4f52dbccd5`。在policy层后加[IOC层](../../deploy/aisoc21/compose.ioc-2c.yml)，完整九层命令见[操作说明](../../deploy/aisoc21/README.md#当前apifusion2c-01本地ioc证据)。仅Fusion覆盖3项环境值：开启本地fuse enrichment/tenant匹配，外部服务URL为空；原私有env保持，无DDL/新依赖/Go服务。

只更新/定向重启API与Fusion，25条旧告警材料hash、其他34容器/18卷及134迁移保持；新增5行总30行，2枚测试key已停用401，2条标记IOC均停用但保留，Kafka lag0，网关计数不增。Agents/Actions及自动worker未动，无模型/厂商动作，费用unknown。

回退先停新输入、核队列，再用保留policy API/risk Fusion镜像；关闭IOC层的配置覆盖，保留首次证据及指标行，不重发原消息或回写历史判断。批次prepare/deploy/acceptance/verify/finish已完成，不能重跑旧检查点；新验收另建tenant/标记。

## 尚未覆盖

- 真正的共享PG故障对Fusion整链的影响、并发/负载、坏数据转换和完整缓存丢失未验；失败/恢复是独立SDK探针，失败结果经enricher/sink的传播另有单元验证。
- 不代表完整2C通过：资产/身份/漏洞、已有UEBA、历史日志仍待2C-02；没有新建这些生产/采集系统。
- 未接调查LLM消费或Agents的旧enrich_ioc工具。后者仍指向未部署的Go增强服务，不能用Fusion本地查询通过替它背书；知识检索/调查另验。
- IOC记录ID/来源URL已进入冻结告警；文档缓存hash在原指标context/来源清单中，不宣称所有外部来源都已验真实性或时效。未重新验证历史域名目前归属。
- Fusion租户ML状态接口认证503、风险持久账本和自动分诊限制继续保留。

