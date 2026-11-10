# Case C1/C3 本地接入验证

本工具验证配置启用的 C1 回执快照、C3 文本输入和七类输出恢复。连接 [config.json](config.json) 指定的既有本机隔离库，模型、分词和查询均为显式替身；不调用真实模型，不连接正式业务库，不部署。测试使用新的合成身份，不重派已经结束的模型对照批次。

在仓库根目录执行：

```sh
.local/conda-envs/socai2/bin/python tools/testdata/case_integration/run.py \
  --config tools/testdata/case_integration/config.json --attempt new-local-check
```

`--attempt` 必须为新目录；可用 `--only <method>` 运行一个直接检查。脚本先核实际数据库和角色，按每项真实结果保存 `checks.json`，再只读导出 29 表范围快照、页面数据和原 Case 服务读取结果。它不会修改表结构或删除历史数据。模型没有真实生成，不能将结果当作质量通过。

本批四项检查分别覆盖：

- 同 A Run 回执与 I 发现/问题进入 C1/C3，短号恢复并保存；Deep/C6 使用的旧 JSON 视图单独生成。
- 空引用先保存原答，再用相同短号范围反馈一次；第二次仍完整校验。
- 单个错误引用不丢弃其他独立有效成员结果。
- 事务内追加一份合成回执，V1 基础检查仍 current 时，扩展检查识别 stale 并阻止采用；注入与测试发布一起回滚。

只验证 C1/C2/C3 和 C4 材料准备，不执行 Deep/C6 模型。成功检查的 Case Run 以 `failed / synthetic_c3_only_test_ended` 明确收口，不能当作完整调查成功。早期失败保留实际 running/unknown 和工件，没有改写成成功；独立方法的最新结果组合说明见[接入报告](../../../openspec/changes/complete-socai2-investigation-chain/case-boundary-integration-20261109.md)。

已完成批次：[case-boundary-integration-20261108-01](../../../docs/operations/evidence/case-boundary-integration-20261108-01/summary.json)。原两次真实模型比较仍在[原批次](../../../docs/operations/evidence/case-model-comparison-20261108-01/summary.json)，已经结束，不再等待授权或重派。

取得快照后更新 4177：

```sh
.local/conda-envs/socai2/bin/python docs/operations/update_processing_audit.py \
  --batch docs/operations/evidence/case-boundary-integration-20261108-01/new-local-check/case-1
```

每个 Case 导出目录独立登记，保留其他批次。候选策略为 [investigation-policy-case-v1.toml](../../../deploy/local-investigation/investigation-policy-case-v1.toml)，候选打包配置为 [processing-build-case-v1.toml](../../../deploy/aisoc21/processing-build-case-v1.toml)；当前线上 A/I 策略没有切换。
