# 验证与两端发布

2026-11-13，证据目录：[http-boundary-20261113-01](../../../../docs/operations/evidence/http-boundary-20261113-01/)。本项保留原53操作，不新增查询字段。测试未修改并行模型输入源码。

- `before-openapi.json`：迁移前从真实应用生成的完整HTTP合同；`contract-check.json`：迁移后完整OpenAPI相同、新旧入口为同一app。
- `test_socai2_http_boundary.py`、independent_app、case_read_gate、case_ai_reserved、case_queue、case_page_data：34项及18个子检查通过。检查对外/内部路由隔离、旧模块转接身份、无HTTP包时核心导入、已有输入/错误与读取规则。
- 本机原生候选 `http-boundary-20261113-r1-local`，`127.0.0.1:18026`，真实隔离库`v12_upgrade_dev`。启动首次受沙箱本机端口限制，未创建进程；获工具审批后启动，原18024保持。
- `fixture.json`：独立新合成3告警/3事件，原批次不重派。`case-task-http/`：新Case、任务创建/修订、历史修订和pending Run读取及501保留。
- `boundary-responses.json`：三类列表、告警反馈/读回、事件管理/读回、Case管理/关闭/重开/读回及旧版本409。合计24次正常TCP请求，未替换业务依赖。
- `functional-check.json`：真实SQL比较告警/事件/Case全部facts，任务当前修订和pending Run正确；无真实模型。
- `stage-asgi-pg.json`：复用A/I入口直接测试，新适配层调用原执行及读取服务。真实PG、ASGI身份替身、不可用模型替身，2项通过；已保存failed状态和幂等重放符合预期，不是模型成功。

发布配置在 `deploy/http-service/http-boundary/`，新入口为 `investigation_http.main:app`。21仅叠加26个HTTP包/兼容文件，基底为已发布subject-management镜像；不带并行模型修改。临时18026候选验收后已停止，见 `candidate-cleanup.json`。其后收到负责人“继续推进”，完成下面的两端发布。该发布回执形成于Git提交之前；后续源码同步以包含本目录的Git提交及父项目server引用为准。

独审发现旧只读校验依赖 `app.socai2_main.configured_database_name`，首轮定向执行报ImportError；已补同函数兼容导出。旧独立包生成器也已补齐新包；主API发布器增加显式 `additional_packages`，冻结、镜像构建、镜像及运行文件核验均包含该包。处理组件仅用调查核心，不要求加载对外HTTP。既有日期固定的历史修复包未重写。

修正后6项离线定向检查通过：3项边界、1项原只读校验、2项新旧打包方式；其中发布器使用真实文件冻结、Docker调用替身核对COPY与逐包摘要，不冒称已构建真实镜像。候选重新打包，最新 `source-manifest.json` 对应reviewed包；首次包摘要保存在 `initial-source-manifest.json`。没有重复24次业务写入。

## 两端发布与读回

- 21：`http-boundary-20261113-r1`，镜像`sha256:b9316a414bf8bc1c388f02cf1edf7137f7ff096a9d05d22559f0acc62b045f3c`，18024；实际reader/writer均为`aisoc`，接口53操作，其他运行容器保持。`21-build.json`、`21-api-release.json`记录实际构建/切换。
- 本机：`http-boundary-20261113-r1-local`，ARM64原生Python，18024，`v12_upgrade_dev`。运行代码位于普通项目目录 `../socai2-http-runtime/http-boundary-20261113-r1`，622文件从21实际发布代码包冻结，26个覆盖文件逐值核验，不加载工作区并行模型修改。配置路径仍由本机profile显式指定；`local-source.json`、`local-api-release.json`保留来源及切换回执。
- 本机正式入口新建合成Case `704fec1e-7533-57e8-9ea9-b662f38b928f`，9次HTTP覆盖创建、任务修订、当前/历史读取、pending Run与501；另GET任务修改后的Case，SQL核对Case/任务修订/Run通过，未启动Run或模型。见 `local-release-http/`、`local-case-after-task.json`、`local-release-sql.json`。
- 21采用既有验收记录：12次GET比较6个告警/事件facts、Case/任务/Run业务字段，并读取管理条件、任务及历史；显式READ ONLY SQL核9个对象通过。`21-readback.json`、`21-readonly-sql.json`保留实际目标及结果，没有新增或修改正式业务数据。
- 自动审批拒绝了正式库新建合成Case/任务的验证请求，操作未执行；改用上述只读复验。本机真实写入已覆盖保存/修订。不能把只读21验收描述为本轮生产写入测试。见 `production-validation-scope.json`。
- 初次读回脚本把动态Run `observed_at`当固定值、把HistoryPage误当含total，已按原合同修正；Case SQL初次使用任务修改前的HTTP版本，改读修改后的Case再核对。均未改变接口或业务数据，原核验问题保留在 `readback-check-correction.json`。
- 两端Swagger保持docs7；业务合同未变，六个入口均200且摘要与已发布版本一致，无文档容器重启。独立HTTP根profile已同步当前发布；主API、处理流程、模型、消费者、数据库结构和内部HTTP保持。

[独立审计](audit.md)已完成本地及发布后的限定复核，无剩余阻断。独审逐值核对26个覆盖文件、622个本机冻结文件、两端profile及实际读回，修正README残留旧版本后通过；没有追加业务请求或真实模型调用。当前汇总见证据目录中的 `delivery-summary.json`。
