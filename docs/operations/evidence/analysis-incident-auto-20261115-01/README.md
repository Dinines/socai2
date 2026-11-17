# 第4步：事件自动诊断

2026-11-15，本步程序实施、直接验收和HTTP联合对接已本地完成；模型正文质量 **NOT_PASSED**，待整个change统一发布。设计先行见[本步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage4-incident-diagnosis-design-20261115.md)，配置入口见[运行说明](../../analysis-incident-diagnosis.md)。本轮未部署、提交推送、启动生产消费者或实施Case后续步骤。

## 已实施行为

新事件与首个成员同事务登记initial，A与I共用唯一dispatcher及N；事件初轮无额外等待全部A的屏障。默认4小时检查当前选入范围、可用A业务结果和有效人工反馈，7天活动窗口与60秒/一次重试沿已有配置；无变化只跳过，自己的I结果、元数据和未选成员A变化不触发。扫描不调用模型，执行前重新加载并固定本轮输入，运行中到达材料不加入原Run。

I按归并时间倒序、ID升序选最近100条，独立配置；所有事件成员与原件保留。Run、输入/运行策略和attempt在调用前绑定保存；准备后的容量超限请求与测量也保存，不发模型、不分段、不重试，同输入同容量配置停止反复预检。HTTP事件专用范围/覆盖分别恢复本轮捕获量与实际分析，告警DTO保持。

关闭/超期沿原规则：关闭前已运行的可完成，未开始的跳过；七天内已受理的首试跨期仍执行但不重试。unknown只结束本地占用，原Run unknown/ended_at=null保持，队列继续。旧直接incident运维CLI移除，目标人工入口为E37异步任务。

## 直接证据

| 证据 | 结论及真实边界 |
| --- | --- |
| [PG/Redis首批](pg-redis-01/result.json)、[原件](pg-redis-01/database.json) | native两A仅一I initial、重放无新任务、A/I真实执行器及模型前绑定、check无变化不创建Run、新告警/A→周期I。真实隔离PG/专用Redis，模型与计数器为明确替身 |
| [最终边界批](pg-redis-03/result.json)、[原件](pg-redis-03/database.json)、[受控IO](pg-redis-03/model-io.json) | 11项通过；另核晚到A、相同业务正文新ID/时间不触发、元数据不使I stale、有效人工反馈、排队前新材料与运行中固定范围、260条保留而选100条、容量、关闭/超期及unknown释放N=1 |
| [范围/覆盖](pg-redis-03/result.json)的partial_coverage样本 | 260个真实保存成员，选最近100、未选160，100成员实际给待核分析；Run delivery=complete，analysis_coverage=partial。全事件成员未删除，未选A结果不触发重复I。此100成员调用使用受控计数器，不能据此声称真实模型100条必定装得下 |
| [容量样本](pg-redis-03/result.json)的capacity_failure | 准备后的完整body、Schema、来源、测量、失败保存，0次实际模型发送、0重试，旧current指针保留；相同输入/配置停止，容量配置改变允许新预检 |
| [真实A→I](real-01/result.json)、[事件任务](real-01/incident-task.json)、[事件读回](real-01/incident-page.json)、[数据库快照](real-01/export/database.json) | 新专用租户、1合成告警/1事件、2task/2attempt/2Run、7步骤/20工件。正常native入站及真实Redis→真实A→真实I→保存/读取，2次真实生成、3764tokens，无追加采样/重试；使用既有SSH验证传输和真实tokenizer，不是生产消费者运行验收 |
| [离线直接检查](direct-tests.txt)、[检查汇总](checks.json)、[代码摘要](source-sha256.json) | 63项通过，覆盖事件视图/覆盖/配置、已有队列及发布打包/生产profile。Ruff及OpenSpec strict通过；不宣称全仓通过 |
| [HTTP本批](../incident-async-http-20261115-01/README.md) | 103次无鉴权HTTP请求通过：E37 202保存任务；check消费无Run、rerun消费新增Run及诊断；部分覆盖、失败/unknown/跨期及真实模型样本同源读回。GET前后业务摘要不变，候选80操作，旧同步入口移除 |

## 模型质量与保留限制

[质量记录](quality-review.json)：真实A理由只有“告”、建议理由“需”；真实I成员assessment为“A”、summary/conclusion及多项正文为“N”。结构、引用检查及保存成功，正文没有可用分析，质量 **NOT_PASSED**。依据已有后置决定保留原答，不再采样，不把coverage complete解释为质量通过。没有独立业务真值，不报准确率。

旧`test_socai2_incident_alias_namespace.py`有4项历史输入/profile重放失败；[当前日志](historical-current.txt)与[内存恢复本步边界修改的对照](historical-baseline-aligned.txt)在相同显式策略下均为4失败/2通过。原因是旧profile缺incident_only、旧提示与现有渲染不同；不属于本步自动接线或容量选择引入的问题。本步不修改历史原件或扩大为旧输入渲染专项。第一次对照漏选策略的[日志](historical-baseline.txt)也保留，不把它作为有效同条件证明。

`pg-redis-02`保留夹具事件namespace与native fusion身份不符造成的失败；修正夹具后以新租户执行03，没有覆盖02的Run/unknown。01及03普通http_sample误把首轮task与最新周期Run配在一起，HTTP严格核对后发现；[更正映射](http-samples-corrected.json)按真实attempt关联另存，旧回执保持，实际数据库关联未改。边界样本及real-01的task/Run原映射正确。

## 4177与发布边界

真实完成快照通过`update_processing_audit.py`导入仓库静态工件，共13份注册快照，历史保留。实际4177仍是21冻结三案的转发，本轮不切服务或重新上线全部历史展示集。HTTP确认所有消费drained后，本轮专用Redis已停止并保留容器/数据。配置示例默认disabled，正式71操作与服务版本未变；统一发布应带齐[发布片段](../../../../deploy/local-investigation/analysis-incident-release-fragment.json)及HTTP变更，再按实际运行读回。

未新增DDL/历史启用逻辑或修改V1告警交接字段。Case创建/续建/自动执行、知识队列、整个change结束审计/发布仍未完成；主调查31/41与流式原任务2/11保持，本步只完成2.2/2.3/2.5/2.7的I部分。
