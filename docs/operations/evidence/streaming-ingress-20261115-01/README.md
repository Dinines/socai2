# 21候选原生入站与来源准备

本轮按第11步[设计及唯一分工](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md#本轮落点入站与来源逐步验收)执行。调查方准备资源和修阻断，测试方只执行一次分阶段Kafka投放/CH与PG断言，HTTP方复用真实ID做接口核对。本目录先记录调查方资源证据，业务测试回执随后链接，不把资源就绪等同整链通过。

## 已通过的资源出口

- [配置](../../../../deploy/aisoc21/streaming-candidate-20261115-01/ingress.json)显式选定新库、四Topic、唯一group、独立Redis及私密连接引用。旧9个业务容器保持暂停；没有启旧projection、Agents或A/I/Case调度。
- [准备回执](prepare-01.json)：候选PG新增sessions/dead letters/AI资产三张公共支撑表，socai2仍32表521列，无public.alerts。ClickHouse新库/空48列表、普通reader/writer；四Topic各1分区/复制1；独立Redis持久目录、无主机端口。
- [连接及启动](start-04.json)：普通PG writer密码/TLS1.3、三表读取和死信试写回滚，Redis认证连接，普通湖writer查询空表，四Topic真实SSL起止位点全0。首次processing r2镜像的Fusion65个源码文件与当时本地相同，工作目录/PYTHONPATH指向该包内完整Fusion，未构造另一条入站业务路径。
- [最终资源就绪](ready-01.json)：Fusion `/readyz`通过，group为Stable/1个成员，实际分配raw(0)和raw_events(0)；读取实际socai2入口、归并86400秒/容量500及功能开关。准入时告警/事件/Case/task/attempt/Run/死信均0，所有Fusion计数和湖缓冲均0。

测试冻结后另补[connector基础来源](connector-01.json)：ID和tenant沿冻结材料，普通writer实际读回通过，health=unknown；不构造告警/事件/调查记录。来源配置为[source-connector.json](../../../../deploy/aisoc21/streaming-candidate-20261115-01/source-connector.json)。

资源就绪回执SHA256为`18d87b25a03a962b158e7b176c33e4453d4cf3276c4ca771cc80d76453d31b9d`。测试用这个唯一文件冻结新batch；旧T2仅是离线材料证据，不重派其身份。

## 保留的失败与定向修正

1. [start-01](start-01.json)在消费者启动前遇到Redis保护模式拒绝容器间连接。没有业务消息；为独立候选配置私密密码并仅重启它，[修正回执](redis-auth-01.json)，共享Redis不变。
2. [start-02](start-02.json)只读Kafka探针未给consumer登记Topic，`partitions_for_topic`返回空；退出清理还出现CancelledError。不是Kafka业务处理失败。
3. [start-03](start-03.json)补取全部Topic仍未填该consumer的分区缓存，断言仍失败。改为明确订阅四Topic且group_id=None、不提交消费位点；start-04实际SSL元数据及空位点通过，然后首次启动候选Fusion。原三次失败和私密诊断文件保留。

每次执行的公开脚本和输入在`*-invocation-*.json`，私密连接不在输入/公开回执中。原准备脚本初次Ruff有2项规范错误（缺check参数/异常记录说明），已修正，当前Ruff通过；原实际脚本保存在prepare-invocation-01中。普通连接重复检查仅为上述失败定位与修正后的直接复验，没有发送/重派测试材料。

## 安装与直接验证

[当前支撑安装](../../../../deploy/database/fusion_public_support_20261115.sql)通过现有install_reader新增`fusion-support`模式。原053/102/110迁移保持，复制定义注明摘要；102仅取sessions及其策略，不执行旧public.alerts字段变更，也不登记全平台迁移完成。最终入口剥离上游默认角色授权，只授予显式配置角色，不对其他既有角色执行授予/撤销；本候选初版仅在新表的同一事务中授予并收回旧默认角色，原回执和输入不改写。相同入口用于新专用调查库完成初始化之后及已有目标库补齐支撑。

直接检查为2项安装器测试（原生支撑源定义/不引入旧告警存储、入口角色显式配置）、实际候选DDL、普通连接回滚写读、资源启动及消费分配。[最终安装入口复验](support-final-01.json)还补齐测试发现的reader读取public.connectors缺项，32表521列保持，不改其他角色授权；测试投递前42501失败保留在其批次中。Ruff和OpenSpec strict通过。未运行全仓回归或故障矩阵。运行变量、必填/默认与测试选择见[部署说明](../../deployment-processing.md#21流式候选入站配置)。

## 业务出口

原准入安排为先12条S01-context经Kafka实际落湖并核0额外告警，通过后3条S01-alerts经原生sink即时保存，再交HTTP。当前已完成下方r3新批两道实际验证及35次同源HTTP读取；首批来源错误及失败原件保持，不追认旧批通过。

本轮不投S04、不创建Case、不调用A/I/Case模型；真实分析/首轮/更新与比较、W2非空/跨Run及查阅、独立结束审计、统一发布仍待。模型正文质量NOT_PASSED保持。


## 来源错误修复及当前r3

真实测试第一道12上下文已通过，第二道发现源告警ID被追加为原始事件来源，3条告警的引用变成6条；[旧批失败](../test-streaming-s01-ingress-20261115-01/README.md)保留。修复只涉及Fusion consumer及内部HTTP /process两个入口：告警使用显式事件来源，空来源保持未知；只有normalized raw_events可追加其真实event_id。外部HTTP/DB字段和API核心不改。

[测试方唯一直接验证](../test-source-scope-fix-20261115-01/README.md)证明冻结r2在新增6例中失败、normalized event原例通过；修复后两个文件21项通过。根侧复用该回执，没有重跑。全文件Ruff存在8项既有问题，[与r2逐项比对](r3-ruff-baseline.json)确认没有新增，未为了本修复批量整理旧代码。

[r3包差异](r3-source-diff.json)为735文件中仅上述2处，API核心及策略完全一致；离线构建验证733个运行文件、无网络、0模型/数据库写入。HTTP r2因此保持现有80操作，不重新打包只换标签。

[唯一候选替换](replace-01.json)先核raw=3/raw_events=12均已提交且lag=0，停r2（exit0）并保留为`socai2-streaming-fusion-20261115-r2-stopped`，再启r3。[当前ready-02](ready-02.json)通过：新镜像`sha256:859c34c4730956511f6fb1c3f54085eeafd48e09671c8ffb45d7a4e5cab9d12f`、Stable/1个group成员、旧材料/3A/1I/4task仍保留，0attempt/Run。其SHA256为`faab593f92cd9537a09bc0669469ea5ec82edba150b6738ff3212657ccf540e3`，新批必须引用它而不是ready-01。

[HTTP关闭旧批](../streaming-failed-batch-close-http-20261115-01/result.json)完成3A completed/1I resolved，保存停止后续分析原因，30次TCP操作/读取通过；原件/6来源/结论指针保持，无新人工反馈。旧4task仍accepted且无attempt/Run，不能提前写成已skip；后续正常调度领取会按既有closed_before_start结束，不新增取消接口。

[r3新批真实复验](../test-streaming-s01-ingress-20261115-02/README.md)已完成两道：12条上下文真实落湖并保留原件/时间/0/false/空列表，按当前来源查询谓词核命中/排除；随后新增3A/3材料/3实际来源/3工件、1新I/3成员、4条accepted initial任务。新I不同于旧批，旧12CH/3A/1I/6来源及4task基线保持。0attempt/Run/Case/模型，未发S04。[HTTP同批35次GET](../streaming-ingress-http-20261115-02/README.md)已通过：双向关联、来源/成员分页、材料原件、4条任务及无分析状态与测试快照一致，无业务写入或重复查库。HTTP首次离线断言错误及修正保留，复用响应完成验证，业务合同未改。

[统一验收回执](../test-streaming-s01-ingress-20261115-02/acceptance-01.json)标明本子步passed及未验范围。根对话核回执文件摘要，没有重跑测试或HTTP。下一子步准备实际A/I调度、模型与来源profile后继续消费这4条已受理新任务，不重投Kafka；同时观察旧关闭对象的4条任务由正常资格检查跳过，不能提前写成已发生。背景/知识仍未实际导入或索引，C4路由、真实A/I/Case和模型质量未验；W2代理非空/跨Run、W3/W4及独立审计/统一发布继续待办。
