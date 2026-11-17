# 第11步HTTP完整候选包与配置准备

> 此处保留r1首次离线验证。负责人随后取消PG证书前置，当前配置/完整包改为[r2回执](../streaming-http-pg-password-20261115-01/README.md)，以下CA待供给条件不再适用。

2026-11-15；状态：**本机离线准备通过，21候选运行未就绪**。隶属schedule-streaming-investigation-updates第11步第一个HTTP子步。没有启动或切换本机/21服务，没有数据库连接、业务写入、Kafka投递、真实模型调用或Git提交推送。

## 交付

- 当前[完整profile](../../../../deploy/http-service/streaming-20261115-01/profile.json)、[可信业务上下文](../../../../deploy/http-service/streaming-20261115-01/context.json)、[尚缺供给](../../../../deploy/http-service/streaming-20261115-01/requirements.json)。全部723个来源文件带hash：完整app 671、完整HTTP 44（含43个冻结py/json及README）、8个公开配置/合同/依赖元数据。
- 处理包processing-20261115-r1的663个共同app文件摘要一致；本HTTP另含3个必要SQL及5个说明文件，不遗漏读侧SQL。HTTP43文件与F5冻结摘要一致。基镜像固定d602316…5425e，但本HTTP的目标AMD64构建/运行尚未验证。
- 实际本机包：`.local/http-candidate/streaming-20261115-01/package-02.tar`；SHA-256 `be88801855711f6de7aa4cfc6a506b9d281ab5f4b4a673ed13b3efefa8bd5f6e`。解包目录extracted-02，manifest覆盖726文件。`package-01`及首次离线成功记录保留；02移除了程序未消费的摘要环境变量，政策hash由manifest及加载器回执核验。
- 最新[Swagger候选](../../../../deploy/api-docs/streaming-20261115-01/handoff/manifest.json)保留三类/80合同，仅更新版本/候选Servers，目标18424/18480均未启动。
- 当前操作入口：[HTTP部署](../../../../deploy/http-service/README.md)、[全部配置项](../../../../deploy/http-service/CONFIGURATION.md)、[Swagger部署/本机查看及配置](../../../../deploy/api-docs/README.md)。旧操作说明字节保存在docs/handoff/history/2026-11-15-http-deployment-docs，不混入当前命令。

## 实际检查

| 检查 | 结果与证据 |
| --- | --- |
| 完整包/显式prepare | [12项直接检查](direct-tests.txt)通过；缺件/变更拒绝、旧容器环境与挂载不继承、错误读写目标/CA/缺文件在Docker操作前拒绝、真实合同变化即使数量相同也拒绝 |
| 解包清单与实际导入 | [offline-02.json](offline-02.json)：165个已加载app/HTTP模块都来自解包目录；socket连接显式禁止，未启动lifespan/服务 |
| 真实候选合同 | 实际app.openapi与冻结合同一致（排除发行号/Servers展示）；80业务操作、无security；无新业务字段/路径 |
| 配置加载 | 当前tenant/actor JSON、9类查询/任务策略和现行A/I/Case合同实际加载成功，数值在同一离线回执 |
| Swagger | 当前compose加候选env离线解析通过；展示合同与上一已验候选一致，Servers仅指候选18424；未打开浏览器或启动容器 |
| 文档及源码 | Ruff及OpenSpec strict通过；逐项字段和相对链接核对结果见docs-check.json；四类配置及是否可省略核对见[docs-check-02.json](docs-check-02.json) |

直接测试使用临时目录、Docker/端口探测替身；包导入只用本机依赖，不能证明21AMD64依赖已齐。首次直接检查9通过1失败：测试未替代端口探测，被沙箱拒绝绑定；补齐替身后通过，没启动服务。首次核心清单比较遇未收录的说明文件，改为共同文件对照并完整保留HTTP必需SQL；未删源码。初次检查情况见initial-checks.json，不改写成一次通过。

## 下一步实际供给

1. 调查部署方提供候选PG及迁移/tenant/actor回执，生成受控http-runtime.json中的真实reader/writer URL；必须同主机/端口/库并启verify-full。
2. 确认实际CA文件hash，替换profile的null并重新冻结运行包。当前缺文件或null时prepare明确拒绝，不继承正式连接。
3. 在21构建当前HTTP候选AMD64镜像、核真实依赖，再按获准第11步安排启动候选18424，检查实际OpenAPI/版本/上下文及无凭据业务保存读回；同步候选Swagger18480。
4. 配合W2–W4及Kafka真实整链/模型。W1已由测试侧完成，完整change结束审计与正式统一发布仍待。

本子步只改部署入口、直接部署检查、候选配置和交接资料；业务核心、HTTP源码及DTO不变。
