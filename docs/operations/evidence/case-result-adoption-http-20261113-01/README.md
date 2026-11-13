# 人工采用结果：三个HTTP接口的本机验证

2026-11-13。本批只负责核心/HTTP代码与本机直接验证；Swagger、根交接文档、统一发布、Git及独立交付change的归档由交接会话负责。交付change为[adopt-investigation-results](../../../../openspec/changes/archive/2026-11-13-adopt-investigation-results/tasks.md)。主调查保持未整体验收，流式后置；本批没有模型/厂商调用、数据库迁移、生产操作、提交或推送。

## 已完成的接口

| 接口 | 实际行为 |
| --- | --- |
| E21 `POST /cases/{case_id}/results/{result_id}/adopt` | 已由501占位改为调用原核心。请求为operation_key、expected_review_token、非空reason及acknowledge_pending_work；返回新/旧判断ID、判断版本和Case行版本。旧operation_key/expected_scope_revision占位body明确422 |
| E63 `GET /cases/{case_id}/results/{result_id}/adoption-preview` | 读取原/新判断、完整结果中的待核/限制、真实覆盖、新鲜度、未完任务/Run及review_token；无写入 |
| E64 `GET /cases/{case_id}/assessments` | limit默认20、1–100，offset默认0、非负；读取判断版本、原Result、采用人/理由和实际覆盖。原Run/Result `/history`含义不变 |

前缀为`/api/v1/socai2`。路由只通过CaseOperations调用既有核心，GET沿用只读连接及cases:read，POST沿用写连接及cases:write，由认证上下文提供tenant/actor。E19/E20仍501；Q保存或局部结果没有因此开放采用。其余61操作和125个原有Schema保持；旧AdoptCaseAIResult占位Schema移出公开合同，新增5个采用DTO。原始[候选OpenAPI](http-01/openapi.json)共有64业务操作、62实现/2预留。

## 直接证据

4项定向检查及12子检查通过：[JUnit](direct-tests.xml)。只执行两个Q预留的既有检查及原HTTP合同兼容检查，没有新增认证/故障/压力矩阵，也没有全仓回归。

一个新Case `81521266-2976-561d-b380-b7251274be75` 完成20次真实TCP请求，见[HTTP汇总回执与原响应](http-01/responses.json)、[汇总](validation.json)。汇总中的第6条请求输入有脚本引用问题，实际请求以[06-intent.json](http-01/06-intent.json)为准，详见下方说明：

- 一条新合成告警、一个C1冻结Run、一份程序构造的uncertain/partial但全员有效覆盖Result；没有执行A/I/C2–C6模型。另显式准备一个pending Run和一项未完人工任务。
- [实际预览](http-01/adoption-preview.json)展示待核事项及未完工作；任务/待启动Run变化后旧摘要409，未确认未完工作409，采用成功200，相同请求重试返回原回执，换理由409。
- Case/Result、判断历史两页、任务、Run和活动读回；[采用前SQL](http-01/sql-before-adoption.json)和[采用后SQL](http-01/database.json)核对原Result/成员、任务/修订、Run/成员及工件全部保持。仅新增一份人工判断及来源/覆盖/活动，旧自动判断保留，Case处理状态保持。
- 旧占位请求422、未知Result404。全部意图在请求前保存，包含原始错误响应；无POST自动重试或业务异常。测试脚本故意进行的幂等重试使用同一操作键。

自动采用时间顺序、H反馈后stale等核心证据复用[上一批](../case-result-adoption-20261113-01/README.md)，没有重跑其四Run流程；该批manifest的74份原文件摘要保持。接受状态不证明模型质量，本批只验证HTTP适配及数据库存取。

审计发现driver把请求body原对象存入汇总，随后更新预览摘要使汇总第6条input被回改。[差异说明](request-reconciliation.json)逐一比对20份调用前意图，只有第6条expected_review_token不同；其原意图与第3条旧预览匹配，服务器409原响应保持，所以旧预览拒绝仍有真实证据。原responses和全部intent不改写；执行时脚本保存在`executed-source/run_http.py`，当前driver已用deepcopy冻结请求及响应，修后没有重跑HTTP。发布侧复用driver时应带上这项记录修复，不用汇总错误值重放第6次请求。

## 候选环境与复用

- 本机候选：`http://127.0.0.1:18027`，release `case-result-adoption-20261113-candidate`；[启动/版本回执](candidate-runtime.json)、[候选profile](candidate-profile.json)。从普通工作树`services/api`启动，使用完整工作树代码；**未验证“已发布基底＋七文件”的部署组合**，由发布会话另验。
- 核心2文件＋CaseService＋HTTP contracts/ports/cases/case_ai共7文件已冻结到`after-source/`，[摘要](source-files.json)、[补丁及来源](source-replay.json)可供发布方选取。HTTP执行后只清除case_ai.py尾部一个空行，无可执行变化。其他并行模型修改不属于这7文件。
- 环境和凭据仅在受控`.local/case-result-adoption-http-20261113-01/environment.json`及既有本机credential文件，未写入证据。[config.json](config.json)固定本次数据目标、地址、时限和受控文件路径；driver不接受隐式数据库回落。
- [run_http.py](run_http.py)同时准备本批合成数据并跑HTTP链路。`http-01`已经结束，不覆盖目录、不重派该批；要验证部署基底，用新输出目录及新合成Case，并显式选择对应profile。21的登录/环境和生产写入标记须由发布方适配，不能直接拿本机profile或`production_changed=false`作21证据。

本机候选启动方式（已运行时不要重复启动）：

```sh
.local/conda-envs/socai2/bin/python deploy/http-service/manage.py --profile docs/operations/evidence/case-result-adoption-http-20261113-01/candidate-profile.json local
```

直接驱动用法（新批输出目录；这不是重跑授权或自动重试入口）：

```sh
.local/conda-envs/socai2/bin/python docs/operations/evidence/case-result-adoption-http-20261113-01/run_http.py --profile <明确环境的配置文件> --output <新的批次输出目录>
```

[本机4177静态详情](../../../../deliverables/investigation-validation-20261106/processing-audit/cases/234ad1b84ff256e9461ede6a4f7abf209a9f79f90a1e178929f194c86ed9cec2.html)已追加1份，85→86，旧记录保留；[导入回执](workbench-import.json)。未同步在线4177、未检查本机4177 TCP可达性。[独立限定审计](audit.md)已通过本地HTTP接线及保存读回，正式发布和Swagger验收不在本批通过范围内。批次原件及修正说明一并封存于[文件摘要清单](files.sha256.json)，不以修后driver追认原日志完整。
