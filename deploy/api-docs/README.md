# Swagger HTTP接口文档部署

2026-11-16。当前21为streaming-http-20261116-r4，**80个业务操作，告警/事件/调查三组，无登录、Token或角色校验**。[同版文档包](streaming-release-20261116-04/handoff/manifest.json)已在18080加载，API为18024。[实际回执](../../docs/operations/evidence/streaming-release-20261116-04/switch-swagger-01.json)核合同、三组和CORS；新业务验收见[02批](../../docs/operations/evidence/streaming-fullflow-20261116-02/README.md)，不把文档200当模型质量通过。

| 目标 | 当前配置 | 状态 |
| --- | --- | --- |
| 21 Swagger 18080 | [aisoc21.env](streaming-release-20261116-04/aisoc21.env)，linux/amd64 | [实际运行](http://192.168.1.21:18080/)；新r4容器，旧展示入口停止 |
| 21 API 18024 | [完整HTTP profile](../aisoc21/streaming-release-20261116-04/http-profile.json) | 正式aisoc，80操作及空态已验 |
| 个人文档18081 | [local.env.example](streaming-release-20261116-04/local.env.example) | 示例须生成本机绝对路径；不宣称已在个人机器启动 |

## 后端在自己电脑启动 Swagger

需要Python 3、Docker及Docker Compose v2。以下在socai2仓库根执行，SpiritHub用户先进入server。只操作个人文档容器，使用18081避开已有18080。配置示例按ARM64；Intel/AMD将DOCS_PLATFORM改为linux/amd64。

先生成带本机绝对目录的env文件：

```sh
mkdir -p .local/api-docs/streaming-release-20261116-04
python3 - <<'PYCONFIG'
from pathlib import Path
source = Path('deploy/api-docs/streaming-release-20261116-04/local.env.example').read_text()
Path('.local/api-docs/streaming-release-20261116-04/local.env').write_text(
    source.replace('<absolute-current-checkout>', str(Path.cwd())))
PYCONFIG
```

核对配置中的架构、镜像和端口后执行：

```sh
docker compose --env-file .local/api-docs/streaming-release-20261116-04/local.env \
  -f deploy/api-docs/compose.yml config --quiet
docker compose --env-file .local/api-docs/streaming-release-20261116-04/local.env \
  -f deploy/api-docs/compose.yml pull
docker compose --env-file .local/api-docs/streaming-release-20261116-04/local.env \
  -f deploy/api-docs/compose.yml up -d
```

首次显式pull取得所选架构镜像；Compose运行配置为pull_policy=never，不在up时自动更新镜像。离线环境由部署方提供对应架构镜像，`docker load -i <镜像文件>`后把SWAGGER_IMAGE设为实际已导入的固定摘要/标签，不能把ARM64镜像给21使用。

打开 [本机Swagger](http://127.0.0.1:18081/)。下载合同的路径是 `/handoff/openapi.json`：

```sh
curl --fail http://127.0.0.1:18081/handoff/manifest.json
curl --fail http://127.0.0.1:18081/handoff/swagger-config.json
docker compose --env-file .local/api-docs/streaming-release-20261116-04/local.env \
  -f deploy/api-docs/compose.yml ps
```

预期manifest为streaming-http-20261116-r4、80操作、告警/事件/调查三组。共用接口可在多组显示，不能把重复显示相加算业务操作数。例子来自隔离验证已保存记录，UUID不是21当前现成数据；调用前换成目标环境实际ID。

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
| `DOCS_PORT` | 部署必填 | integer string；21 18080、个人18081 | 宿主端口；冲突时显式改个人配置，不挤占正式18080 |
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

[swagger-config.json](streaming-release-20261116-04/handoff/swagger-config.json)也明确以下全部字段，由浏览器加载。值与Compose保持一致；更改只读挂载文件后刷新浏览器，改挂载路径需重建文档容器。

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

`servers[].url` 属于**部署必填**，必须选择实际目标；`description`保留对应环境说明。OpenAPI顶层 `servers` 为数组，每项 `url` 是API根地址（不含/api/v1/socai2），`description`为展示说明。当前唯一目标是 `http://192.168.1.21:18024`，已启动并完成空态与合同读取，新02业务整链正在验证。示例ID来自此前隔离记录，不是当前正式库对象。后端要改自己的API地址时复制个人handoff目录、修改个人openapi.json的servers，再把DOCS_CONTENT指向该副本，不能改冻结交付包。

浏览器跨域需要API的AISOC_CORS_ORIGINS包含文档页面origin，当前HTTP含21:18080和127.0.0.1:18081。这是浏览器读取规则，不是登录或角色验证。后端服务器直接HTTP调用无需Swagger或浏览器CORS。

manifest全部字段属于**程序生成**的回执，**不控制服务行为**：`version`发行号、`operations`去重操作数、`groups`三类展示、`state`已验API合同及空态、`api_target`目标、`authentication_required=false`、`business_api_called=true`（本批实际GET）、`business_http_write_verified=false`、`whole_flow_verified=false`、`runtime_evidence`本批证据目录、`source`来源包、`files`两份内容摘要、`examples`样例适用范围。state以实际回执为依据，不能把文档可用等同业务整链通过。

## 后续更新及本轮边界

本轮已按[21发布流程](../aisoc21/README.md)在新目录部署并读回，配置和handoff来自同一r4冻结。后续变更需新的显式批次，核实际HTTP版本/80操作/无鉴权，再核Swagger方法、路径、参数和请求响应Schema一致；tags/examples/description是展示层差异，不能作为原始HTTP合同严格比较的输入。

不使用旧publish.py重新生成包含已退役E11/E13/E36的另一版文档。当前manifest版本、runtime_evidence和文件hash必须指向实际批次。新业务/模型验收、完整change独审及归档各自记录，不能由Swagger成功代替。旧18424/18480候选记录见[历史快照](../../docs/handoff/history/2026-11-16-release-r4/deploy/api-docs/README.md)。

[HTTP配置](../http-service/CONFIGURATION.md) · [前后端交接](../../FRONTEND_BACKEND_HANDOFF.md)
