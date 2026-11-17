# 调查执行模块正式发布确认

审阅日期：2026-11-16。范围为第1–7步/F1–F5的当前源码、正式发布配置、处理包及已保存验收证据。本轮仅只读检查和摘要重算；没有连接21、SQL/HTTP请求、模型调用、Kafka投递、启动服务、重新执行业务测试、提交或推送。只写本文件，不修改业务代码、发布配置、共享根文档或其他模块文件。

**模块结论：已验调查执行功能和当前冻结处理包可纳入本次发布，未发现需要重写调查核心或重跑历史功能矩阵的新阻断。正式切服务仍须完成128/129、普通账号接线和下述必要读回；当前保存证据尚不能写成正式环境已可运行。** 特别是新ingress的已知授权缺口，以及会话写入的实际RLS上下文，必须在普通账号probe中核清。后者目前是具体待验证项，不冒称已证实的正式库故障。

旧S04的3000/length失败已经由11-16新批预算续验承接：新I及整事件Case第二轮完成；W4/W5也已有后续证据。不得继续将这些旧阶段描述列为当前缺口。第8–10步和模型正文/引用质量`NOT_PASSED`保持后置，整个change不归档；本确认不是整个change全部通过或正式发布完成的声明。

## 冻结源码与既有证据

| 核对项 | 结果与可复用边界 |
| --- | --- |
| 当前处理包 | 独立读取`.local/processing-release/processing-20261116-r1/release.tar.gz`，按manifest逐项重算735文件，0缺失、0摘要不符。与已验`processing-20261115-r3`的735文件清单比较，唯一变化是`investigation-policy.toml`，没有新增业务代码分支 |
| 正式HTTP携带的核心 | 当前`http-profile.json.expected_source_hashes`的723来源逐项匹配当前文件；业务方法/Schema的专门审阅由[HTTP模块](module-http-confirmation.md)负责，本模块不重复其HTTP测试 |
| F1–F5 | [审计复核回执](../streaming-audit-recheck-20261115-01/result.json)冻结的11份核心源码仍逐项匹配。F1诊断实际范围、F2管理字段与材料区分、F3确定未发送的有限重试、F4独立请求及事件驱动Case、F5统一A/I/Case合同和工厂的直接PG/Redis/HTTP证据可复用。模型/故障替身证据仍是程序验收，不改成真实模型质量通过 |
| S01实际入站及A/I | [实际A/I验收](../test-streaming-ai-20261115-01/acceptance-01.json)：同批真实Kafka入站后4任务/attempt/Run、4生成、9查询、62GET，告警/事件先保存与受理、随后分析；来源及归并/上下文路由沿同批入站回执。质量仍NOT_PASSED |
| 两案首轮 | [Case验收](../test-streaming-case-initial-20261115-01/acceptance-01.json)：整事件3成员和单告警1成员各一轮，277保存检查、4生成、4次C4和58GET；输入、工具、原答、结果及来源身份有实际保存证据。10项引用问题与partial/uncertain保留 |
| S04续验 | [续验汇总](../streaming-budget-20261116-01/outcome-summary.json)、[119项保存核对](../streaming-budget-20261116-01/saved-validation.json)、[48GET](../streaming-budget-20261116-01/http-validation.json)一致：新I冻结4成员，活跃整事件Case扩到4成员并执行第二轮，比较本案紧邻上一Run/Result；单告警案保持1成员/1轮。独立重算PG快照摘要仍为`a2a2f45e75cd52562c281ab485f152b40a555dcba66a4b9132e9d9a74a204aa2` |
| 预算与输入保护 | 正式policy摘要与续验相同；38项容量检查、真实I/Case后轮及1MiB输入保护的既有证据可复用。[新包无网络probe](package-probe-02.json)实际加载该policy、N1/poll60s及统一工厂导入，0模型/业务写入；首次probe摘要字段误名保留在`package-probe-01.json`，不是业务源码失败 |
| 最终profile | 对[最终冻结清单](frozen-manifest-01.json)中的16份`config/`来源重算，全部吻合。较早`profile-preparation-01.json`中的support SQL摘要已过时，最终清单已承接当前SQL；不能把旧准备回执冒充最终冻结结果 |

已清空的历史业务UUID只用于上述离线证据，不从当前空库追查，不回灌旧数据、账本或评估答案。

## 正式执行配置

| 项目 | 当前确认值及含义 |
| --- | --- |
| 环境与身份 | 显式`aisoc`，tenant `00000000-0000-0000-0000-000000000001`；HTTP提交actor来自同一`context.json`，目标只读回执确认正式库存在该tenant及actor。自动Case沿既有AutomaticCaseActor；用户任务读取实际提交actor，不另造身份 |
| 普通连接 | Fusion=`socai2_prod_ingress`，调度及Case写入=`socai2_prod_processor`，HTTP reader=`aisoc_app`；三者均为普通登录角色。PG账号密码和TLS `require`；Kafka的CA挂载保留其独立用途，不作为PG客户端证书要求 |
| 统一入口 | `app.socai2.analysis_dispatch_runtime --profile /run/analysis/dispatcher.json`，工厂`app.socai2.analysis_case_executor:executors`要求现行A/I/Case合同；HTTP只受理，Fusion只保存对象/初始任务，不在HTTP或Fusion内启动第二个模型执行器 |
| 生命周期 | I检查14400秒、Case检查21600秒、活动窗口604800秒；一次自动重试、间隔60秒，Fusion初始任务和HTTP/调度生命周期一致。已受理首试跨期限可执行，过期不重试；关闭和unknown按已验规则处理，不新增人工解除步骤 |
| 调度与排队 | 总N=1、poll60秒、外层执行超时3600秒；Case优先、A其次、I再次。pending每轮按当时长度有界扫描，忙项回队，不占另一对象的空槽；不同请求不合并，执行前比较无变化时跳过且不造Run。`knowledge_sync`保留优先级名称不等于启用其handler，当前没有启用第10步维护 |
| 业务范围 | Case容量100；I最多选100并保存原选入/实际覆盖，不扩大成事件全部成员；Case跟随事件关联、唯一活跃接收者及容量续建沿现行实现。查询窗口前后各3600秒、单次补查最多50行 |
| 模型 | A/I/Deep输出8192，C3/C6输出16384；A/I每Run总tokens131072，Case393216；服务共同窗口65536，安全余量1024。C3/C6允许的计量输入加包络为48128，A/I/Deep为56320；准备字节和字符保护均1MiB，不能据此声称更大token窗口。调用数/工具数/时限未因总额度增大而放开 |
| 湖 | Fusion写入`aisoc`，执行器读同一`aisoc`；正式writer=`socai2_lake`、reader=`socai2_prod_lake_reader`。直接source_event_ids与按主机/类型/时间补查结果分开，不能把补查范围当直接来源范围 |
| 知识与其他源 | 知识查询开启，正式集合`socai2_knowledge_qwen06b_1024`、embedding `qwen3-embedding:0.6b`/1024维；`sync_after_adopted_triage=false`。清理后零知识不能声称有命中；空结果、未查询和失败分别保存。UEBA/graph/product开关均false，与实际未接入一致 |

生命周期和预算参数已由现行loader/调用路径使用；无需实际等待4小时、6小时或7天来重复验证这些已验时间分支。正式读回不能把候选20/30秒、一天窗口或旧3000预算静默带回去。

## 正式启动前必须完成的接线核对

1. **128/129和普通账号权限。** 保存的正式目标仍28表450列，计划只增量安装到32表521列并verify。`analysis-lifecycle`给processor新三表读写、reader读取；`case-allocation`给排除表对应权限；`analysis-ingress`给初始task/subject-state插入；`support-access`补既有三张公共支撑表和connector必要列。当前已知缺权尚未因SQL写好而解决。应用后必须用实际ingress/processor连接，确认role、database、TLS、租户过滤及正常入站/任务写入所需能力；不运行空库初始化或改RLS的fusion-support建表脚本。
2. **会话写入probe必须模拟真实上下文。** 当前`SessionStore.record_event`/`close_idle`经`main._LazyPool(settings.database_url)`执行，未设置`app.current_tenant_id`；仓库102迁移定义的sessions策略包含`WITH CHECK (tenant_id = current_tenant_id())`。本次target回执未读取正式策略/角色默认GUC，因此不能直接断言正式一定失败，也不能只凭GRANT宣称可写。须核正式实际策略及连接默认值，并按真实连接上下文做最小probe；若probe人为先SET租户，而运行连接并不设置，会掩盖该问题。若正式仍是该WITH CHECK且默认租户为空，session INSERT/UPDATE会被拒绝，需在启用前定向解决普通账号接线，再核直接路径；不通过放宽整表RLS绕过。AiAssetRecorder/DLQ同样按各自真实连接与现行策略核，不因一张表通过替代另外两张。
3. **正式依赖读回。** 新包probe是无网络加载，不证明正式PG/Redis/湖/知识/模型地址可用。复用发布方唯一probe核dispatcher Redis DB8及namespace、Fusion DB9、普通湖reader和writer目标、Qdrant集合/1024维及原文SELECT、模型alias到实际后端和tokenizer的65536窗口。只核需要的依赖，知识零命中和未接入源不是新阻断，不重新索引旧测试答案或额外生成模型回复来测连通。
4. **新批投递入口。** 沿[测试模块确认](module-test-confirmation.md)补显式正式Topic入口，不能直接使用仅允许candidate Topic的旧发送器。配置必须与Fusion的`socai2.raw_events.v1`、`socai2.alerts.raw`一致；只在服务订阅就绪、起始offset已记录后投新批，先上下文入湖再告警。当前清理事实不代替投递时起点核对。

以上是本次发布已有范围内的功能接线和必要验证，不引入新权限专项或额外负责人审批。除明确的缺表/缺权外，尚无本次正式普通账号probe结果，不能将待验证项写成已修复或已失败。

## 唯一执行器、切换与回退

新Fusion `socai2-production-fusion-20261116`及新调度`socai2-production-dispatch-20261116`使用同一处理镜像；固定正式Topic/group、Redis目标和状态目录。`analysis_dispatch_runtime.exclusive_process`的flock仅保护共享同一路径的实例，不能跨旧候选/不同挂载替代部署层唯一性检查。启动前、启动后都需用实际容器/进程及订阅状态确认只有这一对新业务执行入口。

`release.json.must_remain_stopped`已列出原候选各调度/Fusion及旧正式Fusion等，已保存target回执中它们均未运行。**切换检查还应覆盖同一target回执里的五个旧业务容器：`socai2-api-1`、`socai2-investigation-projection`、`socai2-agents-1`、`socai2-next-api`、`socai2-investigation-api`。** 当前它们确实已停止，未发现第二个正在消费的实例；但不能仅核较短的must_remain_stopped数组后声称核全旧入口。保留共享基础设施/其他模块，不用停整个项目实现唯一性。

候选HTTP/Swagger在新正式读取就绪后停止，4177原r4等新r5就绪后再切；新4177的正式tenant、环境标签、合同摘要和18024上游由HTTP/测试模块共同核对。原候选不再作为并行活动业务版本。

回退配置的方向正确：先停本批新入口、读回实际inflight/任务终态，保留已保存数据与失败原件；不降级DDL、不恢复清理备份、不重放请求、不重新启动旧消费者，必要时只恢复旧只读viewer。停止调度会触发本地执行取消/unknown收尾，不能当作待重派的失败。回退后业务暂停是如实状态，旧viewer仍可能只读清空候选库，不能声称业务已恢复。

## 发布后的最小业务读回

与[测试模块](module-test-confirmation.md)采用同一组新批材料和实际身份：**1条v2告警＋3上下文→正式Kafka→A/I→HTTP创建1案→Case首轮→实际4177**。这足以补本次正式环境和新输入材料的正常路径，S04后轮/上一轮比较及F1–F5沿已有实际证据复用；不另造第二轮，不等待周期，不重复投递或为HTTP另跑模型。

只补本次接线直接相关断言：上下文真实入湖、告警直接来源及事件归并正确；对象和task先保存，执行后绑定真实attempt/Run；实际请求读取新policy/输入profile且原答完整留存；I范围和Case冻结输入保持来源，首轮前次比较为空；结果、工件与HTTP/4177指向同轮。当前Case补查按实际前后1小时/主机/类型窗口验，不能机械套用fixture更窄5分钟或目的IP过滤的预期。

程序完成、结构/采用、partial/uncertain、引用及正文质量分别记录。截断导致没有可用I/Case结果、无法保存或读取等仍是本批流程未通过；已确认后置的引用/正文缺陷不追加采样，不冒称消失。新批读回、普通账号probe和唯一运行回执未出之前，本文件仅确认可发布范围及剩余必要条件。

## 本轮核对锚点

| 内容 | 摘要/结果 |
| --- | --- |
| processing manifest | `5046171675199ad1f2b73bb0ad2623f94a46ef9f65258f72d8e39ef68382f227`；735文件匹配 |
| 新处理镜像构建回执 | `sha256:630f1ccba42c4adae81e8802c6734b0c174bd1a231dfd139fd42cea7dfcfbca0` |
| 发布冻结清单 | `98e7bf51775e6422187f2f46770072b7de6710e10a2f797663755c7c277f0d2b`；其中16配置来源匹配 |
| 当前policy | `9ef4129c88b94be7cecfe3b0ad89ba545919554cf93b5ddb8c923f853ef90a8c` |
| 当前lifecycle | `2321938129828f8e768afae14ecffeaaec3f6b0788f54e8e4968ca45c0c5b181` |
| 当前support SQL | `a370c715a4043c8cad21f7c7132c9c91a787d1430e9b54535290e5dba56c7ebd`；与最终冻结一致，未执行 |

最终模块判断：**调查执行已验功能及当前包可发布；正式缺表/缺权须按本批增量补齐，session真实RLS上下文须在普通账号probe中核清，并完成同批最小正式读回。没有要求重做S04/W4/W5、实现第8–10步或重采样模型质量。**
