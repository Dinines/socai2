# Swagger HTTP接口文档服务

当前文档版本docs8，以标准Swagger展示53个后端HTTP操作，按告警、事件、调查归类。每个接口写明用途、输入、输出、结果、实现状态和错误；保留完整Schema及示例。旧功能目录URL转入Swagger，产品演示和页面接线进度不在当前接口入口展示。

| 环境 | Swagger | 平台 |
| --- | --- | --- |
| 本地 | http://127.0.0.1:18080/ | linux/arm64 |
| 21内网 | http://192.168.1.21:18080/ | linux/amd64 |

`/handoff/openapi.json`可下载导入后端工具。18080只提供文档；21正式独立API为`http://192.168.1.21:18024`，本机SSH转发为28024，本机隔离服务为18024。Swagger Servers明确选择数据目标，记录ID不得跨库混用。

## 后端在自己电脑启动 Swagger

需要 Python 3、Docker 和 Docker Compose v2。只启动文档，无需数据库、Kafka、模型服务或 Node。以下命令在 **socai2 仓库根目录**执行；如果使用 SpiritHub，先进入 `server/`。本例用独立项目名和 `18081`，不占已有 `18080`。

1. 生成个人文档副本：

```sh
python3 deploy/api-docs/build.py --output .local/api-docs/developer/handoff
```

2. 选择 Docker 引擎的架构，再生成本机配置。Apple Silicon 通常为 `linux/arm64`，Intel/AMD 通常为 `linux/amd64`；以 `docker info --format '{{.Architecture}}'` 为准。下例是 ARM64，x86 机器只需改第一行：

```sh
SOCAI2_DOCS_PLATFORM=linux/arm64
SOCAI2_DOCS_IMAGE=docker.swagger.io/swaggerapi/swagger-ui@sha256:59ee9021a8884437c7fd8aae79e0a46ee6b6dd3afd7f24a587c4501585fde53b
cat > .local/api-docs/developer.env <<EOF
COMPOSE_PROJECT_NAME=socai2-api-docs-dev
SWAGGER_IMAGE=$SOCAI2_DOCS_IMAGE
DOCS_PLATFORM=$SOCAI2_DOCS_PLATFORM
DOCS_BIND=127.0.0.1
DOCS_PORT=18081
DOCS_CONTAINER_PORT=8080
DOCS_CONTENT=$(pwd)/.local/api-docs/developer/handoff
EOF
docker pull --platform "$SOCAI2_DOCS_PLATFORM" "$SOCAI2_DOCS_IMAGE"
docker compose --env-file .local/api-docs/developer.env -f deploy/api-docs/compose.yml config --quiet
docker compose --env-file .local/api-docs/developer.env -f deploy/api-docs/compose.yml up -d
```

镜像首次需要拉取；Compose 的 `pull_policy: never` 不会自动下载。内网离线环境由运维提供**对应架构**的镜像包，用 `docker load -i <镜像包.tar>` 导入，并将 `SWAGGER_IMAGE` 改为导入后实际存在的标签或摘要。不要把本机 ARM64 镜像直接用于 21 AMD64。上述源摘要与 21 离线导入后的摘要不同，21 当前值保留在 `aisoc21.env`。

`DOCS_CONTENT` 必须是本机生成目录的绝对路径；路径含空格时在 env 文件中给整个值加双引号。不要复制维护者 `local.env` 中的 `/Users/lychee/...` 路径。端口冲突时改 `DOCS_PORT` 后重建该文档容器。

3. 打开 [个人本地 Swagger](http://127.0.0.1:18081/)，下载地址为 `/handoff/openapi.json`。检查：

```sh
curl --fail http://127.0.0.1:18081/handoff/manifest.json
docker compose --env-file .local/api-docs/developer.env -f deploy/api-docs/compose.yml ps
```

当前应显示 `2026-11-13.docs8`、53 操作、告警/事件/调查三组。53 是去重后的操作数，共用接口会在多个业务组显示。

### 选择调用哪个 API

Swagger 页面的 **Servers** 下拉框选择：

| 选项 | 用途 |
| --- | --- |
| `http://192.168.1.21:18024` | 可访问 21 内网的后端联调，正式 `aisoc` 数据 |
| `http://127.0.0.1:28024` | 当前电脑通过 SSH 转发访问同一正式服务 |
| `http://127.0.0.1:18024` | 当前电脑自己运行的隔离 API；仅装 Swagger 不会启动它 |

用已有 SSH 接入配置时，转发命令为：

```sh
ssh -N -o ExitOnForwardFailure=yes -L 28024:192.168.1.21:18024 sting-infra21
```

`sting-infra21` 是维护者的 SSH 别名；其他电脑先按实际账号/跳板配置 SSH，见[接入说明](../../docs/operations/mac-ssh-relay-20261107.md)。转发应保持运行；已有 28024 时不重复启动。

若需要自己的 API 地址，编辑**个人副本** `.local/api-docs/developer/handoff/openapi.json` 的顶层 `servers`：

```json
"servers": [
  {"url": "http://192.168.1.21:18024", "description": "21 调查 API"},
  {"url": "http://127.0.0.1:18024", "description": "本机隔离 API"}
]
```

URL 不带 `/api/v1/socai2`，每条 OpenAPI path 已含这个前缀。保存后刷新浏览器；重新 build 会恢复仓库默认 Servers，需重新应用个人地址。

点击 Authorize 填入现有有效凭据，再使用 Try it out/Execute。示例 UUID 是合成占位值，必须使用[测试数据和操作指南](../../docs/integration/backend-test-guide.md)中的同环境真实 ID。调用 start/analyze/diagnose 会实际运行分析，不能当文档预览。

浏览器的请求由**打开 Swagger 的电脑**发出，`127.0.0.1` 也指该电脑。出现 Failed to fetch 而命令行可连时，核对 API 的 `AISOC_CORS_ORIGINS` 是否包含文档页面实际 origin（如 `http://127.0.0.1:18081`）；这属于部署配置。HTTPS 页面调用 HTTP 还可能被浏览器阻止，可改用本地 HTTP 文档或同源代理。后端程序直接 HTTP 调用不受浏览器 CORS 限制。

### 更新、停止和排查

拉取同一交付版本后，重新运行 build 到个人目录并刷新页面即可，静态目录已挂载；修改 env/镜像/端口后再执行同一 Compose `up -d`。不要直接把业务服务原生 `/openapi.json` 替换交接版，它不包含本项目补充的字段含义、实现状态和功能说明。

```sh
docker compose --env-file .local/api-docs/developer.env -f deploy/api-docs/compose.yml logs --tail 50 swagger
docker compose --env-file .local/api-docs/developer.env -f deploy/api-docs/compose.yml down
```

这里的 down 只针对 `socai2-api-docs-dev` 文档项目，不删除数据卷。页面能开但接口列表失败时检查 `/handoff/openapi.json` 是否 200、`DOCS_CONTENT` 是否正确；镜像缺失/架构不符则按第二步处理。

## 文档来源与构建

原OpenAPI是结构来源，catalog.py保存操作说明，publish.py合并已审计字段并补操作结果；build.py生成静态包。125项原功能范围及历史审计保留在仓库，不据现有接口反向扩展产品。

```sh
python3 deploy/api-docs/build.py --output /tmp/socai2-docs-preview
```

先检查暂存包、完成限定文档独审，再将同一包保存到仓库交接目录及两个profile的DOCS_CONTENT。运行挂载采用不可变版本目录，构建不会直接覆盖在线文档。

## 独立发布

Compose项目为socai2-api-docs，容器为socai2-api-docs-swagger-1。只复制静态包、compose.yml及目标profile，不同步业务代码、私密配置或数据。

- 本地：local.env，内容路径`.local/api-docs/releases/20261113-docs8/handoff`。
- 21：aisoc21.env，内容路径`/opt/socai2-api-docs/releases/20261113-docs8/handoff`。

两端继续使用既有官方Swagger镜像：多架构来源摘要sha256:59ee9021a8884437c7fd8aae79e0a46ee6b6dd3afd7f24a587c4501585fde53b；21单平台导入摘要sha256:95b2555796efa9171c00a281c096499d28261adc24e80856fc11571276251b9c。profile显式指定不同架构，本次不重新拉镜像或修改Docker代理。

本机发布：

```sh
docker compose --env-file deploy/api-docs/local.env -f deploy/api-docs/compose.yml up -d
```

21发布（SSH别名sting-infra21）：

```sh
docker compose --env-file /opt/socai2-api-docs/aisoc21.env -f /opt/socai2-api-docs/compose.yml up -d
```

发布后只读文档版本、内容摘要、容器状态和架构；不调用业务API、数据库或模型。当前结果见deployment-receipt.json，历史结果见receipts目录。文档发布不代表Git远端或SpiritHub引用已同步。
