# F1：事件实际分析范围传入Case

2026-11-15。真实隔离开发库`v12_upgrade_dev`与隔离Redis命名空间；所有模型、补查来源均为明确替身，0次真实模型。不部署、不清旧数据、不重派已结束任务。本批是模块集成验证，不是Kafka端到端或最终模型质量验收。

## 修复与证据

- [修复前失败](before-tests.txt)：真实C3 builder把只分析1条的I结论关联到Case全部3条。
- C1同一SQL选中诊断及其同租户/事件/Run输入工件，校验原件身份、摘要、选入与实际覆盖。新增内部`diagnosis_scope`；缺范围或无交集保留原件/缺口，不用当前事件成员补造覆盖。
- C3概要/结论只关联实际覆盖与Case的交集；原选入范围和跨成员finding/question原scope分别保留，Deep/C6沿冻结来源。Case自身范围保持全量。
- [直接检查](after-tests.txt)：64项通过，含8项范围专项及现有C3/后续来源、变化比较检查。既有`test_history_duplicate_presentation_preserves_c3_and_final_dependencies`仍失败，登记后置、明确排除，未记通过。
- [PG正常批次](pg-04/result.json)：3条事件成员选1条，Case经整事件关联取得全部3条；真实调度及I/Case执行器保存1轮I和完整Case（C3引用I、C6继续引用），关联始终为1条。随后事件新增第4条并保存新I，旧Case输入摘要不变。4次模型替身回复、0真实模型。
- 同批在C3回复前独立读取Case及running task，主体和范围已落库；受理时task可查但无Run，见[受理](pg-04/case-accepted.json)。三类完整异步验收仍按总计划补齐，不能由此仅Case检查替代。
- [原C1](pg-04/case-context.json)、[实际Run](pg-04/case-run-readback.json)、[结果](pg-04/case-result-readback.json)、[数据库快照](pg-04/snapshot.json)、[源码摘要](pg-04/source-hashes.json)。HTTP按该批身份同源读取，回执待HTTP模块补齐。

## 冻结字段与读取

Case C1路径`$.incidents.<incident_id>.diagnosis_scope`保存`source_run_id/input_artifact_id/source_fingerprint`、原I的`input_selection`、`analysis_coverage`、`case_selected_alert_ids/case_covered_alert_ids`。当前事件`member_ids/case_member_ids`仍表示关系，不等于诊断覆盖。模型来源`alert_ids`是实际关联，`original_scope`保留原完整范围。没有新增公共路由、告警DTO或DDL；内部Context JSON Schema及发布片段同步。

HTTP复用E23/E25读取I选择和覆盖，E12/E14及现有工件GET读取Case及其冻结来源。新I不得覆盖旧Case Run的C1及模型请求。

## 失败保留

- `pg-01`在沙箱连接PG前失败，未完成业务写入；[原准备记录](pg-01-sources/result.json)保留。
- [pg-02](pg-02/result.json)合成事件和告警namespace不一致，建案正常拒绝；已完成I及失败记录保留。
- [pg-03](pg-03/result.json)验证回调误用ORM行取值，C3回复前抛KeyError；原Case Run保留unknown，未改写为成功或重派。
- 修正夹具/回调后以全新租户执行`pg-04`，上述失败不计通过。

## 边界

I条数上限仅本地测试profile设1以验证3选1；6小时/7天等生产默认未修改，100条默认及260选100排序/容量证据复用第4步原批次。缺范围/无交集、部分覆盖/待核、跨Case原范围通过离线实际builder及Deep/C6检查，不虚构为本批PG场景。真实模型正文质量NOT_PASSED、21实际TCP、Kafka归并和上下文路由仍留最终验收。
