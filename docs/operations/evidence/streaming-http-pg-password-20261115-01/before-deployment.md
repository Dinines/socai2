# 独立调查 HTTP 部署

2026-11-15。此页只说明最新待交付版本 `streaming-http-20261115-r1`。它提供告警、事件、调查三类 **80 个业务操作，默认内部可信，无登录、Token或角色校验**。独立入口是 `investigation_http.main:app`；HTTP受理操作并保存任务，调查执行由独立调度服务负责，GET不启动分析。

## 当前交付与实际运行

| 内容 | 状态 |
| --- | --- |
| 完整候选源码与配置 | [profile.json](streaming-20261115-01/profile.json)，完整 `app`、`investigation_http` 和所需JSON/SQL，723个来源文件；[离线验证回执](../../docs/operations/evidence/streaming-http-candidate-20261115-01/README.md) |
| 21候选目标 | `http://192.168.1.21:18424`，独立数据库 `socai2_streaming_20261115`，`linux/amd64`；**尚未启动** |
| Swagger候选 | `http://192.168.1.21:18480`，见[部署说明](../api-docs/README.md)；**尚未启动** |
| 实际运行观察 | 21正式18024为64操作且仍401、静态18080为71操作；本机18024/18080也仍是旧服务。它们不代表本候选已可用。[实际观察证据](../../docs/operations/evidence/http-local-runtime-review-20261115-01/README.md) |
| 尚缺供给 | 候选数据库/迁移及记录身份、真实读写连接文件、CA摘要、目标架构镜像与真实TCP验证。见[requirements.json](streaming-20261115-01/requirements.json) |

完整包离线导入核对了80操作、无鉴权Schema、165个实际加载模块均来自解包目录，以及所有HTTP查询配置。12项部署工具直接检查通过。尚未构建/运行本HTTP的21镜像，未创建库、投递Kafka或调用模型；不能把离线结果当运行就绪。

## 配置入口

**所有本次字段的用途、类型、当前值、加载位置、生效方式和验证见[配置字典](CONFIGURATION.md)。** 表内区分部署必填、保留默认、启用时必填和程序生成；保留默认指保留模板值，不代表删除字段。以[候选身份](../aisoc21/streaming-candidate-20261115-01/identity.json)约定的数据库、租户、记录人和端口为准。

- [profile.json](streaming-20261115-01/profile.json)：完整文件/hash、镜像、端口、运行环境和挂载；供 `manage.py` 使用。
- [context.json](streaming-20261115-01/context.json)：数据归属租户和统一记录操作人；需要在目标数据库中真实建立，调用方不提交这些身份。
- 私密运行文件：`/opt/sting-aisoc-socai2/candidates/streaming-20261115-01/private/http-runtime.json`，JSON包含真实 `DATABASE_URL` 与 `SOCAI2_CASE_DATABASE_URL`；当前未创建，不进Git。
- `runtime_mounts[0].sha256` 当前为 `null`，表示CA摘要未确认，**prepare会拒绝**。由部署方核真实文件后填写并重新冻结完整包，不能填任意摘要绕过。

HTTP不需要Kafka、Redis、LiteLLM、ClickHouse、Neo4j或文件存储的直接连接。相应执行/来源由调查服务供给，HTTP读写同一候选PostgreSQL里的业务对象、任务及结果。普通附件只保存业务后端文件ID等关联信息，文件上传下载由业务后端负责。

## 第一步：本机准备完整离线包

以下在仓库根目录执行；本阶段不要求业务数据库或Docker服务。使用显式Python环境，输出必须是一个不存在的新目录：

```sh
.local/conda-envs/socai2/bin/python deploy/http-service/manage.py \
  --profile deploy/http-service/streaming-20261115-01/profile.json \
  package --output .local/http-candidate/streaming-20261115-01/package-new
```

打包前校验所有来源摘要和完整目录成员；输出含Dockerfile、profile、manifest和同名tar。当前已验证的产物为 `.local/http-candidate/streaming-20261115-01/package-02.tar`，摘要见回执。源码改变后须重新核同版清单，不能删掉摘要检查。只用片段覆盖部分路由不足以构成当前版本。

完整包包含当前核心代码是为了提供用例和读写依赖；应用只挂载独立HTTP入口，不启动其他API、消费者、调度器或模型。基础镜像仅提供选定Python依赖，新镜像层整体替换 `/app/app` 与 `/app/investigation_http`，保留包内SQL/JSON；不修改主机或旧容器文件。

## 第二步：部署方补齐21候选后准备、构建

当前仍缺实际连接与CA摘要，下面是**供给齐备后的步骤**，本轮未执行。先由调查部署流程准备同一目标数据库的V1及128/129增量、所需基础身份、只读/写连接；保留所有现有数据。HTTP工具不执行迁移或自动建库。

1. 核候选端口仍空闲、外部网络存在，依赖基镜像ID/AMD64与profile一致。把已冻结tar传到候选根目录，解包至独立release目录。
2. 在21受控目录提供上述私密JSON，并将确认后的CA源路径、容器路径和SHA-256纳入最终profile。配置变更需重新打包/核manifest，不能手改包内文件后绕过校验。
3. 在解包目录执行：

```sh
python3 manage.py --profile profile.json prepare
python3 manage.py --profile profile.json build
```

`prepare`只读取显式私密文件和显式只读挂载；核两条URL的主机、端口、库名均为本候选，不复制参考容器的环境或挂载。它生成 `compose.json`、其他容器状态快照及权限0600的 `private/<release>/runtime.env`。不打印秘密、不启动服务；私密输出目录必须不存在。

`build`只使用已核ID的本地基镜像，`--pull=false --network none --platform linux/amd64`；不下载依赖。依赖缺失时补齐当前候选镜像构建方案并定向验证，不切换旧执行版本。

## 第三步：候选TCP验证及最终发布

候选资源与镜像供给完成后，按本change第11步安排启动候选；操作目标只有本profile的容器和18424：

```sh
python3 manage.py --profile profile.json start
python3 manage.py --profile profile.json verify
```

`verify`核 `/readyz`、实际版本、完整OpenAPI（忽略展示用info/servers）、80操作、无鉴权Schema、镜像及其他容器快照。**这些仍不足以证明业务流程通过**，随后必须以真实TCP无Authorization头完成最小读取/受理→实际任务执行→同身份结果和原件读回，核失败/unknown与未运行空态。调度器启用和Kafka投递由调查/测试统一安排，HTTP启动不会自动替它们完成。

最终从Kafka进入的整链、交接与独立结束审计完成后，再统一发布正式HTTP与Swagger并读回。正式18024/18080需另行冻结实际正式profile，不能直接改候选的端口/数据库然后宣称同包已验收。当前不切正式服务，不推送Git，不重放已结束批次。

## 配套指南

[前后端交接](../../FRONTEND_BACKEND_HANDOFF.md) · [80操作Swagger离线包](../api-docs/streaming-20261115-01/handoff/manifest.json) · [HTTP配置字典](CONFIGURATION.md) · [调查首轮与任务读取](../../docs/integration/case-initial-http.md) · [异步事件/调查提交](../../docs/integration/analysis-submission-http.md) · [完整步骤与原件读取](../../docs/integration/run-records-http.md)
