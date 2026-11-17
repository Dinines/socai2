# D1：租户关联保留，模型视图排除后台标识

2026-11-16。沿[已定稿设计§2.1/§7 D1](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md)实施；OpenSpec strict 在实施前和收口时均通过。本步已完成本机直接检查和测试模块独立复核，未发布到21。

负责人明确的两个要求同时满足：后台保留租户身份与告警关联；分析模型不接收用于后台路由的租户标识。修改仅为两份输入profile各增加以下路径：

- `$.ocsf_json.tenant_uid`
- `$.raw_json.raw_event.ocsf_event.tenant_uid`

A使用`alert-input-v1.json`，I使用`incident-input-v1.json`，Case C3/Deep/C6沿现有`business_profile`复用I的业务投影。规则不依赖本批租户值，不全局删除同名字段，不改写模型提示中的业务原文。数据库、公开告警字段、租户隔离、告警归属和来源映射没有修改。

显式policy为`deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml`，这是当前r3复用的运行policy；离线检查加载当前源码内的新profile。实际21仍使用已冻结的r3镜像，不把本机通过写成运行版本已更新。现有打包器将`app`快照包含进processing镜像，新profile随下次统一冻结发布；本步不修改旧包或旧发布清单。

## 直接结果

| 验证 | 结果与范围 |
| --- | --- |
| 根侧3项直接检查 | A/I实际构造器及C3材料选择保留原件；两处后台字段被省略，业务同名云租户/source/id及0/false/空列表保留。[回执](after-mirror-tests.txt) |
| 测试模块15个独立变体 | A/I/C3/Deep/C6分别使用r3已保存材料、结构化对照、序列化OCSF对照，经实际输入构造及提供端请求封装；15/15通过。[原执行](../test-input-boundary-d1-20261116-01/attempt-02/execution.json)、[pytest](../test-input-boundary-d1-20261116-01/attempt-02/pytest.txt) |
| 后台与来源保留 | 冻结快照字节、加载原件、原`tenant_id`/`alert_id`/OCSF租户值、模型来源ref及所属告警保持；新请求仍有实际告警材料，业务同名字段未误删。各阶段检查留在独立变体JSON |
| 交接读回 | 根侧重新读取15份保存的wire/检查回执并核17份来源摘要，全通过。[核对结果](handoff-verification.json) |
| 代码/规格检查 | [Ruff](ruff.txt)、[diff空白](diff-check.txt)、[OpenSpec strict](openspec-strict.txt)通过 |

## 发现及修正

最初只排除OCSF主副本，根侧3项检查通过后，独立实际请求复核发现`raw_json.raw_event.ocsf_event`镜像仍带入同类字段。本步补齐镜像路径后，15个独立变体及根侧3项重新通过。[初始断言失败](before-config-tests.txt)、[首版局部通过](after-config-tests.txt)及测试模块`attempt-01`都保留。

序列化对照中的残留也来自这条镜像路径；当前证据没有证明额外的序列化过滤缺陷，因此没有扩大修改序列化代码。根侧旧夹具OCSF为空的准备错误、测试侧A来源映射并无`alert_ids`的断言假设分别修正，不算业务修复。

本步0网络请求、0真实模型调用、0数据库写入、0部署。证明的是当前源码的输入过滤和原件/关联保留，不是新的模型正文质量或21实际运行通过。旧16次调用及原失败原答不改写。

下一步为D2：缺少领域限制说明等质量问题保留原结论并登记后继续，由调查模块实施、测试模块独立跟进。D3–D6的截断恢复、异常收尾、后续推进和页面兜底尚未验收；完整change和统一发布保持未完成。
