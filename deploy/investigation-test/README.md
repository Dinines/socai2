# 测试服务部署与配置

2026-11-17。4b发行版为0.6.1，增加报告精确主体/Run链接与按冻结来源识别测试数据。[本轮21配置](releases/workbench-4b-20261117-01/release.json)选择4177 r8，业务上游18024、环境标签acceptance-release-20261117-01及正式tenant保持；实际切换与验证以[发布回执](../../docs/operations/evidence/workbench-4b-release-20261117-01/README.md)和[当前进展](../../PROGRESS.md)为准。保留既有账本与数据，不重新投放。以下W1–W5各批说明保持历史时点，旧release-4177及候选18424示例不是本轮运行参数。
2026-11-17本机任务3a–3c已接入[验收材料与会话入口](../../tools/testdata/ACCEPTANCE.md)：转换、检查、冻结准备、显式首段/追加、只读状态/报告及交互菜单。3c.2真实两段和3c.3报告/菜单均已通过各自独审。3d另提供[专用Docker入口](acceptance-docker.md)、[Compose](acceptance.compose.yml)、[运行配置示例](acceptance.env.example)及[文件配置示例](acceptance-config.example/)；已实际构建linux/amd64镜像，材料/配置只读、结果持久挂载。镜像默认只显示帮助，运行不需宿主Python/源码。实际挂载验证和独审状态以[3d回执](../../docs/operations/evidence/acceptance-docker-20261117-01/README.md)为准；尚未替换21或运行任务4。下文原Dockerfile/serve属于查阅服务，与专用Dockerfile.acceptance入口分开。

## 配置文件与加载

`serve`和`publish`都必须传`--config`；JSON由[Config.load](../../services/investigation_test/config.py)一次性读取。以下9项在JSON结构中全部必填、没有loader隐式默认，额外字段或类型不符拒绝。部署时只需为本环境确认前4项；后5项通常保留模板值，但不能删除字段。表中值来自[read-only.example.json](read-only.example.json)，只是示例，不代表21实际运行值。`serve`修改后需正常停止并用指定文件重新启动；`publish`每次加载所选文件。目录相对配置文件位置解析，不相对shell当前目录。

| 配置项 | 部署分类 | 类型／示例 | 用途、限制及验证 |
| --- | --- | --- | --- |
| `ledger_root` | 部署必填（按环境确认） | 非空字符串；`../../.local/investigation-test/ledger` | 持久账本目录，可为绝对或相对路径。GET/启动不创建；显式publish才创建。升级保留整目录及旧revision；通过保存后详情/原件读取和重启hash核对验证 |
| `environment_label` | 部署必填（按环境确认） | 有限标识字符串；`local-test-records` | 当前读取服务标签，不自动选择业务环境；在capabilities返回。批次自己的environment仍来自账本，archive不会冒充当前运行目标 |
| `host` | 部署必填（按环境确认） | 非空字符串；`127.0.0.1` | Uvicorn监听地址。示例只允许本机回环；实际部署要在完整候选profile明确，W1没有独立鉴权或公网部署设计 |
| `port` | 部署必填（按环境确认） | 整数1–65535；`14178` | 本组件监听端口，与4177及调查HTTP独立。验证实际绑定与GET；端口占用不自动切其他环境 |
| `default_limit` | 保留默认（模板值；字段必存） | 正整数；`50` | 列表未传limit时采用，必须≤max_limit；通过不带limit的分页读取核对 |
| `max_limit` | 保留默认（模板值；字段必存） | 正整数；`100` | 单页上限；超限422。cursor绑定limit，改limit应从第一页开始 |
| `max_document_bytes` | 保留默认（模板值；字段必存） | 正整数；`4194304`（4 MiB） | 发布输入与保存账本的JSON字节上限，不是调查原件上限。需覆盖发布后证据元数据；超限发布失败，不能截断JSON |
| `max_evidence_bytes` | 保留默认（模板值；字段必存） | 正整数；`16777216`（16 MiB） | 每份登记测试证据的字节上限；不适用于W2代理业务原件读取。发布保留完整字节；GET核size/hash，损坏或缺失503 |
| `max_cursor_bytes` | 保留默认（模板值；字段必存） | 正整数；`2048` | API输入游标长度上限；非法/过大422，已合法但数据修订变化409。不据此截断列表数据 |

分类按部署动作区分：**部署必填**要求明确实际目录、环境和监听目标，可以确认继续使用示例值，但不能未经核对就套用；**保留默认**表示保留当前模板给出的值，仍须在JSON中存在；**启用时必填**用于下方W2独立profile；**程序生成**指发布或验证输出，不要求部署人员手填。

| 程序生成项 | 来源与使用方式 |
| --- | --- |
| `revision`、`published_at`、`current.json`指针 | publish成功后生成；不手工编辑。调用方的`--expected-revision`仍须提供，新批填0，更新填已读回的当前修订 |
| evidence的`size`、`sha256` | 从登记原文件计算，不手填摘要冒充校验 |
| 账本/配置/源码的验证hash、验证临时端口 | 验证过程记录；不是常驻部署配置。实际serve仍必须使用profile明确host/port |

上述账本配置不包含数据库、Redis、Kafka或模型连接。W2使用下述独立JSON，页面参数使用下方独立W3 profile，不混入账本配置。

## W2显式只读代理配置

`serve`增加`--upstream-config <文件>`启用，省略时只有账本GET。配置由[UpstreamConfig.load](../../services/investigation_test/proxy.py)读取，以下10项全部必填，额外字段拒绝，无隐式环境回退。示例为[upstream.example.json](upstream.example.json)，绑定当前21候选；本机无直接网络时先使用明确的SSH转发，并把base_url改为该转发地址。HTTP公开路径不提供任意上游参数。

| 字段 | 部署分类 | 类型/示例 | 用途与验证 |
| --- | --- | --- | --- |
| `environment_label` | 启用时必填 | 标识字符串；`streaming-20261115-01` | 必须等于服务配置标签；capabilities及响应来源头显示该标签，页面会与所选批次环境核对 |
| `tenant_id` | 启用时必填 | UUID；当前候选identity中的tenant | 记录实际上游绑定身份；不替调用方添加租户头、不提供跨租户切换。已由HTTP双池回执核实 |
| `base_url` | 启用时必填 | HTTP(S) origin；`http://192.168.1.21:18424` | 不含凭据、路径、query或fragment；当前环境需显式选择。不跟随重定向，不继承系统代理环境 |
| `openapi_file` | 启用时必填 | 配置文件相对/绝对路径 | 指向已读取的当前服务合同；当前55个业务GET，不能使用旧71操作包。部署包须包含此合同文件 |
| `openapi_sha256` | 启用时必填 | 64位小写十六进制 | 必须与文件原字节一致，变化拒绝启动。新合同应重新核对并明确更新profile |
| `connect_timeout_seconds` | 保留默认（字段必存） | 正数；`5.0` | 连接超时，失败返回明确代理错误；不重试 |
| `read_timeout_seconds` | 保留默认（字段必存） | 正数；`30.0` | 读取块等待上限，不是调查Run或模型预算；首块前超时504，开始传输后失败中断流 |
| `max_connections` | 保留默认（字段必存） | 正整数；`10` | 单服务到上游的连接池上限 |
| `max_keepalive_connections` | 保留默认（字段必存） | 非负整数；`5` | 不得大于max_connections；正常关闭服务释放连接 |
| `chunk_bytes` | 保留默认（字段必存） | 正整数；`65536` | 流式转发分块大小，不是原件大小上限；保留完整字节及内容头 |

示例启动方式（先准备匹配环境的服务配置，端口和目录明确选择）：

```sh
PYTHONPATH=services .local/conda-envs/socai2/bin/python -m investigation_test serve \
  --config .local/investigation-test/candidate-service.json \
  --upstream-config deploy/investigation-test/upstream.example.json
```

上述`candidate-service.json`由部署按9字段表提供，不自动生成或回退到旧环境。代理只接受当前合同GET和查询参数；POST/PUT/PATCH/DELETE为405，未知路径404，非法代理参数422；上游业务错误原样保留，连接/协议错误502、超时504。请求不转发浏览器Authorization/Cookie/租户头；响应追加环境与合同摘要。原件采用流式传输，不套用账本max_evidence_bytes，传输失败不能当完整读取。capabilities的`runtime_verified=false`表示启动元数据不证明运行验收，实际证据独立记录。

## 当前可执行入口

在仓库根目录、现有Python环境中执行；本页命令是通用运行方式；本次W2使用单独profile临时运行，结束已停止，未将示例端口部署为常驻服务：

```sh
PYTHONPATH=services .local/conda-envs/socai2/bin/python -m investigation_test serve \
  --config deploy/investigation-test/read-only.example.json
```

`serve --config`为前台只读服务；Ctrl-C/SIGTERM停止，正常启动/重启不发布账本、不续跑任务。独立Python包元数据见[pyproject.toml](../../services/investigation_test/pyproject.toml)，当前验证使用上述PYTHONPATH入口，W4已完成独立包与21候选验证；后续实际4177状态沿本页W5入口读取。

```sh
PYTHONPATH=services .local/conda-envs/socai2/bin/python -m investigation_test publish \
  --config deploy/investigation-test/read-only.example.json \
  --document docs/operations/evidence/test-ledger-w1-20261115-01/tcp-01/inputs/w1-f5-archive/document.json \
  --expected-revision 0
```

`publish`是显式写入测试账本的本地CLI，三个参数都必填。`--document`为UTF-8 JSON路径，字段按version1合同；`--expected-revision 0`新建，同批更新填当前revision，冲突拒绝。finished/failed/interrupted批次不能改写，复验新建batch；命令返回batch_id/revision/execution_state，不触发业务执行。

证据的`path`相对document目录，必须为其内非隐藏普通文件，拒绝绝对路径、上溯及符号链接；发布输入必须标`visibility=public`。`source_ref`仅作来源说明，不会当作路径或URL读取。私密profile建议放`.local/investigation-test/`或部署方明确的private目录，按Git忽略规则保管；秘密文件、完整连接配置、密钥及数据库备份不能登记为public证据。HTTP仅输出登记ID/mime/size/hash与受控内容链接，不输出源文件绝对路径。

## 最小安装、验证和后续部署顺序

1. 冻结当前独立包、配置和依赖版本，按所在环境生成明确profile；确认目录保留、端口归属及运行身份。当前W1只验证单机本地文件系统，未验证共享文件系统。
2. 启动serve，读取`/test-api/v1/capabilities`和`/test-api/v1/batches`；新目录应返回合法空列表，磁盘目录仍不存在。`/openapi.json`应只有8个测试GET，不含执行写接口。
3. 用新batch发布已脱敏的明确来源记录；详情、用例、操作、准备、质量、登记证据原字节逐项核对。archive/live与synthetic_fixture/saved_evidence/live_execution来源分别记录；无Run保持null，合成状态不算真实模型结果。
4. 停止再启动同一profile，核revision、账本/原件hash保持。读取不能新增revision或任务；不可用503与空列表200分开。
5. W2代理组件/真实空态及S01/S04非空、跨Run来源已通过；W3页面已验证，W4完整包验证后，再按21候选profile部署并核实际版本、持久目录与页面取数。各步不能互相替代验收；W5按本轮明确授权单独切换4177。

已完成的W1实际端口为`127.0.0.1:56595`，验证服务已停止；示例14178未作为常驻服务启动。实际验证参数、profile和账本位于`.local/test-ledger-w1-20261115-01/`，公开回执仅保存必要摘要和非私密证据。34次带断言GET、3次启动探测与16项组件测试通过；业务连接、真实模型及Kafka投递为0。

最新W2实际配置见[service-config](../../docs/operations/evidence/test-http-proxy-w2-live-20261115-01/service-config.json)、[upstream-config](../../docs/operations/evidence/test-http-proxy-w2-live-20261115-01/upstream-config.json)和[临时TCP配置02](../../docs/operations/evidence/test-http-proxy-w2-live-20261115-01/tcp-profile-02.json)。SSH转发远端使用当前实际`192.168.1.21:18424`，不能假定远端回环监听。首次错误转发失败已保留；成功验证34GET，另有首次1次本机capabilities成功。临时64396/64397已关闭、原4177保持；新live账本及证据保存在本批目录，GET前后hash一致。该实际profile用于追溯本批，后续启动须重新核目标和端口，不直接复制作为常驻部署。

## W3显式页面配置

`serve --viewer-config <文件>`挂载`/viewer/`及静态资源，省略则不挂载。配置由[ViewerConfig.load](../../services/investigation_test/viewer.py)读取；[viewer.example.json](viewer.example.json)三项均必填，不接受额外字段，无环境回退。

| 字段 | 分类 | 类型/示例 | 用途与边界 |
| --- | --- | --- | --- |
| `poll_interval_seconds` | 启用时必填 | 有限正数；5.0 | 仅当前可见活动记录自动刷新；终态/隐藏停止，目录正文查阅暂停父Run刷新 |
| `request_timeout_seconds` | 启用时必填 | 有限正数；30.0 | 页面配置取得后的HTTP完整读取时限；超时明确报错并保留旧观察，不影响模型预算 |
| `page_size` | 启用时必填 | 整数1–100；20 | 列表/目录页大小，必须≤账本max_limit；非法组合启动拒绝，分页使用原游标 |

示例启动在W2命令末尾增加：

```sh
  --viewer-config deploy/investigation-test/viewer.example.json
```

页面展示同源`/test-api/v1/capabilities`的实际服务/页面版本、环境及合同摘要；live错配禁止业务请求。HTTP参数与地址仍由upstream-config选定，公共页面配置不带上游地址、租户连接或凭据。无CDN、无新增模型或数据库接线。

W3本机联验临时58808服务及58809 SSH转发已关闭；仅访问当前192.168.1.21:18424，运行来源见[根侧本步核对](../../docs/operations/evidence/streaming-w3-viewer-20261115-01/runtime-01.json)。实际[服务profile](../../docs/operations/evidence/test-viewer-w3-20261115-01/service-config.json)、[代理profile](../../docs/operations/evidence/test-viewer-w3-20261115-01/upstream-config.json)、[页面profile](../../docs/operations/evidence/test-viewer-w3-20261115-01/viewer-config.json)用于本批追溯，不直接作为常驻部署。26业务GET均200，账本前后hash一致；0业务写/模型/调度/数据库/Kafka。该W3回执只表示原范围；W4包已另批通过，W5按2026-11-16负责人明确指令推进。

## W4独立完整包

在仓库根目录显式选择[package-build.json](package-build.json)：

```sh
.local/conda-envs/socai2/bin/python deploy/investigation-test/build.py build \
  --profile deploy/investigation-test/package-build.json
```

构建输出release目录、tar.gz和receipt，已有release拒覆盖。包内包括完整测试模块/页面、现有S01/S04驱动及其原合同文件、配置示例、场景说明、test-openapi.json、investigation-openapi.json、compatibility.json和逐文件摘要。源码未提交时以文件摘要为准；不把Git HEAD冒充实际源码。build不发送网络、不发布账本、不启动服务。

| 构建配置 | 作用 |
| --- | --- |
| `schema`、`release`、`output_dir` | 构建合同、独立release身份和相对profile的输出目录；输出不可覆盖 |
| `source_roots`、`source_files` | 完整测试模块和显式驱动/合同/说明来源；拒绝缺文件、上溯及符号链接；缓存不入包 |
| `upstream_profile` | 当前调查OpenAPI文件与已核摘要，复制到包内并改写示例相对路径 |
| `image` | 显式缓存基础tag/ID、目标tag/架构、用户、包内目录/配置挂载、构建时限；运行前核基础ID一致，构建禁止拉取和网络 |
| `acceptance_image` | 可选专用验收镜像配置引用：固定基础摘要/实际ID、Python/平台、非root用户和19项依赖锁；另生成Dockerfile.acceptance，构建按显式公开索引取依赖，运行网络由Compose配置 |

解包后无需原工作树：先执行`python deploy/investigation-test/build.py verify --directory <release绝对路径>`，再按compatibility.json准备Python及依赖。`PYTHONPATH=<release>/services python -m investigation_test`提供serve/publish；`python <release>/tools/testdata/streaming_fixture.py`提供generate/validate，`streaming_send.py`提供显式prepare/send，发送需另行供应对应新批profile、资源回执和私密连接。这里没有默认发送或自动恢复命令。

将config下三个示例复制到包外目录，明确ledger_root、环境、监听和上游。账本及其证据作为独立持久卷：服务只读挂载，publish进程才写指定目录；安装/更换包不复制或清空账本。示例ledger_root指向release外的state/ledger。旧archive可并存，已结束批次不能改写；新增观察使用新batch。独立发布CLI只接收公开证据，不把整份库快照或私密env作为默认公开材料。

容器构建采用包内Dockerfile，基础镜像先核ID，再`docker build --pull=false --network=none --platform <profile值> -t <profile目标tag> <release目录>`。运行时只挂外部三个配置、包内调查OpenAPI及只读ledger，使用显式绑定端口、网络、资源和restart配置；具体21候选值见[candidate-21.json](candidate-21.json)。容器默认入口仅serve，不执行任何测试；不挂数据库/模型/Kafka秘密。

升级：正常停止旧读取进程，用新包与原外部配置/账本启动，核版本、合同、只读GET和证据摘要。回退：停新读取进程，按保存的旧包/配置启动；账本保持原件，不靠重放模型或清数据回退。候选正常重启与保留验证不等于跨schema升级/故障恢复专项。正式4177切换只在W5获准范围执行。

## W5历史安装与当前4177入口

历史[release-4177.json](release-4177.json)曾选择21、回环4177和候选上游18424；当前r6应使用页首r4三份配置，上游为18024。本机沿既有SSH隧道访问`http://127.0.0.1:4177/`，`/index.html`也跳转至`/viewer/`。这是测试查阅服务的独立发布，不等于调查核心或数据库统一正式发布。服务保持只读，启动和刷新不会执行模型/工具或续跑调查。

| 发布配置 | 用途 |
| --- | --- |
| `deployment_root`、`release_parent` | 新发布回执/配置目录与独立release目录；存在时拒绝重复安装 |
| `state_root`、`state_source` | 包外常驻状态目录与首次安装的W4账本来源；第一次复制逐文件核摘要，以后升级使用原状态，不覆盖 |
| `old_site` | 旧三案及历史查阅文件，仅核保留，不改写或用作live后备源 |
| `previous_container`、`initial_state_import` | 升级时明确旧查阅容器与不重复导入旧账本；先备好新镜像，再停旧查阅容器，旧容器保留 |
| `ssh_target`、`container`、`network` | 明确连接目标、新查阅容器名及既有容器网络 |
| `bind_host`、`bind_port`、`container_host`、`container_port`、`local_entry` | 21仅回环4177发布、本机既有转发地址及容器内部监听 |
| `config_mount`、`ledger_mount` | 容器内配置与账本挂载位置，均只读 |
| `memory`、`pids_limit`、`tmpfs`、`restart_policy` | 查阅容器资源及`unless-stopped`策略；不影响调查容器 |
| `environment_label`、`upstream_base_url` | 绑定当前候选调查环境及HTTP，公开页面仅显示环境标签和能力摘要 |
| `command_timeout_seconds`、`http_timeout_seconds`、`startup_timeout_seconds`、`stop_timeout_seconds` | 部署与验证时限，服务请求超时仍由独立upstream/viewer profile控制 |

发布前核旧4177已停止、端口空闲及W4来源摘要，按包内Dockerfile离线构建；三份实际service/upstream/viewer配置写到deployment_root/config并只读挂载，状态挂state_root。新容器运行后经本机真实4177读取和浏览器核版本/来源/原答，再记录当前展示清单。若撤回，只停止新4177容器以恢复本步前的入口状态，保留数据；不自动启动其他旧服务。升级更换包时继续使用原状态目录，不能重新复制W4来源覆盖后来的账本。

0.6.0 沿旧4177布局展示请求接入/自动触发→任务→阶段及组件→结果保存→读回，用紫色标识测试执行。领域分析分别显示身份/云/钓鱼/内部风险及实际适用性、发现；未执行查询显示真实原因。旧样本原答和轮次隔离的浏览器回执保留。

负责人授权清空旧数据后，活动账本为空，页面显示“暂无案例与执行记录”；空列表会取消旧详情与轮询。升级只替换本次只读查阅服务，`initial_state_import=false`，不能重新导入 W4 旧批次。这段空态属于当时W5验收。当前r4 Fusion与调度已启动，新02由测试唯一投放并发布新账本；实际版本见页首r4回执，旧质量问题未核销。

## 按测试告警源识别

`viewer.example.json` 的 `test_source_prefixes` 默认配置为 `["lyc"]`，按大小写精确前缀识别后台 `connector_type`，不按标题/正文猜测。此配置只影响展示，不传给调查执行或模型。告警直接读业务HTTP事实；Case/事件选中轮次后从该轮冻结输入读取来源。全部命中显示“测试数据”，部分命中显示“含测试数据”，缺失/失败显示来源未确认并保留已读流程。没有测试账本也可识别；旧批次仅在精确登记当前Run时补充显示测试关系。未打开的Case/事件列表不预先遍历全部原件，已确认来源或辅助批次关联分别显示。旧部署配置没有此字段时前缀识别关闭，必须显式更新viewer配置后启用，不静默更改当前21。

## 报告定位具体轮次

新版 `report` / `session` 可选 `--report-config`，容器内使用现有只读配置挂载中的 [report.json](acceptance-config.example/report.json)，无需修改prepared。源环境标签与会话一致，目标工作台标签与其HTTP能力声明一致；`workbench_url` 是使用者浏览器可访问的地址，不是容器内HTTP地址。示例中的两个环境名称须按目标显式填写，不能回落别的环境。

页面接受 `subject_type`、`subject_id`、`run_id`、`environment` 四个查询参数，核环境和真实归属后读取指定轮次；缺失/无效目标不选latest，刷新和重载保留目标。告警/事件/Case均复用既有GET和冻结材料，无新增业务接口。报告配置Schema和模块已列入package-build，页面模块由既有web目录收集；该接线现已随0.6.1/r8与同包验收工具发布21；[最终report-02](../../docs/operations/evidence/workbench-4b-release-20261117-01/report-02/report.md)已验证实际4177首轮/后轮、冻结1/2和紫色来源。旧r7及原报告保持，最终挂载布局同时保证原件相对链接可查。
