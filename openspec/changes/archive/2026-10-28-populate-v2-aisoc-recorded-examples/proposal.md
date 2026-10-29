## Why

用户要求用之前 AiSOC 的告警和调查实际结果填充当前 V2，检验 Case 中基础资料与 AI 调查的融合效果。

## What Changes

- 从已保存的 2026-10-24 AiSOC20 六告警读回文件离线投影，追加告警、六次 Run、五份报告及实际查询记录。
- 按原三个场景整理三个明确标识的本地 Case；源后端 Case 仍为空，单告警 Run 不变成多告警调查。
- 对未执行阶段、未知元数据、原始实体和来源环境作最小展示适配；保留原样例及 V1。

## Capabilities

### Modified Capabilities
- `frontend-versioned-investigation-workspace`: 历史实际处理结果填充与本地整理边界。

## Impact

仅 V2 静态前端、离线导出工具、直接测试及文档。读取本机已有证据，不发起模型、重放、后端修改或部署。历史输入为合成演示数据，运行结果真实，不代表真实攻击或调查质量验收。
