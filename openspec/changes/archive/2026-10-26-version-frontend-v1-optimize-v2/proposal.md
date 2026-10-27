# 冻结前端V1并在独立端口优化V2

## Why
用户授权保存当前前端为V1，随后在新的端口修改优化页面。沿已确认的事件输入汇聚/整个Case调查工作区展示AI过程的分工实施，保留告警与样例。

## What Changes
- 逐字节冻结当前前端与交接包，保存V1目录、压缩包及SHA清单；原目录保持。
- 在独立security-pages-v2目录和4174端口优化事件上下文、Chain/Path入口及以Run为中心的调查过程、工具、报告和停止原因。
- 使用原样例及已有六条真实回执；真实Run不补造Case、图数据或执行结果。
- 本地状态与V1隔离，不接生产写入、不调用模型、不部署/提交/push。

## Capabilities
- Added: frontend-versioned-investigation-workspace，限定静态原型；原security-reference-ui-prototype作为V1基线保留。

## Impact
新增prototypes/security-pages-v1、security-pages-v2和V1交接快照/manifest，更新文档索引与进度。涉及本地预览服务器及浏览器验证，不改业务服务。
