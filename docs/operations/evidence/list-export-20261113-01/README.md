# 完整列表CSV导出交付证据

E54告警、E55事件、E56调查；本机和21独立18024，Swagger docs9。输入、处理、CSV和错误说明见[交接指南](../../../../deliverables/investigation-validation-20261106/http-handoff/README.md#完整列表导出)，[验收与独审](../../../../openspec/changes/archive/2026-11-13-export-investigation-lists/validation.md)。

- `delivery-summary.json`：两端最终交付；`loaded-export-config.json`实际配置。
- `fixture.json`/`seed/`：本机新合成批次55告警、3事件、3Case；不重派种子。
- `candidate/`：首轮200后验收脚本停止的原件；原因见validation。`candidate-r2/`：62次候选HTTP和PG只读对照通过。
- `local-http/`、`21-http/`：发布后13/12次真实GET及CSV原文，公开列与列表和SQL一致。
- `*-sql-final.json`：最后只读快照；`21-sql-before/after.json`原四组完全一致，本机五组与候选保持。
- `local-api-release.json`、`21-api-release.json`、`21-runtime.json`：实际入口、版本、11文件和其他36容器。
- `local-swagger.json`、`21-swagger.json`、`swagger-release.json`：两架构、9入口及同源摘要。

17项离线检查和独审范围明确保留。0模型/0Run启动/0生产新增业务写入；不代表模型结论质量通过。前一列表批Git同步见`prior-list-git-sync.json`；本CSV批Git动作在业务归档后由固定skill执行，实际回执以交付答复为准。
