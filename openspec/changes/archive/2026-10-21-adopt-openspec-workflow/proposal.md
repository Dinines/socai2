## Why

用户于2026-10-21要求使用OpenSpec作为项目实施规范。现有迁移执行卡和冻结回执需保留，后续变更需要统一的需求、设计、任务和独审入口。

## What Changes

- 初始化本项目OpenSpec，使用已安装1.13.0 CLI、`spec-driven`与中文上下文。
- 在根AGENTS、README、文档入口及PROGRESS接入“提案→规格增量→设计→任务→验证→独审→归档”。
- 给下一批C03-R02建立待执行change；不复制旧SOCAI任务，不倒填R01或更早批次。
- 明确现有文档的职责及运行前冻结条件，保留原授权和高风险审批边界。

## Capabilities

### New Capabilities

无。本次仅变更实施工具和文档，`.openspec.yaml`设 `skip_specs: true`。

### Modified Capabilities

无产品规格级行为变化。R02的产品目标在独立活动change中描述，尚未实施。

## Impact

仅影响 `openspec/`、根AGENTS、README、PROGRESS与文档导航。0运行源码、依赖、模型、业务数据、远端配置或部署变更；不安装个人快捷指令，不提交或推送Git。
