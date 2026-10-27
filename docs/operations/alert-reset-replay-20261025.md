# 2026-10-25 告警清理与20/21重跑

本批用户明确授权清理192.168.1.21 socai2告警/调查业务数据，保留用户、资产、规则、连接器、配置和ClickHouse；随后从20少量告警经Kafka重跑，比较流程与结论，并按已确认合同在最新告警UI取数。20只读。需要修改本地业务源码时先提供具体差异供用户确认；工具保存及清理本身已授权。此前仅规划/不清历史的约束不作为本批清理阻碍，旧回执不改写为通过。

## 可复用入口

- [清理脚本](../../tools/testdata/reset_socai2.py)
- [预览、执行和失败处理命令](../../tools/testdata/reset-socai2.md)
- [已确认告警页面数据合同](../design/alert-ui-data-contract.md)
- [本批OpenSpec](../../openspec/changes/archive/2026-10-25-reset-replay-alert-flow-20261025/tasks.md)

默认预览；显式`--apply --confirm-target 192.168.1.21/socai2`才清理。每次使用新私有回执目录，禁止覆盖旧证据。脚本及说明未提交/推送，不修改业务实现。

## 已完成：清理

2026-10-25 11:28北京时间续接完成。PG清理31张显式业务表，原非空项目如下：

| 项目 | 清理前 | 清理后 |
| --- | ---: | ---: |
| alerts | 119 | 0 |
| aisoc_cases | 9 | 0 |
| investigation_runs | 88 | 0 |
| investigation_events | 447 | 0 |
| investigation_artifacts | 511 | 0 |
| aisoc_run_costs | 57 | 0 |
| socai2_triage_budget_reservations | 24 | 0 |
| aisoc_shadow_decisions | 32 | 0 |
| aisoc_analyst_feedback | 5 | 0 |
| aisoc_dead_letters | 3 | 0 |
| alert_asset_correlations | 1 | 0 |

Kafka 86个`socai2.`前缀topic的279条既有消息已备份并删除，topic/组/配置保留，offset不归零。Redis DB9的13个Fusion业务key已清理，其余选定DB当时为空；DB12共享TI/enrichment保留。Neo4j47个纯业务图节点已清理，身份图节点/关系指纹一致。ClickHouse、OpenSearch、Qdrant不清理。

全部非清理PG表的行数/内容指纹一致，包括37用户、2资产及其配置关系；用户/资产/规则/连接器/策略/租户技能/其引用评测基线、审计和知识情报保持。API、Fusion、UEBA、Agents、Actions恢复原运行状态。

私有备份与阶段回执：21 `/opt/sting-aisoc-socai2/private/test-resets/20261025-reset01/`；包含PG全库custom dump、Redis DUMP/绝对到期时间、完整图节点/关系、Kafka消息/原坐标。工作站证据在`.local/verification/alert-reset-replay-20261025/`。备份检查及回执不等于完成跨库恢复演练。

## 保留的失败与修复

1. 只读预览先识别租户技能引用历史评测基线；从清理范围移除这类配置依赖，未删数据。
2. 只读辅助程序补Neo4j时间类型编码、Kafka分区元数据读取，之后预览通过。
3. 独立审查要求Redis/图删除绑定备份对象，以及恢复服务失败停回已启动者；修复后限定ACCEPT。
4. 首次apply完成备份/Kafka清理后，PG事件账本的不可变DELETE触发器拒绝操作，PG事务回滚；Redis/图未动，服务保持停止。改为显式TRUNCATE事件/工件/预约三表，保留约束/触发器，无CASCADE；真实事务ROLLBACK验证通过。
5. PG清理已成功提交后，核读因UNION ALL返回顺序变化误报schema_changed。按表名核对确认只有清理表变为空，其他表完全一致；工具改为稳定排序并增加回归测试。第二次续接跳过PG/Kafka，仅完成Redis/图/恢复，11:28完成。

原失败回执保留，不覆盖后声称首次成功。7项离线工具保护测试通过，独立静态复核限定ACCEPT/0必须修；不等于重跑业务质量通过。

## 已完成：Kafka重放与实际结果

从20只读取回三个场景的六条原始输入及六条规范化背景事件。保留原行为、描述和实体，换为21生产租户及新source-v1身份，告警和事件时间统一平移85116.261735秒至本次窗口。原始输入、SHA256、20原ID→21来源ID→21canonical Alert ID映射保存在私有`replay/manifest.json`、`validated.json`及`comparison.json`。因此这是功能对照，不是相同历史上下文下的确定性回归。

背景六条先发`socai2.raw_events.v1`，再逐条发送六条`socai2.alerts.raw`，每条得到Kafka ack并等待其Run结束再发下一条。未直接插入PG最终告警、手工补图或手工写湖；没有重发旧Run或未知请求。每条发送前保存独占intent，ack保留topic/partition/offset。

- PG：6条Alert、6条Run、92条调查事件、77份工件、11行成本；实际Case为0，资产关联为0，负责人均为空。全部工件UTF-8长度/SHA256通过。
- ClickHouse：原LakeWriter消费规范化topic，`aisoc.raw_events`新增并读回6条指定event_id；历史湖数据保留。`socai2_lake`是账号名，不是表名。时间按湖毫秒精度持久化，PG保留微秒。
- Neo4j：自动投影6个本租户Alert节点及30条出边；关联Host/User/IOC/Technique。图开关与写入均已验证。
- Agents：6次自动分诊；5次升级Graph/Deep，1次自动关闭。6个Run为completed，但5份Graph交付均partial、最终verdict为needs_review；不能当作完整调查通过。
- 用量：36个已回复模型调用，157310 tokens；36个调用均unpriced，费用未知，不能把成本列0当作免费。6条分诊预约均responded，无本批unknown/unsettled。
- API/Fusion/Agents原发布服务保持运行。湖、图、Kafka消费及自动升级原本已启用，无需重新打包、改业务源码或部署。单Run配置未修改，真实厂商响应未启用。

### 20与21对照

| 场景 | 20分诊 | 21分诊 | 流程比较 |
| --- | --- | --- | --- |
| Office隐藏PowerShell | true_positive / 0.95 | true_positive / 0.85 | 均升级，均partial |
| 脚本HTTPS连接 | needs_review / 0.65 | needs_review / 0.65 | 均升级，均partial |
| LSASS读取 | true_positive / 0.95 | true_positive / 0.95 | 均升级，均partial |
| SMB远程服务访问 | true_positive / 0.85 | needs_review / 0.85 | 均升级，结论不同 |
| 批量读取与归档 | true_positive / 0.95 | true_positive / 0.85 | 均升级，均partial |
| 归档上传 | benign / 0.95 | false_positive / 0.95 | 均自动关闭，分类不同 |

执行分支6/6相同；分诊分类4/6相同，分数4/6相同。两条分类差异和两条分数差异保留，不能宣称结论完全一致。20原来五次调查主要按Deep六轮截断；21五次也达到六轮，但Graph又记录token预算耗尽，分别26922、26652、29164、33025、28764/20000。Run总tokens还包括首次分诊；不是把模型总量与Graph预算混比。

五条升级调查的最终结论另核：20保存的delivery.verdict全部为`confirmed_incident`，21对应graph_result.verdict全部为`needs_review`，两边completion均为partial。**最终调查结论5/5不同**，不能用分诊4/6相同或执行分支6/6相同来替代。21停止后的交付保留待复核，而20在Deep截断后仍交付确认事件；这反映结果交付语义和已有质量问题的差异，不证明20或21哪一方的威胁判断正确。原报告/最终字段均保留，未统一改写。

### 本批暴露的问题（未修改后端）

1. 第六条21理由把原始描述中的“synthetic demonstration”视为非恶意，并进一步断言规则误报；原始输入没有提供规则误触发反证。该分类与20的benign不同，是实际质量风险，不追认为正确。测试标记对结论的影响保留原文。
2. 五个Graph达到软额度后停止，但请求内用量越过20000边界；没有提高额度或重跑。原分诊0.85、Graph内部heuristic prior/最终0.75不混作同一分数。
3. `process_tree`因湖无父进程字段不可用；`network_connections`返回LakeQueryError，不是“没有网络证据”。`entity_timeline`确实读到主机两条湖事件；背景事件是会话资料，不能证明已补全进程/网络取证。
4. 威胁行为者归因存在401；原图和入湖成功不代表所有富化工具成功。报告中也有无依据的“single-stage attack”等旧表述。本批比较原文，不修改调查设计或宣称内容质量验收。
5. 六次Explain HTTP200，但均`llm_used=false`、`llm_source=none`，理由为没有tenant BYOK或env API key；实际使用模板摘要与两项通用建议。Agents模型可用不代表API Explain的模型配置可用。

上述缺口已具备具体证据，后续若修本地后端源码或部署，先与用户确认修正范围；本批没有顺带修复。

## 告警页面数据交付

原52条样例、12个事件、12个Case及布局/样式保留，追加6条本批真实处理记录，列表总数58；新告警按发生时间默认排在最前。没有增加“21快照”、Mock或缺口面板。事件/Case本批只展示真实关联ID/未关联状态，不接入其页面数据；实际Incident ID没有指向任意旧样例事件。

[页面](http://127.0.0.1:4173/#/alerts)和[首条告警](http://127.0.0.1:4173/#/alerts/4c71eec2-77da-5b81-b68a-72801d55ea24/overview)。当前是实际服务结果的本地离线呈现，按钮仍沿用原浏览器交互，未接后端写入、持续订阅或页面内实时Explain请求；六次Explain由本轮实际调用后保存返回值。无需向浏览器放数据库凭据。

- 严重程度按已确认映射；5条实际启动调查显示进行中，自动关闭的一条显示已解决。Run完成不等于告警完成。
- Fusion置信度来自`alerts.confidence`；风险评分来自`alerts.ai_score×100`，例如首条80/100与85。检测源为`enrichment_data.socai2_fusion.identity.source`，战术为`mitre_tactics`。
- 资产标签只用资产关联表→资产表；本批关联为空，标签留空。原始主机/账户/IP照实展示，不制造库存资产ID或可用的资产详情关联；原样例资产链接保持。
- “发生了什么”展示真实Explain.summary和suggested_actions的title/rationale；不把“待核实事项”作为必须存在的独立字段，也不解析摘要补结论。
- 时间线只使用落库发生、入库、分诊、Graph步骤/交付、关闭等实际时间，最新在顶部；没有生成检测/取证完成假时间。
- “响应”保持原卡片和自动过程，建议、要求审批与实际未执行分开。工具区明确当前只有最多200字符的持久摘要；graph_step没有完整输入输出，不从摘要伪造原文。
- 同主机相关告警最多7条；相似历史按同主机+战术或同IP/文件hash最多5条，仅在本批读到的数据中筛选。完整后端查询、Case关联和人工反馈写入仍待承接。

导出入口为`tools/testdata/export_alert_ui.py`；读取白名单字段与已校验工件，生成`prototypes/security-pages/replayed-alerts.js`，不包含模型prompt、调用凭据或全库原文。原`data.js`、`styles.css`字节未改，浏览器已保存内容按ID合并，不重置已有操作。

## 验证与边界

清理工具7项离线保护测试通过；投影5项字段/语义测试、2项前端契约测试通过（含6条×4页签渲染、原样例保持、重复合并、时间线不补造）；JS语法检查通过。浏览器核对58条列表、新告警侧栏、首条概况/响应/倒序时间线，截图保存在私有证据目录。本轮不做全仓回归、不新增模型复跑。

操作证据：`.local/verification/alert-reset-replay-20261025/replay/`下`ack-*`、`observed-final.json`、`graph-observed-final.json`、`lake-observed.json`、`explain-*`、`comparison.json`。20参考为只读`source20.json`及原`aisoc20/showcase-20261024/evidence/final-read-verification.json`。本地代码/文档未提交、未推送。结束独审以本批change的audit回执为准。


结束独审及最终Graph对照补充均限定ACCEPT，0剩余必须修项；OpenSpec已归档`2026-10-25-reset-replay-alert-flow-20261025`。封后主规格/活动变更7项、归档16项strict通过。用途占位文案的首次静态校验失败与修正见audit，不涉及业务运行。
