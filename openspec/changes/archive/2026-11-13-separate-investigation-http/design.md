# HTTP服务边界设计

## 1 代码归属与依赖方向

`services/api/investigation_http/` 为独立HTTP包，与现有 `app/` 同级。保留同一构建上下文，避免要求处理服务安装HTTP包或重排整个调查核心。独立应用入口为 `investigation_http.main:app`。

| 目录/模块 | 职责 |
| --- | --- |
| `main.py`、`external_routes/` | 仅对外业务接口的应用装配、HTTP参数、响应与状态码；不直接读写SQL或调用模型 |
| `dependencies.py`、`errors.py` | 请求所需服务、身份及统一已有业务错误到HTTP的转换 |
| `ports.py` | 路由实际使用的用例方法合同；不暴露Session、Store或消费者 |
| `contracts.py` | HTTP专用请求定义；显式导出已冻结的共享业务DTO，避免复制模型导致合同漂移 |
| `adapters/services.py` | 唯一业务实现装配；Case管理、A/I执行后读取在此接现有业务方法 |
| `adapters/identity.py` | 接现有身份解析和登录路由，复用凭据，不另建认证体系 |
| `adapters/runtime.py` | 接既有配置/连接/健康检查；只启动HTTP所需资源，不导入主API生命周期 |
| `deploy/http-service/` | 独立profile、端口、目标库、镜像与私密配置路径 |
| `app/socai2/` | 调查用例、存储、模型、执行；不导入 `investigation_http` 或HTTP路由 |

依赖方向：HTTP路由 → 用例端口 → 适配层 → 现有调查核心。共享业务数据合同作为公开边界保留原定义；HTTP专用定义归HTTP包。核心业务不因为返回JSON而反向调用HTTP包。

不是将调查复制到新目录，也不承诺第三方依赖/镜像已完全瘦身：本批复用当前业务核心及认证运行依赖，但HTTP代码归属与调用边界独立。以后替换部署或业务实现时修改适配层；不在路由塞入SQL、模型编排、Kafka消费者或调查规则。

## 2 对外与内部调用的具体区别

负责人追加明确：分类依据是调用用途，不是“是否使用HTTP”。不将所有HTTP都归入对外交接，也不强行把内部调用改为HTTP。

| 调用 | 当前代码事实 | 本次处理 |
| --- | --- | --- |
| 业务后端查询/管理告警、事件、Case、任务/结果 | 18024的53操作 | 归本包external_routes，对外Swagger只维护这些业务能力 |
| 业务后端显式analyze/diagnose/start | 对外入口调用StageResultService/CaseService | 仍是对外业务操作；不将入口后的每个阶段暴露为新接口 |
| Case背景→分析→补查→综合→保存 | BaselineService/BaselineExecutor直接函数调用 | 留在调查核心，不经过对外列表/详情接口 |
| 模型、token计数、嵌入和Qdrant | TenantChatGateway、BackendTokenMeter、Vectors向组件发送HTTP | 内部出站客户端留在核心适配器，不挂对外路由或混入业务Swagger |
| 当前日志查询、UEBA/情报及资产 | LakeGateway直连ClickHouse；对应适配器查询PG | 保持当前调用方式，不为分层改成HTTP |
| 旧调查v2内部链 | Agents的activity_records调用 `/api/v2/investigation/query`；gateway调用独立Agents `/internal/investigation-v2/...` | 原独立应用/客户端和路径保留，不并入18024；源码存在不代表当前主流程使用或线上启用 |

旧内部应用在 `app/investigation_v2/*_api.py`、`services/agents/app/investigation_v2/*_api.py` 独立创建，18024没有挂载。本批不迁移这些历史协议、不启停对应服务。以后若新增内部回调，归内部应用并维护独立内部合同，不能加到external_routes或公开业务Swagger中。复用能力通过业务服务实现，避免内部组件调用对外列表接口获取调查所需原件。

## 3 兼容

- 53个调查操作的方法、路径、参数、operationId、状态码、请求/响应Schema保持；预留3操作仍501。
- 旧入口与7个旧路由模块仅作兼容转接，同一模块/依赖对象支持既有调用与依赖覆盖。主API仍按原挂载范围运行，不新增A/I执行路由。
- 数据库、模型调用、Run、消息主题和消费者不改。显式执行继续调用同一调查服务；读取不产生执行。
- 所有可变地址、端口、库、开关仍经独立profile/受控环境装配；不在新包引入默认环境回退。新候选配置显式选择新入口，在线配置在发布时才切换。
- 列表新增两个封套字段已于2026-11-13获确认，只在列表change实施，本项纯边界迁移不提前改字段。

## 4 直接验收

迁移前保存运行时OpenAPI，迁移后比较所有调查operation及可达Schema。验证新入口和兼容入口使用同一实现、旧主API仍不加载独立执行路由；通过静态依赖检查禁止路由导入app/sqlalchemy/模型/消费者，禁止核心反向依赖HTTP。

复用已有Case/任务/主体管理/执行入口定向验证，直接检查请求传入、服务结果与错误原样映射。新批次在本机隔离库走真实HTTP读取与Case/H/管理保存读回；模型使用现有替身或不触发，不调用真实模型。未部署21必须明确记录，不由候选成功冒称线上生效。
