# socai2 · stingAISOC

本仓库提供告警分诊、事件诊断、Case 调查，以及对应的管理、保存和查询服务。前后端从[交接指南](FRONTEND_BACKEND_HANDOFF.md)开始，通过 HTTP 对接。

21 的后端接口为 **`http://192.168.1.21:18024`**，业务路径前缀为 `/api/v1/socai2`；[Swagger](http://192.168.1.21:18080/)按**告警、事件、调查**分类，包含用途、参数、输入输出示例、错误和实现状态。当前列出 57 个 HTTP 操作：54 个已实现，3 个问答／采用操作预留并返回 `501`。Case 基本管理、关闭和重开，以及告警人工判定、告警／事件的单条和批量管理已实现。告警、事件和调查列表支持全库筛选、双向排序、游标分页及完整CSV导出（E54–E56）；新增事件归并统计E57，在同一范围内区分已归并和未归并告警；Swagger已同步docs10。

本机18024为 `grouping-summary-20261113-r1-local`，21正式18024为 `grouping-summary-20261113-r1`；两端均已挂载57操作，本机使用 `v12_upgrade_dev`，21使用 `aisoc`。

| 内容 | 入口 |
| --- | --- |
| 对接总入口 | [前后端交接指南](FRONTEND_BACKEND_HANDOFF.md) |
| 页面功能与产品规则 | [125 项功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)：告警 22 项、事件 15 项、调查 88 项，包含目的、结果、后端实现状态和接口；[产品说明](docs/design/alert-incident-case-product-requirements.md)、[已确认的七类规则](docs/design/investigation-product-decisions.md) |
| HTTP 接口与字段 | [接口交接包](deliverables/investigation-validation-20261106/http-handoff/README.md)、[逐接口说明](deliverables/investigation-validation-20261106/http-handoff/endpoints.md)、[页面字段与跳转](deliverables/investigation-validation-20261106/frontend-data-navigation-contract.md) |
| 对外与内部接口边界 | [调用分类与代码归属](docs/design/investigation-http-boundary.md)：对外查询/业务操作与内部步骤、内部HTTP分开；分离架构继续保持，列表新增参数及两个封套字段见当前交接 |
| Swagger 本地配置 | [Docker 安装与配置](deploy/api-docs/README.md)：本机 ARM64、21 AMD64、服务地址选择与离线安装；[本机已部署 Swagger](http://127.0.0.1:18080/) |
| Kafka 与其他组件 | [当前组件对接说明](docs/integration/component-handoff-current.md)：Topic、生产者/消费者、消息示例、数据库、模型与知识服务 |
| 测试数据与操作 | [后端测试指南](docs/integration/backend-test-guide.md)、[21 测试记录 ID](docs/integration/examples/current/live-21-fixtures.json)、[4173 测试页用法](docs/integration/test-page-4173.md) |
| 调查数据 | [表职责与写入范围](docs/investigation/investigation-table-scope.md)、[当前字段字典](docs/design/socai2-data-contract-current.json)、[数据库安装入口](deploy/database/CURRENT.md) |
| 服务配置与部署 | [独立 HTTP 服务](deploy/http-service/README.md)、[21 部署](deploy/aisoc21/README.md)、[SSH 接入](docs/operations/mac-ssh-relay-20261107.md) |
| 当前进度与待办 | [PROGRESS](PROGRESS.md)、[未实现功能计划](docs/investigation/http-implementation-plan-20261112.md)、[问题清单](docs/investigation/current-issues.md) |
| 开发约定 | [AGENTS](AGENTS.md)、[OpenSpec](openspec/README.md)、[当前调查任务](openspec/changes/complete-socai2-investigation-chain/tasks.md)、[文档导航](docs/README.md) |

告警接收、Fusion 处理和调查数据整理自动运行；告警分诊、事件诊断与 Case 调查由调用方显式启动，启动后程序完成该次处理和保存。Agents 自动分析消费者目前关闭，未交付“新告警自动串起整条调查流程”。HTTP 功能验证与模型结论质量分开记录：完整调查的真实模型质量仍未通过，本轮模型输入修改尚未部署；实际版本和证据见 [PROGRESS](PROGRESS.md)。

调查库当前为 `aisoc.socai2`，28 表、450 列。业务后端通过 HTTP 对接，资产库存由业务后端维护，调查服务只读取匹配结果。未解决问题随调查结论展示；用户需要人工核实时创建任务。4173 页面用于测试，具体后端功能以接口文档的实现状态为准。

范围以已确认的告警、事件、调查功能清单为准。告警交接字段保持稳定，配置从显式 profile 读取，凭据保存在忽略提交的受控文件中。
