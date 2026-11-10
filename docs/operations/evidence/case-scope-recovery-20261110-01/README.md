# Case 来源与纠正验收证据

对应 [OpenSpec 验收报告](../../../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md)。所有已结束 Run、失败和原答保留；不以结构校验代替正文质量。

- `final-contract-tests.xml`：最终 69 项来源、合同、策略及容量检查通过，包含两协议 unknown／截断不纠正；前期报告保留。
- `budget-checks.xml`：9 项容量及预留检查；此前收集／环境错误另留原报告。
- `local-pg-03/summary.json`：3 项真实隔离 PostgreSQL 流程、4 份 Run 读回；模型／数据湖为替身，0 真实模型调用。`local-pg-01` 在连接阶段被本机沙箱拦截，没有执行 SQL。
- `preparation-only-01/plan.json`：导入顺序整理前的预备计划，未发起任何调用；整理后重新冻结 `real-model-01/plan.json`。
- `real-model-01/`、`real-model-02/`、`real-model-03/`：原始材料的新本地 Case、真实模型请求和可见原答、计量／配置、正常执行器保存及 HTTP 读回。隐藏推理只留移除字段的 hash 元数据，不保存正文；费用未知。

本机隔离库为 `v12_upgrade_dev`；本地验收阶段没有更新 21 服务或正式业务数据。全批没有 DDL 或权限设计变更；完成独审后才统一发布 21，发布与本地测试分别留证。

三轮真实调用合计 14 次、161,323 reported tokens，费用未知；160 GET、9,819 字段检查通过，模型质量 NOT_PASSED。逐轮错误、纠正、采用与交付见 `execution-summary.json`；本地发布资料在 `published/`，原数据库及原答保持。

- `independent-audit.json`：独立结束审计 ACCEPT，0 个未解决必须修正项；保留审计时点结论。
- `delivery-summary.json` 与 `unified-*.json`：21 `r5` 统一发布、实际来源及六项服务健康；只更新 API，五项继承服务保持。
- `production-readback/summary.json`：365 次真实生产 GET／16,820 项字段关联检查通过，原数据保持，0 模型调用和业务写入。
- `static-publication.json`：4177 追加 6 份记录至 26 份，524 文件／525 HTTP 核验，原资料保持。
