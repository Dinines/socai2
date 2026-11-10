# C3 输入候选与同材料对照

本目录的 `audit` 只读取已保存快照、生成候选输入并检查结构转换，不被线上执行器引用，不访问数据库或远端，不创建 Case。独立 `measure_capacity` 按明确授权调用已有后端 `/tokenize`，只计量、不启动模型生成。`model_eval` 使用固定请求进行有界模型对照，执行记录与离线、分词记录分开。[设计与范围](../../../openspec/changes/complete-socai2-investigation-chain/case-model-boundary-design-20261108.md)。

`config.json` 指定来源、输出目录、复用的 A/I 业务字段字典及 Case 自身的结构规则。原件、完整管理信息、来源路径、原范围和被省略项留在账本；模型视图只用本轮短号。未知业务字段、0/false/有效空列表保留，不按样本名称筛选。

## 运行

在仓库根目录执行：

```sh
.local/conda-envs/socai2/bin/python -m tools.testdata.case_io_eval.audit
```

程序通过已有本机配置初始化导入环境，随后只做纯函数和文件操作。每次生成独立时间目录，不覆盖旧结果。候选请求名称明确为 `candidate-request-not-sent.json`，不能将它当作已发送或已通过真实模型验证。

直接检查：

```sh
.local/conda-envs/socai2/bin/python - <<'PY'
import json
from pathlib import Path
from tools.testdata.case_io_eval.audit import initialize
initialize(json.loads(Path('tools/testdata/case_io_eval/config.json').read_text()))
import pytest
raise SystemExit(pytest.main(['-q', 'tools/testdata/case_io_eval']))
PY
```

## 当前结果

最新目录：[20261108T142501924719Z](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/summary.json)。配置版本 `socai2.case-input-candidate.v3`；原材料、前序分析、查询回执、指令和输出 Schema 不变，只调整主输入及工具目录的呈现。

- [新版输入](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/input-after.txt)：上一版全部 120 条来源的原值、已选业务值、原范围保持，含 53 个观察来源、8 条 I 发现、2 个待核问题和 9 份同 A 回执。已知类型/动作按现有词典显示含义；未知值不解释。观察和标签按成员/角色集中呈现，发现标题列原范围，窗口和对象仍保留。
- [工具目录](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/tool-catalog-after.txt)：用途、返回内容的业务说明、能/不能回答的问题、实际可用状态及 binding 保留。能力说明完整且字段已知时，逐字段技术清单留账本；未知字段或缺说明时回退显示，不按工具数量写死。
- [输入账本](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/input-ledger.json)：原引用、原范围、角色、各层省略、重复原文及业务释义/标题范围映射均可回查。查询返回仍明确对应回执和记录，未合并不同来源。
- [材料覆盖](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/material-coverage.json)：云审计/邮件仍为 12/15/11 项。本轮没有再减少来源条目；这是已有材料片段检查，不是新 Case 或模型结论。
- [输出往返](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/output-replay.json)：旧原答还原后逐值相同，原答和还原结果均保持 `domain_finding_scope_mismatch` 拒收；独立合成合同样例通过原解析器。

[同材料离线比较](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/hierarchy-comparison.json)：

| 项目 | 前一候选 | 本轮候选 | 字节减少 |
| --- | ---: | ---: | ---: |
| 主材料正文 | 23,718 | 21,994 | 7.27% |
| 工具目录 | 3,702 | 3,059 | 17.37% |
| 完整候选请求（含指令和 Schema） | 37,167 | 34,765 | 6.46% |

前轮省略的 12 个非观察条目是三个成员各自的空 MITRE tactics/techniques、字段元数据及无业务内容的 enrichment 包装；每条都有结构原因。本轮 120 个来源条目全部保留。相同已有分析正文只显示一次，不能据此合并来源或认定独立佐证；未知业务分支、不同时间/等级、非空会话、失败/截断、0/false 和业务空列表保持。

旧 `program_facts` 大 JSON 改成补充业务事实；本例只需另列事件程序等级/生效等级及计算方式。活动时间、告警时间和成员等级只有在确切来源和值已经显示时去重，不改成根据正文猜测。三份快照、15 份生产源码/策略指纹保持。各次中间稿和前批原件均保留。

历史生产请求主正文为 24,129 字节，材料比候选少，只作历史参照。上述离线和分词阶段不产生新分析或验证业务存取；后续独立生成结果见下方，分词服务耗时不能当作推理耗时。

## 后端 token 计量

[用户明确授权](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/user-authorization.json)的 4 次只读 `/tokenize` 已完成：经 `sting-infra21` 到 `192.168.1.43:8000/tokenize`，使用后端 chat template，并单独保守计入 Schema/外层字段。两份请求先经过与生产相同的 `vllm_grammar_v1` 发送层适配，原规范 Schema 保留，实际计量请求分别为 37,148/34,746B。[计量回执](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/token-capacity/summary.json)。

| token 项目 | 前一候选 | 本轮候选 |
| --- | ---: | ---: |
| 消息（指令、主输入、工具目录及 chat template） | 9,663 | 9,044 |
| Schema 与外层字段保守计量 | 1,984 | 1,984 |
| 安全余量 | 1,024 | 1,024 |
| C3 输出预留 | 4,096 | 4,096 |
| 合计占用 | 16,767 | 16,148 |
| 后端窗口 | 65,536 | 65,536 |

消息 tokens 减少 619（6.41%），两版均能容纳。这是后端分词和保守容量核算，不是生成返回的实际 usage，也不代表整轮 Case 剩余预算已验证。该分词批次 0 次生成、0 DB 连接/写入、0 新 Case、0 部署变更。

初次普通执行被本机沙箱禁止 SSH，后续自动审批因缺少具体数据外发授权而拒绝，均保留失败记录；用户明确允许本批后执行 4 次并结束，不再重派计量。[同材料模型对照计划](../../../docs/operations/evidence/case-io-offline-20261108-03/20261108T142501924719Z/next-model-comparison-plan.json)为准备时的原快照，后续两次生成已另行获准并完成，不将分词许可扩作生成许可。

沿现有原日志直传检查，三份原材料各有 `raw_text`、`ocsf_json.raw_data`、原封装内 `raw_data` 共 9 处正文表示被排除；这些是三份日志的重复表示。其结构化字段仍进入候选，原正文留在快照，输入显式说明限制。没有修改或绕过该检查，不能声称模型读过全文。云/邮件本轮保留的 12/15/11 项全部通过同一检查。

同 A 回执来自冻结分诊指定的 Run，逐项核租户、告警、原件 hash/长度和参数范围，但旧 C1 没有冻结这些回执。因此当前只是离线补充快照；正式接入仍需 C1 快照版本、角色登记和新鲜度兼容，不能直接把本工具接到线上。

## 校验与后续

45 个不同直接检查最新通过：原 39 项覆盖路径/类型词典、未知工具字段回退、跨案件原范围及全部 120 条来源保真；本次新增 6 项验证有界执行、未知执行停止、不重派、请求冻结、截断不接收、实际路由和隐藏推理不落日志。初次 32/33 中一项仍要求技术字段显示在模型文本，已按新合同改验后台保留并增加回退反例；未改写原答。Ruff 和 OpenSpec 通过，详见[当前检查](../../../docs/operations/evidence/case-model-comparison-20261108-01/local-validation.json)及[前轮校验回执](../../../docs/operations/evidence/case-io-offline-20261108-03/validation.json)；前轮原件保持。

两组结论、事实、引用和范围已逐项复核，下一先补 C1 回执冻结、来源角色和新鲜度，再验 C3 交接。输入原日志检查边界和模型质量问题仍保留；生产 C1/C3、Deep、C6、数据库、API、部署和 4177 均未切换。

## 固定模型对照批次

配置为 [evaluation.json](evaluation.json)，批次 `case-model-comparison-20261108-01`。[计划与请求](../../../docs/operations/evidence/case-model-comparison-20261108-01/plan-and-packets.json)已固定，两份请求与已分词的前后版本逐值相同，各含相同的 120 条来源；系统指令、输出 Schema、模型及参数不变。每组一次、单次 300 秒，不自动重试；未知执行停止，不创建业务 Run/Case，不调用数据库或业务工具。

用户明确回复“允许”后两次生成已完成，实际路由为 `openai/aisoc-test-investigation`、`http://192.168.1.43:8000/v1`，前后配置指纹相同。2 HTTP 200、finish=stop、合计 24,778 tokens、0 重试；远端两份 intent 和结果与本机固定请求/回执相符。[最初拒绝](../../../docs/operations/evidence/case-model-comparison-20261108-01/automatic-review-initial-rejection.json)与[后续明确授权](../../../docs/operations/evidence/case-model-comparison-20261108-01/user-authorization.json)分别保留，现已不再等待授权。

四个阶段分别为 `python -m tools.testdata.case_io_eval.model_eval prepare|preflight|run|review`，使用本项目 Python。本批四阶段均已结束，不重跑 `prepare/preflight/run/review` 覆盖原件。原始可见答复、实际用量和耗时单独保存；隐藏推理只记录哈希与长度，本次提供方 reasoning_tokens=0、无非空隐藏字段被省略。

实际输入 9,663→9,044 tokens（−6.41%）；输出 2,410→3,661，总量 12,073→12,705（+5.23%），耗时 49.04→73.73 秒。两份规范 Schema 均通过、严格业务校验均拒收：前版两个补查绑定不匹配；新版旧分析被提升为 observed，依赖领域/冲突及两个补查排除。局部有效保留不代表正文正确；新版出现历史查空及无依据会话/攻击链推断，整体质量 NOT_PASSED。没有业务保存/采用或真实工具调用。

完整[对照分析](../../../openspec/changes/complete-socai2-investigation-chain/case-model-comparison-20261108.md)、[用量和执行汇总](../../../docs/operations/evidence/case-model-comparison-20261108-01/summary.json)、[精简前原答](../../../docs/operations/evidence/case-model-comparison-20261108-01/before-answer.txt)、[精简后原答](../../../docs/operations/evidence/case-model-comparison-20261108-01/after-answer.txt)已保存。只是一组材料、各一次，不报告准确率或稳定的速度收益；输入原值/范围保持，不把质量退化直接归因于删除了必要信息。
