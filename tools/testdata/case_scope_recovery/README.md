# Case 来源与纠正验收

此目录只向配置明确指定的本机隔离库写入新测试身份。正式数据不变；SSH 只复用现有模型网关并保存独立调用回执，不部署或重启 21。

- `config.json` 配合 `../case_integration/run.py` 执行真实 PostgreSQL、模型／工具替身的完整流程。
- `real-model*.json` 分别固定独立批次、原材料快照、数据库、模型路由、可用工具和证据位置；预算读取正式 Case 策略。
- `real_model.py prepare --config <文件>` 冻结源文件指纹与原材料；`run` 只执行一次正常 C1–C6；`export` 保存 29 表范围快照及原 GET 处理函数读回。
- `verify_local.py --config <文件>` 使用既有交接核验器逐字段比对 GET、工件 hash、外键及随后只读快照，结果写入对应 `export/field-summary.json`。

Python 使用仓库指定环境。数据库、模型地址和秘密读取位置均由配置提供；不在日志或 Git 输出凭据。运行前需本机隔离库可连接，SSH 别名可达。

同一批次禁止重派，含已有 intent 但未知结果的调用。源码／配置改变时保留原批次，准备新的批次名、输出目录及远端模型回执目录。只读导出失败可先查已存在文件及原因，不覆盖原答或业务失败。中间失败与最终修复分别见[验收报告](../../../openspec/changes/archive/2026-11-10-fix-case-evidence-scope-and-recovery/validation.md)，不能把真实模型、测试替身或本地与生产混记。
