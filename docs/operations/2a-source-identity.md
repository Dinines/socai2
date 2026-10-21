# 2A-01 上游告警独立身份

2026-10-20。上一轮已建议独立保存上游告警；用户继续要求推进，本批采用此前推荐合同实施。范围：同一租户/来源/连接器下，稳定上游告警UUID表示同一条告警；不同UUID表示独立告警，特征相同仍各自保存，按原实体/战术关联。一次新发生必须提供自己的稳定UUID，不能每次重试随机生成，也不把来源事件列表当告警ID。

实施前合同：新HTTP入口要求显式id；服务生成`source-v1`身份标记与`source_alert_id`，调用者不能覆盖。Kafka旧消息无标记时仍为`legacy-v1`，指纹/canonical不变。新标记的去重与PG身份由租户、来源、connector_id和source_alert_id计算，标题、时间等内容不改变该身份。连接器不同或来源不同不串用身份。

独立告警原文、时间、external_id按行保留；首次材料不可被重投覆盖。身份及incident_id写入现有enrichment_data的项目命名空间，API详情显式交付身份/关系/来源字段，不对旧行补写。无SQL变更。新身份duplicate须核PG存在，数据库不可用不能伪称durable duplicate。

验收：新ID同特征→两行且同incident；真重投→原行/来源/关系稳定；另一租户/来源/连接器隔离；缺ID/未知身份拒绝；旧消息ID与原回执一致；单个测试缓存键丢失后的重投及服务重启后仍可读取独立材料/关联。consumer先升级，再升级publisher；恢复先停输入，保留消息/行，不让旧consumer处理新身份消息。

只验所列小批路径，不启模型/自动分诊/响应，不外推完整缓存丢失重建、并发或风险累计幂等。完成后记录真实值与限制。

## 已执行与实际结果

本批限定验收通过，见[机器回执](2a-source-identity.json)。API/Fusion各自按锁环境运行34/61项相关测试，共95项；同一模型合同在两环境分别验证，替身与真实服务证据分开。原批处理sink测试的3个替身因缺新可选属性首次失败，已补兼容默认值后通过，未删除测试。原API detail字段集断言增加本批要求的4个字段，差异已记录。

| 输入→调用 | 最终值与关系 |
| --- | --- |
| 两个UUID、特征相同、时间相差1分钟 | 两个canonical ID、两行PG，分别保留raw_event/event_time/external_id；API显示同一fusion_incident_id |
| 同一条原样重投 | duplicate，不增PG行，原材料/来源列表不变 |
| 同UUID，另一source或connector_id | canonical ID分别不同，不串用来源命名空间；可按实体/战术关联 |
| 同形告警，另一tenant | canonical及incident隔离，互读404，伪造tenant403 |
| 新UUID不同实体，或仅改战术的另一新UUID | 独立行、不同incident，不依赖改title来避开原指纹 |
| 清除一个自有dedup键后重投 | PG仍duplicate，原行不变；共同incident仍4成员，列表/last_seen保持 |
| 精确重投原2A旧告警，经HTTP及直接Kafka分别发送 | 均保持原canonical ID；没有转换或回写旧行 |
| HTTP缺稳定id或未知identity_version | 422、无broker offset变化；无身份401 |
| broker未知identity_version | 真实PG DLQ，topic/partition/offset、tenant及来源可回查 |
| API/Fusion分别重启 | 对11次已验投递的API回查保持原文hash、时间与持久关联ID，无重新提交 |

共12条broker投递（11条告警投递、1条非法身份DLQ），新增7条独立告警；运行27项、重启后11项及停用key后3项HTTP验收检查，共41项。12条此前告警的不可变材料摘要保持，现共19条合成告警。134份SQL/迁移记录不变，无DDL；仅重建并定向重启API/Fusion，其余34容器及18卷保持。3枚测试key已停用并返回401；网关成功计数与1G相同，未调用模型或厂商，费用unknown。

实际ID、两条原文及关联、raw/fused坐标、镜像与源码指纹均在JSON和[来源差异层](../handoff/2a-identity-source-manifest.json)。原1F、首次2A错误回执及2A成员修复不改写；本文件是其后续结果。

## 兼容与运行合同

新入口要求调用方在`id`提供稳定UUID；`identity_version`与`source_alert_id`由服务设置，不需要调用方提交。`source`与`connector_id`须稳定，同一条告警重试保持相同id，新发生用新id。同id的新正文不覆盖首次材料；需要修订/补充的场景另走明确的数据合同，不能靠重试替换事实。

HTTP在发布前用认证tenant、原legacy canonical、connector及已记录input UUID检查精确旧投递，命中时保持legacy身份；PG不可用返回503且未发布。该桥接不声称恢复旧200条来源列表上限之外的输入、被折叠丢失的原文，或识别任意修改过的旧payload。未标记的Kafka旧消息按legacy算法处理；未知身份拒绝。发布超时仍为unconfirmed，先检查回执/结果，不盲目重发。

`enrichment_data.socai2_fusion`保存只写首条的identity与incident_id，API详情以`fusion_identity`、`fusion_incident_id`、`source_event_ids`和`external_id`交付。未改旧行，旧行没有元数据时返回null；后续增强写入须保留此命名空间。PG插入/查询失败不当作新身份duplicate已持久化；此故障分支只有替身验收，未对共享PG注入真实故障。

消费者先部署，发布者后部署，启用见[Compose叠加层](../../deploy/aisoc21/compose.identity-2a.yml)。通用升级需受控停止新输入并核对backlog，再按顺序切换；不能让旧consumer读source-v1。回退先停新输入、保留支持新消息的consumer直至队列确认处理完，不改写已存ID或重新向旧合同投递已受理消息。旧镜像保留，操作见[运行说明](../../deploy/aisoc21/README.md)。

**当前2A限定的正常/重投/身份/材料/关联及旧样本兼容已通过，下一单项2B风险与处理规则。** 不宣称完整Redis丢失恢复、并发、自然窗口长测或所有风险支路幂等；这些不是本批已验结果。自动分诊、记忆写回、知识消费及真实响应仍关闭。
