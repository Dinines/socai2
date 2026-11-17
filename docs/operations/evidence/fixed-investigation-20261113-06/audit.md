# 固定调查06批限定独立审计

2026-11-13。审计者为未参与本轮实现的 `/root/historical_release_audit`。**本轮真实执行证据及不可用比较基线修复的限定审计通过，未发现该修复新增的实际程序阻断；三场景的最终业务交付与模型质量仍未通过。** 本结论不构成主 change 归档或发布验收。

审查范围为 [comparison.md](comparison.md)、[comparison.json](comparison.json)、[replay-manifest.json](replay-manifest.json)、[validation.json](validation.json)、三个场景的已保存请求/原答/数据库快照/HTTP读回，以及比较接收、Schema和v7反馈的局部修改。HTTP并行变更不在范围内。审计没有运行测试、重放脚本、模型、网络或数据库；仅新增此文件。

## 实际执行与保存

已只读核对13对请求/原答与各自数据库工件一致；usage合计输入145,281、输出37,777、总计183,058 tokens，费用未知。三Run分别使用原6次调用、131,072 tokens及1500秒限制，没有提高预算或以预算耗尽解释拒收。13次是三Run合计，不是一个Run的调用数。

| 场景 | 实际模型调用 | 总tokens | 保留的最终问题 |
| --- | ---: | ---: | --- |
| B01 | C3×2、Deep×1、C6×2 | 74,030 | 两份C6均声明三成员影响，但impact依据未覆盖A2，严格接收报`delivery_source_coverage_missing`。 |
| H01 | C3×1、Deep×2、C6×1 | 44,069 | 指定B01没有可用结论，原答仍给`unchanged`并沿用本轮前序判断作比较，报`comparison_not_available`。 |
| H02 | C3×2、C6×2，无Deep | 64,959 | 两份C6的impact均声明三成员但`support_ids=[]`，报`delivery_source_coverage_missing`。 |

三个Run均为`completed`，停止原因均为`partial_analysis_saved_conclusion_rejected`；对应Result均为`rejected / unavailable / partial`、`conclusion=null`，当前判断均为空。执行收尾不代表最终结论成功。B01和H02的最终拒收能由原答与冻结范围/来源映射直接解释，不能因正文写了待复核而放行。

11份已保存HTTP读回均为200；Result、H版本及当前判断与快照一致。B01无H；H01和H02各四次请求中的H正文、版本、原适用范围及`human_statement`角色与冻结C1一致。H02仅覆盖进程成员，原文明确是模拟业务反馈、不是实际生产授权，也未附审批原件；不能将它作为通常有效授权陈述被正确采纳的正向验收。

## 不可用比较的程序修复

`comparable_source_ids`抽取原接收条件：只有程序判定`eligible`且实际存在指定Result引用才可比。接收端原有初次比较、可比基线及当前来源要求保持；没有放宽成员范围、角色、原件保护或最终采用条件。

配置C6生成Schema在不可比时只允许`not_comparable`和非空说明，初次无比较仍由程序恢复，可比Result仍保留原可选比较种类。`FinalReview`向v7反馈传入同一比较信息；新错误定位`comparison.kind`或`comparison.summary`根字段，保留原值和允许值，不改模型原答。混合其他错误仍保留完整诊断，纠正仍使用既有最多一次流程。

[离线回执](comparison-fix/summary.json)及代码显示：H01旧原答在新Schema下因`comparison.kind`被拒绝，严格接收仍是原`comparison_not_available`，独立局部分析保留、最终结论不可采用。新反馈为555字符，与[纠错预览](comparison-fix/C6-correction-preview.json)一致。记录的4项定向检查通过；本审计未重跑。真实H01使用修复前程序，新反馈未发给模型，不能声称纠正效果已验证。

## 重放与原失败

只读核对最终9项源码/脚本/报告摘要、重放清单126项文件摘要、离线修复所列115份原文件及5项当前源码摘要，均匹配。B01/H01/H02分别对应`plan.json`/`plan-v2.json`/`plan-v3.json`及驱动v1/v2/v3，实际plan hash与execute-intent一致，驱动快照hash与plan一致。各例旧summary保留的基准plan hash不能替代这一实际映射。

B01、H01的驱动异常发生在业务执行后的read_run序列化阶段，原异常未改写。随后只读导出确认Run已结束并取得GET；没有为修正驱动重新派发模型。Git基点和模型源码补丁、完整请求、Schema、原答和来源映射已留存；本审计未实际应用补丁或执行重放，也不宣称当前数据库重新查询仍会获得同材料。

## 必须保留的未通过边界

- 三例知识查询的向量集合读取成功，但嵌入POST均503，`knowledge_embedding_request_failed`；本批未取得新知识正文，不能验收知识正常检索后的效果，也不能核销该运行失败。
- B01第二份C3遇`observed_original_fields_exceed_statement_contract`，属于原观察字段装配容量约束，不能统称为模型引用错误或由本次比较修复追认通过。H02两份C3的`answered_question_needs_sources`及各最终拒收同样保持。
- H01增加了历史、比较上下文及不同查询时刻，并非仅改变H的受控A/B。名称/标签推断自动化、时间邻近推完整行为链、查询状态混写等已记录正文问题仍未通过；输入与引用合法不能证明正文真实。
- 本机4177仅有静态追加回执，不构成在线入口或生产发布验收。主调查仍**31/41**，任务3.16真实效果、M01/M02及F02不核销；未归档、未部署模型修改，也未以本审计要求追加采样。
