# 独立调查 HTTP 服务

当前测试和对接目标为21。本机环境停用；以下本机启动方式仅供后续明确需要时使用。2026-11-15只读预检确认：21的18024实际镜像为`main-a6660267-full`、版本`main-a6660267-20261114`，64个业务操作；静态Swagger仍docs19/71操作，缺失7项既有路由，无凭据业务读取返回401。见[原始HTTP回执](../../docs/operations/evidence/investigation-test-preflight-20261115-01/http.json)和[差异与处理](../../docs/operations/evidence/http-test-alignment-20261115-01/README.md)。

仓库候选为79个业务操作、默认内部可信，无需登录/Token/角色；21尚未加载可信配置，数据库仍127/28表450列，128/129及新任务/Case能力待统一发布。按负责人最新要求，运行版本与设计不一致就等待发布，本轮不修改21、不增加旧版认证接入方案。

| 环境/资料 | 用途与边界 |
| --- | --- |
| 21 AMD64、aisoc、18024 | 当前实际联调目标，版本及供给以上述11-15只读回执为准；未达本期测试就绪条件 |
| 根aisoc21.json及core-sync profile | 原11-13的investigation-sync-20261113-r1/71操作发布配置留存，不能代表当前main镜像；下一统一发布须显式准备对应版本及全部依赖 |
| 本机ARM64 local.json | 原隔离验证配置，非当前使用环境，不因旧文件存在而启动或回退至本机 |

对外HTTP与内部调查调用保持[架构边界](../../docs/design/investigation-http-boundary.md)，独立入口为`investigation_http.main:app`；核心不导入HTTP包。当前候选的A自动分诊、I异步诊断及Case分配通过各自本地验收，[Case首轮执行](../../docs/integration/case-initial-http.md)已通过受控依赖联验，[第7步更新闭环](../../docs/operations/evidence/case-update-http-20261115-01/README.md)亦已本地通过。HTTP服务不负责调度器生命周期，GET不触发分析。

以下命令及历史profile说明供部署工具使用；执行以届时已验收的完整清单、明确profile和发布范围为准，不能直接重用旧镜像/片段覆盖正在运行的服务。历史[11-13同步回执](../../docs/operations/evidence/investigation-http-sync-20261113-01/README.md)保留，不改写成11-15现状。

本机启动：

```sh
python3 deploy/http-service/manage.py --profile deploy/http-service/local.json local
```

根local profile记录本机实际路径，换电脑时先复制为自己的profile，显式填写已准备的源码目录、Python路径、私密环境文件和目标数据库，再启动；不要直接使用原机器的绝对路径或静默切换数据库。本机不是当前测试目标，不因本页命令而自动启动。

21先在本机`package --output <新目录>`生成无凭据候选，传至profile的`root/releases/<release>`；在21按`prepare`、`build`、限定独审、`start`、`verify`顺序执行。构建使用显式本地镜像标签和已核对ID，`DOCKER_BUILDKIT=0`，不拉取基础镜像。每次新发布使用独立release目录和与当前运行基底一致的profile，不重复执行已完成批次的prepare。

```sh
python3 manage.py --profile profile.json prepare
python3 manage.py --profile profile.json build
python3 manage.py --profile profile.json start
python3 manage.py --profile profile.json verify
```

私密环境只在主机`private/<release>/runtime.env`，权限0600；不进Git或文档。其他容器身份/镜像/启动时间在prepare时保存，verify逐值核对。当前18024是替换已有独立API容器；若需退回，使用上一release保留的compose、镜像和环境重新启动该API，并核对实际版本与数据目标，单纯停止新容器不会恢复旧版。18000/18020其他入口一直保留，数据库不回退或清空。

[直接验证](../../openspec/changes/archive/2026-11-12-serve-investigation-api/validation-20261112.md)区分本机TCP、受限写连接、实际SQL读回和21发布观察；历史真实模型失败不因入口通过而关闭。HTTP操作验证用`verify_flow.py`及环境专属profile，一次新Case/H，意图和响应逐步保存，不自动重试POST、不启动Run。

前批[归并统计验收](../../openspec/changes/archive/2026-11-13-summarize-incident-grouping/validation.md)包含新批次本机真实TCP/PG、原56操作合同保持和21既有合成范围只读复验；该批Swagger docs10同步，其他服务/消费者保持。18026仅作候选验收，正式入口18024。

原发布profile显式设`replace_existing=true`，先核原镜像及端口；`expected_operations=71`是原批读回值；新发布应按冻结合同核准确method/path、字段和实际配置，不能只改数量使验证通过。`alert-host/preview.json`的18026仅作本机验收，正式本机使用根local.json的18024。`verify_management.py`按环境专属profile新建验收Case，记录意图及响应，不自动重试写入或启动模型。

告警／事件验收使用 `verify_subject_management.py` 和 `subject-management/verify-*.json`，只操作本批明确标记的合成主体；`subject_management_fixture.py`提供受控新样本与SQL读回。`SOCAI2_MANAGEMENT_CONFIG_FILE`显式指定批量配置，默认交付`max_batch_items=100`，变更后重启本项服务。人工写入复用`SOCAI2_CASE_API_ENABLED`及既有调查写连接，关闭时新接口返回`503 socai2_subject_write_not_enabled`。

三类列表验收脚本为verify_list_query.py，配置在list-query/；seed仅允许本机隔离库，一批只建一次，verify仅GET及只读SQL，不重派分析。发布后复验脚本和回执保存在本批证据目录。

CSV导出配置为`app/socai2/list_export.json`，用`SOCAI2_EXPORT_CONFIG_FILE`显式选择；max_rows=10000、max_bytes=16777216、statement_timeout_ms=30000。启动时检查配置，错误不回落。完整只读CSV验证为`verify_list_export.py`及`list-export/verify-local.json`；发布后通过独立读取SQL核对。

归并统计直接验收使用`verify_grouping.py`和`grouping-summary/verify-*.json`；seed仅允许明确本机验证库，一批一次，verify/http只读且不调用模型。E57无新增可变运行配置，复用页面读取开关、数据库与既有只读事务。

本批普通评论E58/E59及验收见[Case评论](../../openspec/changes/archive/2026-11-13-add-case-comments/validation.md)。`case-comments/`保留评论批次profile，`verify_comments.py`新批次只创建明确标记的Case/H/评论，不启动Run；`--read-existing`只读复验。发布SQL脚本在容器内只读事务运行；只读rootfs拒绝docker cp时，保持配置，用docker exec标准输入执行，不放宽容器。

当前附件引用E60–E62见[验收](../../openspec/changes/archive/2026-11-13-link-case-attachments/validation.md)；`case-attachments/`保留附件批次profile，`verify_attachments.py`只创建本批合成Case/H/文件引用，`--read-existing`只读复验。真实文件上传/下载由业务后端承接；测试使用明确合成file_id，不调用文件平台。21仅叠加8文件，无迁移，源码/配置及其他36容器已核对。

前批采用发布使用`case-result-adoption/`，从附件基底叠加7文件；E21/E63/E64复用核心，本机20次HTTP/SQL通过。21只读已有判断、预览和历史；生产采用写入未实测。详细[本批验收](../../openspec/changes/archive/2026-11-13-adopt-investigation-results/validation.md)，测试不调用模型。

本轮[E65故事查询](../../docs/integration/case-story-http.md)使用case-story/ profile，已在本机/21发布并各7次只读GET核验；本机候选30次HTTP与补验1次GET/11表原行保持，原核验脚本失败保留。无模型、迁移或生产业务写入，AI对话暂缓。

[E66候选查询](../../docs/integration/case-exploration-http.md)已两端发布，各11次GET核对版本、候选/对象/原材料及Case保持。`verify_exploration.py`在新本地合成批完成30次HTTP及10表只读核验，随后显式E08加入；`read_exploration_release.py`只读核验已发布环境。配置`SOCAI2_EXPLORATION_CONFIG_FILE`可指定独立查询窗口文件，默认24小时；旧查询/C5/模型未改。

[E67–E69探索保存恢复](../../docs/integration/case-exploration-save-http.md)已发布两端，`verify_exploration_state.py`本机27HTTP与7业务表保持，`read_exploration_state_release.py`两端各6GET。配置`SOCAI2_EXPLORATION_STATE_CONFIG_FILE`指定`exploration-state.json`，默认1000关系/4MiB。21本轮未写入探索；无迁移。

[E70相似历史复核](../../docs/integration/alert-review-http.md)已两端发布。`verify_alert_review.py`本机23GET/10表只读保持，`read_alert_review_release.py`正式本机8GET命中3条、21既有记录5GET为空候选。`SOCAI2_ALERT_REVIEW_CONFIG_FILE`指定`alert-review-query.json`，默认回看30天。无模型、无迁移、无生产写入。

[E71同主机近期告警](../../docs/integration/alert-host-http.md)已完成独立审计并统一发布正式两端；`alert-host/`包含本轮显式profile，`SOCAI2_ALERT_HOST_CONFIG_FILE`指定`alert-host-query.json`，当前display_limit=7。`verify_alert_hosts.py`本机20条合成记录17GET/4表保持，暂不提交Git。

调查核心发布后同步使用`core-sync/`，来源固定为已发布的不可变目录及文件摘要；`source_root/expected_source_hashes`在打包前核验，不默认带入工作树的新修改。`mount_sources`只替换已存在的只读挂载并核摘要；本机`environment`可显式覆盖私密连接文件之外的运行配置。两端数据库、CPU架构及来源开关分别保留。该批核对71操作与既有调查结果，不重新调用模型。

## 默认内部可信（本轮候选）

独立18024不要求登录、Token或角色。`SOCAI2_HTTP_CONTEXT_FILE`选择本环境的绝对路径JSON，字段为tenant_id、actor_id、actor_name；仅用于数据归属及操作记录，不代表验证过真实调用者。`trusted-internal/`提供本机/21独立配置，actor_id指向已有记录身份，actor_name明确为业务后端。不要将本机ID套到21。无新增表或配置接口。

当前仅18026候选已完成20次无凭据管理请求与保存读回，正式18024/root profiles仍为上一版；未混入调查并行修改。统一发布前将上下文文件放入冻结运行包并配置绝对路径；不使用全局开发认证绕过开关，不改其他应用/内部组件。

## 完整步骤和原件读取（本地实施，待统一发布）

新增三个GET及E12/E32完整目录链接，使用[读取配置](run-records.json)：default_limit=50、max_limit=100；只限制单页，目录没有总量截断。通过`SOCAI2_RUN_RECORDS_CONFIG_FILE`显式选择绝对路径；未提供或非法时新读取接口返回503，不回退其他环境。两端可用同一数值文件，路径按各自运行包配置。

[发布清单片段](run-records-release-fragment.json)列出本步源码、配置和两端环境项，需并入最终冻结profile，不能单独交给manage.py执行。本机将配置复制到冻结运行包的config/run-records.json并填本机绝对路径；21镜像放/app/config/run-records.json，选择该容器路径。保留两端各自的架构、数据库和业务上下文。不能只覆盖新路由而遗漏核心读取模块、DTO、端口和配置。此处未执行打包、重启、切换或发布；现行服务仍按当前正式profile运行。

输入输出、错误及直接验证见[接口指南](../../docs/integration/run-records-http.md)。


统一Run目录R1已完成[完整HTTP本地验收](../../docs/integration/run-directory-http.md)：真实task/intent关联、筛选/分页及统计。发布前须同一目标库应用调查侧迁移128并同步配套ORM；不得仅复制HTTP文件到旧数据库，也不做缺表回退。run-records发布片段已列出R1/R3共用依赖及迁移前提，仍为待统一发布的非执行片段；本步未打包、更改正式profile或重启服务。


## 分析任务列表与详情（本地实施，待统一发布）

三类主体各两个GET只读取真实任务，见[接口指南](../../docs/integration/analysis-tasks-http.md)。沿核心`SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`选择绝对路径policy，默认50/最大100及更新资格窗口只保留一份配置。缺配置返回503。

[任务HTTP发布片段](analysis-tasks-release-fragment.json)须与核心analysis-lifecycle及R1/R3片段共同合入最终冻结profile；先在明确的目标数据库应用128，再装配核心结果引用四字段及HTTP。两端架构、数据库和业务上下文各自保留；本机路径取冻结包绝对路径，21取/app/config/analysis-tasks.json。不启用调度/消费者/模型，不执行旧表兼容回退。本步尚未打包或切换正式服务；当前候选80操作、21实际64操作/静态Swagger71，详见本页运行状态。


[事件异步提交](../../docs/integration/analysis-submission-http.md)E37已注册202并通过执行/保存/读取联验；[Case首轮](../../docs/integration/case-initial-http.md)亦已通过本地受控依赖验证，Case check/rerun现已完成新批执行、保存、终态读取/原key回放和周期样本读取。统一发布须合入[Case更新HTTP片段](case-update-release-fragment.json)及其依赖的[Case首轮HTTP片段](case-initial-release-fragment.json)及核心A/I/Case执行器片段，移除外部E11/E13，保持唯一调度器。HTTP不管理执行器生命周期。本轮候选80操作，未切换正式服务。
