# 本机隔离验证与配置入口

2026-11-15。本机用于中间程序验证，最终整体验收在21从Kafka开始。当前主线为第1–7步及F1–F5修复后的统一A/I/Case执行；部署参数见[处理链](../../docs/operations/deployment-processing.md)、[数据湖与数据库](../../docs/operations/deployment-datastores.md)和[模型](../../docs/operations/deployment-models.md)，不再把旧分阶段A/AI样例或历史直接start命令作为操作入口。

## 当前选用配置

| 配置 | 用途与填写方式 |
| --- | --- |
| [analysis-aic-dispatch.example.json](analysis-aic-dispatch.example.json) | 唯一联合调度模板；部署确认tenant/DB/Redis/路径，普通PG URL显式postgresql+asyncpg，TLS/超时按asyncpg参数；其余一般保留。enabled默认false |
| [analysis-aic-executors.example.json](analysis-aic-executors.example.json) | 当前策略、事件100条、扫描批量、补查前后各1小时/50条 |
| [analysis-tasks.json](analysis-tasks.json) | 重试1次/60秒、I4小时、Case6小时、活动7天、分页 |
| [case-allocation.json](case-allocation.json) | Case100条续建及来源分页 |
| [investigation-policy-case-v1.toml](investigation-policy-case-v1.toml) | 当前A/I/Case输入合同；A/I/Deep输出8192，C3/C6输出16384；A/I总131072、Case总393216；输入文件随包冻结 |
| [knowledge-profile.json](knowledge-profile.json) | 启用知识时提供embedding/Qdrant/私密key；其余检索参数通常保留 |

模板中有默认值不代表字段可删；严格loader仍要求完整键集。地址、库、租户和秘密文件必须按本批明确配置，不继承终端环境或自动回落正式库。PG目标使用账号密码，不要求客户端CA；生产模板require保留服务器TLS，本机实际传输模式必须据该隔离服务确认，不拿无TLS连接冒称验证了require。

C4 湖查询使用本请求独占连接。当前源码的两份 `investigation-policy*.toml` 已加入 `[query_transport]`：`query_timeout_seconds=20`、`connect_timeout_seconds=10`、`send_receive_timeout_seconds=25`、`close_timeout_seconds=5`。四项均为正数，查询时限至少1秒，并受本 Run 剩余时限约束；关闭观察超时只记异常，仍须等待线程退出后才能释放名额。实际启用 C4 查询必须显式提供此表，不从其它环境回落。下一次统一打包需冻结该策略及 `app/db/clickhouse_owned.py`；旧发布包保留，不因模板更新宣称21已加载。

## 现有隔离资源与证据

本机原临时盘PG发生空间耗尽后，已完整复制到磁盘绑定新容器`socai2-case-trigger-db-20261115`，入口127.0.0.1:28413、库v12_upgrade_dev；34表计数核对一致，旧容器/数据和失败记录保留，见[复制核对](../../docs/operations/evidence/case-trigger-fix-20261115-01/storage-copy-readback.json)。这里包含业务支撑表；socai2目标业务Schema本身为32表521列。私密连接位于本机`.local`，不写进文档。

[第7步及F1–F5证据](../../openspec/changes/schedule-streaming-investigation-updates/stage7-case-updates-design-20261115.md)明确真实PG/Redis、模型替身与真实模型的边界。不能把这些程序检查当21完整Kafka验收；测试缩短检查周期只改独立测试profile，不修改正式6小时/7天默认。

已有本机run.py/config.py及remote只读工具仍保留原用途，它们不是当前完整流式部署入口。未重构路径中的历史固定环境和证书要求不由局部修改冒称全仓已清理；本轮实际连接、HTTP和调度使用上述明确目标配置。[SSH接入说明](../../docs/operations/mac-ssh-relay-20261107.md)用于网络接入，不把SSH密钥当成PG账号认证。

## 保存和读取

新数据库沿[当前安装/增量入口](../database/CURRENT.md)，不能清库绕过结构核验。一次执行开始前保存最新适用材料与范围，结束只更新实际结果；旧原答、失败、unknown和范围保持。查看时通过[HTTP指南](../../FRONTEND_BACKEND_HANDOFF.md)读task、Run、结果、工件；pending对调用方透明。

调查用例取得落库快照后按[记录页用法](../../deliverables/investigation-validation-20261106/README.md#调查运行记录页)导入新记录并保留原批次。当前实际4177仍为原三案快照，仓库新卡片不等于已发布。新增W1账本的配置、CLI和全部9项参数见[测试服务入口](../investigation-test/README.md)。

完整部署和读回状态统一见[PROGRESS](../../PROGRESS.md)；整理前说明在[历史快照](../../docs/handoff/history/2026-11-15-deployment-docs/README.md)，不作为当前启动命令。

## S6 文件日志候选

[候选打包片段](operational-logs-release-fragment.json)接当前API/Fusion和dispatcher的异常文件日志；[配置模板](operational-logging.example.json)给出INFO、20 MiB、10份。正式服务尚未切换。

新装或升级当前dispatcher源码时，所选JSON必须增加绝对`logging_profile_file`；四份`analysis*dispatch.example.json`已同步。日志profile中明确服务、实例、持久目录、级别和轮转参数；先配置文件再连接Redis/PG。旧冻结源码/旧批次profile不追改。API/Fusion以环境配置文件的`SOCAI2_LOGGING_PROFILE_FILE`选择自己的profile，内部只读query应用和独立lake delivery进程也沿此入口初始化，不因模块导入启动消费者。

三个进程使用独立service名称，并各自挂载只读profile和其声明的可写持久目录；文件名为`service.instance.pid.jsonl`。沿现有受控部署准备目录属主，不更改共享服务目录权限。HTTP打包器的`logging_directory_mount`详见[配置字典](../http-service/CONFIGURATION.md#文件日志候选配置s6)。调查回执目录与日志目录分别保存，日志不替代完成回执。

错误记录含程序事件码、真实task/attempt/Run/step引用和异常类型/调用栈位置；未取得任务的依赖失败没有task字段。普通日志不复制第三方异常正文、请求/告警或模型材料，既有凭据保护保持；按负责人要求不新增业务数据脱敏或通用脱敏模块。调试原件沿原受控工件读取，业务数据不改写。
