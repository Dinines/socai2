# 20参考AiSOC：自动处理展示与三个场景

2026-10-24。仅作用于192.168.1.20原版参考部署，固定上游revision `34ca18c57dd4175539e5c6dd3d04a72dc057306b`。不属于21迁移收尾或独立调查模块交付，未改21/43、未Git提交或推送。

用户先选3个完整场景（各2—3条告警），随后授权修补自动持久化/Case展示直接缺陷；最后明确Graph/Deep无需自动建Case，重点是告警详情展示实际做过什么。本批按此口径交付3场景各2条告警，展示真实分支及partial，**不宣称3例完整调查质量通过**。

## 查看入口与实际结果

控制台：[告警](http://192.168.1.20:3000/alerts)、[实体关系图](http://192.168.1.20:3000/graph)。点击下表告警后，在“自动处理过程”展开步骤、Deep参数/返回预览、调查发现与建议、持久化报告。

| 场景 | 两条告警 | 自动结果 | 背景日志 |
| --- | --- | --- | --- |
| Office脚本执行与可疑外联，DEMO-FIN-11 | [Office启动PowerShell](http://192.168.1.20:3000/alerts/6b75ea5e-ce23-598c-9e63-90043bcb53f4)、[脚本HTTPS外联](http://192.168.1.20:3000/alerts/d71b5c96-361d-5c21-b234-0b9ad3f854b2) | 两个Graph均partial，各6轮/6工具；报告3384/3558字节 | 2行 |
| 凭据访问与远程服务关联，DEMO-APP-12 | [LSASS读取](http://192.168.1.20:3000/alerts/9181b087-c9e0-5318-990f-085681201a92)、[SMB远程访问](http://192.168.1.20:3000/alerts/306bf0d6-1a23-5d77-aa8e-0ba0f2e2e5a7) | 两个Graph均partial，各6轮，9/6工具；报告2883/3036字节 | 2行 |
| 服务账号批量读取与归档外传线索，DEMO-DATA-13 | [批量读取归档](http://192.168.1.20:3000/alerts/3c98c56d-5bde-570c-a0a1-1c4bef90d509)、[归档进程上传](http://192.168.1.20:3000/alerts/ef9c21f4-d703-5be8-a6d2-63195e09da36) | 前者Graph partial、6轮/7工具、报告2946字节；后者benign 0.95自动关闭，未升级、无调查报告 | 2行 |

全部6条告警走`aisoc.alerts.raw`→常驻Fusion→fused Kafka→常驻Agents，raw ACK为partition0 offset1—6，没有用手动调查冒充自动链。6条低级别成功登录背景事件走原Okta ingest→Kafka→Fusion湖写入，三个marker查询各2行；不是完整EDR或网络遥测。6个最终样例均`case_id=null`。

Fusion分组：前两对graph_state分别共享Incident `85b81836-be47-4ab0-8c1f-6d360c5fb0a2`、`014cbba0-d7f7-45ec-b87f-d81cc9c24772`；第三对首条Incident为`775bf856-91e9-413b-8777-f2366f27102b`，第二条原Fusion叙述明确“2 related alerts”，其仅分诊结果没有graph_state中的Incident字段。这是原Fusion事件归组，非Case自动创建或因果证明。

## Deep truncated的具体含义

第一条告警Run `b250e383-9221-550f-b192-bc1d62b450f1` 的Deep为6轮、`truncated=true`、`over_budget=false`、`cost_capped=false`，`latency_ms=16010`。Deep实际6次模型调用21538 tokens，连同分诊共7次22962 tokens。原`run_with_tools`只有用尽轮次且模型仍请求工具时返回truncated，因此表示**达到6轮调查上限，尚未收束**，不是报告文本截断。

实际依次查询process_activity、process_tree、historical_execution、entity_timeline、network_connections、persistence_mechanisms。进程/历史执行为空、时间线读到2行；进程树/持久化类型未存储，网络查询LakeQueryError。查询失败不等于无活动。页面已将原“Deep truncated: True”译为具体原因，保留原始原因；未增加轮次或重跑旧Run。其余4个Graph也均6轮truncated，报告保留PARTIAL提示及原模型判断，不视为已验收结论。

## 直接缺陷及修补

1. 自动Run原`case_id`是Alert ID，原Case接口只按业务Case UUID过滤；自动worker也不在手动API的内存`_runs`中。新增同tenant、Case既有alert_ids→Run.raw_alert.id读取兼容，保原人工回退，不改写Run ID或case_id、不自动建Case。
2. 自动Graph原来只有步骤记录，最终状态/报告未持久化。仅新自动Run将graph_state、Markdown、HTML与graph_result事件同事务保存；分开执行status与completion，Deep限额/异常为partial。旧缺失不伪造补写。
3. Case页面明确区分automatic_graph/automatic_triage及原人工四角色；告警详情和列表侧栏新增“自动处理过程”，只读刷新同一Run。展示真实节点结束、跳过、工具参数及原版返回预览、发现/缺口/原因、建议和报告。无Case的attack_path节点明确skipped，建议不冒充执行。自动分诊关闭为not_escalated且没有报告按钮。
4. 原APOC路径节点ID用coalesce而边只取.id，导致部分边端点null/500；部署专用副本两处统一ID取法，原源码保留。图通过原host/user/alert投影API整理示例关系；全租户图实读35节点34边，含原数据与诊断材料，不能当3场景独占数量或自动发现的攻击因果路径。

实现及复现配方见[部署目录](../../deploy/aisoc20/README.md)；生成文件通过只读挂载，Web采用固定原镜像构建20专用镜像。没有修改本地参考`opensource/AiSOC`或服务器原始源码，没有引入21独立调查设计。

## Chain、Attack Path及Explain的区别

- 原CaseWorkspace的Attack Chain时间线和Attack Path专门面板均按真实Case ID请求。Chain从Case上下文查询相关告警，不等同于Fusion内部Incident分组；Attack Path读Case已有关系子图，也不自动证明攻击因果。全局`/graph`实体关系图无需Case，可以独立查看。
- 自动Graph固定流程为triage→enrichment→investigation（含Deep）→attack_path。最后的attack_path节点只有解析到Case关联才调用图API、再对最多5个候选实体计算blast radius；无Case直接返回。本批5个Graph均实际skipped，没有生成Attack Path结果。原Deep工具注册表没有Attack Path工具，本批工具调用也未出现它。
- 若有Case且成功读到图，原attack_path节点仅将节点/边数量、战术序列、类型计数及高影响实体摘要写入`state.threat_intel.attack_path`，文字补进findings/建议；不把完整nodes/edges存进Deep结果。完整图由Case的Attack Path页实时读取图API。本批保存的graph_state也会保留上述字段，但本批字段不存在，因为实际跳过。告警页“已执行步骤”明确记录skipped；全局图中的示例关系不能冒充该Run已消费的图证据。
- 告警顶部Explain打开ExplainDrawer，优先`POST /api/v1/alerts/{id}/explain`，读取当前告警、候选规则/历史误报统计、本地MITRE卡片及原始字段证据，可能调用模型生成一次摘要；结构接口不可用时回退Agents流式`POST /api/v1/explain`（429不回退）。它不是Deep调查或已有Run过程回放。新增“自动处理过程”才读本次Run的真实执行记录。本轮只读核源码，未点击Explain或新增解释模型调用。 正常摘要prompt只含告警title/severity/category/source/description/tags、规则名称/描述/匹配方式及可信度、MITRE ID/名称/战术、historical_fp误报率/样本数/窗口/范围；要求模型生成3—5句解释，不查询既有Run工件，也不启动工具循环。侧栏其余结构项由程序整理，摘要可回退模板。

## 验证与证据

- 新6告警/6Run，71条实际步骤/事件、34个工具调用记录、27份工件；27份UTF-8正文大小/hash核对一致。5组graph_state/Markdown/HTML各同一graph_result事件关联。
- 实际`aisoc_run_costs`为36次模型调用、117286 tokens（6次分诊＋30次Deep）；这是用量，不是已定价费用。Deep状态原tokens字段为0，不能按零用量解释；页面采用成本表计数。
- 新报告5份可从告警持久接口读取；真实running观察先无报告，完成后读到partial。错误告警ID和不关联Case下读取Run均404。实际API容器内将既有诊断Case在事务内临时关联第一条合成告警，Case列表predicate、自动详情和3384字节报告均可读，其他tenant helper返回None；随后rollback并确认alert_ids恢复，未保留Case修改。此为真实数据库直接接缝，不宣称新身份的跨租户HTTP实测或Case全UI验收。
- 原类直接probe覆盖正常、Deep截断、外层超时和workflow形状，不调用模型。Web `pnpm type-check`和Next build通过，最终`web-build-final.log`于03:53:51Z写完，导出manifest index `a3284678a1519292ad04117eb59b17596191dd1ca21df76d5e10fd1a80edb286`，与实际容器和当前tag一致、容器03:55:21Z启动；`web-build-alert-details.log`为03:51:33Z的前一构建，两者均包含AlertDetailView，不能按名称倒推先后；首次禁网build因Google Fonts下载失败保留，后续使用正常构建网络成功。
- 实际浏览器核第一场景停止文案/查询参数/报告入口、第二场景16事件、第三场景仅分诊关闭及全局实体图。截图`alert-process-visible.png`为可见停止文案；较早`alert-stop-reason.png`未包含该区域，不作为展示证明。
- API/Neo4j健康检查healthy；Web/Agents/Fusion/ingest/ClickHouse均running，无healthcheck不写healthy。

服务器证据根为`/home/lychee/beenuar/deployment/showcase-20261024/`；安全白名单副本在本地`.local/aisoc20/showcase-20261024/evidence/`：`final-{1,2,3}.json`为输入与ACK、`final-*-delivery.json`及报告为真实结果、`final-*-lake.json`为背景查询、`final-read-verification.json`为hash/用量/拒绝/状态、`final-graph-overview.json`为图、`delivery-patch.json`/`graph-patch.json`为来源hash。原配置、数据库备份和完整docker inspect在服务器私有`before/`，权限0700；command日志可能含配置，不复制或输出。正式凭据仍仅存私有配置，不写入本回执。

## 保留的限制与诊断记录

未接完整厂商遥测/SIEM、enrichment/UEBA查询不完整、Agents原图读取认证接线未扩展；工具结果原版仅200字符preview，步骤时间是持久化时间，不能证明每步完整输入输出或精确执行游标。缺少进程树、持久化等数据和查询失败保留，未扩大为工具/模型质量改造。原报告文字可能有超出证据的判断，PARTIAL提示不等于已修正所有原文质量。

最初经`/alerts/submit`直写的2条告警不经过自动Kafka链，及诊断Case `7ddb9f0e-38de-4b5b-9a4b-e642f2451150`保留；其2条背景告警实际自动BTP关闭，2次模型2884 tokens。随后诊断Kafka告警`819d6d07-09e3-5df9-9cf6-9c26a919a6a7`自动7次模型22883 tokens，但发生在修补前，最终Graph报告缺失保持，未补写/重跑。以上另计，不混入最终6例117286 tokens。初次湖SQL `%` 驱动格式错误、首次配置restart未应用新挂载、初版构建失败和错误快照容器名均作为过程失败保留；修后使用实际compose up及定向读取，不追认为首轮成功。

后续若要调查自然收束，需要另行讨论工具可查数据、查询失败及轮次/预算策略；本批不通过增加上限凑完成。用户已授权的直接展示修补与3场景数据准备之外，不继续新的调查设计或模型调用。

结束独审限定ACCEPT、0必须修，按实际展示/示例范围归档并同步3条20专用规格；[审计及封后核对](../../openspec/changes/archive/2026-10-24-prepare-aisoc20-showcase-examples/audit.md)。不外推为调查质量或21服务验收。
