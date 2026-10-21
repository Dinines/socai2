# C03-02C-02：v4 新输入有界质量验证

2026-10-21。本批受控收尾与凭据撤销经独立审计确认；实际质量结果为 **stopped_no_quality_pass**。常驻 worker 继续 OFF，完整准入与整个迁移仍未完成。

[执行卡](c03-triage-authorization-quality-plan.md)、[结构回执](c03-triage-authorization-quality.json)与[证据清单](../handoff/c03-triage-authorization-quality-evidence-manifest.json)记录同一次执行；不改原02、02B或v4的0模型回执。

实际模型发送检查点 3 个；已知完整总usage为 5971 tokens，美元费用未知。Mock预检另计 3 次。没有发送检查点的case：case04。

| Case | 实际分类 | 分类门 | 理由门 | 独立质量门 | tokens |
| --- | --- | --- | --- | --- | --- |
| case01 | true_positive | True | True | True | 1920 |
| case02 | benign_true_positive | True | True | True | 2077 |
| case03 | false_positive | False | False | False | 1974 |

新增材料与预算的精确差值见结构回执。旧7预约/140000预留单位/3 unknown保持，本批新增 3 预约/60000预留单位；预留单位不作实际tokens。新增pending QA 0，原QA关联问题继续登记，不用QA替代质量门。

本批三枚操作key已停用且逐枚真实API401，十枚reader保持。两个旧quality/DLQ组、六budget组和主group提交保持；常驻Fusion raw的推证交付与临时消费者直接观测分开报告。真实HTTP、host显式SQL和独审读取在结构回执分别计数，不冒称全内部SQL或0HTTP。

运行仍为26 Compose/23来源层，四服务769 Py、Agents184 Py及独立prompt lock引用[v4父清单](../handoff/c03-triage-authorization-source-manifest.json)，无新增运行层/重启/DDL。C01旧observer导入副作用的104 SQL/4 HTTP及112追加计数文件继续归原C01，原B844文件与24份父公开原件保持；不声称旧B目录从未追加文件。

下一项：Preserve the actual failure/unknown; separately scope the next correction and fresh inputs, with no automatic retry. 原失败、未知及六条旧未执行样例事实保留，不自动重调或改判据。
