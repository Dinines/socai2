# 案件探索候选 E66 本批证据

本机使用新合成批验证，21仅既有记录GET。无模型调用、表迁移或生产业务写入。[设计和验收](../../../../openspec/changes/archive/2026-11-13-query-case-exploration-candidates/validation.md) · [调用指南](../../../integration/case-exploration-http.md)。

- `local-http/seed-*`：10条合成告警及2个Case的输入和创建回执；不复用生产UUID。
- `local-http/verify-http.json`：30次HTTP；逐次意图另存。
- `local-http/sql-before.json` / `sql-after.json`：查询阶段10表原行保持。
- `local-http/query-verification.json`：只读查询确认；`verification.json`另含随后明确关联和原案保留。
- `before-openapi.json` / `compatibility.json`：原65合同与旧Schema保持；新增E66。
- `candidate-source-manifest.json`：本机冻结11文件，不含并行模型修改。
- `docs-check.json`：Swagger合成示例/Schema检查，非业务调用。
- `initial-check-notes.md`：最初检查命令和文档生成失败及修正，保留失败事实。

两端发布：[delivery-summary.json](delivery-summary.json)、`local-release-http/`、`21-release-http/`各11次GET；`local-runtime.json`/`21-runtime.json`实际源码与挂载，`local-swagger.json`/`21-swagger.json`各11入口。最终结束审计见对应change的audit.md。
