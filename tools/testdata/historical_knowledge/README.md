# 历史告警知识直接验收

`local.json` 复用本地 PG、现有 Qdrant 和本地嵌入服务的转发；`history-fixture.json` 是明确构造的历史演练资料。分诊和人工陈述均为测试输入，不是真实业务历史、人员授权或模型已完成分析的证明。当前 Case 保持 C02 原材料，在独立身份上运行一次。

正常入口：

```sh
.local/conda-envs/socai2/bin/python tools/testdata/historical_knowledge/run.py prepare --config tools/testdata/historical_knowledge/local.json
.local/conda-envs/socai2/bin/python tools/testdata/historical_knowledge/run.py knowledge --config tools/testdata/historical_knowledge/local.json
.local/conda-envs/socai2/bin/python tools/testdata/historical_knowledge/run.py run --config tools/testdata/historical_knowledge/local.json
.local/conda-envs/socai2/bin/python tools/testdata/historical_knowledge/run.py export --config tools/testdata/historical_knowledge/local.json
```

已启动的批次不可重新执行上述写入/模型步骤。`historical-knowledge-20261112-01` 保留两项前置问题：首次种子 JSON null 违反已有对象约束，事务已回滚；第二次重复入库响应后的累计回执文件采用排他创建而报错，卡片已保存。后者只修回执脚本并从已有文档继续索引/GET，记录 `driver-correction.json`，不重建来源、不重发已启动 Case。业务源码冻结仍以 plan 为准，脚本修订单独核 SHA。

验证使用原 KB/Case HTTP 路由、真实 PG、向量与嵌入，认证及模型传输沿已有本机适配。卡片入库和模型合理使用分别判断；真实原答、拒收及质量限制完整保留。无压力/可用性专项，不重跑全仓测试。
