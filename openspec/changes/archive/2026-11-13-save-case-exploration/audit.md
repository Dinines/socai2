# 独立结束审计

审计者：`exploration_state_end_audit`，未参与本变更实现。2026-11-13。

## 当前结论

本地完整流程、文档及两端发布独立审计 **ACCEPT，可归档**。本机和21的独立 API 与 Swagger 已同步，实际版本、加载文件及读取回执匹配；当前记录和任务由实现者依据已完成证据收口，不以归档命令替代功能验收。本结论仅覆盖探索保存/恢复程序功能，不代表模型质量或产品页面接线通过。21本轮只读，生产保存写入未实测。

## 已核对内容

- 独立核心 `exploration_state` 保存至 `artifacts` 的专用 `socai2.case-exploration.v1` schema，`run_id=NULL`；只追加快照与活动回执，不修改 Case 行、成员、Run、Result、任务或当前判断。
- `case_data.source_binding()` 对证据来源按 schema 注册；新探索 schema 未被注册，不能因 kind 为 `source_snapshot` 就成为独立证据。调查上下文及图来源按显式来源/schema 读取，未发现反向混入探索状态。
- 来源对象读取带租户与 Case 告警来源限制；普通值/明确哈希算法复用 E66 规则；按输入次序检查连回底图或前序告警。旧材料版本被明确允许，保存不宣称重新执行当前 E66 时间筛选。
- 底图按本案已完成 baseline Run 读取并保留交付状态；新完成轮缺图返回 unavailable，不取前一轮图补齐。继续保存复制既有不可变底图；显式重置才读取新的底图。
- Case 行锁内比较最新快照 ID；相同 operation_key 的完整意图与操作者绑定，重试读回原保存，变更请求返回409。API 路由仅通过用例端口调用核心，核心未引入外部 HTTP 包依赖。

## 直接证据复核

证据目录：[case-exploration-state-20261113-01](../../../../docs/operations/evidence/case-exploration-state-20261113-01/)。

- 逐项读取 `verify-http.json` 的20次与 `continuation-http.json` 的7次实际回执；包括空保存、底图、E66、保存/读回、幂等、冲突、非法来源、断开分支、撤销、历史底图、缺图、新 Run 后继续旧底图。共27次，预期状态一致。
- 重新比较 `sql-before.json` 与 `sql-after-save.json`，7张业务表原行相等。该比较覆盖第一阶段保存/恢复，后续程序合成 Run 的新增记录不在这条“无变化”声明内。
- 合成历史图构造曾在发布 Result 后尝试修改图引用，被历史只追加约束拒绝；既有成功业务操作未重派。续验改为发布前登记图原件再通过 Publication 引用，失败 Run 保留。不得把该程序夹具视为真实模型调查。
- `contract-check.json` 记录原66操作与138个 schema 不变，新增3操作和7个 schema。审计者另运行 `openspec validate save-case-exploration --strict --no-interactive` 及3项 HTTP 边界测试，通过。

## 冻结与文档复阅

- 最终10文件已重新冻结，审计者逐文件核对源码、候选目录及 `frozen-files.json`，hash 全部一致；包含三类图 kind 读取。真实程序夹具验证的是 alert_graph；另两种为对既有 Publication 合同的代码兼容，未将其标为另做真实图专项验证。
- 重新读取 `frozen-readback/responses.json` 的6次GET，实际候选服务69操作；最新底图缺图、既有保存保留旧图、Case前后不变。0写入/0模型。
- E67–E69 文档及 docs16 候选已复阅：新增6个业务schema的31个字段有说明；三操作输入、输出、真实状态与错误一致；旧材料保存不冒充实时查询，view_state不当业务事实。`docs-check.json` 的27请求/616响应JSON及3CSV校验回执存在，125功能保持22/15/88、tags为告警/事件/调查。
- 证据 README 已按实际回执修正为20/7（总数27不变）。`graph_artifact_id` 的新DTO、源OpenAPI、Swagger及交接已区分“未关联图为null”和“已关联但内容不可用仍保留引用”；实际不可用状态以graph_state为准。审计者再次核对最终10文件源码/冻结/hash一致；此次仅修新字段描述，不改变运行行为。

## 发布后最终复阅

- 21实际版本 `case-exploration-state-20261113-r1`，数据库 aisoc，镜像 `sha256:09272fcdc398e4d896c2cb576f99ef1354e98e80b7d2ad65fc7f7db11a262273`；本机同源 `-local`，PID 34799，数据库 v12_upgrade_dev。两端各69个业务操作，原66合同保持。
- 重新比对 `local-loaded-files.json`、`21-loaded-files.json` 与最终 `frozen-files.json`，两端各10个文件全部匹配。21发布回执记载其他既有运行容器未变。
- 逐项复阅 `local-readback/responses.json` 与 `21-readback/responses.json`，每端6次GET均200，完整Case前后相等。本机已有保存保留旧图；21既有真实调查图可读、探索尚无保存返回null。两端均0业务写入/0模型调用，不能据此声称21生产保存链路实测通过。
- Swagger最终 `2026-11-13.docs16`，69操作/67实现/2对话暂缓，154 schema、725固定字段出现位置、125功能；最终OpenAPI SHA256为 `d8182b54661d1a08075e89f4b1782342ebc9a0a132486c9b5ade5f048e830c84`。审计者重新比较两端12个HTTP入口回执完全一致，并逐文件核对仓库静态包与本机冻结包的35个hash一致。
- 手写指南原遗留“保存画布尚未实现”已更正，最终 README.md / guide.html 静态文件读回通过；首次回执保留为 `*-initial.json`，没有用更新后的内容改写首次读取证据。
- 归档后仅需把本文件及validation中的相对入口随归档目录调整，并完成OpenSpec封后校验；无需重复运行已通过的业务流程。

## 归档回执

主代理已在独审 ACCEPT 后归档为 `2026-11-13-save-case-exploration`，任务5/5。主规格新增2条要求。首次封后严格校验提示新主规格Purpose不足50字；仅补足职责说明后全部34项通过，归档33项通过；原失败日志保留在本轮.local验收目录，不影响业务验收。归档后的证据/交接相对链接已修正。
