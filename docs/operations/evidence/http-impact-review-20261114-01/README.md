# 调查接口影响评估证据

2026-11-14。评估范围、结论和后续动作见[评估正文](../../../integration/investigation-api-impact-20261114.md)。

- `contract-and-formal-readback.json`：本机正式18024公开OpenAPI读回；现行工作树与正式业务Schema比较。在明确排除另一change的可信接入差异后，71业务操作、148业务结构保持。正式153结构包含另5个认证结构。21现有转发不可读；正式业务GET既有凭据返回401，没有绕过或变更服务来完成评估。
- `freshness-compatibility.json`：同一只读PostgreSQL快照、同一既有I Run，正式冻结版本与当前版本实际新鲜度SQL分别得到stale/current。无数据更改。
- `source-comparison.json`：按正式发布manifest记录与当前工作树文件hash对比，用于定位差异；不是发布清单或全量测试证据。
- `peer-assessments.json`：负责人授权询问的两个现有聊天的评估原文摘录及身份。调度最新结论以主流程第10节为准；阶段一聊天提及的旧H-only设想已经被规划聊天标为撤回，不作为当前方案。
- `workflow-coordination.json`：后续启动/任务读取的目标设计确认及产品供给回执；规划侧和阶段一侧确认完整跨主体目录/统计、完整步骤工件遍历的待补要求。Q1–Q6及第8节具体HTTP合同已双向确认，四项最终修订和“讨论确认后可以实施”授权见final_http_contract_agreement；按统一版本推进，不作为已实施证据。
- `product-requirements-check.json`：按产品反向提出[供给要求](../../../integration/product-api-data-requirements-20261114.md)，核125项唯一编号、22/15/88分组、32组数据责任、来源及本地链接。只做文档检查，不是125项功能测试或业务验收。
- `product-updates-readback.json`：后续Q1–Q4及本聊天“关联规则已定”的确认来源、本机4173只读脚本核对和同步文档。定向/综合、默认补查、Case续建/唯一事件接收者、两级关联列表及事件诊断覆盖已纳入需求；同ID材料重新分诊提案撤回。没有修改业务程序、数据、服务或Swagger实现清单。

执行时先遇到代理/转发连通失败，随后本机公开OpenAPI经直连读回；未修复网络或正式接入配置。未新增模型、业务写入、部署或Git操作。大原件问题的证据等级为正式旧源码检查及既有步骤6保存读取，不记为本轮正式TCP复现。

