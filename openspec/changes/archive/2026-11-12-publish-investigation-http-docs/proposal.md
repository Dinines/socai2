# 调查 HTTP 交接与 Swagger 文档服务

## Why

负责人要求前后端通过 HTTP 对接，并将现有 125 项页面功能逐项对应参数、输入输出、错误和实现边界；随后授权在本地及 21 用 Docker 安装接口文档。现有 OpenAPI 只有结构，缺少功能对应和使用说明。

## What Changes

- 从现有 43 个调查 HTTP 操作整理可导入的 OpenAPI、参数字典、合成示例、错误说明与 125 项功能映射。
- 使用官方 Swagger UI 镜像，独立 Docker Compose 项目提供静态文档，本地与 21 使用相同文档包。
- 仅部署文档；保留现有业务 API、模型、数据表及消费者配置。用户明确不要求接口或权限验证，本项只读回文档页面与容器状态。

## Capabilities

### New Capabilities
- `investigation-http-documentation`: 调查功能到 HTTP 合同的查阅及独立文档发布。

## Impact

仓库交接资料、文档部署配置及两个新增文档容器。无业务源码、字段或数据库变化。资产基础资料和真实响应操作仍由业务后端负责；Q 等未实现能力不因有文档而变为可用。
