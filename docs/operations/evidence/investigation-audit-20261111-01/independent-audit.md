# 调查流程审查的独立结束复核

日期：2026-11-11。审计者：独立审计子代理 `current_release_audit`，未参与本 change 的报告、探针或业务实现编写。本回执是本次唯一文件写入。

**结论：ACCEPT，0 项未解决必须修正。** 接受的是[调查流程审查报告](../../../investigation/investigation-flow-review-20261111.md)及其证据、适用范围和修复建议；不是 A01–A04 的功能修复验收，也不是模型质量通过。模型质量仍为 `NOT_PASSED`，主调查仍为 31/41。

## 基线与复核范围

- 实读分支 `V1.1`，HEAD 为 `45063c97f81b4f2d6bf504a6261ee7087a2353ca`。
- 检查本 change 的 proposal/design/tasks、报告、PROGRESS、前后端交接、问题入口和本批证据；检查四项发现关联的真实实现及相关入口。既有本地归档修改保留。
- 独立重算 [baseline.json](baseline.json) 中 2,788 个受保护文件的 SHA-256，全部一致。未发现本审查引入业务源码、测试、部署配置或合同变化。未读取或操作 `tools/model-preflight/`。
- 检查 Hunt 的认证依赖、默认租户解析及 SQL 参数路径；不存在报告遗漏的 principal 隐式传递。检查直接 query、Deep、C5/C6 的实际调用顺序、预算与终态边界；未将 `accepted`、`completed`、`partial` 或 `uncertain` 等同于语义正确或安全。

## 发现与证据的独立判断

| 发现 | 独立结论与精确依据 | 适用限制 |
| --- | --- | --- |
| A01 Deep/C6 正文依据 | 历史 call-3 原答确实把缺少演练/审批材料写为支持非演练，并把 `N3_S4` 的本地验证说明推断为原事件环境。核对原始 receipt 的 `raw.choices[0].message.content`、对应 intent 输入行及导出数据库。`baseline_analysis_contract.py:190` 起校验角色/成员，并不校验任意正文真值；报告对此区分正确。 | C6 “工具查询查空”是摘要区分不足，不能据此断言模型声称所有查询均为空。带“若”的 impact、空 `supported_changes` 和 `cannot_generalize` 不等于确认影响；作为需要更精确表达的质量问题处理。未证明误判安全，亦未提供独立攻击真值。 |
| A02 C3 补查数量 | `services/api/app/socai2/baseline_analysis_contract.py:81`、`:90` 允许 12 项，`:267` 提示最多 2 项；`case_model_boundary.py:83` 装入该提示；`baseline_dispatch.py:64` 起处理全部合法项。独立复跑证实三项通过 Schema/解析，派发器调用三次工具替身。 | “最多两项”应明确是执行上限还是输出目标。没有绕过总工具预算、实际执行三次外部查询或动态增加问题身份的证据。 |
| A03 Hunt 租户未传递 | `services/agents/app/api/hunts.py:39` 只挂依赖，`:82`、`:91` 未传 principal，`:118` 取全局 scheduler；`hunt/store.py:61` 按所传 tenant_ref 解析，`:279`、`:310` 默认 `default`；`hunt/scheduler.py:67`、`:297` 也使用默认租户。两 principal、六个 ASGI 请求实际落到相同默认目标的探针独立成立。 | 认证 principal 是替身，未验证真实 JWT；没有读取真实跨租户数据。Agents/Hunt 的当前生产暴露未验证，不将其记为当前主线已发生的数据泄露。 |
| A04 Hunt 失败成为成功零行 | `hunt/scheduler.py:235–243` 捕获源异常并返回空列表；`:161–174` 返回成功摘要；`hunt/engine.py:181` 对空输入返回无错误结果；`hunt/store.py:203–224` 生成 `completed/0/0/error=None` 插入参数。TimeoutError 反例独立成立。 | 实际 loader/scheduler/engine/store 执行，数据库连接是参数捕获替身。API 对该摘要的返回有 `api/hunts.py:119–122` 静态依据；此次超时反例没有再通过真实 HTTP 或数据库执行。没有 synthetic 静默替代证据。 |

Swarm/Debate 的检索与实现阅读支持报告的限定：目前所查 `services/agents/app` 内未找到接入主线的调用点；确定性评分及模拟 token 数不能作为已交付多模型调查的证明，也不能反推主线伪造。

## 独立执行与证据完整性

只独立复跑本批 6 个反例/约束检查，未重复全部 56 项或扩大业务回归：

| 执行 | 实际结果 |
| --- | --- |
| `probe_current.py`，`PYTHONPATH=services/api:services/api/tests:docs/operations:.` | 4 passed，0.91 秒 |
| `probe_agents.py`，`PYTHONPATH=services/agents` | 2 passed，0.24 秒 |

两次均使用 `.local/conda-envs/socai2/bin/python`，设置 `PYTHONDONTWRITEBYTECODE=1`、`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`，以 `pytest.main(['-q', '-p', 'no:cacheprovider', <probe路径>], plugins=[ProbeOutput()])` 执行。`ProbeOutput.pytest_collection_modifyitems` 将探针模块的 `OUT` 改为内存收集对象：仅实现 `/文件名` 和 `write_text`，解码 JSON 后保存到字典。保留原探针的 socket 禁网 fixture；没有覆盖原证据或生成缓存/XML。

内存生成的 `followup-limit.json`、`semantic-boundary.json`、`hunt-tenant.json`、`hunt-failure.json` 与本批保存版本全部逐值一致。缺陷断言通过只证实当前缺陷存在，不作为修复后的预期行为。

独立读取并核对全部测试 XML：最终 40 Case + 14 A/I + 2 Hunt = 56，均为零失败、零错误。除上述 6 个反例外的 **50 项既有检查仅核对 XML、用例归属和报告范围，未独立复跑**。首次 Case 的 1 项 frozen 赋值失败、A/I 的 7 项缺显式策略失败保留，不计为业务缺陷或成功。`test_socai2_stage_execution_api.py:26` 的入口为 `run_checks`，内部测试嵌套于该函数，没有顶层 pytest 用例；不能将文件出现在命令中计为本轮 HTTP/PG 验证。

对 [historical-model-review.json](historical-model-review.json) 的独立复核包括：

- 原 Run plan 中 98 个冻结源码/配置/材料文件重新计算 hash，全部与当前一致。
- 汇总引用的 6 个历史原件重新计算 hash，全部一致。
- Deep `answer.text`、C6 `conclusion` / `impact` 与原 receipt 解码结果逐值一致；`N3_S4` 及六条背景查询状态行确实存在于各自实际 intent。
- 导出数据库中的 Run、Result、Case 当前 assessment 指针及 `case_assessment_sources` 与汇总逐值一致。它证明原批本地运行的保存和采用，不能冒称本次数据库读取或当前生产数据。

## 复核中修正的报告问题

发现的唯一必须修正项：原 Mermaid 将 C4 直接 query 和 Deep 合并为“工具调用后进入 Deep”，还遗漏首次 Deep 可以直接 answer/handoff。依据 `baseline_dispatch.py:77–95`、`baseline_deep.py:143` 起和 `baseline_executor.py:89–97`，这会错误描述实际调用顺序。

报告作者已修正：direct query 单独保存回执并汇总；Deep 先作模型决策，只有合法 query 才调用工具，完成后重建输入进入下一轮；answer/handoff 可直接汇总，全部派发后进入 C5/C6。独立复读后该项关闭。A01 查询状态摘要同时补充了“不据这句推断模型声称全部查询都为空”的限定。

复现建议：探针原文件的 `OUT` 指向本批目录；后续复现使用新批次目录或本次内存方式，不覆盖已结束批次的回执。此建议不阻塞报告交付。

## 未验证项

本审计未调用真实模型、数据库、厂商服务、网络或 SSH，未启动/停止服务、部署、提交或推送；没有重新观测 21。未独立验证真实 Hunt 暴露与多租户数据、主线完整产品 HTTP 写操作、自动消费、非空知识使用、真实证据变化后的模型决策、提示注入全集或恢复竞争。未检查独立未提交模型工具内容。既有真实运行仅作为带原批时点的历史证据；此报告不关闭主调查未完任务，不计算准确率，也不形成模型总体质量通过结论。

## 输出路径建议落实后的补核

2026-11-11，报告作者已落实上文保留证据建议。静态复读并用 AST 核对：`probe_current.py:24` 的 `OUT` 为 `Path(tempfile.mkdtemp(prefix='socai2-audit-current-'))`；`probe_agents.py:22` 对应前缀为 `socai2-audit-agents-`。四处 JSON 写入全部经各自 `OUT`，再次执行会使用新建系统临时目录，不覆盖本批四份原 JSON。README 已说明该行为。另清除了未使用的导入，不改变探针断言或业务调用。

本次补核仅静态检查，没有新增复跑；原独审实际复跑 6 项、核对另外 50 项 XML 的范围不变。上文关于原固定输出路径的观察保留为修正前记录。无新增阻塞，结论维持 **ACCEPT**，业务问题及模型质量结论均不变。
