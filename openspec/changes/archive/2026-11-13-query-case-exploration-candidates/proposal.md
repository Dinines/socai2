# 案件关系图候选查询

## Why

现有 related_alerts 只返回共同对象告警，调查图只读本轮材料；两者都不是案件探索查询。负责人在核清对象提取、匹配和构图差别后要求继续。需要按真实对象查候选，并明确展示匹配原件、时间和归属。

## What Changes

- 新增 E66 `GET /api/v1/socai2/cases/{case_id}/exploration-candidates`：按当前成员、指定告警或指定对象查询一层候选。
- 明确六类对象匹配，原件/既有对象键不修改；哈希必须有受支持算法和值，两边共同核对。
- 查询范围、稳定分页、逐条匹配依据及原材料回查进入 Swagger 和交接指南。
- 不修改旧65操作、调查构图/执行、成员关联、表结构；保存探索另一个交付单元，AI对话继续暂缓。

## Capabilities

### New Capabilities
- `case-exploration-candidates`: 有来源的案件候选查询。

### Modified Capabilities
- 无。

## Impact

独立核心读取模块、对外HTTP用例端口/路由、配置文件、直接验证和文档。继续本地及21独立API/Swagger交付，保留并行模型修改。无模型、无迁移、无生产写入；本地新合成批验证查询及现有成员关联的衔接。Git不随本次继续开发自动推送。
