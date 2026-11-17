# 候选HTTP与调度的生命周期配置对齐

2026-11-15。**已在21实际完成，唯一变化是候选HTTP增加一个只读配置挂载并重建容器。** 保留镜像`sha256:35d4021c6a1b31a57161e8cadd6a5bc004152648cbcb12e7aa1b0c140b3842f8`、release `streaming-http-20261115-r2`、18424入口及80操作无鉴权合同。

原因：任务列表的`update_state.auto_expires_at/eligible/ineligible_reason`使用读取端lifecycle计算，原HTTP为7天、同批调度为1天，截止时间会相差6天。统一运行配置即可解决，不修改业务代码或接口字段。

| 配置 | 变更前 | 实际加载后 |
| --- | --- | --- |
| 活动窗口 | 604800秒 | 86400秒 |
| 事件检查间隔 | 14400秒 | 20秒 |
| Case检查间隔 | 21600秒 | 30秒 |
| 重试次数/等待 | 1次/60秒 | 1次/5秒 |
| 分页默认/上限 | 50/100 | 50/100 |

宿主文件为`/opt/sting-aisoc-socai2/candidates/streaming-20261115-01/analysis/config/lifecycle.json`，只读挂载到原环境变量`SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`所指的`/app/config/analysis-tasks.json`。实际容器内`AnalysisTaskPolicy.load()`所得配置与[同批源文件](../../../../deploy/aisoc21/streaming-candidate-20261115-01/analysis/lifecycle.json)相同，SHA-256为`4ab6f1b11d5bc3a87005c92597ccba6f6d9a58ce880417eb729d90c77941e6aa`。

直接验证：

- 原运行镜像、环境摘要、命令/用户/工作目录、端口、安全/内存/网络/重启参数保持，只新增该只读挂载；只执行已有镜像的Compose重建，没有构建/拉取镜像。
- `/readyz`正常，完整`/openapi.json`变更前后相同，80业务操作、无鉴权；规范化合同摘要`0dcd2e518e2d4558c67882f4bbaaa1084549c43c4e6a907f36fbdb681db281ba`。
- Swagger及9个已停止旧业务容器的ID、镜像、状态保持。原Compose文件未修改，原私密环境文件沿用，未输出凭据。
- 0业务GET、0业务写入、没有调度/模型启动；已有task的冻结重试参数未改。本回执仅证明配置实际加载一致，任务资格/真实A/I结果的业务GET仍等待测试同批保存回执。

运行清单见[lifecycle-runtime.json](../../../../deploy/http-service/streaming-20261115-01/lifecycle-runtime.json)。原Compose位于`http/releases/streaming-http-20261115-r2/compose.json`，当前同时使用`http/runtime-overrides/lifecycle-20261115-01.compose.json`；后续重建应保留两份配置。原Compose单独运行会恢复镜像内旧lifecycle，不能当成保持当前配置。

证据为[变更前](preflight-01.json)、[应用及变更后](apply-01.json)和[执行脚本](align_lifecycle.py)。原配置源及冻结包保留，仓库当前profile同步记录挂载。执行前OpenSpec严格校验通过；本步骤未推送Git或正式发布。
