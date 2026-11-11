## Why

告警分诊（A）、事件诊断（I）、Case 调查（C）和人工反馈（H）需要贯通实际输入、模型判断、保存及读取。现有组件已有分批验收，剩余问题是结论依据、H 对下一轮的实际影响、真实知识使用、正常操作接线和自动处理。

当前交付基线为 21 r1，数据库 29 表、462 列。存储与读取已核验，模型正文质量仍为 NOT_PASSED；主任务为 31/41。状态和证据以 [PROGRESS](../../../PROGRESS.md)、[当前任务](tasks.md)为准，不把历史批次的环境或限制当成当前配置。

## What Changes

- 沿现有 A/I/C/H 职责补齐正常功能，保留冻结身份、来源角色、成员范围、历史结果和失败原件。
- 基于[已完成审计](../../../docs/investigation/investigation-flow-review-20261111.md)，按 [后续功能顺序](design.md#后续工作顺序)推进；[ground-case-conclusions](../archive/2026-11-11-ground-case-conclusions/proposal.md)已交付限定程序范围，持续模型问题按负责人决定后置。下一项为 Case/H 正常操作，再推进实际知识使用、页面数据对应和自动处理；复用既有证据，不重复全面审计。
- 复用已完成的来源范围、Finding 角色、有限纠正和读取能力；告警字段合同保持稳定，数据库设计调整依项目确认规则另行处理。
- Q 问答仅保留明确未实现的接口，评论附件、探索保存及外部响应继续单列，不因表或路由存在认作功能完成。

## Capabilities

### New Capabilities

- `socai2-investigation-data`：A/I/C/H 职责、来源、范围、结果与页面读取。
- `socai2-case-ai-reservation`：Q 的三个预留接口及未实现、无业务副作用合同。
- `socai2-case-investigation-workspace`：Case 操作、当前判断与依据覆盖、历史、人工版本及下一轮的最小闭环。

### Modified Capabilities

无新增范围。本 change 的增量规格仍是目标合同，完成事实由任务和回执分别说明；历史自动调查链不因本 change 自动切换。

## Impact

实现入口为 `services/api/app/socai2/`、相关路由、Fusion 接线及原型的数据适配；权威字段、API、模型输入输出统一从[前后端交接](../../../FRONTEND_BACKEND_HANDOFF.md)进入。迁移 123–126 及已确认表设计保持。

后续功能遵循本地实施、少量直接边界检查和一条完整路径、交接及变更范围独审后，一个 change 统一发布和推送。达到本次功能目标即停止加测；不默认重跑完整审计、全仓/全表/全接口或可用性矩阵。各功能子 change 如实记录实现与发布，不扩大主任务完成范围；[整理前原文](../../../docs/handoff/history/2026-11-11-local-cleanup/investigation-change/proposal.md)保留各批次范围与原未完项。
