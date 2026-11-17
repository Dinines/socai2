# 阶段一对外HTTP影响评估

2026-11-14。应接口交接聊天转达的负责人要求，按现有代码及步骤1–7证据核对；未另改业务接口或发布。对照基线为核心v1.2-20261113-r1与独立18024 investigation-sync-20261113-r1。接口侧可信认证变更及docs20候选属于另一范围，不归因于阶段一。

负责人后续明确统一目标版本、不做新旧兼容工程：下述混版问题仅为已发生的事实，处理方式是核心、独立API读侧、配置和Swagger同步至同一目标合同；不增加旧客户端适配、双轨返回或临时表。阶段一已定稿内容可供接口侧继续开发，不等整个调查阶段或质量改进完成；新增/修改接口及依赖表未定稿时，仅暂缓该项及其依赖。阶段一正式清单见[详细设计第10节](../../../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#10-阶段一稳定交接与统一目标版本)。

下表及其后调用顺序描述阶段一已验代码现状。

| 范围 | 受影响入口（省略原业务前缀） | 影响 |
| --- | --- | --- |
| 执行 | E13 `POST /cases/{case_id}/runs/{run_id}/start`；E36 `POST /alerts/{alert_id}/analyze`；E37 `POST /incidents/{incident_id}/diagnose` | 固定请求/响应合同与同步等待保持；新执行使用结论保留、C3七部分/8192/最多5、最多一次补缺及补查分流逻辑 |
| 业务结果读取 | E12 `GET /cases/{case_id}/runs/{run_id}`；E14 `GET /cases/{case_id}/results/{result_id}`；E22/E23主体`/analysis`；E24/E25主体`/analysis/runs/{run_id}` | 原结论、原判定及新鲜度读取实现需要一致；引用问题独立记录，不据此抹掉结论或改成不确定。执行/交付/结论/采用/质量仍是不同状态 |
| 原件及目录 | E15 Case Run `/artifacts/{artifact_id}`；E16 Case非Run工件；E31告警`/materials/{material_id}`；E32主体Run `/trace`；E33主体Run工件；E34/E35主体非Run工件 | 固定字段、枚举和不可变ID保持；详情解除旧1 MiB拒读，列表仍为元数据；动态正文及关联扩展见下文 |
| 采用关联 | E03 Case详情；E21显式采用；E63采用预览；E64判断历史 | 固定请求、预览令牌、人工选择和stale保护保持；有引用问题的原结论仍可按既定条件流转/采用，不能把采用当引用或正文质量通过 |

动态内容扩展：A/I的`content_json.citation_review`，Case的`content_json.payload.raw/derived/citation_review`及独立`model_original_response`；C3的`c3_section_completion`计划/合并与`basis.section_completion.field_origins`；C4/Deep的`socai2.followup-activity.v1`活动记录；查询已取得额外行的`overflow_rows`；新Run通过`source_refs`关联`socai2.runtime-policy.v1`配置快照。`rows`与额外行分开不等于模型实际用了全部原件。旧无配置、未收到原答、unknown不回填。

调用顺序与规则：Case仍准备/显式start后查Run与Result；A/I仍直接调用同步执行入口。连接超时或unknown先查原Run，幂等键规则保持。C3补答在同Run预算内执行，初答、补答分别计次，C6预留不变。human建议不自动建任务，graph不冒充取证；没有新增自动采用、自动关闭或重开即重跑规则。

实施状态：阶段一已按负责人确认以 **“本地验收完成，待统一发布”** 收口。步骤1–6的限定本地保存读取及步骤7的快照/浏览器验收均已完成，见[本步回执](README.md)。核心、独立HTTP读侧和实际4177尚未发布；模型质量仍NOT_PASSED，原答、失败和unknown保持。

实际混版风险已由接口侧只读验证证实：[freshness-compatibility.json](../http-impact-review-20261114-01/freshness-compatibility.json)在同一PG快照、同一I Run上得到旧`freshness_sql=stale`、新`=current`，没有改数据或调用模型。旧正式reader还保留1 MiB门槛，会拒读新大原件。接口侧提供的固定OpenAPI对比排除可信认证调整后相同，但这不覆盖reader、动态正文和实际语义兼容；统一发布应同步核心与独立API读侧。

代码入口：`services/api/app/socai2/{alert_basic_executor,incident_diagnosis_executor,stage_results,citation_quality,baseline_reasoning,case_c3_completion_flow,baseline_store,stage_inputs,page_reader,runtime_policy}.py`；步骤7为`docs/operations/processing_audit_{delivery,detail,flow,inspector}.py`。详细字段位置、前六步证据与实际采用验证见[前后端交接阶段一说明](../../../../FRONTEND_BACKEND_HANDOFF.md)。接口侧需同步动态正文示例、原件遍历方式、状态解释及版本依赖，不必新增固定HTTP字段。

阶段一仅保留统一发布及发布后验证两项交付待办，具体范围见[阶段一收口安排](../../../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#发布与发布后验证待办)。后续调度讨论不计入阶段一待办或关闭条件；本文件不再承载其索引、领取、重试及结案设计反馈。
