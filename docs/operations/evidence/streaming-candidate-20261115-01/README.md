# 第11步候选包与资源准备

2026-11-15。当前完成21独立候选目录、核心处理镜像、HTTP完整包及候选数据库/基础身份/普通连接供给；W1测试账本已完成。HTTP/Swagger实际候选接入、同库双池TLS及空态读取已通过，Kafka资源和整链服务仍待。负责人随后授权[暂停9个旧业务容器](../streaming-old-services-pause-20261115-01/README.md)，共享依赖保留；这不代表新版本正式发布。本批准备没有模型调用或Kafka投递。

## 已完成的实际操作

| 项目 | 证据与结果 |
| --- | --- |
| 资源只读核对 | [参数](resource-target.json)、[探针](inspect_resources.py)、[08:03Z回执](resource-readback.json)：当时新库/角色、四Topic、目录均不存在，18424/18480/18479/14177无监听，所在文件系统约848GiB可用 |
| 独立目录 | [创建回执](directory-created.json)：仅新增本批candidate目录和release路径，不覆盖已有项目 |
| 第一份核心包 | [r1冻结](core-package.json)及[source manifest](core-source-manifest.json)：735文件，修正Dockerfile漏COPY两个投影文件；既有8项打包检查通过。r1保留为PG简化前证据 |
| 当前核心包r2 | [冻结](core-package-r2.json)、[完整源码manifest](core-source-manifest-r2.json)：PG无CA修改后重新冻结735文件，archive SHA256为71de91d5b9aaaf99de82090645d255ccbea88b33124217ad8b761f4ba4a21e0e |
| r2上传/构建 | [上传](processing-upload-20261115T085252759564Z.json)、[AMD64镜像回执](processing-build-20261115T085516691476Z.json)：镜像sha256:01900f1dd10a96070eb56884fc6c5e86ab42de64c8d13cebb93e07d273b4d6db，733运行文件与包一致；network=none自检，0DB/模型/服务变更 |
| 当前HTTP包r2 | [HTTP回执](../streaming-http-pg-password-20261115-01/README.md)：完整包、663共享app文件同r2，80操作合同/无鉴权、实际两池无CA参数装配通过；13项工具检查；这是构建前离线证据，后续实际启动见下一行 |
| HTTP/Swagger实际候选 | [18424启动](../streaming-http-runtime-20261115-01/start-01.json)、[双连接](../streaming-http-runtime-20261115-01/connection-01.json)、[空列表](../streaming-http-runtime-20261115-01/empty-reads-01.json)、[18480 Swagger](../streaming-http-runtime-20261115-01/swagger-01.json)：r2镜像80操作一致，普通reader/writer同库TLS1.3，无鉴权3列表空态通过，业务记录仍0；零行更新/回滚仅核事务边界，不算成功业务写入 |
| W1测试账本 | [W1回执](../test-ledger-w1-20261115-01/README.md)：16组件检查、34带断言GET+3启动探测，保存/重启/只读保持；临时服务已停止 |
| W2只读代理部分交付 | [W2回执](../test-http-proxy-w2-20261115-01/README.md)：绑定实际80操作合同的55个业务GET，24组件检查及本机代理到21的8项GET/2组错误对照通过；临时代理/隧道停止。非空、真实跨Run及21测试服务/查阅部署仍待 |
| 资源重新核对 | [第二次只读观察](resource-readback-02.json)：建库前数据库/角色和四Topic仍不存在，四候选端口未占用；旧容器暂停另存回执 |
| 候选库与基础身份 | [实际供给](database-prepare-01.json)、[执行驱动](prepare_database.py)：仅创建新库socai2_streaming_20261115及NOLOGIN owner/普通reader/writer，复用123–129；32表521列、reader verify及tenant/actor引用通过。告警/Case/task/Run均0；HTTP私密双连接文件0600，默认require、无CA |

本批目标以[identity](../../../../deploy/aisoc21/streaming-candidate-20261115-01/identity.json)、[当前build](../../../../deploy/aisoc21/streaming-candidate-20261115-01/processing-build.toml)和[当前transport](../../../../deploy/aisoc21/streaming-candidate-20261115-01/transport.json)为准。PG目标已按负责人确认改为账号密码、无需客户端CA，默认require。建库复用[显式安装profile](../../../../deploy/aisoc21/streaming-candidate-20261115-01/database-install.toml)和当前新空库入口；[普通功能访问及种子](../../../../deploy/aisoc21/streaming-candidate-20261115-01/database-access.sql)仅作用于新库，收回V1按集群旧aisoc_app生成的默认访问，不修改其他库或原角色。管理socket安装检查不是普通密码/TLS验证，后者由HTTP对同一候选双池继续完成。

## 仍未就绪及下一步

新库/普通运行角色、tenant/actor和私密HTTP连接已供给。四个候选Topic及消费group/明确起点、Redis namespace/运行profile、Fusion来源表、湖与知识来源、唯一调度及测试/查阅实际服务仍需供给。名称未占用是当时观察，后续创建仍核实际身份，不覆盖后来出现的资源。旧正式18024/18080/4177已主动暂停，容器与数据保持。

先按HTTPr2入口完成实际AMD64构建/TCP空态与同库双连接核对；空库不能成功创建要求告警/事件的Case，不用夹具补成通过。首个Kafka真实材料生成后再验证HTTP建Case、同key回放和任务读取；测试补T2及W2–W4必要供给。普通模型场景从Kafka开始，核告警入库、事件关联/上下文路由、A/I、首轮/更新/上一轮比较和同批结果读取。模型质量未通过保留，不用替身或镜像构建替代最终验收。

实施顺序沿[第11步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md)和[总计划5.4](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#54-f5之后的21完整测试准入与实际下一步)，第8–10步后置。当前子步不勾整体任务、不归档、不发布正式新版本、不提交推送。
