## Why

2026-10-31 [详细审计](../../../docs/investigation/design-implementation-audit-20261031.md)确认：进程 Tool 可能混入非进程事件（A01）；概况刷新失败保留旧 Case 正文时，stale 与权限/提交顺序不一致（A02）；Case 未取入已有告警正文和原始材料（D01）。这些问题影响证据含义、正常刷新及调查取材，需要在既有 Case 流程内修正。

用户随后要求“推进执行”；本 change 已完成B1–B3和本地组合验证，部署/真实复验及结束独审待完成。精确状态见[实施记录](../../../docs/investigation/audit-fixes-implementation-20261031.md)。起始源码基线 `5b95138`；最近真实四案例仍为 `512c004/r1`，2/4 流程通过。A03/A04 文档修正已经完成，不重复列为待实现功能。

## What Changes

- A01：`process_activity` 限定进程类事件，返回类别与活动/动作信息，明确“进程活动”不自动证明执行成功；给新查询合同加版本，阻止旧混合类型结果被复用。
- A02：沿同一 summary 行锁，在模型调用前确定请求及失败保旧正文所需权限；成功按新来源模式，失败按旧正文来源模式组装返回值并计算 stale，正常保存已准入尝试的错误/已知用量。
- D01：给 Case 与选定 Alert 增加有来源、指纹及裁剪说明的有界原始材料；冻结材料和模型视图分开，正文/原始 JSON 变化会使新 Run 的历史查询复用失效。
- 保持现有请求参数、预算、Case/Run 归属和同 key 仅读行为；原 Run/报告不回填。新增证据字段兼容读取，旧证据不升级为新合同。
- **BREAKING（条件收紧）：**已有 Case 来源概况的事件，即使本次请求 `include_investigations=false`，刷新也须在模型调用前通过 `cases:read`，以便失败时安全返回原正文。纯基础概况仍沿原权限。错误使用现有 403 合同，不新增权限类型。
- 将本 change 与已有 `fix-case-followup-gaps` 在同一实际版本做一次受影响验证；不重写旧批次结果、不重复实现 required_tools 或压缩逻辑。

## Capabilities

### New Capabilities

- `case-process-evidence`：进程 Tool 的类型、活动语义及查询复用版本合同。
- `incident-summary-refresh`：刷新前权限、失败保旧来源模式及尝试记录合同。
- `case-source-material`：当前 Case 的有界来源材料、模型视图、指纹和历史兼容合同。

### Modified Capabilities

无。现有主规格 `alert-investigation-integrity` 是已归档迁移的限定合同；不改其历史验收范围。本次三项是当前 API v2 的新规格，实施并完成结束审阅前不写入主规格库。

## Impact

- 修改范围主要为 `services/api/app/investigation_v2/` 下 Case tools/runtime/context、Incident api/summary，以及对应直接用例；必要时拆一个纯材料投影 helper，不建设新运行框架。
- API 请求形状不变；预览、结果及证据读取增加来源信息；进程 Tool 返回行增加类型字段；概况刷新增加上述条件式前置 403。
- 不新增数据库表/迁移、模型或厂商调用能力、权限种类、后台任务、事件深入分析、F5、前端、恢复/压力测试。
- 路线归属：当前 Case 功能修复；[上层旧调查 change](../continue-isolated-investigation-v2/tasks.md) 的 2.2/2.3 不因此核销。[追加修复](../fix-case-followup-gaps/tasks.md)保持原完成事实和真实复验待办，由本计划汇总版本与执行批次。
- 前置依据：[静态清单](../../../docs/operations/investigation-static-audit-20261031.json)、[四案例原结果](../../../docs/investigation/multi-case-http-20261028.md)、[本地追加修复记录](../../../docs/operations/investigation-followup-fix-local-20261028.json)。
- 用户已推进本地实施和必要直接验证，沿原边界准备可审阅版本；实际更新/调用、提交与推送状态另记，不把本地结果冒充真实交付。
