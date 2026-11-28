# 21部署：当前运行与统一交付

本轮手工重装以[2026-11-27调查服务部署与恢复手册](../../docs/operations/investigation-manual-deployment-21-20261127.md)为入口：只操作调查 HTTP 与联合执行器，经现有 SSH 跳板连接；新空验收库、完整候选和恢复原服务的步骤已列，尚未实际执行。下列旧批次的清理、全栈发布和资源名不作为本轮执行指令。

## 当前发布

2026-11-27手册核对时，当前调查HTTP容器为`socai2-http-incident-saved-diagnosis-read-20261126-01`（83操作），平台API为`spirithub-backend:incident-saved-diagnosis-read-20261126-01`；唯一联合调度仍为`socai2-analysis-incident-diagnosis-live-20261125-01`，已发布容量修正保持。web/Swagger/4177沿原版本。本次没有发布；实际运行与候选范围见[只读评估](../../docs/operations/evidence/investigation-release-readiness-20261127-01/README.md)。

## 11月25日发布记录

当前告警发布：调查 HTTP 18024 为 `c173-alert-attck-readback-20261125-01`（83 操作）；web 为 `spirithub-web:alert-20261125-729288945206`，平台 API 为 `spirithub-backend:incident-grouping-e57-20261125-01`。E57在原Q09镜像上仅覆盖路由及合同两文件，实际加载、配置保持、静态路由顺序及8181队列压缩卡片已通过独立验收，原Q09镜像保留（[本轮回执](../../docs/operations/evidence/incident-grouping-live-20261125-01/README.md)）。联合调度已按本轮明确授权限定更新为 `incident-diagnosis-live-20261125-01`，仅新增已独审计量模块只读挂载，原镜像/配置/提示保持，旧调度器停止保留（[发布回执](../../docs/operations/evidence/incident-diagnosis-live-20261125-01/core-release.json)、[独立读回](../../docs/operations/evidence/incident-diagnosis-live-20261125-01/independent-release-read.json)）；Fusion 基础镜像仍为 `c173-release-20261121-03`，接收规则映射使用已验单次 worker 源码覆盖；独立 Swagger 保持 `c173-release-20261121-04`（82 操作），4177 保持 r9。本次容量修正没有迁移或Kafka投递，随后完成一笔同组事件真实诊断；HTTP基础镜像及网页版本沿原告警发布；HTTP条目复用与平台Q09身份适配的限定更新见下文。新诊断保存/采用及PG/HTTP、4177已核，E23同Run读取已限定发布，当前HTTP容器为`socai2-http-e23-entry-reuse-20261125-01`，原镜像/profile/83操作合同保持；8181诊断正文与刷新通过，Q09事件运行身份接线已限定发布并独核实际源码/配置，新完成和旧失败Run概览均通过8181独立验收（[单笔回执](../../docs/operations/evidence/incident-diagnosis-live-20261125-01/README.md)）。实际镜像、挂载保留、回退点和只读核验见[本批发布回执](../../docs/operations/evidence/alert-git-21-release-20261125-01/README.md)。

11月25日按负责人再次授权完成[两文件限定发布](../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/core-release-resume-result.json)。该批调度器为 `socai2-analysis-alert-rule-source-confidence-20261125-01`，沿原镜像／启动配置，新增单个只读提示挂载，实际所选新提示及正常调度已核；旧实例停止保留。规则映射安装于 `/opt/sting-aisoc-socai2/deployments/alert-rule-source-confidence-20261125-01/fusion`，已核同镜像以此工作目录和 `PYTHONPATH` 加载，并沿已安装的 `delivery-confidence-enabled.json`。发布步骤未启动独立交付 worker。后续按[单条补验回执](../../docs/operations/evidence/alert-score-first-receive-20261125-01/independent-closeout.json)执行一轮独立交付：批准组1条仅换测试UID，取得created及Fusion有限分数／因子持久正例和8181显示。新A真实请求使用已发布提示并完成，但confidence仍为null，数字正例未取得、null理由语义未验；不追加生成。统筹另行SSH读回及发布后8181同材料显示核对通过。[限定发布独审](../../docs/operations/evidence/alert-rule-source-confidence-20261125-01/independent-release-resume-review.json)。上轮三次自动权限审核超时均未创建进程的事实仍保留在原阻断回执。

[C173 发布清单](c173-release-20261121-04/release.json) · [正式服务与库表读回](../../docs/operations/evidence/c173-escalation-release-20261121-04/README.md) · [后端联调交接清单](../../docs/integration/c173-backend-handoff-20261121.md)

## 2026-11-17 发布记录

2026-11-17。负责人明确要求“先部署到21 清除历史数据 然后再测试数据”。[acceptance-release-20261117-01](acceptance-release-20261117-01/release.json)已完成完整服务发布、受控备份与明确历史清理；[实际就绪](../../docs/operations/evidence/acceptance-release-20261117-01/deployment-ready.json)核五服务、源码/配置、合同和空态。后端采用3c.2真实正常两段所验的完整组合，工作台1/2及3a–3d入口已发布。[新两段测试](../../docs/operations/evidence/acceptance-fullflow-21-20261117-01/README.md)已完成：2告警/3上下文、同事件/同Case两轮、477份HTTP回执和8次真实模型均stop。5项模型质量问题后置；4b后续按明确指令已[发布0.6.1/r8与验收工具并验实际链接](../../docs/operations/evidence/workbench-4b-release-20261117-01/README.md)，2026-11-18随后按明确指令完成[D6工作台0.6.2/r9正式发布](../../docs/operations/evidence/workbench-d6-release-20261118-01/README.md)，四异常代表和恢复日常两轮实际HTTP/浏览器读回通过；核心、验收工具、账本保持，不清理或发告警。D5写侧新改动及整个change不据此核销。

### 当批资源

| 服务 | 当前实际入口 |
| --- | --- |
| PostgreSQL | aisoc，32表521列，普通密码及TLS require；本轮无迁移 |
| 入站/处理 | socai2-production-fusion-20261117-r1、socai2-production-dispatch-20261117-r1，同一processing镜像、N=1 |
| HTTP | [18024](http://192.168.1.21:18024)，socai2-production-http-acceptance-http-20261117-r1，80业务操作，无鉴权 |
| Swagger | [18080](http://192.168.1.21:18080/)，同版合同及告警/事件/调查三组 |
| 查阅 | [4177](http://127.0.0.1:4177/viewer/)，21的0.6.2/r9容器，经本机SSH隧道访问 |

发布位于21 `/opt/sting-aisoc-socai2/deployments/acceptance-release-20261117-01`。连接、凭据和处理挂载明确沿用release中的prior_runtime_root，没有静默改库或加载旧候选短周期配置。I4h、Case6h、7天窗口及65536上下文预算保持，详见[配置索引](../../docs/operations/configuration.md)。旧消费者、旧r3和旧HTTP/展示入口停止，禁止同时恢复。

当前4177单独发布根为`/opt/sting-aisoc-socai2/deployments/workbench-d6-20261118-01`；当前容器`socai2-investigation-test-4177-r9`，旧r8停止保留。最终配置在`viewer-config/`，恢复日常18024上游及原账本。三个D5样本临时context均已停止，日常页面不依赖它们。原核心发布根及参数继续适用。

## 本轮执行顺序

1. 按[OpenSpec §12.14](../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1214-负责人明确要求先发布21清历史再测试2026-11-17)冻结来源。完整HTTP730来源、处理742包文件；670共有runtime逐字相同，286份API/Fusion与3c.2已验冻结一致；同包HTTP80操作/181schemas未变。
2. 新包上传和镜像构建期间旧服务保持。处理镜像禁网自检、新4177及3d04验收镜像原生amd64内容核对通过；未触发业务/模型。
3. 核无在途任务及待写回执后停止旧五服务，沿[精确清理清单](acceptance-release-20261117-01/cleanup-scope.json)备份并清理：84业务表521行、湖15条、Redis13键、4Topic25消息、24账本文件核零；127未选表和Schema不变。
4. 启动唯一新版HTTP、调度、Fusion、Swagger及4177，核处理741运行文件（含策略）、HTTP730来源、三类业务/账本空态。新工作台浏览器默认Case空态通过。
5. 最终3d04容器准入后，由协调方在确认尚未发送并保存接管回执后作为唯一执行者完成run首段→检查点→只读TTL→append。测试模块与HTTP模块限定独审通过；同一整事件Case实际1→2成员，R2比较真实R1，8次模型调用均stop。4177三类主体/两轮/HTTP/领域/原答及5项问题已核；随后4b已完成新验收工具/工作台发布；最终报告精确首轮/后轮链接和按冻结来源显示紫色通过实际4177浏览器及26GET核对。

[本轮操作与备份](../../docs/operations/evidence/acceptance-release-20261117-01/README.md)保留清理、发布、首次核对失败及修正回执。不得直接重放此批清理或重发已执行段。数据库新装/升级见[CURRENT](../database/CURRENT.md)，本轮无迁移。清理前部署说明见[历史快照](../../docs/handoff/history/2026-11-17-acceptance-release/deploy/aisoc21/README.md)。

## 回退边界

旧包、容器和受控备份保留。本轮已产生新C1/Run/Result，不适用“无新业务写入”的直接应用回退前提；仍保持单一执行入口，不自动恢复已清历史或重放Kafka。

新版C1含analysis_material，旧r3 Context Schema已实证拒绝该字段。产生新C1/Run后，不直接回退旧核心或HTTP；保留新读侧及记录，暂停新工作后修复当前版本。不能删新字段、改写Run、降级DDL或并行启动旧消费者。

总体状态见[PROGRESS](../../PROGRESS.md)，发布前文档见[历史快照](../../docs/handoff/history/2026-11-16-release-r4/deploy/aisoc21/README.md)。本次不含Git提交、推送或整个change归档。

### 湖3f候选查询交付

[配置及接线](lake-query-3f/README.md)提供显式查询profile和两个候选HTTP入口；[回执](../../docs/operations/evidence/lake-query-3f-20261119-01/README.md)记录现有3e数据的只读检索及完整原文关联。候选82操作保持正式80操作合同，正式48列表和服务尚未更新，按统一交付范围后续发布。

### 4a已有告警选择（只读候选）

[规则profile和私有报告入口](lake-alert-selection-4a/README.md)使用已确认的metadata.uid全局唯一、无更新合同。[4a历史回执](../../docs/operations/evidence/lake-alert-selection-4a-20261119-03/README.md)保留只读判定证据；4b另以显式初始活动配置完成候选接收，当前范围如下。

### 4b首次接收候选交付

[运行配置与完整读取合同](lake-alert-receive-4b/README.md)接现有RawAlert/Fusion、内部130回执及首次A/I登记；旧告警HTTP字段/路径不变。[隔离验收](../../docs/operations/evidence/lake-alert-receive-4b-20261119-03/README.md)已通过真实湖→PG→HTTP读取、同文幂等、长正文及新装/重复迁移；初诊accepted未执行。正式服务及48列表保持。4c后续结果见下，工具/Case及整个change统一发布仍按依赖推进；不可直接把示例profile当作已启用服务。

### 4c持久交付候选

[独立worker与配置](lake-alert-delivery-4c/README.md)先把湖选择去向保存到内部131，再调用4b；接收及确认事务持久完成后才推进。同文幂等，失败/unknown阻断后项，未知接收先只读回执恢复。[本批隔离验收](../../docs/operations/evidence/lake-alert-delivery-4c-20261119-01/README.md)通过同批湖真实CLI/PG/TCP HTTP、合成边界及131新装/重复增量；每轮上限外保留待处理工作。候选compose及示例禁用开关不代表已部署；正式Fusion/HTTP/湖保持，初诊模型未执行。
