# Case附件引用：2026-11-13

负责人确认业务后端保存/上传/下载文件，本服务只保存Case关联及元数据。本批E60–E62使用既有artifacts，不新增表、模型调用或调度。

- [验收结论](../../../../openspec/changes/archive/2026-11-13-link-case-attachments/validation.md)、[独立审计](../../../../openspec/changes/archive/2026-11-13-link-case-attachments/audit.md)、[汇总](delivery-summary.json)。
- `candidate/`：首次活动目标列错误；保留意图/已有响应及failure.json，rollback-check.json独立确认整笔回滚。原非JSON错误正文未完整捕获，不声称原件齐全。
- `candidate-02/`：重启后过早OpenAPI GET失败，0业务请求，原非JSON内容和失败说明保留。
- `candidate-03/`：修后25次HTTP，fixture、responses、实际OpenAPI及独立SQL原行。
- `local-http/`：正式服务8次GET，不重复写；SQL与candidate-03相同。
- `21-http/`：26次HTTP，仅本批新合成Case/H/文件引用；独立SQL，2附件/2活动/2目标、任务/Run保持。
- `local-source-manifest-initial.json`为首轮失败源码摘要；`local-source-manifest.json`为最终8文件摘要。实际两端发布/运行、Swagger入口/摘要分别保留。

所有测试文件ID均为明确合成引用。没有真实文件上传、下载、存在性探测或内容校验，不把managed_by_backend写成文件可用证明。原失败不因修后成功而覆盖；真实模型质量和其他模块问题不由本批核销。
