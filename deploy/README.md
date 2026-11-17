# 全模块部署与配置入口

更新于2026-11-16。本入口只按本轮最新目标版本组织：告警自动分诊、事件异步诊断、Case首轮/持续更新共同使用一个A/I/Case调度器，外部HTTP提交任务并读取结果。第8–10步人工定向/手动综合和知识后台调度后置；已有知识查询保持其已实现范围。旧分阶段包、旧启动接口和参考工程不作为并列部署方案。

**当前：21完整r4已部署，历史业务数据按清单清理并核零。** [实际发布](../docs/operations/evidence/streaming-release-20261116-04/README.md)包含唯一Fusion/联合调度、完整HTTP18024、Swagger18080和4177 r6。正式aisoc为32表521列；新[完整链02](../docs/operations/evidence/streaming-fullflow-20261116-02/README.md)正在执行。D5/D6整体、模型正文质量及change结束审计仍待，当前以[PROGRESS](../PROGRESS.md)为准。

## 配置分四类

| 标记 | 部署人员怎么处理 | 例子 |
| --- | --- | --- |
| **部署必填** | 按目标环境填写或确认，不能用示例地址/账号直接启动 | 数据库地址/库名、tenant/actor、Topic/group、私密文件路径、监听端口、模型上游 |
| **保留默认** | 配置文件提供推荐/当前值，一般不改；需要调整时同时确认影响 | 重试1次/60秒、I4小时/Case6小时、7天窗口、Case100条、日志50条、分页和超时 |
| **启用时必填** | 只有启用对应模块/功能时才填；未启用不要求制造凭据或服务 | 知识向量库/嵌入、外部情报provider、图来源、TLS客户端证书 |
| **程序生成/只读核对** | 由构建/运行记录生成，读回验证，不手工改成“成功” | 镜像ID、文件hash、配置指纹、实际容器ID、任务/Run及验收状态 |

**“保留默认”不等于可以删除字段。** 本项目不少JSON/TOML采用严格结构：复制模板后保留默认值即可，但字段仍必须存在。第三方或源码的开发默认不等于本轮部署推荐；地址中`localhost`、演示账号或历史Topic必须按目标覆盖。生效方式由每页写明，启动时读取的配置修改后需重启相应进程。

## 各模块说明

| 模块 | 部署与逐项配置 | 本轮边界 |
| --- | --- | --- |
| 核心A/I/Case、调度/队列/重试、入站/Fusion、Case容量 | [处理链](../docs/operations/deployment-processing.md) | 唯一联合工厂；默认示例不启用 |
| 对外HTTP、任务/Run/结果读取、写连接和查询策略 | [HTTP服务](http-service/README.md) | 当前源码80操作；异步提交和pending内部透明 |
| Swagger | [API文档服务](api-docs/README.md) | 与同批HTTP OpenAPI一起冻结，不混旧静态文件 |
| LiteLLM、上游模型、tokenizer、预算与输入合同 | [模型配置](../docs/operations/deployment-models.md) | A/I/Deep=8192、C3/C6=16384，按实际上下文计量；最多5发现、一次七部分 |
| Ollama嵌入、Qdrant知识集合与C2检索 | [模型与知识配置](../docs/operations/deployment-models.md) | 维度/集合/来源适用条件必须一致 |
| PostgreSQL、Redis、Kafka、ClickHouse湖、Qdrant、Neo4j、OpenSearch | [数据湖与数据库](../docs/operations/deployment-datastores.md) | 连接与服务端参数分开，保留已有数据 |
| UEBA、Enrichment、ThreatIntel、Actions、Agents保留配置 | [支持服务](../docs/operations/deployment-support-services.md) | 不因列出配置就启用采集、自动响应或旧消费者 |
| 测试账本/只读API | [测试服务](investigation-test/README.md) | W1–W5各步证据保留；当前0.6.0/r6在4177运行，新02批次沿实际读回发布账本 |
| Docker验收CLI | [专用镜像/Compose/操作说明](investigation-test/acceptance-docker.md) | 本机3d封装八个命令；材料/配置只读、结果持久、默认禁网，仅显式run/append可执行。最终验收见3d回执；未部署21或启动任务4 |
| 4177/静态查阅与本地预览 | [支持服务中的查阅说明](../docs/operations/deployment-support-services.md#工作台测试api与swagger) | 实际4177为HTTP只读工作台；旧4173静态演示停止，历史快照不作为活动数据 |
| PG新装/增量与reader | [数据库当前入口](database/CURRENT.md) | 当前正式123–129，32表521列；空库与增量入口不可混用 |
| 21资源、候选及统一发布顺序 | [21部署](aisoc21/README.md) | 本轮按明确授权分阶段发布r4，整体change独审仍待 |
| 本机隔离环境与证据 | [本机说明](local-investigation/README.md) | 中间程序验证；不代替21 Kafka整体验收 |

配置全量导航为[configuration.md](../docs/operations/configuration.md)。逐项覆盖“本轮选用配置+保留支持服务”，不把未使用的平台功能、历史模型示例或数据库厂商所有可选项复制为第二套操作说明。

PG按负责人最新确认只用账号密码，应用不配置CA或客户端私钥；`sslmode=require`作为保留默认，详见[认证口径](../docs/operations/deployment-datastores.md#本轮认证口径)。

## 最小部署填写清单

| 必须确认的内容 | 放在哪里 | 应一致的模块 |
| --- | --- | --- |
| 目标主机/网络/新批目录/平台 | candidate identity、build、transport | 构建/HTTP/调度/测试 |
| 数据库host/port/name、reader/writer/ingress及密码文件 | PG安装profile、HTTP运行profile、调度连接文件 | 入站、任务、执行、读取使用同目标库 |
| 租户、actor及必要基础记录 | identity与运行profile | HTTP创建、入站、Case分配、测试数据 |
| Redis地址/逻辑DB/namespace | 调度及Fusion受控配置 | 独立批次不与正式队列混用 |
| Kafka地址/TLS、Topic/group和明确起点 | 入站/测试producer/Fusion/投影配置 | producer与consumer同Topic，消费组隔离 |
| 数据湖库/读写账号/地址及实际表结构 | 处理profile与Fusionenv | 写入日志与调查补查同一租户/时间/来源 |
| 模型网关地址/路由/key、tokenizer endpoint | LiteLLM私密env及case-v1策略 | 路由和模型合同一致，不自动降级后端 |
| 知识embedding/Qdrant及维度 | knowledge-profile及私密key文件 | 查询与索引一致，功能启用时必填 |
| HTTP/Swagger/测试/查阅监听与挂载 | 各模块显式profile | 候选端口不接管现有服务 |

其余配置原则上先保留本轮模板值；模型并发N、检查周期、重试、容量与工具条数均可配置，但调整需按相互预算核对。测试缩短间隔仅写独立测试profile，不改变正式默认。

## 通用容器字段

| 字段 | 分类 | 含义及核对 |
| --- | --- | --- |
| `name` / 服务名 / `container_name` | 部署必填 | 区分正式与候选对象，不能复用别的项目名误操作 |
| `image` / 镜像摘要 | 程序生成/只读核对 | 选择已冻结镜像并核实际ID，不临时升级latest |
| `pull_policy` | 保留默认 | 固定镜像通常never，目标需预先具备镜像 |
| `command` / `entrypoint` | 保留默认 | 模块唯一启动入口；参数中的配置路径随挂载明确 |
| `env_file` / `environment` | 部署必填或按项默认 | 文件注入环境，显式environment覆盖env_file同名值；秘密不进镜像 |
| `volumes` | 部署必填 | 宿主→容器路径、ro/rw；源码/CA/策略只读，持久数据/回执按需可写 |
| `ports` / `networks` | 部署必填 | 监听与网络；区分容器端口、宿主入口和SSH转发 |
| `user` | 保留默认 | 非rootUID:GID，挂载访问权限匹配 |
| `read_only` / `cap_drop` / `security_opt` | 保留默认 | 根层只读、删除不需能力、禁止提权；可写数据走挂载 |
| `tmpfs` | 保留默认 | 临时内存文件系统及独立大小上限；不放PG数据或审计原件 |
| `cpus` / `mem_limit` / `memswap_limit` / `pids_limit` | 保留默认 | CPU、内存、含交换总额度和进程数；不等于数据盘容量 |
| `ulimits` | 保留默认 | 进程资源上限，例如打开文件数 |
| `restart` / `stop_grace_period` | 保留默认 | 重启策略与正常结束等待，不是业务任务自动重试 |
| `healthcheck.test/interval/timeout/retries/start_period` | 保留默认 | 健康探测命令、周期、超时、失败次数和启动宽限；健康不代表业务/模型验收通过 |

## 发布、验证和回退

顺序为依赖身份/迁移→完整包与显式配置→候选实际TCP→Kafka最小完整链→同批HTTP/查阅→交接与独立结束审计→统一正式发布与实际读回。本轮r4已按用户明确指令完成完整服务发布/清理，新02整链正在验收；实际清单见21发布目录，不重放历史清单。各步骤沿[OpenSpec同一任务树](../openspec/changes/schedule-streaming-investigation-updates/tasks.md)，不另建并行发布流程。

保留上一版镜像、冻结profile与回执。回退只针对本批服务/入口，先停止新的消费和派发并按实际执行状态收尾，再切换已核验配置；不删数据库/卷，不重派结束批次，不用旧代码强行读取不支持的新合同。文档整理没有重启服务、恢复消费者或新模型调用。
