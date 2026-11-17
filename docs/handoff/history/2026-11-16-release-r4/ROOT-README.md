# socai2 · stingAISOC

本仓库提供告警分诊、事件诊断、Case 调查，以及对应的管理、保存和查询服务。前后端从[交接指南](FRONTEND_BACKEND_HANDOFF.md)开始，通过 HTTP 对接。

21 的后端接口为 **`http://192.168.1.21:18024`**，业务路径前缀为 `/api/v1/socai2`；[Swagger](http://192.168.1.21:18080/)按**告警、事件、调查**分类，包含用途、参数、输入输出示例、错误和实现状态。原交接合同列出71个业务操作（69实现、2问答暂缓501）；**11-15测试预检发现21实际仅64操作，缺7项既有功能，无凭据业务读取返回401**，见[运行差异与处理](docs/operations/evidence/http-test-alignment-20261115-01/README.md)。以下功能描述指仓库已交付能力，不代表当前21全部可用。Case 基本管理、关闭和重开，以及告警人工判定、告警／事件的单条和批量管理已实现。告警、事件和调查列表支持全库筛选、双向排序、游标分页及完整CSV导出（E54–E56）；新增事件归并统计E57，在同一范围内区分已归并和未归并告警；Case普通评论E58/E59支持提交和分页读取；Case附件引用E60–E62支持登记、目录和单项信息，文件上传/下载由业务后端负责；E21采用已有调查结果、E63采用预览与E64判断历史已实现；新增[E65案件故事查询](docs/integration/case-story-http.md)，支持集中阅读、搜索和分页；新增[E66案件候选查询](docs/integration/case-exploration-http.md)，逐对返回匹配依据，支持时间范围及分页；新增[E67–E69探索保存恢复](docs/integration/case-exploration-save-http.md)，固定底图、展开来源及画布，新结果不替换旧保存；[E70相似历史复核](docs/integration/alert-review-http.md)支持同主机且同战术、同IP或合法算法哈希，逐对说明依据；AI对话暂缓。新增[E71同主机最近告警](docs/integration/alert-host-http.md)，取同主机最新发生7条，不要求同战术。预检确认静态Swagger仍docs19/71操作，与实际64操作不一致；按负责人要求等待统一发布后联验。

当前测试目标为21：实际18024版本`main-a6660267-20261114`，镜像`main-a6660267-full`，数据库`aisoc`仍为127增量/28表450列。本机停用，不作为当前联调环境；原11-13发布回执保留历史。

本地待统一发布的接口保持内部可信、无鉴权：新增[统一分析记录目录](docs/integration/run-directory-http.md)、[步骤与工件读取](docs/integration/run-records-http.md)及[分析任务列表/详情](docs/integration/analysis-tasks-http.md)，当前主应用候选80操作；[告警自动分诊查询](docs/integration/alert-auto-http.md)已完成同源联验，旧手动告警入口已从候选移除。这些候选功能尚未同步至21，实际状态以上述只读回执为准。[事件异步诊断](docs/integration/analysis-submission-http.md)已接真实执行器并通过提交、消费、保存及读回；[范围/覆盖](docs/integration/incident-analysis-http.md)含部分覆盖、失败和unknown，103次HTTP及12项直接检查通过。E37在候选中返回202，[Case分配和关联查询](docs/integration/case-allocation-http.md)已完成72次HTTP联验，[Case首轮执行与读取](docs/integration/case-initial-http.md)已完成39次HTTP及6项直接检查，旧E11/E13已从候选移除；第7步[Case检查/再次调查](docs/integration/analysis-submission-http.md)已完成新案首轮→无变化检查跳过→再次调查闭环，41次终态读取/原key回放及47次周期边界读取通过；[80操作三类Swagger包](docs/operations/evidence/case-update-http-20261115-01/swagger/manifest.json)和交接文档已同步，保持无鉴权。第8–10步定向分析、手动综合及知识后台异步维护后置，不提前开放接口，不作为本期第1–7步主流程联验前置；第11步结合测试对话既有[完整测试方案](openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md)完成本期主流程及独立HTTP最终验证。暂不部署，统一交付安排见当前OpenSpec。

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
| 服务配置与部署 | [独立 HTTP 服务](deploy/http-service/README.md)、[全模块部署](deploy/README.md)、[21 部署](deploy/aisoc21/README.md)、[SSH 接入](docs/operations/mac-ssh-relay-20261107.md) |
| 当前进度与待办 | [PROGRESS](PROGRESS.md)、[未实现功能计划](docs/investigation/http-implementation-plan-20261112.md)、[问题清单](docs/investigation/current-issues.md) |
| 开发约定 | [AGENTS](AGENTS.md)、[OpenSpec](openspec/README.md)、[当前调查任务](openspec/changes/complete-socai2-investigation-chain/tasks.md)、[文档导航](docs/README.md) |
| 历史资料 | [归档索引](docs/handoff/history/README.md)、[11-14整理及路径映射](docs/handoff/history/2026-11-14-investigation-cleanup/README.md)；旧设计和执行回执按原批次解释 |

告警接收、Fusion 处理和调查数据整理自动运行；告警分诊、事件诊断与 Case 调查由调用方显式启动，启动后程序完成该次处理和保存。Agents 自动分析消费者目前关闭，未交付“新告警自动串起整条调查流程”。固定流程的输入筛选和存取程序已随功能版发布，完整调查的真实模型质量仍未通过；实际版本、当前评审问题和证据见 [PROGRESS](PROGRESS.md)。

调查库当前为 `aisoc.socai2`，28 表、450 列。业务后端通过 HTTP 对接，资产库存由业务后端维护，调查服务只读取匹配结果。未解决问题随调查结论展示；用户需要人工核实时创建任务。4173 页面用于测试，具体后端功能以接口文档的实现状态为准。

范围以已确认的告警、事件、调查功能清单为准。告警交接字段保持稳定，配置从显式 profile 读取，凭据保存在忽略提交的受控文件中。
