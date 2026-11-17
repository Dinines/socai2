# 建案后的首轮调查：后端接口对接

2026-11-15：当前21候选18424 API/18480 Swagger为80操作、默认内部可信、无鉴权，旧18024/18080已停止。此前第6步替身联验保留[原验收](../operations/evidence/case-initial-http-20261115-01/README.md)。S01真实A/I保存及62次GET之后，[整事件Case和A01固定范围对照](../operations/evidence/streaming-case-http-20261115-01/README.md)已完成2次POST/5次GET持久受理，再由唯一调度执行首轮；[结果58次GET](../operations/evidence/streaming-case-result-http-20261115-01/README.md)通过，2个Run/Result、34步骤、96工件目录及44份必要正文与测试快照一致。两案completed/accepted/uncertain/partial，实际范围分别3和1。Case为正常长文本，引用问题保留、正文全面评估未做，不算质量通过；S04和整个change验收仍待。

业务后端创建案件后，调查服务会通过调度器完成首轮调查。后端使用创建回执中的任务地址查进度，再沿任务中的链接读结果。无需另发“准备Run”和“启动Run”。HTTP只负责业务受理与读取，执行由独立调查服务负责。

## 输入、操作和结果

以下路径省略`/api/v1/socai2`。服务默认内部可信，不要求登录、Token、角色或客户端提供租户/操作者。

| 步骤 | 接口与输入 | 输出及用途 |
| --- | --- | --- |
| 创建案件 | `POST /cases`；operation_key、title、alert_ids/incident_ids；完整约束见[分配接口](case-allocation-http.md) | 201，返回实际分配到的案件和各新案initial_task；仅表示持久受理，不等待模型完成。 |
| 查询分析任务 | `GET initial_task.status_url`；或`GET /cases/{case_id}/analysis-tasks`，可用limit/cursor分页 | status、reason_code、attempts、latest_run_id、results；未执行时Run及结果可为空。每个续建新案有自己的任务，不合并成一个进度。 |
| 读取执行记录 | `GET attempts[].run_url`，即`/cases/{case_id}/runs/{run_id}` | 实际执行/交付状态、冻结成员、当前成员数、result_ids及steps_url/artifacts_url。任务身份与Run身份分开。 |
| 读取结论 | `GET results[].url`，即`/cases/{case_id}/results/{result_id}` | 本轮结论、发现、未解决问题、建议、来源及覆盖。questions随结论展示；需要人工核实由用户另建人工任务。 |
| 读取当前判断 | `GET /cases/{case_id}` | current_assessment返回当前已保存判断、来源和覆盖。可能为空，也可能已由首轮发布规则形成；不能固定显示为空或自行采用最近结果。 |
| 读取完整过程 | 沿steps_url/artifacts_url GET，limit/cursor分页；沿工件content_url取正文 | 查询回执、模型请求/原答、校验和报告原件。Run所属工件必须走含run_id的原件地址，不能用Case独立证据地址代替。 |
| 检索案件调查历史 | `GET /analysis-runs?subject_type=case&subject_id={case_id}&intent=initial` | 真实Run与task关联、统计和下一页；未生成Run的任务从analysis-tasks查询。 |

例如创建请求（ID是占位，必须换成同环境真实告警和新操作ID）：

```json
{"operation_key":"00000000-0000-4000-8000-000000000601","title":"核查异常登录","alert_ids":["00000000-0000-4000-8000-000000000602"]}
```

创建回执中每个新案的`initial_task`形如：

```json
{"task_id":"00000000-0000-4000-8000-000000000603","subject_type":"case","subject_id":"00000000-0000-4000-8000-000000000604","status":"accepted","status_url":"/api/v1/socai2/cases/00000000-0000-4000-8000-000000000604/analysis-tasks/00000000-0000-4000-8000-000000000603"}
```

这是分配回执的一个字段，不是整个POST响应；完整真实输入输出见[examples.json](../operations/evidence/case-initial-http-20261115-01/examples.json)。相同operation_key重放同一创建请求只恢复原回执；查询进度使用GET，不换key重建案或重复执行。

## 必须区分的状态

- `accepted`仅受理；`running`是实际执行；`completed`是程序完成，不能当作模型结论准确或全部问题已解决。
- 容量超限时任务和Run为`failed`，reason_code/stop_reason为`capacity_exceeded`。仍可能有系统收尾Result和已保存输入，不能因为有结果就展示“成功”。本步样本0生成调用，材料未被删除以适配容量。
- 缺少可信告警时间时不编造查询时间；查询失败不改成查空。这两种情况下其他分析可继续，完整回执从工件读取；任务完成也不表示每个工具都成功。
- 调查准备前的成员按实际冻结输入确定。运行中新增成员只进入当前案件，不追写旧Run；样本当前Case为3成员，Run保持2成员。用`current_member_count`和`input_member_count`区分。
- 仅选择单条告警建案时，C1可以参考它所属事件的诊断，`linked_from_case=false`表示没有显式事件关联。事件原分析范围保持，本案使用范围按`case_selected_alert_ids/case_covered_alert_ids`取交集；来源范围超出本案时保留`diagnosis_scope_extends_beyond_case`，不扩充Case成员或结论依据。详见[冻结事件范围](run-records-http.md#case使用了事件结论时如何核对范围)。
- 首轮没有上一轮比较对象，comparison_result_id为null。当前已保存判断及其来源按实际数据读取，系统收尾与有效模型判断仍分别显示。

字段逐项定义复用[任务GET](analysis-tasks-http.md)、[Run目录](run-directory-http.md)及[步骤/工件](run-records-http.md)，不另造状态或重试流程。

## 错误和实现边界

创建的404/409/422/503及operation_key、范围冲突处理见[分配接口](case-allocation-http.md)。读取中对象不存在或不属于路径返回404；非法UUID/分页参数返回422，失效游标按对应列表合同处理；缺配置或数据依赖不可用返回503。错误不能当空列表。HTTP工件时间使用带时区的ISO格式；比较数据库导出时比较同一时刻，不能只比较空格/T/Z的字符串写法。

候选已删除E11 `POST /cases/{case_id}/baseline/prepare`及E13 `POST /cases/{case_id}/runs/{run_id}/start`，均404且不在Swagger；内部准备/执行原语保留。Case `POST /cases/{case_id}/investigations`已在第7步完成检查/再次调查及周期样本联验，见[异步提交指南](analysis-submission-http.md)。AI对话继续暂停，第8–10步定向分析/手动综合/知识后台异步维护后置。

## 部署依赖与验证范围

沿已确认128/129增量，无第6步新迁移。HTTP使用明确的业务上下文、任务policy、分配policy及Run记录读取配置；调查调度使用唯一的A/I/Case工厂`app.socai2.analysis_case_executor:executors`和独立显式配置。补查默认前后各3600秒、日志上限默认50且受Run额度约束，HTTP请求不接收这些执行参数。

[HTTP发布片段](../../deploy/http-service/case-initial-release-fragment.json)组合[核心片段](../../deploy/local-investigation/analysis-case-release-fragment.json)；不能只替换路由、启动第二套调度器或在旧21数据库缺表时做兼容回退。该历史验证批次不部署、重启或推送Git。39次成功验收请求（1 POST/38 GET）及6项定向检查通过；读取前后19类记录一致。当前候选独立TCP、A/I及两案真实首轮保存/读取已通过；后续更新与完整change验收继续沿既有[测试方案](../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)，原NOT_PASSED保持。
