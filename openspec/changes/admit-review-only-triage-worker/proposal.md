## Why

C03-R01只证明review_only_v1代码隔离和worker OFF部署，尚未证明新profile由真实服务main消费并持久交付。本change对应当前路线C03-R02，沿用[人审准入卡](../../../docs/operations/c03-review-only-profile-plan.md)的有限窗口合同。

**状态：待补齐运行前冻结，尚未执行或验收；任务全部未完成。** 本change不是执行回执，不授予永久常驻或真实响应能力。

## What Changes

- 为A/B各一条全新输入定义有限真实main消费与首次结果恢复合同，最多两次实际SDK发送、最多40000预留单位；预留单位不等于实际usage。
- 用新operational group显式冻结main fused各partition end起点，保留旧main及全部历史组/unknown，不以latest跳过历史。
- 验原建议未审核、effective needs_review/null、canonical Alert AI字段保持及0自动效果；验真实reader、PG/Kafka及保存/确认失败恢复。
- 在同R01镜像下做有界启动/停止与最多一次fresh进程恢复周期，最终OFF；独审后才可认定所选窗口准入。

## Capabilities

### New Capabilities

- `review-only-resident-admission`: 所选A/B和两条新输入的有限main消费、人工复核交付及同Run首次结果恢复合同。

### Modified Capabilities

无现成OpenSpec主规格需要修改。R01及更早回执作为前置证据，不倒填为本change任务。

## Impact

计划仅涉及临时Agents配置、受控operator、两条新业务输入及验收/审计文档；不新增产品源码、依赖、DDL或镜像build。真实运行前必须冻结输入/hash、所有具体操作上限与恢复配置。C04—C11仍待验；自治模型质量失败保持，真实响应不开放。

前置：[R01回执](../../../docs/operations/c03-triage-review-only.md)、[来源清单](../../../docs/handoff/c03-triage-review-only-source-manifest.json)、[完成计划](../../../docs/operations/completion-plan.md)。
