# Swagger HTTP接口文档部署

2026-11-15。本页使用21已启动的独立候选 `streaming-http-20261115-r2`：**80 个HTTP业务操作，按告警、事件、调查集中展示，无登录、Token或角色校验**。输入、输出字段、示例及错误来自已核候选合同。[当前文档包](streaming-20261115-01/handoff/manifest.json)已在18480加载并与18424实际合同核对；[运行回执](../../docs/operations/evidence/streaming-http-runtime-20261115-01/README.md)只完成空态接入，成功业务写入及整链仍待。

Swagger是静态说明服务，不执行调查或保存数据。点击具体API的Execute才会调用Servers选中的业务服务；写操作会真实受理/保存，查看文档本身不会调用模型。

| 目标 | 当前选定配置 | 状态 |
| --- | --- | --- |
| 21候选文档18480 | [aisoc21.env](streaming-20261115-01/aisoc21.env)，linux/amd64 | [已启动](http://192.168.1.21:18480/)，页面及三个文档文件读回通过 |
| 21候选业务API18424 | [HTTP部署说明](../http-service/README.md) | 同库普通读写连接、真实TCP三类空列表及80操作合同通过；成功写入待真实Kafka材料 |
| 后端电脑查看文档18081 | [local.env.example](streaming-20261115-01/local.env.example) | 独立本机查看；不需要数据库/Kafka/模型 |
| 21旧服务 | 旧18024 HTTP和18080 Swagger已于2026-11-15按负责人要求主动停止，容器/数据保留 | [停止回执](../../docs/operations/evidence/streaming-old-services-pause-20261115-01/pause-01.json)；不恢复，不代表候选发布 |
| 本机最近观察 | 本机18024/18080仍为旧版本，未随本次21操作变更 | [观察证据](../../docs/operations/evidence/http-local-runtime-review-20261115-01/README.md)，不作为本候选就绪证明 |

## 后端在自己电脑启动 Swagger

需要Python 3、Docker及Docker Compose v2。以下在socai2仓库根执行，SpiritHub用户先进入server。只操作个人文档容器，使用18081避开已有18080。配置示例按ARM64；Intel/AMD将DOCS_PLATFORM改为linux/amd64。

先生成带本机绝对目录的env文件：

```sh
mkdir -p .local/api-docs/streaming-20261115-01
python3 - <<'PYCONFIG'
from pathlib import Path
source = Path('deploy/api-docs/streaming-20261115-01/local.env.example').read_text()
Path('.local/api-docs/streaming-20261115-01/local.env').write_text(
    source.replace('<absolute-current-checkout>', str(Path.cwd())))
PYCONFIG
```

核对配置中的架构、镜像和端口后执行：

```sh
docker compose --env-file .local/api-docs/streaming-20261115-01/local.env \
  -f deploy/api-docs/compose.yml config --quiet
docker compose --env-file .local/api-docs/streaming-20261115-01/local.env \
  -f deploy/api-docs/compose.yml pull
docker compose --env-file .local/api-docs/streaming-20261115-01/local.env \
  -f deploy/api-docs/compose.yml up -d
```

首次显式pull取得所选架构镜像；Compose运行配置为pull_policy=never，不在up时自动更新镜像。离线环境由部署方提供对应架构镜像，`docker load -i <镜像文件>`后把SWAGGER_IMAGE设为实际已导入的固定摘要/标签，不能把ARM64镜像给21使用。

打开 [本机Swagger](http://127.0.0.1:18081/)。下载合同的路径是 `/handoff/openapi.json`：

```sh
curl --fail http://127.0.0.1:18081/handoff/manifest.json
curl --fail http://127.0.0.1:18081/handoff/swagger-config.json
docker compose --env-file .local/api-docs/streaming-20261115-01/local.env \
  -f deploy/api-docs/compose.yml ps
```

预期manifest为streaming-http-20261115-r2、80操作、告警/事件/调查三组。共用接口可在多组显示，不能把重复显示相加算业务操作数。例子来自隔离验证已保存记录，UUID不是21候选现成数据；调用前换成目标环境实际ID。

## 当前配置全部字段

### Compose env文件

配置类别沿HTTP的四类约定：**部署必填**确认目标，**保留默认**保留模板字段和值（不代表可以删键），**启用时必填**在使用该能力时供给，**程序生成**据实生成/核对。Swagger静态服务的7项env当前全部提供；没有数据库、认证或模型的条件配置。

以下7项在当前env中全部显式填写；`${...:?}`字段缺失会在Compose解析时拒绝。env文件选择用`--env-file`，不会自动使用其他环境文件。修改后重新执行所选项目的up -d；不重启API。

| 字段 | 配置类别 | 类型／候选值 | 用途、默认与验证 |
| --- | --- | --- | --- |
| `COMPOSE_PROJECT_NAME` | 部署必填 | string；21为`socai2-streaming-swagger-20261115`，个人为`socai2-streaming-swagger-local` | 项目隔离；本部署显式必填，避免复用正式文档项目。用compose ps核项目 |
| `SWAGGER_IMAGE` | 程序生成 | image reference；21摘要`95b255…51b9c`、个人示例摘要`59ee90…de53b`，完整值在对应env | 选择已有/显式取得的Swagger UI镜像；up不拉新版本。核容器实际image与架构 |
| `DOCS_PLATFORM` | 部署必填 | string；21 linux/amd64，个人示例linux/arm64 | 目标CPU；无本部署默认，用Docker引擎实际架构选择 |
| `DOCS_BIND` | 部署必填 | IP string；21 192.168.1.21、个人127.0.0.1 | 宿主监听地址；必填；个人示例只本机可访问 |
| `DOCS_PORT` | 部署必填 | integer string；21 18480、个人18081 | 宿主端口；冲突时显式改个人配置，不挤占正式18080 |
| `DOCS_CONTAINER_PORT` | 保留默认 | integer string；8080 | 容器PORT及端口映射目标；两处由同一变量生成 |
| `DOCS_CONTENT` | 部署必填 | absolute host path | 当前handoff目录，含openapi.json/swagger-config.json/manifest.json；只读挂到`/usr/share/nginx/html/handoff`。本机不能照抄维护者路径；含空格时在env中给值加双引号 |

Compose内部固定 `pull_policy: never`、`restart: unless-stopped`、只读内容挂载；无数据库卷或应用secret。

### compose.yml的Swagger环境与展示配置

[compose.yml](compose.yml)读取以上env后设置下列容器环境。它们是当前部署显式值，改变镜像/展示配置须核实际返回；不改变业务API合同。

| 项 | 配置类别 | 当前类型／值 | 用途与验证 |
| --- | --- | --- | --- |
| `PORT` | 程序生成 | string；来自DOCS_CONTAINER_PORT | Swagger Web监听端口，核HTTP可访问 |
| `SWAGGER_JSON_URL` | 保留默认 | string；`/handoff/openapi.json` | API合同位置，下载核版本与80操作 |
| `CONFIG_URL` | 保留默认 | string；`/handoff/swagger-config.json` | 浏览器加载展示选项的位置，核此文件200 |
| `VALIDATOR_URL` | 保留默认 | string；none | 不向外部Swagger校验器发送合同 |
| `DOC_EXPANSION` | 保留默认 | string；none | 默认折叠操作，按业务组展开 |
| `DISPLAY_OPERATION_ID` | 保留默认 | boolean string；true | 显示接口编号/operationId便于检索 |
| `PERSIST_AUTHORIZATION` | 保留默认 | boolean string；false | 不保存授权信息；当前API本身没有鉴权方案 |
| `TRY_IT_OUT_ENABLED` | 保留默认 | boolean string；false | 默认不进入试调编辑模式；不是禁止用户手动执行请求 |

[swagger-config.json](streaming-20261115-01/handoff/swagger-config.json)也明确以下全部字段，由浏览器加载。值与Compose保持一致；更改只读挂载文件后刷新浏览器，改挂载路径需重建文档容器。

| JSON字段 | 配置类别 | 类型／当前值 | 用途 |
| --- | --- | --- | --- |
| `url` | 保留默认 | string；`/handoff/openapi.json` | 同源读取合同 |
| `filter` | 保留默认 | boolean；true | 提供搜索过滤 |
| `validatorUrl` | 保留默认 | null | 不调用外部合同校验器 |
| `docExpansion` | 保留默认 | string；none | 默认折叠 |
| `displayOperationId` | 保留默认 | boolean；true | 显示接口标识 |
| `persistAuthorization` | 保留默认 | boolean；false | 不保留授权数据 |
| `tryItOutEnabled` | 保留默认 | boolean；false | 默认不打开试调模式 |

### API地址及文档manifest

`servers[].url` 属于**部署必填**，必须选择实际目标；`description`保留对应环境说明。OpenAPI顶层 `servers` 为数组，每项 `url` 是API根地址（不含/api/v1/socai2），`description`为展示说明。当前唯一目标是 `http://192.168.1.21:18424`，已启动并完成空列表读取，真实业务写入及整链待验。示例ID来自此前隔离记录，不是当前候选库对象。后端要改自己的API地址时复制个人handoff目录、修改个人openapi.json的servers，再把DOCS_CONTENT指向该副本，不能改冻结交付包。

浏览器跨域需要API的AISOC_CORS_ORIGINS包含文档页面origin，当前HTTP候选含21:18480和127.0.0.1:18081。这是浏览器读取规则，不是登录或角色验证。后端服务器直接HTTP调用无需Swagger或浏览器CORS。

manifest全部字段属于**程序生成**的回执，**不控制服务行为**：`version`发行号、`operations`去重操作数、`groups`三类展示、`state`已验API合同及空态、`api_target`目标、`authentication_required=false`、`business_api_called=true`（本批实际GET）、`business_http_write_verified=false`、`whole_flow_verified=false`、`runtime_evidence`本批证据目录、`source`来源包、`files`两份内容摘要、`examples`样例适用范围。state以实际回执为依据，不能把文档可用等同业务整链通过。

## 21候选及最终发布顺序

1. 调查/HTTP先补齐候选数据库、连接、身份和完整HTTP镜像，按第11步核18424实际连接、就绪及无鉴权读取。成功建案/管理写入衔接首批Kafka实际落库的主体；空库读取与Swagger就绪不等于业务写验收。
2. 把本次handoff完整目录复制到21的 `.../candidates/streaming-20261115-01/swagger/handoff`，核文件hash；使用[候选aisoc21.env](streaming-20261115-01/aisoc21.env)及当前compose.yml，核固定AMD64镜像已在主机。
3. 在获准的候选启动阶段执行所选env的compose config/up，随后GET manifest、swagger-config和OpenAPI，核实际页面Servers指向18424、三类/80操作及无security要求。不能只核文档200就认定API可用。
4. 完整业务验收、交接与独审结束后，正式HTTP与Swagger统一发布；正式目标配置另行冻结并实际读回。当前候选18424/18480已启动并读回，21旧18024/18080保持主动停止；本批新增两个独立候选容器，其余29个运行容器保持。

更新文档必须从同版实际OpenAPI生成/核对，保持参数、输入输出、错误、异步202及退役入口一致。不要用旧功能目录脚本重新生成另一版合同覆盖本候选。[HTTP配置详情](../http-service/CONFIGURATION.md) · [前后端交接](../../FRONTEND_BACKEND_HANDOFF.md)
