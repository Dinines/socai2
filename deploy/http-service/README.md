# 独立调查 HTTP 部署

2026-11-16。21当前为 **streaming-http-20261116-r4**，入口[18024](http://192.168.1.21:18024)，正式库aisoc，80个业务操作，内部可信、无登录/Token要求。应用为`investigation_http.main:app`；HTTP受理并保存任务，独立调度器执行，GET不启动模型。

## 当前包与运行

- [完整profile](../aisoc21/streaming-release-20261116-04/http-profile.json)冻结729来源：721个app/investigation_http文件及8个配置/合同文件。六个新增核心模块、输入JSON与C1 Schema均进入同一镜像。
- [启动回执](../../docs/operations/evidence/streaming-release-20261116-04/http-start-01.json)核镜像、版本、80操作及完整raw OpenAPI；[发布读回](../../docs/operations/evidence/streaming-release-20261116-04/deployment-ready.json)核729运行文件和三个业务空列表。
- [Swagger 18080](http://192.168.1.21:18080/)使用同版[展示包](../api-docs/streaming-release-20261116-04/handoff/manifest.json)。tags/examples增强与raw合同分开，不能拿增强Swagger直接作manage.verify期望。
- [新02验收](../../docs/operations/evidence/streaming-fullflow-20261116-02/README.md)负责Kafka、异步建案/更新及同源结果读取；就绪不等于整链或模型质量通过。

运行目录为21 `/opt/sting-aisoc-socai2/deployments/streaming-release-20261116-04/http/releases/streaming-http-20261116-r4`，容器socai2-production-http-20261116-r4，旧HTTP停止。I4h、Case6h、7天窗口、1次/60秒重试保持；不再加载旧候选20秒/30秒、1天窗口覆盖。

## 显式配置

字段说明见[配置字典](CONFIGURATION.md)，取值以本批profile为准。reader/writer来自明确指定的受控runtime_environment_file，本轮沿r2正式配置；prepare核host/port/database一致，使用普通密码及TLS require，不要求PG客户端CA/证书/私钥。秘密不进Git或日志。

tenant/actor沿正式[context](../aisoc21/streaming-release-20261116-02/context.json)，调用方不提交后台身份。包内policy、lifecycle、case-allocation、run-records和共享核心完整冻结。HTTP不直连Kafka、Redis或模型，内部阶段执行及自动迁移关闭。

## 打包、构建和切换

以下用于后续明确授权的新批次，不重放已结束发布。先按完整源码生成精确patches与hash；源码变化重新冻结整个包，不只复制路由或新模块。

```sh
python3 deploy/http-service/manage.py --profile <新批HTTP-profile.json> package --output <新且不存在的目录>
```

新镜像整体替换/app/app及/app/investigation_http，基镜像只供锁定依赖；构建使用`--pull=false --network none`。上传后可先build，无需提前停旧HTTP。切换前核无在途并停旧写入口，再在新解包目录执行：

```sh
python3 manage.py --profile profile.json prepare
python3 manage.py --profile profile.json start
```

prepare要求端口可绑定，生成0600私密env、Compose和其他容器快照。start核readyz、版本、完整raw合同、80操作、镜像及其他容器未变化；因此先完成HTTP start/verify，再启动本次其他新服务。不能在预期新服务已经启动后，用旧“其他容器不变”快照误报故障。

同批再核真实受理、attempt/Run、全分页步骤/工件及content_url。Case创建使用当前真实告警/事件；旧UUID不能重放到空库。唯一投放及业务操作由测试执行，独立审查复用同批证据。

新C1写入后不可盲目切回旧r3核心或HTTP，见[回退边界](../aisoc21/README.md#回退边界)。旧18424/18480候选及逐批回执只作[历史追溯](../../docs/handoff/history/2026-11-16-release-r4/deploy/http-service/README.md)。

[前后端交接](../../FRONTEND_BACKEND_HANDOFF.md) · [异步提交](../../docs/integration/analysis-submission-http.md) · [Case首轮](../../docs/integration/case-initial-http.md) · [步骤及原件](../../docs/integration/run-records-http.md)
