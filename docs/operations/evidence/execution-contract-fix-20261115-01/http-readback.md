# F5：统一执行合同的 HTTP 读回

2026-11-15。**F5本机直接验证及同源HTTP读回通过，5项审计问题均已有修复与直接验证；完整change、21真实链及独立结束审计仍未完成。** 本轮不改业务代码或公开字段，未部署、推送或启消费者。

测试模块亲自运行的 [test-pg-01](test-pg-01/result.json) 使用真实本机 `127.0.0.1:28413/v12_upgrade_dev` 和专用Redis。A→I→Case实际程序产生3个task/Run，A/I/Case各1份结果，Case包括C3、查询处理、Deep及C6。[独立执行回执](../test-f5-independent-20261115-01/pg-contract-01.json)记录30份源码/支持依赖及4份配置摘要前后稳定，HTTP读取前再次核对一致。

**模型和日志来源是模拟的。** 原执行用了5份构造的模型回复和合成查询记录，0真实模型。它验证程序执行、保存、合同和读取，不能验证模型正文质量、厂商日志连通性或21最终链路。

[http-read-01.json](http-read-01.json)首轮 **90次无鉴权GET通过**：当前独立应用经ASGI、真实核心读取器和强制只读PG连接；19张直接相关表的本租户计数/摘要前后一致，新增模型调用、业务执行及写入均为0。

| 核对项 | 实际结果 |
| --- | --- |
| 三类主体与任务 | 告警、事件、Case详情可读；各自列表/详情为原任务completed，attempt/Run及结果链接属于相同主体和原执行 |
| 完整步骤及原件 | 3个Run共25个步骤、69份原件全部通过公开目录与content_url读回，状态、正文及摘要与PG冻结快照一致 |
| A/I合同 | 原模型请求的alert_boundary、incident_boundary版本与profile摘要等于该批选定合同；对应原回复与保存结果可读 |
| Case合同 | 冻结C1的case_input_profile与本批选定profile一致，C3、Deep、C6请求均使用同一身份，无旧路径替代 |
| 上游输入与范围 | C1只含本案原1条告警，已有分诊/事件诊断可用，事件来源Run对应本批I；未扩大调查范围 |
| 查询及最终保存 | C4.query保存1行合成记录及原输入/回执，Deep和C6原请求/回复完整；Case Result与核心保存读回一致 |

入口：[validate_http_readback.py](validate_http_readback.py)；检查代码：[test_socai2_execution_contract_http_pg.py](../../../../services/api/tests/test_socai2_execution_contract_http_pg.py)。显式加载该批调查/任务/分配策略，使用已结束source及新output路径，不重派旧任务。

候选检查另通过[现有6项HTTP分层/可信测试](http-boundary-tests-01.txt)及OpenSpec strict；公开OpenAPI与第7步候选完全一致，80操作、无鉴权，I/Case提交异步202，E11/E13/E36保持退役，内部路径未混入公开合同。核心负责启动/执行时拒绝缺少现行IO的配置和旧输入，预算仍可配置；HTTP仍是独立受理/读取服务，不承担执行器生命周期或模型预算验证。

发布依赖检查发现原片段链未显式列入 `investigation_http/adapters/identity.py` 和 `runtime.py`，已补入[HTTP片段](../../../../deploy/http-service/case-update-release-fragment.json)，防止按片段更新时漏掉无鉴权装配。原[候选检查01](http-candidate-check-01.json)是修正前108份源码的文件存在/合同检查，不是完整部署物验收；最终供给按后续冻结回执及21显式profile核对。检查器最初未处理既有单字符串requires写法的[失败说明](http-candidate-driver-error-01.txt)保留，该问题不涉及产品代码。

修正后的[候选检查02](http-candidate-check-02.json)核11份片段、110份源码及4份公开配置文件；[HTTP冻结清单](http-source-freeze.json)保存43份HTTP包源码、原80操作合同及3份Swagger文件摘要。这里冻结的是交付源和合同，尚未组装/启动21候选包，不能把文件存在检查当作实际加载成功。

HTTP可交付上述合同、受理/读取代码与同源证据。21候选服务、实际profile、Kafka/来源接线及W1–W4仍需逐步供给，详见[第11步HTTP准入与供给](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#第11步http准入与实际供给)。旧21的64操作/静态71和401仍是待候选供给差异；本轮没有切换旧服务。
