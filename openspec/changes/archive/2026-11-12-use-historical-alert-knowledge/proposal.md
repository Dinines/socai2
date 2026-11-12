# 历史告警知识及模型消费

## Why

用户要求继续知识功能，并明确历史告警信息如何给模型使用。已交付的 C2 知识只有技术解释、取证指导；`history` 是同对象、同时间窗的数据库查询，不是相似案例知识库。沿主调查 3.14 推进本 change，复用上一轮检索、模型边界和 4177，不重开已归档 change。

## What Changes

- 新增显式历史告警知识入库入口：从指定告警的实际材料、分诊、人工反馈生成有版本来源的结构卡片，保存到既有 KB 文档表；不让模型编写“已核实经验”。
- C2 增加 `historical_case_reference` 目标，用已有本地嵌入检索同租户历史案例；排除当前成员，限定明确历史时间范围。原 `history` 查询保持。
- 卡片分别呈现历史观察、检测标签、既往判断和人工陈述。C3 用来比较解释/提出问题，Deep 用来参考验证方法，C6 用来解释差异和建议；不继承既往良恶结论或授权。
- 4177 展示历史卡片来源版本、命中依据、实际输入和输出引用；模型可见与合理采用分别记录。

## Capabilities

### New Capabilities
- `historical-alert-knowledge`: 历史告警卡片入库、检索和按角色消费。

### Modified Capabilities
- `case-purpose-knowledge`: 在已有两个目的之外支持历史案例参考。
- `investigation-knowledge-inspector`: 历史卡片版本及分角色引用展示。

## Impact

本文件是目标合同，不代表已交付。增量涉及 KB API、知识配置/索引/C2、Case 模型输入与内部 4177。复用 `public.aisoc_kb_documents` 与现有向量集合；不新增调查表，不修改告警交接字段、V1 表列、Case 结果或模型输出合同。常规读写接线随功能处理，不设权限专项。

前序证据：[知识交接](../../../../docs/investigation/case-knowledge-handoff.md)、[前次验收](../2026-11-11-enable-purpose-aware-case-knowledge/validation.md)。M01-A/M01-B/M02 保持已知质量问题，不重复采样求通过。只做改动相关检查和一次本地代表性功能链，收口后一次发布/推送并同步父项目。
