# 当前独立 HTTP 入口验证

本轮响应负责人“OpenSpec规划并推进”，复用本change承接主调查3.12的入口部署子项。其余功能计划留在[接口路线](../../../../docs/investigation/http-implementation-plan-20261112.md)，不据入口修复核销主调查31/41或模型质量。

## 本地实施和验证

- 独立入口现在要求显式数据库名、读取目标和已启用写入目标一致，允许明确选择正式`aisoc`。启动只读连接确认，退出释放两个连接池；无DDL、消费者、字段合同变更。
- A/I手动执行依赖改为现有调查写连接，Case/H和认证/GET合同不变。新增稳定缺配置错误，沿用既有503编码。
- [10项定向测试](../../../../docs/operations/evidence/http-service-20261112-01/direct-tests.txt)通过：目标匹配/缺失拒绝、正式目标、手动A/I写依赖、Case/H连接配置及既有本机只读入口边界。旧来源检查/模型测试复用上轮证据，不扩大测试矩阵。
- 本机原应用TCP服务`127.0.0.1:18024`已就绪，43操作齐全，显式连接`v12_upgrade_dev`。第一次JWT使用旧合成用户，写范围不足返回403，未修改该用户；原失败保留。本批仅新增一个两日有效的隔离测试key，现有用户/角色不变。
- [本机9次HTTP](../../../../docs/operations/evidence/http-service-20261112-01/local-http-02/verification.json)经原认证、路由、业务服务和实际读写会话完成建案→H创建→完成修订→当前/历史读取；没有依赖替换。当前H七项值与[真实SQL读取](../../../../docs/operations/evidence/http-service-20261112-01/local-sql-readback.json)一致，旧修订原文保留，Run仍pending、零模型调用；Q明确501。

## 21候选与发布边界

独立正式入口配置为`192.168.1.21:18024`，新容器`socai2-http-api`，正式`aisoc`；原主API、旧独立API及所有数据保持。以实际已部署主API镜像`sha256:0c7fc22631c5dd05719e43c8097ead1d112f1d9220e2028fa76e8cb50214fee9`为基础，只覆盖`app/socai2_main.py`和`app/api/v1/endpoints/socai2_stage_execution.py`。当前模型输入工作树修改不在候选范围。凭据和模型配置在21继承原受控环境及只读挂载，不导出内容。

r1仅构建阶段失败：Docker BuildKit把裸sha256当成远端镜像名，受本机既有代理不可用影响；没有启动服务或改代理。r2使用固定本地标签且校验相同镜像ID、关闭BuildKit，离线构建。[发布前限定独审](audit-20261112.md)通过后，一次启动r2正式服务。

真实模型质量仍NOT_PASSED；不发起新模型调用，不启动自动消费，不把HTTP或模型替身通过当模型效果通过。

## 21实际验收

- [实际连接](../../../../docs/operations/evidence/http-service-20261112-01/21-actual-targets.json)：reader为`aisoc_app`、writer为`socai2_prod_processor`，两者实际数据库均`aisoc`；两处运行源码摘要与候选一致。
- [发布读回](../../../../docs/operations/evidence/http-service-20261112-01/21-final-runtime.json)：`http-20261112-r2`，43操作，ready200；镜像`sha256:1db7027b962b6576b3e395adf28e7cc108e9893bd27132ebd89d5ea0c057c3a6`。新服务启动后所有原运行容器ID、镜像、启动时间不变，旧主API/旧独立服务及消费者配置保持。
- [9次真实HTTP](../../../../docs/operations/evidence/http-service-20261112-01/21-http-03/verification.json)：正常登录现有账号，创建验收Case `773a8339-19e3-5917-b6ca-7c6cdaaf6eb9`及H任务，完成修订后读取当前/历史版本。结果、范围、事项等七字段与[SQL读回](../../../../docs/operations/evidence/http-service-20261112-01/21-sql-readback.json)一致；Run仍pending_update且started_at为空，Q返回501，零模型调用。
- 首次21来源GET因旧API key过期401，第二批旧28000转发返回空503，均在任何业务写入前停止；原失败保留。新显式28025认证转发连接21原主服务，正常登录成功；没有续期key、改账号或权限。只读SQL脚本首次模块路径错误，改为实际`app.db.case_database`后通过，没有数据库写入。
- 43操作/100个源组件合同与候选一致；40操作完整覆盖沿用前轮ASGI/真实库和明确模型替身证据。本轮真实TCP只补入口和Case/H直接路径，不声称真实A/I模型、完整调查或未调用接口已在21逐项通过。

## Swagger与交接

[docs5两端回执](../../../../deploy/api-docs/receipts/20261112-docs5.json)确认本机ARM64/21 AMD64的九个入口均200、内容摘要一致。默认正式API为21:18024，另列28024正式转发与本机18024隔离库。40操作标已实现，3操作标未实现/501；522字段、28动态结构、109文档Schema保持，未改变输入输出。发布后[容器复核](../../../../docs/operations/evidence/http-service-20261112-01/21-after-docs.json)仅既有Swagger容器变化，原业务容器与新API镜像保持。

限定独审已复核正式发布证据与docs5内容，无阻塞。下一项调查基本管理/关闭重开仍是未实现计划；主调查31/41、真实模型质量NOT_PASSED保持。本change未Git提交、推送或更新SpiritHub引用；21 Swagger可直接查阅。
