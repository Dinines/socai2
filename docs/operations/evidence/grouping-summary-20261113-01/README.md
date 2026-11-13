# E57同范围事件归并统计

对应F06-06；[交接说明](../../../../deliverables/investigation-validation-20261106/http-handoff/README.md#事件归并统计)、[本批验收](../../../../openspec/changes/archive/2026-11-13-summarize-incident-grouping/validation.md)。

- `fixture.json`/`seed/`为本机独立8告警/4事件/6关系批次，不重派；21使用已有合成来源，0新增业务写入。
- `candidate/`包含13次真实TCP（7成功/6预期422）和SQL前后；各数量及比例按独立原行重算一致。
- `local-http/`保留首次切换失败后的SQL读取；原因见validation。`local-http-r2/`为本机正式13次验收，`21-http/`为21正式12次，只读且不调用模型。
- `local-api-release`、`21-api-release`、`21-runtime`及`loaded-runtime-config`核对实际8源码文件、版本/开关/库和36个其他容器保持。
- `*-sql-*.json`记录实际原行；`*-swagger.json`及`swagger-release.json`核对docs10、57操作、129Schema、554固定字段和两端9入口同摘要。
- `delivery-summary.json`汇总实际发布；归档后Git推送由固定skill执行，以实际回执核对，不提前写成完成。

仅本批统计功能通过；模型质量、页面修改及后续采用/评论功能不在本轮验收范围。
