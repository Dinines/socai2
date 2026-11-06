# 调查测试与数据交接

本目录是2026-11-06已完成测试材料的分发入口，随`codex/case-baseline-history-20261103`提交。先读[测试结果、F01—F28字段对应及下一轮计划](../../docs/investigation/investigation-test-handoff-20261106.md)，再按[提交范围与剩余问题](../../openspec/changes/complete-socai2-investigation-chain/publication-20261106.md)继续推进。

[下载交接包](socai2-investigation-tests-20261106.zip)：10,079,558字节，1272文件，SHA256：

```text
361eb5b37d89bf31663f813f991c373f5f65173a80789963e40bef2142b8170a
```

ZIP保持原已核验包逐字不变；解压后先打开`START_HERE.md`。包含13个本机模型批次的已保存材料、4个无模型数据合同样例、原页面和固定候选代码，以及本轮数据/语义审阅。较早失败导出和校验器问题保留。它是数据与复现资料，不是自动部署包；旧21环境m/k/r原件继续通过主报告中的仓库索引查阅。

本轮三案15次DeepSeek、累计63次，三案C6均保存；48GET/674项数据比较、557项页面检查/87视图通过。**模型语义质量仍未通过**，两次C3范围拒收、效果扩大、知识未实际消费等问题不以成功保存代替修复。独立审计仅接受已保存的数据与交接范围。

完整运行配置、API Token和密码没有纳入。原包内`committed_or_pushed_this_turn=false`及`uploaded=false`记录的是测试/打包当时状态；本次发布以此目录的Git提交和远程分支为准，不回写原测试证据。下一轮部署模型尚未执行，数据服务和过程记录仍留本机。
