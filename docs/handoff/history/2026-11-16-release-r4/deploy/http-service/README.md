# 独立调查 HTTP 部署

2026-11-15。此页说明21已启动的独立候选 `streaming-http-20261115-r2`，正式交付仍待整链验收。它提供告警、事件、调查三类 **80 个业务操作，默认内部可信，无登录、Token或角色校验**。独立入口是 `investigation_http.main:app`；HTTP受理操作并保存任务，调查执行由独立调度服务负责，GET不启动分析。

## 当前交付与实际运行

| 内容 | 状态 |
| --- | --- |
| 完整候选源码与配置 | [profile.json](streaming-20261115-01/profile.json)，完整 `app`、`investigation_http` 和所需JSON/SQL，723个来源文件；[离线验证回执](../../docs/operations/evidence/streaming-http-pg-password-20261115-01/README.md) |
| 21候选目标 | [18424 API](http://192.168.1.21:18424)，独立数据库 `socai2_streaming_20261115`，`linux/amd64`；**已启动，真实连接及无鉴权三类空列表通过** |
| Swagger候选 | [18480 Swagger](http://192.168.1.21:18480)，80操作/三类合同与实际API一致；**已启动并读回**。见[部署说明](../api-docs/README.md) |
| 21旧服务状态 | 2026-11-15按负责人要求主动停止旧18024 HTTP及18080 Swagger；容器和数据保留，不恢复。[停止回执](../../docs/operations/evidence/streaming-old-services-pause-20261115-01/pause-01.json)。这不是候选发布或故障 |
| 本机最近观察 | 本机18024/18080仍为旧服务，未随本次21暂停操作变更。[观察证据](../../docs/operations/evidence/http-local-runtime-review-20261115-01/README.md)；不能据此认定候选可用 |
| 未完验证 | 旧失败批管理写读30请求、新批入站非空35 GET已通过；真实A/I执行后62次GET也已通过，正文质量NOT_PASSED保留；建案及同批Case整链/独立结束审计仍待。见[requirements.json](streaming-20261115-01/requirements.json) |

完整包离线导入核对了80操作、无鉴权Schema、165个实际加载模块均来自解包目录，以及所有HTTP查询配置；13项部署工具直接检查通过。本次沿冻结包在21构建并启动镜像`sha256:35d4021c6a1b31a57161e8cadd6a5bc004152648cbcb12e7aa1b0c140b3842f8`，[实际运行回执](../../docs/operations/evidence/streaming-http-runtime-20261115-01/README.md)记录普通reader/writer同库TLSv1.3、三类空列表200、Swagger合同一致；零行UPDATE后回滚，0业务提交/模型/Kafka。实际建案写入及整链未验。

**此前连接补验：** [测试侧回执](../../docs/operations/evidence/pg-password-connection-20261115-01/README.md)的21普通reader密码/TLS及本机disable写入回滚保留原范围；本次21候选require双池/TCP有独立新回执，不拼接旧结果充当当前验收，也未重跑原业务批次。

## 当前生命周期配置覆盖

2026-11-15已完成[实际对齐](../../docs/operations/evidence/streaming-http-lifecycle-20261115-01/README.md)：HTTP与调度共用同一lifecycle，活动窗口86400秒、事件20秒/Case30秒检查、重试最多1次等待5秒；已有任务的受理时冻结值不追改。保留r2镜像/80合同，环境不改，只新增只读文件挂载并重建候选HTTP；Swagger和旧服务保持。

当前运行采用原冻结Compose加[单挂载覆盖文件](streaming-20261115-01/lifecycle-compose.override.json)，具体21路径/源摘要见[lifecycle-runtime.json](streaming-20261115-01/lifecycle-runtime.json)。后续需要重建本候选时，保留两份配置：

```sh
docker compose \
  -f /opt/sting-aisoc-socai2/candidates/streaming-20261115-01/http/releases/streaming-http-20261115-r2/compose.json \
  -f /opt/sting-aisoc-socai2/candidates/streaming-20261115-01/http/runtime-overrides/lifecycle-20261115-01.compose.json \
  up -d --no-deps --no-build --pull never api
```

原Compose单独运行会移除该挂载并回到镜像内旧配置；普通`docker restart`保留当前挂载。仓库当前profile已同步runtime_mounts，未来按新profile准备时仍须核同批宿主文件及摘要。上述实际回执只验配置/健康/合同，随后[A/I业务结果62次GET](../../docs/operations/evidence/streaming-ai-http-20261115-01/README.md)已通过，同批1天截止时间已核，模型正文质量NOT_PASSED。

## 配置入口

**所有本次字段的用途、类型、当前值、加载位置、生效方式和验证见[配置字典](CONFIGURATION.md)。** 表内区分部署必填、保留默认、启用时必填和程序生成；保留默认指保留模板值，不代表删除字段。以[候选身份](../aisoc21/streaming-candidate-20261115-01/identity.json)约定的数据库、租户、记录人和端口为准。

- [profile.json](streaming-20261115-01/profile.json)：完整文件/hash、镜像、端口、运行环境和挂载；供 `manage.py` 使用。
- [context.json](streaming-20261115-01/context.json)：数据归属租户和统一记录操作人；需要在目标数据库中真实建立，调用方不提交这些身份。
- 私密运行文件：`/opt/sting-aisoc-socai2/candidates/streaming-20261115-01/private/http-runtime.json`，JSON包含真实 `DATABASE_URL` 与 `SOCAI2_CASE_DATABASE_URL`；调查方已提供，文件权限0600，不进Git。
- PG只填地址、端口、库名、用户名和密码；[私密环境模板](streaming-20261115-01/runtime-environment.example.json)中的两条连接填完整后保存到受控路径。`postgres_sslmode=require`由模板提供，prepare自动补入省略模式的URL；无需CA、客户端证书或私钥；当前`runtime_mounts`仅包含同批lifecycle文件只读挂载。空模板有意不可启动。

HTTP不需要Kafka、Redis、LiteLLM、ClickHouse、Neo4j或文件存储的直接连接。相应执行/来源由调查服务供给，HTTP读写同一候选PostgreSQL里的业务对象、任务及结果。普通附件只保存业务后端文件ID等关联信息，文件上传下载由业务后端负责。

## 第一步：本机准备完整离线包

以下在仓库根目录执行；本阶段不要求业务数据库或Docker服务。使用显式Python环境，输出必须是一个不存在的新目录：

```sh
.local/conda-envs/socai2/bin/python deploy/http-service/manage.py \
  --profile deploy/http-service/streaming-20261115-01/profile.json \
  package --output .local/http-candidate/streaming-20261115-01/package-new
```

打包前校验所有来源摘要和完整目录成员；输出含Dockerfile、profile、manifest和同名tar。当前已验证的产物为 `.local/http-candidate/streaming-pg-password-20261115-01/package-01.tar`，摘要见回执。源码改变后须重新核同版清单，不能删掉摘要检查。只用片段覆盖部分路由不足以构成当前版本。

完整包包含当前核心代码是为了提供用例和读写依赖；应用只挂载独立HTTP入口，不启动其他API、消费者、调度器或模型。基础镜像仅提供选定Python依赖，新镜像层整体替换 `/app/app` 与 `/app/investigation_http`，保留包内SQL/JSON；不修改主机或旧容器文件。

## 第二步：部署方补齐21候选后准备、构建

本候选已按以下步骤完成准备和构建。先由调查部署流程准备同一目标数据库的123–129、所需基础身份、只读/写连接；保留所有现有数据。HTTP工具不执行迁移或自动建库。以后新部署使用新release目录，不覆盖本批产物。

1. 核候选端口仍空闲、外部网络存在，依赖基镜像ID/AMD64与profile一致。把已冻结tar传到候选根目录，解包至独立release目录。
2. 在21受控目录提供上述私密JSON，核两条普通账号密码连接的目标。无需提供PG证书或证书挂载。公开配置/源码变更需重新打包核manifest；真实连接只保存于受控私密文件。
3. 在解包目录执行：

```sh
python3 manage.py --profile profile.json prepare
python3 manage.py --profile profile.json build
```

`prepare`只读取显式私密文件；本候选无额外挂载。核两条URL的主机、端口、库名均为本候选，且有用户名和密码，不复制参考容器的环境或挂载。它生成 `compose.json`、其他容器状态快照及权限0600的 `private/<release>/runtime.env`。不打印秘密、不启动服务；私密输出目录必须不存在。

`build`只使用已核ID的本地基镜像，`--pull=false --network none --platform linux/amd64`；不下载依赖。依赖缺失时补齐当前候选镜像构建方案并定向验证，不切换旧执行版本。

## 第三步：候选TCP验证及最终发布

候选资源与镜像供给完成后，按本change第11步安排启动候选；操作目标只有本profile的容器和18424：

```sh
python3 manage.py --profile profile.json start
python3 manage.py --profile profile.json verify
```

`verify`核 `/readyz`、实际版本、完整OpenAPI（忽略展示用info/servers）、80操作、无鉴权Schema、镜像及其他容器快照。**这些仍不足以证明业务流程通过**，随后必须以真实TCP无Authorization头完成最小读取/受理→实际任务执行→同身份结果和原件读回，核失败/unknown与未运行空态。调度器启用和Kafka投递由调查/测试统一安排，HTTP启动不会自动替它们完成。

最小验证分两步：空库先核同库普通reader/writer实际连接、require TLS、可信上下文、无鉴权列表和空态，以及18480的同版合同。`POST /cases`必须至少选择一个真实告警或事件，不能用空案验证成功写入。成功写读并入首批S01的Kafka→真实A/I→整事件建案流程，使用实际canonical ID读取Case/首轮任务、同key重放，再做一次管理修改并读回；调查方统一安排Case受理读回与调度开始的观察点，原首轮任务进入同批后续执行，不额外预建单告警Case。空库连接成功、错误请求回滚均不计作成功业务写验收。详细顺序见[第11步HTTP实际验证安排](../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#第11步候选实际启动与最小tcp验证)。

最终从Kafka进入的整链、交接与独立结束审计完成后，再统一发布正式HTTP与Swagger并读回。正式18024/18080需另行冻结实际正式profile，不能直接改候选的端口/数据库然后宣称同包已验收。旧21服务保持主动停止，本次仅启动独立候选；未推送Git、未重放已结束批次。

## 配套指南

[前后端交接](../../FRONTEND_BACKEND_HANDOFF.md) · [80操作Swagger离线包](../api-docs/streaming-20261115-01/handoff/manifest.json) · [HTTP配置字典](CONFIGURATION.md) · [调查首轮与任务读取](../../docs/integration/case-initial-http.md) · [异步事件/调查提交](../../docs/integration/analysis-submission-http.md) · [完整步骤与原件读取](../../docs/integration/run-records-http.md)
