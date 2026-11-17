# 阶段一步骤3：C3正常输出合同

2026-11-14。状态：**本地实现、直接检查及保存读取通过，未发布**。所属[OpenSpec change](../../../../openspec/changes/complete-socai2-investigation-chain/tasks.md)；实施前已将目标、步骤和判据写入[阶段一第三步](../../../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#本轮步骤3c3七部分8192额度及最多5个核心发现)，并先运行严格校验。主change仍31/41，模型正文质量NOT_PASSED，补答及后续步骤未完成。

## 目标、步骤和实现

本轮只统一新C3正常一次七部分、输出上限8192和最多5个核心发现。实施顺序为配置/冻结边界→提示与生成Schema→接收及0/5/6项检查→新隔离PG保存和HTTP读取。保留步骤1/2结论与引用诊断行为；C6仅复用既有收口作为下游读取验证。

| 落点 | 实际变化及效果 |
| --- | --- |
| `investigation-policy-case-v1.toml` | 当前显式Case策略只有`model.output_tokens.C3`从4096改为8192；A/I/Deep/C6、Case总预算及C6预留相同 |
| `case-input-v1.json` / `runtime_policy.py` | `c3_output`配置增加`socai2.c3-output.v1`版本和`max_findings=5`；加载检查版本、整数范围和提示占位符，不静默回落 |
| `case_model_boundary.py` | 提示一次返回summary、members、findings、questions、domains、conflicts、followups；数量由配置替换，并随profile/hash冻结到`case_boundary.c3_output` |
| `case_output_adapter.py` | 只约束新C3 Schema及接收最多5发现；0项合法，6项记`case_finding_limit_exceeded`，不裁剪或通过partial重新接收，不归为引用问题 |
| `baseline_analysis_contract.py` | 移除受影响C3提示中的固定3发现/1800输出目标，按Schema上限；共享Analysis容量24及C6合同保持 |

固定成员逐一覆盖、五个模型业务问题、四领域、最多2条可为空的followups保持，程序另补coverage为第六问。旧冻结边界无新`c3_output`时保持原接收容量，新版本配置无效时明确失败。数量上限不限制成员数量，不要求凑满发现或补查。

[修改前指纹](baseline.json)、[本轮六个实现文件差异](implementation.patch)及[范围核对](scope-checks.json)可对照：238份既有源码/测试/策略只有6份实现配置变动，其余保持；PG验收使用的145份源码/配置/入口与最终文件相符。补答、执行、调度、Deep/C6、输入筛选及预算路径与本轮开始前字节相同。新增两个本步直接验证文件，没有迁移或HTTP合同变更。

## 直接检查

以下命令完成48项检查，日志见[offline-tests.txt](offline-tests.txt)。新增覆盖0/5接收、6项拒收且不裁剪、单配置同时驱动提示/Schema/接收、旧冻结/C6兼容、无效版本/配置拒绝及配额不越界；复用Case输入、程序装配和步骤2引用诊断检查。

```sh
PYTHONPATH=services/api:services/api/tests .local/conda-envs/socai2/bin/python -m pytest -q \
  services/api/tests/test_socai2_c3_output_contract.py \
  services/api/tests/test_socai2_case_model_boundary.py \
  services/api/tests/test_socai2_case_program_output.py \
  services/api/tests/test_socai2_case_citation_quality.py \
  services/api/tests/test_socai2_runtime_policy.py --tb=short
```

定向[Ruff](ruff.txt)及[OpenSpec严格校验](openspec-final.txt)通过。没有重跑全仓；前两步登记的既有输入裁剪/历史查询展示断言不在本轮修复范围，原失败保持。

## 保存和读取

[run.py](run.py)按[config.json](config.json)显式使用隔离PG `v12_upgrade_dev`及当前Case策略。新批`attempt01`一次完成，没有重派旧Run；完整范围、配置和源码hash在[plan.json](attempt01/plan.json)。复用已有2A→1I夹具建新Case，用模型替身验证C3→空补查→C6，查询回执也是替身，真实模型及外部来源调用均为0。

| 标识 | 值 |
| --- | --- |
| Case | `6fef2141-2ef0-4985-9280-e3e9a6aabc9e` |
| Run | `3af18c13-7e38-4e47-b2d0-6f3f3d5a0df9` |
| Result | `ab5996bf-703b-4dac-9a84-65c71cddaff4` |

[checks.json](attempt01/checks.json)直接核对：

- C3只调用1次，保存的实际请求`max_tokens=8192`，七个必需顶层字段、生成Schema `maxItems=5`及冻结数量一致。模型给出5项发现、完整成员/五问/四域，空followups不产生Deep、查询、重分析或补答。
- 原答先保存，`model_response`原始返回与原答工件相同；派生结果、C3汇总及hash一致。5项发现原文字节（包括前后空白）保持；程序coverage使保存结果有6个问题。
- C6实际输入以`prior_analysis`读取全部5项C3原文，完成Result、报告与当前判断保存。既有服务的重复读取直接返回保存结果，没有再次调用模型。
- 44次现有ASGI GET读取Case、Run、Result及41份Case工件，正文/文本与PG快照一致；读取前后快照相同，没有写入或新派发。使用既有路由及真实读服务，认证/服务依赖由验收替身覆盖，不冒充正式TCP或生产验收。

证据包括[数据库快照](attempt01/database.json)、[实际替身请求/原答](attempt01/substitute-calls.json)、[HTTP读回](attempt01/api-responses.json)、[执行记录](attempt01/execution.json)及[完整性清单](attempt01/manifest.json)。总计5次模型替身：夹具2A+I，Case C3+C6；补答0次。Result保持`accepted/uncertain/partial`并自动采用；partial、合成材料和正文质量未检查保持，不能据此宣称完整取证、模型准确率或所有案件均能在8192内完成。

按既有`update_processing_audit.py --batch .../attempt01`追加本机静态材料，登记7条记录；原286份非索引文件字节保持，新页关联本Case及上游3个Run，[静态核对](audit-readback.json)和[更新前指纹](audit-before.json)可查。只读静态核对曾错误推断文件名及Run数量，改用保存的detail和数据库Run集合后通过，未重新执行业务。实际4177仍是SSH转发，本轮没有替换服务、发布页面或处理RV12展示问题。

## 停止边界

补答触发、截断边界解析、冻结上下文重带、初答/补答/合并保存仍留步骤4。本轮不扩大Run预算，不实施超限原件存取、补查能力或4177展示修复；旧工件、失败、unknown及质量NOT_PASSED不回写。没有真实模型采样、部署、提交或推送。本步保存读取已通过并在此停止，阶段一整体及主change未完成，结束审计和统一发布仍待整体收口。
