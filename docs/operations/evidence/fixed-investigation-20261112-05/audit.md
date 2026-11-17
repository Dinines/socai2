# 固定流程第五批限定独立审计

审计日期：2026-11-13。审计者：未参与本轮实现的 `/root/historical_release_audit`。

结论：本批知识传递、实际调用、失败保存读取及已有静态发布回执的限定审计通过，未发现本批拒收属于程序误拒。完整固定流程与模型质量仍未通过；主 change 保持 **31/41**，F02、M01 保持未通过，不具备整体归档条件。

## 审阅范围与方法

只读核对本批保存的调用原件、知识导入/索引回执、数据库导出、HTTP 读回及静态发布回执，并对照相关引用接收规则。未修改运行代码、旧原答或证据；未调用模型、数据库或网络，未新增或执行测试。此次仅新增本审计文件。

主要依据：[数据库及导出清单](flow/export/manifest.json)、[保存读取核对](flow/readback-checks.json)、[实际输入清单](flow/input-summary.json)、[调用原件](flow/Case/calls/call-6-receipt.json)、[知识回执](flow/knowledge-ready.json)和[静态发布回执](workbench-publication.json)。

## 已核实的功能事实

- 全部 A 分诊沿用原 Run：登录分诊失败、另两条分诊有效，不将复用写成重新通过。新增 I 2 次、Case 6 次真实模型调用，共 **97,835 tokens**；费用未知。8 份实际请求 `body` 与保存的 `model_request` 相等，8 份响应原件与保存的 `model_response` 相等；导出文件摘要匹配。I 第二次引用校验接受，但其 Run 交付状态仍为 `partial`。
- 完整 AN0846 正文通过正常 API 新导入为 1 块、845 字符，索引至本批独立 collection；SQL 读回与提交正文一致，4 个旧块保持。导入后脚本曾误将预览 DTO 当作全文 DTO；随后核对已提交全文并完成此前未执行的索引，没有重复导入。见[导入](flow/knowledge-http/import.json)、[完整正文读回](flow/knowledge-sql-readback.json)及[索引](flow/knowledge-http/index.json)。
- C2 按技术解释、取证指导两用途返回同一文档版本的 2 行，合并后的 448 字符知识正文实际进入 C3、两个 Deep 及 C6 请求。来源保持 `source_label`、原知识工件引用及进程成员的查询适用范围；知识只作辅助，不计入本案成员/结论覆盖。授权 Deep 未结构化引用知识；行为性质 Deep 引用 `N5_S106`。C6 的行为性质问题保存了原工件 `$.rows.0` 的知识引用，GET 同值；原综合结论中的知识引用没有使该结论被采用。
- 三条 Case/Run/Result GET 均为 200，核心正文、引用和状态与 SQL 一致：Result 为 **`rejected / partial / conclusion=null`**，Case `current_assessment=null`，无新增 Case assessment。Case Run 的 `completed` 表示执行及失败结果保存已收尾，**不表示 C6 结论成功或可采用**。

## 保留的实际失败与质量问题

- C6 两次完整原答的 `recommendations[1].source_ids` 均为 `N6_S9, N6_S23, N6_S9, N6_S10`，重复 `N6_S9`。首次反馈明确指出 `duplicate_source`；一次纠正后仍重复，接收器报 `delivery_source_not_visible_or_duplicate` 与实际原答相符。独立有效分析按既有 partial 规则保留，未追认总体结论。
- C3 两次仍将 `N3_S238` 用作 A3 成员依据；该来源是案件外历史目录，角色为 `source_label`，本案 `alert_ids=[]`，原记录主体为另一条案件外告警。第二次没有纠正该范围错误，局部结果与拒收信息保留。
- I 输入实际提供了登录成员的时间、账号、主机、动作和源 IP，模型仍写“无有效原始记录……可供评估”；这属于忽略已给材料，不能归因为输入删除。前序及 Deep/C6 仍从主机名、用户名或来源标签推断自动化流程、同步验证模板，合理性未被证实。知识已传递并被引用，不等于 F02 合理使用效果或 M01 正文质量通过；不追加采样追求通过。

## 静态发布与本机入口边界

[workbench-publication.json](workbench-publication.json)记录远端静态追加 **42→43 条记录**，新增 1 条、无刷新旧记录，核验 **80 个文件／81 次 HTTP**；旧记录、旧文件和无关记录保持，容器不变，运行源码未变，发布动作没有模型调用或数据库写入。本次补审核对该已保存回执，未重新探测网络；这不是本轮模型源码部署回执。

本轮最新本机检查由主代理提供，本审计未复测：本机 4177 无监听、无 SSH Control socket；LaunchAgent 为 `spawn scheduled`，日志显示 Windows 中转 `192.168.3.57:2221` 超时或无路由。故**远端静态发布成功不能表述为当前本机 4177 入口可用**；回执中的本机 URL 仅标识页面路径，不构成当前可达性证明。

本批不核销完整业务流程、模型质量、历史知识召回效果或其他未验范围；不声称主 change 已归档、模型修改已部署或 Git/父项目引用已交付。
