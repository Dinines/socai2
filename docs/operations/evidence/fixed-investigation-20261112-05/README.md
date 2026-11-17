# 固定流程：精简输入与完整知识实际执行

2026-11-12 执行，2026-11-13 收尾。当前源码、本机隔离 PostgreSQL `v12_upgrade_dev`、Qdrant、真实嵌入和项目内网模型；API 使用原业务处理器的 ASGI 调用，不是21生产调查。没有修改 HTTP 合同、数据库表、消费者或流式行为。

**知识进入实际请求、执行及失败保存读回已核对；完整固定调查和模型质量未通过。** Case Run 的 completed 表示执行已收尾，正式 Result 为 rejected/partial，conclusion=null，没有当前采用判断。不能把可打开的页面或生成报告当成 C6 成功。

## 实际输入

以下正文由 `verify_readback.py` 从实际派发请求逐字导出，并核对数据库工件相等，没有手工压缩。字符数仅计算首份请求的主业务材料；系统指令、Schema、工具目录及有界纠错消息另见原始请求。

| 环节 | 主业务正文 | 实际调用原件 |
| --- | --- | --- |
| I | [3,047字符／71行](flow/I-model-input-exact.txt) | [首次请求](flow/I/calls/call-1-intent.json)、[纠错请求](flow/I/calls/call-2-intent.json) |
| C3 | [9,802字符／112行](flow/C3-model-input-exact.txt) | [首次请求](flow/Case/calls/call-1-intent.json)、[纠错请求](flow/Case/calls/call-2-intent.json) |
| Deep：授权 | [12,214字符／124行](flow/Deep-1-model-input-exact.txt) | [实际请求](flow/Case/calls/call-3-intent.json) |
| Deep：行为性质 | [12,258字符／124行](flow/Deep-2-model-input-exact.txt) | [实际请求](flow/Case/calls/call-4-intent.json) |
| C6 | [18,563字符／158行](flow/C6-model-input-exact.txt) | [首次请求](flow/Case/calls/call-5-intent.json)、[纠错请求](flow/Case/calls/call-6-intent.json) |

与此前离线预览的前序 I/C3/Deep 不同，因此不能直接当作同材料的压缩对照。本批没有输入超限，新增生成调用共8次：I两次，Case六次；prompt 77,588、completion 20,247、合计97,835 tokens，费用未知。没有额外重跑 A 或旧 Run；driver 的 A1/A2/A3 是批次标签，模型短号以各请求的冻结映射为准。

## 知识实际经过了什么

1. 从已核对原始 MITRE 数据取得 AN0846 的完整选定内容，845字符；既有导入 API 返回1个完整块。文档 `9a9633d7-e1c3-46f3-ab93-1b85ddb35f66`，集合 `socai2_fixed_input_20261112_05`，4个旧 SQL 块保持，原集合未改。
2. 正常索引使用 qwen3-embedding:0.6b/1024；C2 技术解释和取证指导各命中该文档一次，保留两条检索出处，模型展示合并成一份448字符业务正文。名称、说明、平台、参考日志、核查要点保留，结构内部 ID 不进入正文。
3. C3、两项 Deep、C6 均收到这份正文。授权 Deep 未引用知识；行为性质 Deep 有结构化引用。C6 的行为性质问题引用同一原工件 `$.rows.0`，以 source_label 辅助角色保存，结果 GET 与数据库一致。C6 原 conclusion 也引用知识，但整体结论被拒收，未采用。

[导入/索引回执](flow/knowledge-ready.json)、[SQL完整原文](flow/knowledge-sql-readback.json)、[逐请求用途和引用](flow/knowledge-use.json)。本批专用集合只含这份技术资料，没有重验历史卡检索。引用存在不能证明知识合理改变判断；F02仍未通过。

## 执行、拒收与读回

Case `2ef348f7-1d81-5d11-8d76-18ab8812f37e`，Run `2644edd3-d207-41e7-b78b-a83301f2fbf6`，显式关联事件 `29603d79-aa4e-5fb5-89b3-5264df926793`。登录 A 复用原失败，网络和进程 A 复用有效结果；新 I 一次纠错后保存，delivery_state仍为partial。

C3 两次均错误使用案件外历史目录来源 `N3_S238`，按原规则保留独立有效部分。C6 两次的 `recommendations[1].source_ids` 都为 `N6_S9,N6_S23,N6_S9,N6_S10`；首次明确反馈 duplicate_source，纠正后仍重复，拒收符合原答，未发现程序误拒。模型还忽略了已经提供的登录事实、从主机名/用户名推断自动化流程，M01保持未通过。没有手工删除引用或改写正文来追认成功。

[数据库快照](flow/export/database.json)、[直接读回核对](flow/readback-checks.json)、[实际请求摘要](flow/input-summary.json)证明8份新请求逐值保存，Result、Case GET、报告都保留 null／未采用含义；独立审计另核8份原答相等。这里是失败和局部结果的闭环，不是有效综合结论的闭环。普通厂商/ClickHouse工具未接通，没有新外部日志证据，Deep执行完成不代表问题解决。

## 查阅与操作边界

本机静态包已从72追加到73份。21的4177静态站点从42追加到43份，80个文件及81次静态HTTP核对通过，历史、容器、业务源码和数据库保持，见[发布回执](workbench-publication.json)。本批属于隔离库的保存快照，应使用[归档入口](workbench-readback.json)中的 archive_url，不能用 `#live/<本批CaseID>` 查询21生产库。

2026-11-13 本机入口复查时4177无监听，既有SSH隧道正在重连，Windows中转2221日志显示超时／无路由；当前本机访问尚不可用。远端此前发布和HTTP核对成功与当前本机网络状态分开记录；未为此重启远端服务。可先打开上述本地实际输入及数据库工件。

前置问题全部保留：导入已经201后，驱动误读 GET DTO 中不存在的 content 而停止；未重复导入，`finish_knowledge.py` 用SQL核完整正文，再完成首次索引。初次模型派发被自动审批因目的地未验证而阻止；核实合成材料、公开知识和项目内网模型路由后，同一路径获批执行，见[审批与材料记录](flow/destination-and-material-review.json)。离线读回脚本首次假定 A/I 与 Case 工件同一封装，修正只读取件后完成核对，未因此调用模型或写业务数据。

限定[独立审计](audit.md)不替代主 change 结束验收。主任务仍31/41；当前模型修改未部署，不归档主 change。后续先离线定位 C3 案件外历史引用、C6 重复引用与反馈材料的最小处理边界，不追加模型采样或放宽依据规则；可采用结论及正文质量保留未完，流式仍后置。
