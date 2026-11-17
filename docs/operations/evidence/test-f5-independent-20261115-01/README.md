# 测试侧F5独立执行验证

2026-11-15。按既定“本机隔离环境做中间验证，最终在21验收”范围，测试会话实际执行一个全新批次，**A→I→Case当前合同及C3→补查→Deep→C6保存读回通过；同批HTTP的90次GET也已通过。** 本批没有真实模型请求，不是Kafka或21整链验收，整体审计未据此通过。

## 本次实际执行

- [命令、目标、配置指纹及源码前后摘要](pg-contract-01.json)，退出码0。
- [驱动原始结果](../execution-contract-fix-20261115-01/test-pg-01/result.json)、[19类表快照](../execution-contract-fix-20261115-01/test-pg-01/snapshot.json)。
- [冻结C1](../execution-contract-fix-20261115-01/test-pg-01/case-context.json)、[Case Run读取](../execution-contract-fix-20261115-01/test-pg-01/case-run-readback.json)、[Case Result读取](../execution-contract-fix-20261115-01/test-pg-01/case-result-readback.json)。
- [A/C3/Deep/C6请求及模拟回复](../execution-contract-fix-20261115-01/test-pg-01/calls.json)、[I请求及模拟回复](../execution-contract-fix-20261115-01/test-pg-01/incident-calls.json)。

分支`V1.1`，显式私密配置`.local/execution-contract-fix-20261115-01/verification.json`指向本机PG `127.0.0.1:28413/v12_upgrade_dev`、Redis `127.0.0.1:32774/0`、独立namespace `socai2-execution-contract-fix-20261115-01`；Case容量沿当前配置100。运行前确认`test-pg-01`及其sources目录不存在，各只执行一次；没有恢复或覆盖F1–F4旧任务。

新tenant `a7367ebc-823f-4fe7-a0a0-8b54c00cf9bd`；来源夹具共2告警，其中1条进入本次分析链，另1条未分析。实际形成1份A分诊、1份I诊断、1个Case及Case Result，共3个completed task/attempt/Run、25步骤、69工件。模型阶段A、I、C3、Deep、C6共5份模拟回复，真实模型请求0；补查C4.query实际经过程序处理，数据由合成日志提供。

驱动[四组断言](../execution-contract-fix-20261115-01/validate_contract.py)实际通过：统一工厂完整注册；A→I→Case按现行合同保存；C3后补查、Deep、C6完成且Run/Result读回；C1冻结现行Case profile且对应A/I来源均可用。执行前16核心文件及10支持文件与核心[冻结清单](../execution-contract-fix-20261115-01/source-hashes.json)相同；另核4份直接依赖，共30文件运行前后摘要一致。4份私密运行配置只保留路径与hash，前后一致，不记录凭据。stdout为空是驱动不打印输出，不作为通过依据。

## “替身”的具体来源及边界

这里的替身指仓库测试代码提供的**模拟响应**，不是另一款模型，也不是调用真实模型后缓存的答案。

| 环节 | 本批实际行为 | 来源与局限 |
| --- | --- | --- |
| A模型 | 实际A程序构建并保存请求，测试Gateway读取来源映射后返回预设needs_review JSON | 本批`validate_contract.py`内`AlertGateway`；不访问模型服务 |
| I模型 | 实际I程序构建、校验、保存诊断，返回由当前选择成员组装的合成答案 | 复用`services/api/tests/test_socai2_incident_boundary_pg.py`的`Gateway`；不访问模型服务 |
| C3/Deep/C6模型 | 实际Case程序构建请求，测试Gateway按当前Schema组装回复；C3固定提出一次查询和一次Deep，C6使用测试结论 | 复用`case-initial-20261115-01/controlled.py`的`Gateway`；原请求/模拟回复已保存，不代表模型质量通过 |
| 日志及背景来源 | 实际查询处理、SQL校验、关联和工具回执；日志内容是合成记录，部分背景查询返回明确空列表 | 同文件`Lake`、`empty_query`；没有访问真实日志库/厂商服务，也不能证明真实上下文路由正确 |
| PG/Redis/执行器 | 实际隔离PG/Redis、统一调度及A/I/Case执行、保存与读取 | 来源告警及事件关系由显式夹具建立，未经过Kafka消费者/Fusion |

该中间验证只证明程序能按已约定合同处理这些受控输入。真实模型可能出现格式错误、超时或其他影响程序流程的结果，最终21批次仍必须发送真实模型请求并保留原答，验证接收、校验、错误收尾及保存读回；正文判断质量单独记录后置，程序流程阻断不能按质量问题豁免。真实告警入站、归并、事件与上下文路由仍须从Kafka验证。

## 核心提供方证据与下一步

已读取核心[28项直接测试](../execution-contract-fix-20261115-01/direct-tests-final.txt)及JUnit，包含15项新执行合同、10项配置、3项调度检查；另[84项模型合同检查](../execution-contract-fix-20261115-01/model-contract-tests.txt)通过，已后置历史重复展示1项明确deselected，未计通过。本测试会话只读复用这些离线证据，未声称由测试侧重跑。

缺A/I/Case任一合同、部分handler注册、旧冻结输入均须拒绝执行；旧政策仍可读取。完整现行合同下将C3额度调为4096仍可构造执行器，说明预算没有被当成版本标识。这些拒绝及可配置边界由上述定向离线测试证明，PG本批验证正向真实执行路径，不冒充PG中逐一注入全部错误配置。

HTTP模块的[原始回执](../execution-contract-fix-20261115-01/http-read-01.json)、[说明](../execution-contract-fix-20261115-01/http-readback.md)及[最终摘要](../execution-contract-fix-20261115-01/http-final-summary.json)已核：90次无鉴权GET全部200，真实PG强制只读/ASGI，19表本租户摘要前后一致；25步骤及69工件全部同源，A/I/Case各自结果及当前合同、C4.query一行合成记录和Deep/C6可读。0新执行/模型/写入，没有POST或真实TCP业务验收。HTTP发布依赖另补齐两个已有无鉴权装配文件；该清单修正不改变本批业务源码或结果，不需要重派调查。

F5本机直接验证及同源HTTP读取已齐备。[总计划5.4](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#54-f5之后的21完整测试准入与实际下一步)记录三方准入讨论：当前21候选运行profile/隔离资源及真实来源路由未供给，源头工具必要适配、W1–W4未实现，因此仍不能开始完整测试。下一实施落点为不依赖调查接口的W1，随后逐步完成候选参数、HTTP/4177接线及真实S01/S04链；本轮仅记录，不启用短周期配置或21测试。

测试侧未修改业务源码、调用真实模型、投Kafka、清理旧库、部署或提交推送；W1仍未实施，21完整验收与结束审计继续待办。
