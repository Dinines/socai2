# D5a Deep 局部输出：本机实施与当前验证边界

2026-11-17。**D5a尚未完整验收。** 核心接收/保存/C6取数已实现，直接检查及独立母本接收通过；唯一真实批次因测试驱动切点错误，只验证了Deep无可用答案时C6继续，未验证有效Deep答案经真实PG进入C6。按负责人先统一测试模块与工作台需求的最新安排，保留本步修改和证据，不新派模型或Run、不推进D5b/c、不部署。

## 已实现与直接证据

- Deep完整/局部正文均进入`case_deep_delivery`；完整answer独立保留，四控制字段不齐/不合法时不形成可派发Decision。正常与异常共用一条接收路径；生成Schema、枚举、预算不变。
- 每模型子步保存严格stage_delivery，验证实际原件、span/hash和值；Deep摘要关联回执，完整答案经既有C6构造器按prior_analysis传递。
- [direct-02](direct-02.txt)：68项相关检查通过，1项不相关历史展示检查未纳入。覆盖完整stop/length、答案与控制独立、半答案、非法binding、重复键、质量保留、C6实际构造及C3必要回归。独立测试方[receiver-01](../test-deep-unit-continuation-d5a-20261117-01/receiver-01.json)对真实母本10个切点通过，含3个固定随机切点，0新模型/PG/HTTP。
- [direct-01](direct-01.txt)保留首次68通过/1失败：`test_history_duplicate_presentation_preserves_c3_and_final_dependencies`在C3输入视图历史记录数量处得到0而非2；本步未改该输入选择路径，未在D5扩展修复或宣称该项通过。

## 唯一真实批次的实际结果

[原始驱动](real-01/validate-source.py)、[实际调用](real-01/calls.json)、[数据库快照](real-01/snapshot.json)、[原验证失败](real-01/result.json)保持原样。当前`validate.py`已修正切点定位及完整/部分输出的断言，仅供未来新批使用，**未再次执行**。

本机显式隔离PG `v12_upgrade_dev`（127.0.0.1:28413）和既有Redis新namespace；原告警材料来自新02保存包，在新租户/告警/Case身份下调用当前任务入口。没有重投Kafka、复制旧Run结果或修改21业务数据。

| 项目 | 实际值 |
| --- | --- |
| Case | `549230d4-387c-5eeb-b53b-7c8fab67550b`，4成员 |
| Task / Run | `7a738152-0eba-4f6a-a7ef-b71a6b16e647` / `1b2e500c-acdf-4025-875c-df7ce0312933` |
| Result | `53cf0290-04ba-41f2-bf4e-3a9ac4d6dcc3` |
| 保存数量 | 1任务、1attempt/Run、17步骤、51工件、1Result |
| 真实模型 | C3、Deep、C6各1次，均原始stop；共29462 reported tokens，费用未知 |
| Deep受控返回 | 实际为`{"answer":null,"action":"ans`；原完整真实答复另存verification工件，不替换实际接收片段 |
| Deep处理 | partial回执保留显式null与控制缺口，无有效答案/Decision/查询；Deep阶段failed，C6继续 |
| 最终结果 | Task/Run completed，attempt本地ended；Result accepted / uncertain / partial，C6结论逐字保存 |
| 质量 | C3 1条、C6 8条诊断保留；正文未全面验证，不因诊断重采样 |

切点错误来自测试驱动用首次出现的`"answer"`定位属性，误命中了`action`的字符串值，再截到了后面的null。程序依真实接收内容没有编造答案。原批验证又将部分解析的`conclusion_modified=null`要求为false，因而在HTTP之前失败。这些是验证驱动错误，不能据后来修脚本追认原批目标通过。

## 同Run只读收尾

[readback-01](readback-01/result.json)保留核验脚本误用数据库/HTTP状态字段的失败；修正后[readback-02](readback-02/result.json)与[读取报告](readback-02/http-validation.json)核同一已结束Run：69次ASGI GET，实际目录分页发现全部17步骤/51工件，content_url与PG逐值一致，严格回执来源校验通过；25张相关表读取前后摘要一致，0新模型/0新业务Run。228份运行源码/profile在原执行前后摘要相同。ASGI不等于21 TCP或4177浏览器。

当前读回证明的是“Deep无可用答案→真实C6继续→原结论保存读取”，不能替代“有效Deep答案→C6”的实际存取链。独立PG/HTTP复核、有效答案代表批次及完整D5a出口仍待统一安排。没有更新4177展示账本、发布或推送；C6自身截断、超时/断连、比较资格属于D5b/c，均未据此核销。
