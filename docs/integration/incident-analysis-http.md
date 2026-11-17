# 事件诊断：本轮范围与实际覆盖查询

2026-11-15：当前21候选18424 API/18480 Swagger为80操作、无鉴权，旧18024/18080已停止。事件专用范围/覆盖和异步提交已纳入候选代码；[S01-r3真实入站](../operations/evidence/streaming-ingress-http-20261115-02/README.md)已核新事件与4条accepted任务，[真实A/I结果62次GET](../operations/evidence/streaming-ai-http-20261115-01/README.md)已通过，I选入/覆盖3条、采用的A及原答与保存一致；正文仍为“A”，质量NOT_PASSED。按[HTTP联验计划](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#已有ai任务执行后的http联验2026-11-15)推进。原103次HTTP/12项直接检查属于此前隔离PG批次，不能代替本轮21真实模型验收。提交/轮询方法见[事件异步接口](analysis-submission-http.md)，当前整体状态见[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。

S04新增A04后，事件全量及新Run选入变为4；模型输出达到本次I配置3000并截断，新Run/诊断failed，analysis_coverage为unknown。旧current_pointer保留，但current.freshness=stale、valid_for_current_input=false。[44次失败路径读取](../operations/evidence/streaming-s04-http-20261115-01/README.md)已核错误、原答、停止检查及两Case原记录；没有Case后轮，不能据GET成功判S04正向链通过。

这两个对象回答不同问题：`input_selection`说明本轮选了哪些告警；`analysis_coverage`说明实际结论覆盖了多少。事件保存的全部成员不会因为单次选入上限而被删除。

F1修复后，Case使用I结论也保存这份来源的选入、覆盖及Case交集，不能把整个事件成员都当作已分析；后续新I不改写旧Case输入。读取位置见[Case冻结事件范围](run-records-http.md#case使用了事件结论时如何核对范围)，[同源22次HTTP读回](../operations/evidence/incident-case-scope-fix-20261115-01/http-readback.md)已通过，已进入21候选但未正式发布。当前候选80操作，Case异步POST已挂载并联验；本页原103次批次仍保留其当时验证范围。

## 请求与结果位置

以下接口默认内部可信，不需要登录、Token或角色信息；路径省略`/api/v1/socai2`。

| GET接口 | 输入 | 返回与操作结果 |
| --- | --- | --- |
| `/incidents/{incident_id}/analysis` | `incident_id`必填UUID；`limit`可选，默认20、1–50；`before_run_id`可选，使用上一页`next_before_run_id` | `current`返回当前诊断指针对应记录，`entries`返回历史分析；两处的每个事件Entry均含下述对象。请求只读取保存内容，不发起诊断。 |
| `/incidents/{incident_id}/analysis/runs/{run_id}` | 事件UUID和属于该事件的Run UUID | 返回该Run的执行状态、实际诊断及冻结范围/覆盖。任务GET和统一Run目录中的结果链接指向这里。 |

上述查询参数`limit`是历史列表单页条数，与响应`input_selection.limit`所表示的单次诊断选入上限无关。

事件详情沿原`analysis_url`进入诊断目录；当前指针、历史尝试、是否适用于当前材料分别保留原字段。不把最新失败尝试当成当前有效诊断，也不在事件列表复制一份全事件结论。

## input_selection：本轮实际选入范围

| 字段 | 含义 |
| --- | --- |
| policy | `recently_linked`，按最近加入事件的成员选择，不按告警发生时间选择。 |
| limit | 本轮实际采用的选入上限，来自执行配置；默认100。 |
| order | `linked_at_desc_alert_id_asc`，加入时间倒序，同时间按告警UUID升序稳定选择。 |
| captured_at | 本轮捕获成员范围的时间，带时区。 |
| total_member_count | 捕获时事件的全部成员数，不是页面当前数量。 |
| selected_count | 本轮实际选入数量，等于`selected_alert_ids`长度。 |
| omitted_count | 捕获时未选入数量；与selected_count之和等于total_member_count。 |
| selected_alert_ids | 本轮实际选入的告警UUID，沿保存的选择顺序返回；不能拿当前成员替换。 |
| input_artifact_id | 保存本轮冻结输入的工件UUID，可沿该Run工件目录/正文接口追溯。 |

本对象来自同一次Run保存的输入。开始后新加入事件的告警不会改写它；需要查看当前成员时使用原事件成员查询。

读取时的新鲜度按该Run冻结的选择规则与当前业务材料比较；运行配置调整选入上限后，下一次check/执行才重新选择，不回写旧Run的范围回执。

## analysis_coverage：结论实际覆盖

| 字段 | 含义 |
| --- | --- |
| state | `complete`覆盖捕获时整个事件；`partial`只覆盖部分；`none`已知没有成员被实际覆盖；`unknown`无法可靠确定。 |
| analyzed_count | 已分析且给出判断的选入成员数，不含下面待核成员。 |
| unresolved_count | 已分析，但结论仍待核的选入成员数。待核不等于没有分析。 |
| not_analyzed_count | 已选入但未被实际分析覆盖的成员数。 |
| covered_alert_ids | analyzed和unresolved两组的成员ID并集；数量等于这两项之和。 |
| limitations | 保存结果对应的覆盖限制说明；不能把限制说明当成新的分析结论。 |

三种计数在选入集合内互斥，已知时之和等于selected_count。未选入的成员只记在omitted_count，不再算进not_analyzed_count。无法可靠确定时计数和covered_alert_ids保持null，state为unknown，不补成0。

例如捕获事件260条，实际选入100条，其中80条给出判断、20条待核、0条未分析：选入范围全部交付仍可为`delivery_state=complete`，但另160条没有纳入，因此`analysis_coverage.state=partial`。执行是否结束、交付是否完整、覆盖范围和模型质量分别判断。

## 历史、失败及错误

- 历史Run未保存选入或覆盖信息时，相应对象为null，不用当前数据回填统计。
- Run失败或结果未知时保留原状态和已保存原件；覆盖字段按真实保存情况返回，不因为HTTP成功而标成complete。
- 不存在的事件或不属于该事件的Run返回404；UUID/分页参数不合法返回422；依赖不可用返回相应5xx。合法空历史返回200，不能把读取失败当成空历史。

新增字段仅属于事件Entry及事件目录。告警的分析列表和Run详情继续原StageEntry/StagePage合同，没有这两个对象。

## 验收与接入状态

已完成[真实保存及HTTP读回核对](../operations/evidence/incident-async-http-20261115-01/README.md)：常规事件、260成员选入100/遗漏160、容量失败、unknown、跨期首试失败及已结束的真实模型样本。每个事件Entry的输入和诊断来自同一Run原件；全部只读阶段的12类记录前后摘要一致。真实部分覆盖样本为100条全部待核，接口返回analyzed=0、unresolved=100、not_analyzed=0、state=partial；前文80/20只是字段解释示例。

E37已异步202，真实check无变化不产生Run，rerun生成新Run及诊断、保留旧记录；终态重复提交仍返回原受理回执。实际模型样本虽然执行/保存成功，但正文为“N/A”，质量NOT_PASSED，接口保留原文，不把coverage=complete当作质量通过。该103次批次当时Case新POST未开放，现第7步已挂载并联验，F1–F5本机修复及接口验证均已完成。该103次历史批次未部署、推送或新增真实模型调用；当前候选及真实链验证进度见页首。
