# 湖3e固定范围聚合验收

[实施安排](../../../openspec/changes/complete-socai2-investigation-chain/clickhouse-lake-design-20261119.md#118-湖3e实施安排2026-11-19)沿用3b/3c/3d的存储、来源及消费profile。仅在受控环境中运行[验收入口](../../../docs/operations/replay_spirithub_lake.py)，不启动Fusion服务，不重置已有group，不向客户Topic发送测试消息。

选择新的lyc_lake_3e_*库及独立lyc消费组、以lyc开头的中性source/connector。连接参数和凭据在受控connection.json；ingress引用同库storage.json，consumer选broker/group及请求限制，limits明确唯一Topic、最大消息数/运行时长和读回限制。实际TLS/CA沿env文件配置；示例Topic仅用于合成，不替换对方正式目标。

空库按3b新装及005迁移准备，核同版TTL/清理配置。程序会拒绝非空库、已有该Topic提交的group及已存在结果目录；先检查Topic存在再冻结起止范围，不自动创建客户Topic。固定范围不包含运行中新到达的消息，也不代表Kafka已过期的历史。

```bash
PYTHONPATH=services/fusion python docs/operations/replay_spirithub_lake.py \
  --connection /controlled/connection.json --ingress /controlled/ingress.json \
  --consumer /controlled/consumer.json --limits /controlled/limits.json \
  --private-results /controlled/new-batch/results \
  --execution-status /controlled/new-batch/execution-status.json
```

运行前设置umask 077，把stdout/stderr留在同环境私有日志。范围/进度/类别/数量/摘要及查询结果均不传Codex/GPT；只允许取回execution-status的固定执行/验证状态。私有report无正文样例，报告和范围文件拒绝覆盖并读回核对。

验收按实际消息数、逻辑版本、重复投递/同来源版本更新分别计数；从湖内完整正文重新计算身份及材料摘要。重复版本可能已由ReplacingMergeTree合并，不能用物理行数对账；等价原文变体只要求保存实际收到的完整版本代表，不承诺每次投递副本永久保留。数据损坏、缺/多版本、位点确认不符、超时、条数上限或范围失效均判未通过。失败后先查看受控报告和原位点，不能直接重派该批或重置group。

本入口没有告警分类、模型、3f对象检索或正式发布逻辑。完整验收回执见[本批记录](../../../docs/operations/evidence/lake-replay-3e-20261119-01/README.md)。
