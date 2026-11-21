# socai2 · stingAISOC

本仓库提供告警分诊、事件诊断、Case 调查，以及对应的管理、保存和查询服务。前后端从[交接指南](FRONTEND_BACKEND_HANDOFF.md)开始，通过 HTTP 对接。

21 当前使用 `c173-release-20261121-03`。正式 API 为 `http://192.168.1.21:18024/api/v1/socai2`，Swagger 与 API 共 82 个业务操作。产品联调从 C173 清单开始。[C173 后端联调交接清单](docs/integration/c173-backend-handoff-20261121.md) · [在线 Swagger](http://192.168.1.21:18080/) · [OpenAPI 下载](http://192.168.1.21:18080/handoff/openapi.json)

2026-11-17 历史验收发布processing-20261117-r1、完整HTTP acceptance-http-20261117-r1、同版Swagger及4177 r8（0.6.1），正式aisoc保持32表521列。[完整服务发布](docs/operations/evidence/acceptance-release-20261117-01/README.md)后，[新两段正常流程](docs/operations/evidence/acceptance-fullflow-21-20261117-01/README.md)以2条告警/3份上下文形成同一事件、同一Case两轮，冻结成员1→2；7任务、6Run、48步骤、142工件及477次HTTP成功回执已核。8次真实模型均stop，5项质量问题保留。随后[4b发布](docs/operations/evidence/workbench-4b-release-20261117-01/README.md)通过报告精确Case/Run跳转、紫色逐轮来源及原件读回和7组限定独审；整个change仍未完成。

工作台默认Case，事件、告警分别列出，每轮展示流程、HTTP接入、具体领域、组件和原答。独立[Docker验收CLI](tools/testdata/ACCEPTANCE.md)负责材料转换、检查、显式发送/追加、等待及报告汇总；新测试来源以lyc开头，后台来源与tenant关联保留，控制标记不进入模型。

告警入站后自动登记首次分诊，事件诊断和Case首轮/更新由唯一联合调度器执行。建案HTTP返回受理任务，后续沿task、attempt、Run、结果和原件查询；旧手动告警及Case prepare/start入口已退役。[任务读取](docs/integration/analysis-tasks-http.md)、[异步提交](docs/integration/analysis-submission-http.md)、[Case首轮](docs/integration/case-initial-http.md)、[完整步骤/工件](docs/integration/run-records-http.md)说明具体合同。

D1–D4c的输入过滤、质量独立记录、C3闭合信息恢复与A/I部分材料继续已进入r4。Deep/C6自身异常与网络异常等D5能力、D6完整异常展示仍待；模型引用及正文质量保留问题，不为质量重采样。人工定向、手动综合、知识后台维护（第8–10步）仍后置，AI对话未完成；此次分阶段发布不等于整个OpenSpec change完成。

| 内容 | 入口 |
| --- | --- |
| 对接总入口 | [C173 后端联调交接清单](docs/integration/c173-backend-handoff-20261121.md) · [前后端交接指南](FRONTEND_BACKEND_HANDOFF.md) |
| 页面功能与产品规则 | [125 项功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)：告警 22 项、事件 15 项、调查 88 项，包含目的、结果、后端实现状态和接口；[产品说明](docs/design/alert-incident-case-product-requirements.md)、[已确认的七类规则](docs/design/investigation-product-decisions.md) |
| HTTP 接口与字段 | [接口交接包](deliverables/investigation-validation-20261106/http-handoff/README.md)、[逐接口说明](deliverables/investigation-validation-20261106/http-handoff/endpoints.md)、[页面字段与跳转](deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |
| 对外与内部接口边界 | [调用分类与代码归属](docs/design/investigation-http-boundary.md)：对外查询/业务操作与内部步骤、内部HTTP分开；分离架构继续保持，列表新增参数及两个封套字段见当前交接 |
| Swagger 本地配置 | [Docker 安装与配置](deploy/api-docs/README.md)：本机 ARM64、21 AMD64、服务地址选择与离线安装；[21当前 Swagger](http://192.168.1.21:18080/) |
| Kafka 与其他组件 | [当前组件对接说明](docs/integration/component-handoff-current.md)：Topic、生产者/消费者、消息示例、数据库、模型与知识服务 |
| 测试数据与操作 | [Docker验收CLI](tools/testdata/ACCEPTANCE.md)、[21两段流程](docs/operations/evidence/acceptance-fullflow-21-20261117-01/README.md)、[4177部署与配置](deploy/investigation-test/README.md) |
| 调查数据 | [表职责与写入范围](docs/investigation/investigation-table-scope.md)、[当前字段字典](docs/design/socai2-data-contract-current.json)、[数据库安装入口](deploy/database/CURRENT.md) |
| 服务配置与部署 | [独立 HTTP 服务](deploy/http-service/README.md)、[全模块部署](deploy/README.md)、[21 部署](deploy/aisoc21/README.md)、[SSH 接入](docs/operations/mac-ssh-relay-20261107.md) |
| 当前进度与待办 | [PROGRESS](PROGRESS.md)、[未实现功能计划](docs/investigation/http-implementation-plan-20261112.md)、[问题清单](docs/investigation/current-issues.md) |
| 开发约定 | [AGENTS](AGENTS.md)、[OpenSpec](openspec/README.md)、[当前调查任务](openspec/changes/complete-socai2-investigation-chain/tasks.md)、[文档导航](docs/README.md) |
| 历史资料 | [归档索引](docs/handoff/history/README.md)、[11-14整理及路径映射](docs/handoff/history/2026-11-14-investigation-cleanup/README.md)；旧设计和执行回执按原批次解释 |

业务后端通过HTTP对接，资产库存由业务后端维护，调查服务只读取匹配结果。未解决问题随调查结论展示，需人工核实时由用户创建任务。当前服务配置、数据边界及未完成事项见[前后端交接](FRONTEND_BACKEND_HANDOFF.md)。旧4173静态样例、旧UUID与历史模型失败只作离线追溯，不回灌已清理的活动环境。
