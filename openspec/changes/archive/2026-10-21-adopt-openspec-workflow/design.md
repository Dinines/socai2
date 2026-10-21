## Context

原范围、路线、批次卡、回执及来源清单已经存在；用户要求接入OpenSpec，并不要求重新定义迁移完成或执行下一批运行操作。当前下一项仍为C03-R02，前置R01只完成代码隔离与worker OFF部署。

## Goals / Non-Goals

目标是让下一实施者能从根AGENTS找到唯一活动change、任务、规格增量、验证与独审要求。保留既有文档职责，不迁移或重写冻结证据，不改变业务服务。

## Decisions

1. 使用当前已安装1.13.0的CLI及其自带schema/templates，`init --tools none --language zh-CN`。根AGENTS和CLI足够接入；不安装工作流技能或个人slash commands，避免改变其他项目工具配置。
2. 将规则放入 `openspec/config.yaml`，入口和执行约束写根AGENTS；scope/roadmap/completion-plan/PROGRESS/冻结回执继续各自维护权威内容，不再复制全量目标。
3. 接入本身是工具/文档change，使用 `skip_specs: true`。不为满足validator虚构业务规格；主规格逐批从实际验收的change同步。替代方案是倒填全量已迁功能，缺少独立逐项规格验证且容易混淆历史事实，因此不采用。
4. R02建立独立活动change，提供目标规格、执行设计和未勾选任务。输入/hash、具体operator及资源额度待按原执行卡冻结；计划产物齐全不允许启动运行。
5. 独立审计之后归档本接入change并复核CLI、链接及业务文件保留。归档只记录接入完成，不归档R02。

## Risks / Trade-offs

- 双重文档事实冲突 → 用职责映射及链接衔接，冲突先对齐，不覆盖旧回执。
- CLI状态显示artifacts齐全被误当准入 → proposal、tasks、入口均明示R02未执行、任务未勾选及运行前冻结条件。
- 工具/文档change没有产品spec → 用工具支持的 `skip_specs: true`，不称当前OpenSpec已覆盖全部服务端能力。
- OpenSpec产物夹带秘密 → 仅记录受控位置与hash，不复制凭据、隐藏推理或原始敏感材料。

## Migration Plan

只增加本项目OpenSpec文件并更新四处文档入口；严格校验、独审后归档。无需部署或数据迁移。若撤回此接入，移除本批文档入口和新目录即可；不操作运行服务或历史证据。
