# 一轮固定调查：真实知识、局部纠错与保存读取

2026-11-13。沿用06批B01/H01的Case、三成员材料、原A/I及H01核查意见，只显式创建一个新Run。正常知识连接保持至Run结束；共3次生成调用、一次嵌入，没有重派旧Run或追加采样。最终 **accepted / uncertain / partial**，Result及采用的当前判断保存、读取一致；**正文质量NOT_PASSED**，接受不代表主张已核实。

## 本次直接结果

| 实际步骤 | 输入正文 | 调用结果 |
| --- | ---: | --- |
| C3 | [10,894字符](flow/R01/review/call-01-C3-input.txt) | 首答接受，程序v2恢复原观察；未提出补查，Deep未派发 |
| C6首答 | [17,209字符](flow/R01/review/call-02-C6-input.txt) | `delivery_source_coverage_missing`：影响段只支持进程/连接，却声明三个成员 |
| C6一次纠错 | [正文](flow/R01/review/call-03-C6-input.txt)保持17,209字符，另加1,165字符反馈 | 原影响范围A1/A2/A3收窄为A1/A3，支持来源不变；同时调整影响问题回答措辞，末答接受 |

[逐调用汇总](flow/R01/summary.json)与[原答对照](review.json)保留实际请求、提示/Schema、配置、原答、校验及读取关系。完整纠错请求在[call-3-intent.json](flow/R01/calls/call-3-intent.json)，含前次原答和局部反馈。程序没有代模型改范围或正文，范围变化来自真实末答。

C2沿原profile完成一次9输入的嵌入及9条知识查询，技术解释/取证指导两用途返回同一AN0846，程序合并为一张448字符业务卡；C3与两次C6实际请求各出现一次，保持用途、范围和参考角色。三份原答的结构化引用均未使用该知识，不能据“进入输入”宣称知识改善了判断。本次复用A/I，登录A原失败、I部分交付仍保留。

生成用量32,981输入＋8,339输出＝41,320tokens；嵌入用量另记查询回执，费用未知。沿用6次调用/131,072tokens/1,500秒预算，未提高额度。临时知识SSH连接在本次Run结束后关闭，不代表常驻转发或旧503根因已经修复。

Case `ca9de71e-0f0c-5075-8fd1-eb5257aefbd7`；Run `ee0f3e6f-95f4-4a81-aff7-16eef347d003`；Result `fbe3de16-515c-4bca-b190-c50e2a00b0e8`。H修订 `02c1aff9-e9f6-4b54-9d39-489c12c4e06a`原文及附件不变。显式指定的旧Result `987ebbe7-df55-42a5-8349-6b606cfaf40a`为拒收结果，不可作历史综合判断比较。真实隔离PostgreSQL为`v12_upgrade_dev`；4次原ASGI处理器GET（Case/Run/Result/H）200，并与数据库逐项核对，不冒称生产或TCP验收。

## 与既有案例的参照

| 案例 | 人工/知识条件 | 生成调用 | 最终结果 |
| --- | --- | ---: | --- |
| 06 B01 | 无H；知识嵌入503 | 5 | C3程序观察容量阻断；C6影响缺成员依据，拒收 |
| 06 H01 | 核查意见；知识嵌入503 | 4 | 不可用历史却输出unchanged，拒收 |
| 06 H02 | 限定模拟H；知识嵌入503 | 4 | C6影响缺依据，拒收 |
| 本次07 R01 | 原H01意见；正常知识；当前程序 | 3 | 一次局部纠错后接受并采用，正文质量未通过 |

旧三例完整材料见[原对照](../fixed-investigation-20261113-06/comparison.md)。程序版本、查询返回和历史上下文不同，本表不是受控A/B，没有独立真值，不报告准确率或因果收益。115份06批原流程文件摘要不变。

## 保留的质量问题与本次程序修复

末答仍用主机/账号名称推自动化；威胁情报实际未查询，却在限制中写“查询无结果”；比较种类虽为not_comparable，说明仍声称与历史一致，所指是本轮A/I/C3中间判断。这三项记为NOT_PASSED，原答及已保存采用记录保持，不回改历史制造通过。

比较说明属于程序已知事实，本次随后实现[不可用比较的固定装配](../case-fixed-comparison-20261113-01/README.md)：新C6请求不让模型生成该字段，由程序恢复请求前冻结的not_comparable及固定说明。有可用指定历史结论仍由模型比较。此修复只作4项直接检查、1条隔离库替身存取和旧答离线回放，**没有再调用真实生成模型**；本Run记录仍是修复前真实原件。

## 原件、展示与重放

原[export/database.json](flow/R01/export/database.json)及其清单不变。首次4177严格导入发现快照含历史I诊断、却遗漏其source Run，错误保留在[processing-audit-update.json](processing-audit-update.json)。随后只读补取相同Case实际关联的历史来源，另存[workbench-export](flow/R01/workbench-export/manifest.json)，Case/Result/H/采用判断等逐值保持；成功导入本机静态包79→80。没有重新调查、发布在线4177或改动原快照。

离线`review.py`最初遗漏了影响问题回答的措辞变化，断言失败保存在[review-attempt-01.json](review-attempt-01.json)；现在同时报告两处真实变化。不会改写原答，也没有因此重跑模型。

`summarize.py`从本批原快照导出实际输入/原答，`review.py`核对知识、纠错差异和旧文件摘要。可在记录的源码版本下离线运行：

```bash
.local/conda-envs/socai2/bin/python docs/operations/evidence/fixed-investigation-20261113-07/review.py
```

本次运行源码见[source-replay.json](source-replay.json)、[冻结计划](flow/plan.json)和补丁；后续比较修复有单独源码包。`run.py`是有副作用的真实执行入口，既有批次不重派，未来确需执行必须使用全新批次及显式私密profile。回放无需新模型调用。验证摘要见[validation.json](validation.json)，限定结束审计见[比较修复审计](../case-fixed-comparison-20261113-01/audit.md)。HTTP字段、数据库表、部署和流式流程均不变；主调查仍31/41，不以本次接受核销知识合理使用或整体质量。
