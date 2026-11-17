# 当前 HTTP 候选配置字典

适用版本 `streaming-http-20261115-r1`，仅解释[本候选profile](streaming-20261115-01/profile.json)及实际加载的配置。完整部署顺序见[部署入口](README.md)。下面“当前值”来自仓库候选，不代表21已加载。所有文件路径都必须按实际运行主机/容器解释；没有配置时不改用其他环境。

## 加载与生效

`manage.py --profile <JSON> <action>`每次读取指定profile。`package`校验并冻结来源；`prepare`读取私密JSON后合并profile.environment（后者优先），加上数据库名/发行号，生成私密env文件；`start`按生成的Compose创建单worker服务。进程级环境在启动时生效；运行中编辑仓库JSON不会更新已发布镜像。查询策略虽在调用时读取文件，发布仍采用新包/正常重建，不在容器里修改文件。政策对象有进程缓存，变更后重启相应服务。

以下profile字段均在本候选显式填写。工具保留的一些可选默认不作为本部署的选择；JSON布尔是true/false，`environment`和私密环境里的值全部为字符串。

## 哪些需要部署方填写

| 类别 | 部署方怎么处理 | 字段能否省略 |
| --- | --- | --- |
| 部署必填 | 确认本环境真实库地址/连接、端口、目录、网络、租户和记录人；候选已有目标值也要核实 | 本候选必需；模板中的示例/预定值不等于资源已经创建 |
| 保留默认 | 使用随本候选提供的完整模板值，通常不改分页、数量上限、时限、开关或包内路径 | “保留默认”指保留模板字段和值，**不代表可以删键**；JSON策略字段通常没有省略默认 |
| 启用时必填 | 使用对应能力时供给；本候选已启用写入、可信上下文及PG TLS，所以对应项当前必需 | 只有该能力明确未启用且加载器允许时才可不供给；不能靠缺文件使程序猜测环境 |
| 程序生成 | 使用打包、镜像观察和实际运行核对产物；程序据实生成或核对后记录 | 不手填hash、数量或状态来假装通过；内容变化后重新冻结/验证 |

当前可以直接保留模板的是分页/查询上限、每案容量和任务策略等；修改业务规则按既有OpenSpec范围处理。真正缺少的是新库及记录身份的实际供给、真实读写URL和CA摘要，不是要求操作者重新设计所有参数。

## 打包与部署profile逐项

| 字段 | 配置类别 | 类型、当前值或示例 | 用途、必填与验证位置 |
| --- | --- | --- | --- |
| `version` | 保留默认 | string；`socai2.http-service.v1` | 工具格式版本；CLI必需且精确匹配 |
| `release` | 部署必填 | string；`streaming-http-20261115-r1` | 独立发行号；生成私密目录及SOCAI2_HTTP_RELEASE，实际OpenAPI版本须一致 |
| `root` | 部署必填 | absolute path；候选根下`/http` | prepare的私密输出根；不指向正式服务目录 |
| `reference_container` | 部署必填 | string；`socai2-http-api` | prepare核参考基镜像ID；不继承它的连接和挂载 |
| `base_image` | 程序生成 | string；`sha256:d602…5425e`，完整值见profile | 固定依赖镜像ID；prepare/build校验，不能用浮动latest替代 |
| `base_tag` | 程序生成 | string；`socai2-http-base:streaming-d60231607c5e` | build为已核ID生成本地FROM标签，不拉取 |
| `buildkit` | 保留默认 | boolean；false | 选择本次docker build的BuildKit环境；不影响业务行为 |
| `image` | 部署必填 | string；`socai2-http-api:streaming-http-20261115-r1` | 构建输出标签；verify对照容器实际镜像ID |
| `container` | 部署必填 | string；`socai2-streaming-http-20261115` | 候选容器名；只操作该服务 |
| `project` | 部署必填 | string；`socai2-streaming-http-20261115` | Compose项目名，避免复用正式项目 |
| `platform` | 部署必填 | string；`linux/amd64` | 21目标CPU架构；本机ARM64导入通过不代替该镜像验证 |
| `network` | 部署必填 | string；`socai2_default` | 已有Docker外部网络；工具不创建网络 |
| `bind` | 部署必填 | IP string；`192.168.1.21` | 宿主机监听/验证地址；prepare检查端口可绑定 |
| `port` | 部署必填 | integer；18424 | 候选宿主端口；不修改正式18024 |
| `container_port` | 保留默认 | integer；8000 | Uvicorn容器端口及映射目标；同一profile一致 |
| `database` | 部署必填 | string；`socai2_streaming_20261115` | 显式库名；prepare核URL，lifespan核current_database |
| `database_host` | 部署必填 | string；`192.168.1.21` | prepare要求读写URL都精确匹配；不会自动替换为localhost |
| `database_port` | 部署必填 | integer；5432 | 同上；URL必须带显式端口 |
| `entry` | 保留默认 | string；`investigation_http.main:app` | 唯一外部应用入口；不能换成平台main或内部调查应用 |
| `memory` | 保留默认 | Compose memory string；`2g` | 容器内存上限；prepare写入Compose，启动后核实际配置 |
| `tmpfs` | 保留默认 | mount string；`/tmp:rw,nosuid,nodev,size=128m,mode=1777` | 只读rootfs下的临时目录；不存数据库或持久结果 |
| `build_timeout_seconds` | 保留默认 | integer；300秒 | 等待本地镜像构建命令的上限；超时不能当构建成功 |
| `startup_timeout_seconds` | 保留默认 | integer；50秒 | start等待readyz/读回的上限；不代表模型调用时限 |
| `environment` | 保留默认 | object；下表列全量字段 | 当前候选的非秘密字符串环境，优先于私密JSON同名值 |
| `runtime_environment_file` | 启用时必填 | absolute path；候选根`/private/http-runtime.json` | 必需；主机受控JSON，仅运行阶段读取。不存在时prepare在Docker操作前拒绝 |
| `runtime_mounts` | 启用时必填 | array；本次仅PG CA | 显式挂载清单；不从参考容器补齐，全部只读 |
| `runtime_mounts[].source` | 启用时必填 | absolute host path；`/opt/sting-aisoc-socai2/certificates/socai2-ca.crt` | 必须是实际文件；prepare读取计算hash |
| `runtime_mounts[].target` | 启用时必填 | absolute container path；`/run/certs/ca.crt` | 容器读取位置；不得重复目标 |
| `runtime_mounts[].sha256` | 程序生成 | 64位hex；当前null、待提供 | 必需实值；null有意阻止prepare，不是关闭校验 |
| `source_root` | 保留默认 | path string；`.` | 相对仓库根的来源，也可显式绝对路径；当前取已核同版工作树 |
| `complete_packages` | 保留默认 | object；`services/api/app→app`、`services/api/investigation_http→investigation_http` | 两个完整包根必需；拒绝漏件、多余映射或符号链接，不打包隐藏文件和Python缓存 |
| `patches` | 程序生成 | object；723条source→target映射 | 明确源码、JSON/SQL、公开策略及依赖元数据；目标相对包根，不是仅增量覆盖清单 |
| `expected_source_hashes` | 程序生成 | object；每个来源SHA-256 | 键与patches完全相同；打包前逐项核对，变动必须重新冻结 |
| `expected_openapi_file` | 保留默认 | relative package path；`contract/openapi.json` | verify比较实际合同，只排除展示用info/servers，不能仅检查路由数量 |
| `expected_operations` | 程序生成 | integer；80 | 业务method/path数量；完整合同比较同时进行 |
| `replace_existing` | 保留默认 | boolean；false | 本次只新增候选，不替换正式服务；正式发布另行冻结目标profile |

生成的 `manifest.json` 记录全部包文件SHA-256；`compose.json`与`before.json`在prepare后生成。固定运行方式为UID/GID10001、单worker、只读rootfs、显式tmpfs、只读挂载，不另外启动worker/消费者。当前工具未提供这些固定项的独立运行参数，不能把文档里的其他值当可用配置。

## 私密连接与环境逐项

私密JSON必须包含以下两项；值不写入Git、公开回执或命令参数。URI中的账号/密码须按URL规则编码。当前未生成真实文件，文档不提供可误用的假连接。

| 字段 | 配置类别 | 类型、目标与用途 | 加载/验证 |
| --- | --- | --- | --- |
| `DATABASE_URL` | 部署必填 | string；`postgresql+asyncpg`读连接；192.168.1.21:5432/socai2_streaming_20261115，角色`socai2_streaming_20261115_reader` | prepare核目标；应用启动建立读连接并核实际库。URL带`sslmode=verify-full`，CA由PGSSLROOTCERT指定 |
| `SOCAI2_CASE_DATABASE_URL` | 启用时必填 | string；同库写连接，角色`socai2_streaming_20261115_writer` | 独立事务保存Case、管理、人工反馈及分析任务；目标必须与读连接相同。启动核实际库，真实业务保存/读回另外验证 |

以下是profile.environment的全部当前字段。末尾两项由工具生成，无需调用方传入。

| 字段 | 配置类别 | 类型／当前值 | 用途、加载与验证 |
| --- | --- | --- | --- |
| `ENVIRONMENT` | 保留默认 | string；test | 候选进程环境标记；settings启动读取，不据此选择其他数据库 |
| `DEBUG` | 保留默认 | boolean string；false | SQL引擎不输出debug SQL；不是业务错误吞掉开关 |
| `PYTHONDONTWRITEBYTECODE` | 保留默认 | string；1 | 禁止Python在只读镜像写pyc；解释器启动读取 |
| `PYTHONPATH` | 保留默认 | absolute path string；`/app` | 包导入根；离线验证核所有app/HTTP模块来自完整包 |
| `SOCAI2_CASE_API_ENABLED` | 保留默认 | boolean string；true | 启用调查业务写入及任务受理；false时相关写操作503。它不启动执行器 |
| `SOCAI2_PAGE_READ_ENABLED` | 保留默认 | boolean string；true | 告警/事件/Case列表、详情和业务查询；false时对应读取503 |
| `SOCAI2_ANALYSIS_READ_ENABLED` | 保留默认 | boolean string；true | 分析任务、Run、结果与原件读取；false时对应读取503 |
| `SOCAI2_STAGE_EXECUTION_ENABLED` | 保留默认 | boolean string；false | 本外部服务不使用阶段内直接执行；事件/Case异步提交依赖Case写入开关，执行归独立调度 |
| `AISOC_STARTUP_SCHEMA_MIGRATIONS` | 保留默认 | boolean string；false | 明确不由HTTP启动迁移；本独立lifespan本身不调用迁移器 |
| `AISOC_DEV_AUTH_BYPASS` | 保留默认 | boolean string；false | 必须保持false；无鉴权来自独立可信上下文装配，不借平台开发绕过。true在启动检查被拒绝 |
| `SOCAI2_HTTP_CONTEXT_FILE` | 启用时必填 | absolute container path；`/app/config/context.json` | 启动读取tenant/actor，缺失或格式错停止；不是登录凭据 |
| `SOCAI2_RUN_RECORDS_CONFIG_FILE` | 保留默认 | path；`/app/config/run-records.json` | Run目录/步骤/原件分页策略；实际用例加载校验 |
| `SOCAI2_ANALYSIS_TASKS_CONFIG_FILE` | 保留默认 | path；`/app/config/analysis-tasks.json` | 三类任务读取/受理使用，与调度服务同版；HTTP不执行周期扫描 |
| `SOCAI2_CASE_ALLOCATION_CONFIG_FILE` | 保留默认 | path；`/app/config/case-allocation.json` | Case容量分配与关联Case分页；建案/读取用例加载 |
| `SOCAI2_INVESTIGATION_POLICY` | 保留默认 | path；`/app/config/investigation-policy.toml` | 核心读取、边界/业务判断所需同版政策，缓存于进程；当前三个IO合同离线加载通过。HTTP不调用模型；详项由调查/模型配置说明维护 |
| `SOCAI2_MANAGEMENT_CONFIG_FILE` | 保留默认 | path；`/app/app/socai2/subject_management.json` | 告警/事件单批管理上限，调用读取 |
| `SOCAI2_EXPORT_CONFIG_FILE` | 保留默认 | path；`/app/app/socai2/list_export.json` | CSV行数、字节及SQL时限；启动及导出读取校验 |
| `SOCAI2_EXPLORATION_CONFIG_FILE` | 保留默认 | path；`/app/app/socai2/exploration-query.json` | 关系图候选的默认时间范围；查询读取 |
| `SOCAI2_EXPLORATION_STATE_CONFIG_FILE` | 保留默认 | path；`/app/app/socai2/exploration-state.json` | 图保存大小和展开关系上限；保存读取策略 |
| `SOCAI2_ALERT_REVIEW_CONFIG_FILE` | 保留默认 | path；`/app/app/socai2/alert-review-query.json` | 相似历史告警回看时间；查询读取 |
| `SOCAI2_ALERT_HOST_CONFIG_FILE` | 保留默认 | path；`/app/app/socai2/alert-host-query.json` | 同主机近期告警显示条数；查询读取 |
| `DATABASE_POOL_SIZE` | 保留默认 | integer string；5 | 每个读/写SQLAlchemy引擎的基础连接池容量；启动生效；两池不能误计成总5个 |
| `DATABASE_MAX_OVERFLOW` | 保留默认 | integer string；5 | 每池临时增加的连接数上限；启动生效，不是调查并发N |
| `DATABASE_POOL_RECYCLE_SECONDS` | 保留默认 | integer string；300秒 | 每池连接回收间隔；启动读取，不是SQL超时 |
| `PGSSLROOTCERT` | 启用时必填 | path；`/run/certs/ca.crt` | PostgreSQL客户端CA文件，配合URL verify-full；实际TLS连接在候选启动时验证 |
| `AISOC_CORS_ORIGINS` | 保留默认 | comma-separated string；`http://192.168.1.21:18480,http://127.0.0.1:18081` | 浏览器允许访问的Swagger来源，启动装配CORS；不是调用者鉴权，业务后端HTTP不受浏览器CORS限制 |
| `SOCAI2_SERVICE_DATABASE_NAME` | 程序生成 | string；工具从database生成 | 应用启动比对URL及current_database；避免读写混库 |
| `SOCAI2_HTTP_RELEASE` | 程序生成 | string；工具从release生成 | OpenAPI info.version与运行回执标识；verify精确核对 |

无额外HTTP认证secret、Redis URL、Kafka topic、模型key或上传目录参数。不能因核心包包含其他模块就把它们的全平台环境变量复制进HTTP运行文件。

## 可信业务上下文

[context.json](streaming-20261115-01/context.json)三个字段全部必填、只接受这三个键；应用启动加载，修改须重新冻结和重启。当前ID是候选约定，尚待数据库实际准备。

| 字段 | 配置类别 | 类型／当前值 | 用途与验证 |
| --- | --- | --- | --- |
| `tenant_id` | 部署必填 | UUID；`fa031e01-0c89-5b35-88e7-37c1d5cf078b` | 所有业务读取/写入的数据归属；与消费/调度候选一致 |
| `actor_id` | 部署必填 | UUID；`a745100d-0bad-5c24-a9e2-5cdab10a0963` | 统一记录操作人；必须在同租户有实际用户记录，否则业务保存无法完成 |
| `actor_name` | 部署必填 | nonblank string；`streaming-acceptance` | 操作记录显示名；不证明实际访问者身份 |

## 查询、保存与任务JSON全部字段

以下数值是当前选定文件值。字段均必需；不依赖加载器的路径默认。分页上限只限制单页，按返回游标可以继续读取完整目录。非法分页请求一般422，策略缺失/非法按各接口的503或启动错误处理；不能静默读另一个环境。

| 文件／字段 | 配置类别 | 类型／当前值 | 业务含义、约束与直接验证 |
| --- | --- | --- | --- |
| `run-records.json.default_limit` | 保留默认 | 正整数50 | Run目录、步骤、原件未指定limit的单页条数；不得大于max_limit，检查省略limit的返回 |
| `run-records.json.max_limit` | 保留默认 | 正整数100 | 单页上限；超限422；无总量截断 |
| `analysis-tasks.json.retry_limit` | 保留默认 | 非负整数1 | 确定可重试失败的额外尝试上限；执行由调度负责，HTTP按真实attempt返回 |
| `analysis-tasks.json.retry_delay_seconds` | 保留默认 | 非负整数60秒 | 两次尝试等待；HTTP展示保存的next_retry_at，不自己计时重试 |
| `analysis-tasks.json.automatic_window_seconds` | 保留默认 | 正整数604800秒（7天） | 自动更新资格窗口；与调查侧同版，不当API超时 |
| `analysis-tasks.json.incident_check_interval_seconds` | 保留默认 | 正整数14400秒（4小时） | 事件周期检查间隔，由调度执行 |
| `analysis-tasks.json.case_check_interval_seconds` | 保留默认 | 正整数21600秒（6小时） | Case周期检查间隔，由调度执行 |
| `analysis-tasks.json.default_limit` | 保留默认 | 正整数50 | 任务列表默认单页条数，≤max_limit |
| `analysis-tasks.json.max_limit` | 保留默认 | 正整数100 | 任务列表单页上限；完整任务历史按游标继续读取 |
| `case-allocation.json.case.max_alerts` | 保留默认 | 正整数100 | 每案最多接纳的告警数；超容量按已定续建分配，不静默丢弃成员 |
| `case-allocation.json.source_page_size` | 保留默认 | 正整数200 | 读取来源告警的内部分页大小；不是案容量或API总量上限 |
| `case-allocation.json.default_limit` | 保留默认 | 正整数50 | 关联Case列表默认分页，≤max_limit |
| `case-allocation.json.max_limit` | 保留默认 | 正整数100 | 关联Case单页上限；分两级展示的关联规则不由此改变 |
| `subject_management.json.max_batch_items` | 保留默认 | 正整数100 | 告警/事件人工判定或管理每批最多对象数；超限/空批/重复对象拒绝；单条不改合同 |
| `list_export.json.max_rows` | 保留默认 | 正整数10000 | 单次CSV最多行数；超限按导出接口错误提示，不悄悄截成完整结果 |
| `list_export.json.max_bytes` | 保留默认 | 正整数16777216（16MiB） | 单次CSV字节上限；与分页条数、附件大小无关 |
| `list_export.json.statement_timeout_ms` | 保留默认 | 正整数30000毫秒 | 导出SQL事务语句时限；不是模型或HTTP整请求时限 |
| `exploration-query.json.default_window_hours` | 保留默认 | number；24小时，0＜值≤8760 | 未指定候选查询时间时采用的范围；实际返回window用于核对，不改变成员或创建调查 |
| `exploration-state.json.max_snapshot_bytes` | 保留默认 | 正整数4194304（4MiB） | 保存图快照的JSON字节上限，超限拒绝，不截断原图 |
| `exploration-state.json.max_expanded_links` | 保留默认 | 正整数1000 | 保存的展开关系数量上限，不是自动扩大Case范围 |
| `alert-review-query.json.default_lookback_days` | 保留默认 | number；30天，0＜值≤3650 | 相似历史告警默认回看范围；以源告警时间为参照 |
| `alert-host-query.json.display_limit` | 保留默认 | integer；7，范围1–100 | 同主机近期告警显示条数；不要求战术相同，不代替相似历史查询 |

上述9类查询/任务策略已从解包目录调用实际加载器验证，数值见[离线回执](../../docs/operations/evidence/streaming-http-candidate-20261115-01/offline-02.json)。目标库保存、读回与执行效果仍需真实候选TCP验证。

### 无独立部署参数的功能

- 告警/事件/Case列表筛选、排序、游标及 `filtered_total/next_cursor` 是HTTP请求/返回合同；当前没有额外列表JSON开关。每个参数的默认值/范围看候选OpenAPI，不新增另一个limits文件。
- 事件归并统计按当前数据库成员计算；无独立归并统计配置，不改变Fusion归并规则。
- 附件关联没有上传目录、文件服务器地址或文件大小策略JSON。业务后端传file_id、file_name、mime_type、size_bytes及可选sha256，调查服务保存关联；size_bytes只是对方声明，未探测真实文件。参数长度/分页约束见[附件合同](../../services/api/app/socai2/case_attachment_contracts.py)和Swagger。
- 评论、人工任务、采用、故事及管理的输入限制来自现行DTO/Schema，没有另外的部署参数；不能把请求字段当服务器配置。
- 模型政策详细字段由调查/模型部署说明负责，本服务只引用同版文件；`*_input*.json`、`*.schema.json`是当前执行/数据合同，不能当自由调整的普通限额。
