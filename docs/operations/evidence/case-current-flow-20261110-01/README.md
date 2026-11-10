# Case 流程实测证据

本批使用两组已有演练材料，新建两个 Case、三个 Run，包含助手依用户要求补充的材料完整性核查 H。结论与范围见[实测报告](../../../../openspec/changes/complete-socai2-investigation-chain/case-current-flow-20261110.md)。

- `run-config.json` 固定真实调用的发布、身份、来源与预算；私密 API key 不在本目录。
- `execution-summary.json` 定位 8 次真实模型请求／原答／用量和步骤状态。模型质量 NOT_PASSED，三个 Run 均部分交付，最终结论未采用。
- `H-*-request.json` 与 `H-create/H-complete/H-metadata` 保存明确动作及回执；`H-metadata-check.json` 核管理字段修订和新鲜度。
- `readback-01/02` 保留核验器失败／误判；`readback-03` 是最终 365 GET、16,820 项检查；独立活动复核另存 `independent-activities.json`。
- `local-validation.json` 是当时源码的初验；最终核验器对应的源码 hash 和已保存响应重放另见 `final-validation.json`。
- `wire-repair-check.json` 仅离线核生成约束，未改写原答，也不是修正后真实模型生成验收。
- `published/C01` 与 `published/C02` 是正式发布 4177 的读回导出；`workbench-manifest.json` 和 `workbench-publication.json` 固定文件及静态发布回执。
- `operator-sources` 保存本机批次编排脚本来源，含原批次私密配置路径但无凭据。脚本不是通用运行入口，不能从本目录直接重放已结束动作。运行维护使用仓库现有正式入口及新批配置。

所有失败、原答和原批次来源保持。构建回执包含未激活的中间候选；实际部署以 `unified-activate-20261110T104633458561Z.json` 为准。
