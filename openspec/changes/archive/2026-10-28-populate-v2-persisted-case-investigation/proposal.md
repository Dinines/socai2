## Why

用户要求继续使用已找到的本地实际Case记录，展示原Case调查与攻击链/路径，而非仅查看后来整理的告警组。

## What Changes

- 追加2026-10-21真实创建的Case、三条保存输入告警、对应Run、四阶段采用结果、三类图工件及原报告。
- 保留原Case/Run身份、输入范围、历史状态及来源；攻击链候选不自动成为Case成员。
- 最小适配阶段内容、工具实际返回、保存路径图及Case空态，不改后端。

## Capabilities

### Modified Capabilities
- `frontend-versioned-investigation-workspace`: 实际Case联合调查历史资料展示。

## Impact

仅本地V2、离线导出及直接验证。来源为本地API/Agents借21基础设施的历史联测，合成输入、真实执行；不宣称当前库存或完整质量通过，不新查询/模型/重放/部署，原V1及已有样例保留。
