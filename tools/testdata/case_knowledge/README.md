# C2 知识功能直接验收

`local.json` 选择本地实际数据库、独立 Qdrant、已有本地嵌入服务和分析模型传输；地址/端口在 profile 与 local-services.json，私密连接在被忽略的 environment.json。`corpus.json` 从既有 MITRE STIX 原件选择字段，保留来源对象、修改时刻、来源文件 hash，不把内容改写成案件事实。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/case_knowledge/run.py prepare --config tools/testdata/case_knowledge/local.json
.local/conda-envs/socai2/bin/python tools/testdata/case_knowledge/run.py run --config tools/testdata/case_knowledge/local.json
.local/conda-envs/socai2/bin/python tools/testdata/case_knowledge/run.py export --config tools/testdata/case_knowledge/local.json
```

已结束的 `case-knowledge-20261111-01` 不再执行 run。prepare 固定业务源码、策略和资料；run 使用真实路由/DB/嵌入/向量/分析模型，只适配本机认证和模型传输。export 为该 Case 的只读快照，不是全库对账。断言只证明检索传递、保存/读回和原件保持，模型质量另列。

一次发布后的 `production.py import --config tools/testdata/case_knowledge/production.json` 沿原 API key 认证执行两份公开资料导入、索引和块元数据读取。已有 output/intent 不自动重试；失败先检查是否已写入。`production.py probe --config ...` 使用已保存查询文本对两个目的做只读 C2 adapter 检索，回读 PG 原文/hash。探针不建立 Case/Run、不调用分析模型，不能替代本地端到端验收或声称生产自动消费已启用。

[验收和限制](../../../openspec/changes/archive/2026-11-11-enable-purpose-aware-case-knowledge/validation.md) · [字段与配置交接](../../../docs/investigation/case-knowledge-handoff.md)
