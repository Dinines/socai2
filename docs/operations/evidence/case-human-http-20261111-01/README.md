# Case/H HTTP 功能批次

对应 OpenSpec `enable-case-human-http-flow`。本地一条正常 HTTP 链路包含两轮调查及一次人工反馈完成/修订；[验收与限制](../../../../openspec/changes/archive/2026-11-11-enable-case-human-http-flow/validation.md)区分程序功能、模型质量和生产发布。

- `direct-tests.txt`：11 项直接检查，未连接数据库/模型。
- `real-http/plan.json`、`http-source-sha256.json`：输入、配置和实际执行源码锚点，凭据只在忽略提交文件。
- `real-http/http/`：13 次原 HTTP 请求和响应；本机认证为明确替身，业务路由/依赖/执行器原样使用。
- `real-http/round-1`、`round-2`：实际提示、计数、原答及调用回执，分别 5/4 次。
- `real-http/export/`：本 Case 落库、读取、人工版本/请求 body 核验和 4177 输入，非全库审计。
- `api-connection-prerequisite.json`：21 既有证书挂载和非敏感 TLS 配置只读核实，没有服务改动。

首轮模型引用非法保持 rejected；后轮 accepted 不等于正文质量通过。M01/F01 等质量未完项保持。[生产写读](production-http/verification.json)、[实际运行](runtime-after.json)、[静态资料发布](static-publication.json)及[交付汇总](delivery-summary.json)已完成；API 只更新一次，其余五容器保持，无生产模型调用。
