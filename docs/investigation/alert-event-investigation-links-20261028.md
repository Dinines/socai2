# 告警、事件与Case调查结果的关联

2026-10-28。后续计划第1、2批已实现代码：告警处理上下文、事件调查列表，以及手动AI概况引用已有报告。无新表或迁移，未部署。事件仍汇总和展示，实际调查继续在Case中执行。

## 接口

| 接口 | 输入 | 输出 |
| --- | --- | --- |
| `GET /api/v2/investigation/alerts/{alert_id}/investigation-context` | canonical Alert UUID；limit/cursor | 来源、当前状态/处置、已保存摘要、最新分诊、所属事件、关联Case、覆盖该告警的新版Run及读取链接 |
| `GET /api/v2/investigation/incidents/{incident_id}/investigations` | Fusion Incident UUID；limit/cursor | 当前事件成员、关联Case、实际覆盖成员的新版Run、报告摘要及结果/步骤/下载链接 |
| `POST /api/v2/investigation/incidents/{incident_id}/overview/refresh?include_investigations=true` | 无请求体，显式选择引用Case报告 | 根据当前成员、分诊和已有报告摘要生成概况，保存引用Run与范围 |
| 原事件GET | 同上Incident UUID | 新增investigations_url；若已存概况引用Case报告，还读取当前调查信息到investigations并计算过期标记 |

告警/事件不存在返回404。列表limit默认20、1–50，按Run.started_at及Run ID倒序分页，next_cursor为null表示没有下一页；游标不能换到另一个告警或事件。当前Case列表最多50个，cases_truncated明确是否省略；历史转Case回执仍通过case_links_url单独读取。

新关联读取复用alerts:read和cases:read；刷新继续需要alerts:write。选择引用Case报告、读取已引用Case报告的概况时也要求已有cases:read；未增加权限体系。默认刷新不传include_investigations时保持原基础概况，首次任务也保持原行为。

## 返回内容和范围

告警入口顶层字段包括alert_id/title/severity/status/disposition/saved_analysis，source中的connector_id/source_alert_id，triage、incident_id及相关URL。processing_context_url指向原告警处理上下文，triage_url指向原分诊Run；旧Run不转换成case_analysis.v1结果。

告警的investigations字段和事件调查列表共同包含：

- cases：当前Case ID、标题、状态、与本次来源相交的当前成员和Case/历史链接。来自Case.alert_ids，不使用Alert.case_id猜完整关系。
- items：case_analysis.v1 Run的身份、状态、起止时间、完整固定scope、前次Run、原来源事件、停止原因、completion、result_available、最多800字符的报告摘要及summary_truncated。
- 每个item带matched_member_ids和matched_read_member_ids，分别表示本来源与Run选定/实际读取成员的交集；另有result_url、steps_url、report_url。
- member_ids_with_runs / member_ids_without_runs：当前来源成员在全部匹配Run中的覆盖情况，独立于当前分页。覆盖只表示被选入过Run，不能解释为已完成分析或已证实攻击。

查询依据是Run保存的selected_member_ids。Case里包含A1/A2/A3，而某Run只选择A1/A2时，A3只显示Case关联，不会被列为该Run的调查对象。running没有最终工件时result_available=false，摘要和completion保持null。Case状态、告警处置、Run状态分别显示，不互相推导。

事件关联基于当前PG成员；成员移组后的旧关系可从历史F4回执及Run.source_incident_ids查看，本接口不重建过去的事件成员快照。

## 事件概况引用规则

include_investigations=true读取最近一页20个相关Run，选取已有结果的报告摘要作为材料，并受现有概况材料长度限制。不会加载完整报告、执行工具或再次启动Case调查。材料说明来源Run、Case、原选定范围、与当前事件相交的成员及结果完整度。

source_refs新增include_investigations、investigation_run_ids、investigation_scopes和investigation_results_truncated。investigation_results_status表示included、omitted或no_saved_results_in_page；没有选择引用时保留not_linked，它表示这份概况未引用，而不是系统没有关联能力。遗漏分页或长度受限时明确标记，不把一页当全部调查历史。

普通GET不重新生成文字。新成员、分诊变化或当前展示的Run/报告变化会使已存概况标旧，原正文和生成时间保持不变；再次手动刷新才更新。失败保留原正文。报告只适用于原成员与窗口，不能泛化为整个事件已调查或已解决。

例子：I1当前有A1/A2/A3，C1有这三条告警，R1只调查A1/A2且报告有缺口。A3的入口仍能看到C1，但没有R1；I1显示R1覆盖A1/A2、A3尚无新版Run。之后加入A4，R1范围不变，事件未覆盖成员变为A3/A4；已引用R1的AI概况标旧而不自动重写。

## 运行入口与验证

新增组合入口`app.investigation_v2.application:create_app`提供当前query、告警、事件、Case及成员关联API，无须配置旧fixed/program结果网关。旧program_result/start组合也已注册告警入口；旧服务main没有自动改动。

本轮新增3个直接ASGI流程用例通过：告警Case关联与Run选择的区别；事件新增成员/分页及全历史覆盖；手动概况引用报告、保存来源范围、后续GET只标旧。受影响的原事件读取及概况8个用例通过。PG、事件数据及模型HTTP由替身提供；未验证真实PG或真实模型业务判断，没有运行可用性/恢复/压力专项。

源码：[关系读取](../../services/api/app/investigation_v2/related_investigations.py)、[告警入口](../../services/api/app/investigation_v2/alert_context_api.py)、[事件入口](../../services/api/app/investigation_v2/incident_api.py)、[AI概况](../../services/api/app/investigation_v2/incident_summary.py)、[直接用例](../../services/api/tests/test_related_investigations.py)。

下一项产品HTTP Tool仍需将来源connector绑定带入实际调用；现有vendor_reads按产品类型选择实例，不能直接当作已绑定告警来源实例。第3–6批的其他功能尚未因此完成。
