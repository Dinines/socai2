# F2：管理编辑与已有分诊的HTTP读回

2026-11-15。**F2同源HTTP读回通过，可与核心直接证据共同收口本项；F3–F5及第7步整体审计仍待完成。** 本轮只新增读取测试与文档，没有修改业务代码、数据库结构或发布服务。

复用核心已经结束的[pg-01](pg-01/result.json)，实际管理用例完成owner/tags和人工反馈写入，HTTP不重做写操作或消费任务。使用真实隔离`v12_upgrade_dev`、真实核心读取器及强制只读连接，经ASGI完成[24次无鉴权GET](http-read-01.json)。17张相关表的本租户计数/摘要前后一致，4份核心源码与该批[source-hashes](pg-01/source-hashes.json)一致；新增模型/执行/业务写入均为0。原核心5次模型替身（A1+Case4）、0真实模型，不能当作Kafka/21 TCP/真实模型验收。

| 核对项 | 实际结果 |
| --- | --- |
| 管理和原材料 | 告警GET的owner_id、assignment_state、tags与实际管理回执一致；原latest_material_id、latest_triage_id及原分诊Run不变，原材料正文按保存值返回 |
| 原分诊与查询 | 原A任务completed、分诊正文/来源Run不变；原输入和3份配对工具回执仍可沿HTTP读取，内容/hash与保存一致。未查询、查空等状态不改写 |
| 管理后的检查 | 同一Case的check任务为skipped/no_changes，attempts/results为空、latest_run_id为空。HTTP没有启动新检查，未把跳过显示为调查完成 |
| 有效人工反馈后的手动检查 | source=user的check已completed，完整Run/Result可读；冻结C1同时保留原A、配对查询以及独立human_feedback正文/来源。首轮旧C1仍无该反馈、无后来owner修改 |
| 结果身份 | 2个Case Run/Result与原任务对应，Case仍为1成员；原A与人工判定是两份独立记录，不互相覆盖 |
| 只读边界 | 24次均GET，无Authorization；数据库连接强制只读，17表本租户摘要不变，无模型或调度调用 |

公开A历史响应仍为`freshness=stale`、`valid_for_current_input=false`，含义保持“原历史请求与当前完整输入不一致”；管理字段和人工判定确实发生了变化。这不等于删除已保存A，也不能据此直接判定Case不能使用它。Case C1的`triage_usable=true`按同原材料、已完成的A及其来源判断可否作为prior_analysis使用；两轮C1仍保留原A与工具回执，反馈在新轮单独加入。本批未修改公开A DTO或历史freshness口径，不通过改返回字段伪造新鲜。

修复前[before-01](before-01/result.json)及原失败保留，不复活其未执行Case任务；HTTP本次首轮直接通过。本项不证明晚到A或人工反馈已按新的自动触发规则执行，当前反馈样本明确为手动check；F4的事件链规则、F3重试、F5配置及最终Kafka完整链另行验收。

复现入口：[validate_http_readback.py](validate_http_readback.py)；直接检查：[test_socai2_case_metadata_http_pg.py](../../../../services/api/tests/test_socai2_case_metadata_http_pg.py)。使用显式私密`--config`、已结束`--source`和新的`--output`路径，不覆盖旧回执。数据库参数/凭据只从受控配置读取；本文件不记录凭据。接口读取说明见[管理变化后的分诊使用](../../../../docs/integration/run-records-http.md#管理变化后如何读取已有分诊)，公开80操作/Schema保持不变，最终发布包在全部审计修复收口后统一冻结。
