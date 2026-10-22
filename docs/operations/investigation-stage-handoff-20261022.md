# 调查阶段功能与版本交接

2026-10-22后续收口：已形成[逐项责任与候选发布差异](investigation-stage-closeout-20261022.md)及[机器清单](../handoff/investigation-stage-closeout-20261022.json)。19个拟选运行文件的审查副本与7个后置C2/文案差异分开，Deep只提取链图摘要；不是直接拿本页原36份整文件保版部署。下文原批次证据与局部ACCEPT保持原范围，未发布/5/15不变。

2026-10-22。沿[总计划](completion-plan.md)B5→B6与[restore任务](../../openspec/changes/restore-alert-investigation-integrity/tasks.md)2.1/4.1收敛已有证据，补链图本地保版。**第一步告警→自动实际调查→基本结果与Markdown读取已接通；本地链图增量也已限定验证，但未发布21。** 当前没有新证据表明基本交付存在必须追加的接线阻断；整体迁移、全部质量和常驻准入仍未完成。

本轮只整理交接和保存版本，无业务代码变更、新模型/HTTP/消息/业务测试或部署。下表复用原批次结果，既有失败、unknown和未发输入保持；不汇总重叠测试为新的通过总数，也不将不同Run拼成一个新的端到端实测。

## 已有功能证据

| 能力 / 交给谁 | 已取得的直接证据 | 所在版本与实证边界 |
| --- | --- | --- |
| 已有告警→Fusion→持久化/fused | [B1](integrity-b1.md)两条source-v1覆盖HTTP/Kafka顺序，身份、首次材料、PG/API结果一致；119项直接测试、10次HTTP | 已部署。复用B1限定证据，不重跑已有告警或raw生产/检测 |
| 自动分诊→按策略关闭 | [B4 C1](integrity-autonomy-r01.md)原worker消费，BTP0.95按0.85阈值实际关闭，PG/API resolved；1回复2174tokens | 已部署代码的受控执行；常驻worker OFF。一例通过不能覆盖旧分类/理由质量失败 |
| 自动分诊→无需人工再点的调查→报告 | [B4 C2](integrity-autonomy-r01.md)真实ingress→Kafka/Fusion/fused→原worker→graph/deep，6工具含MITRE，MD及11工件可读；Run `e3d019ae`前缀 | 第一条主链接通证据已成立。graph partial、Deep截断及报告超证据表述保留，不能称完整调查或质量通过 |
| 默认人工四节点→结果/Markdown | [人工R01](integrity-investigation-r01.md)4次模型10167tokens、25事件、MD读取；[链图新Case](attack-chain-path-local-20261021.md)4次模型18388tokens、29事件/4工件、Case/Run MD一致 | 前者已部署版本，内容质量未全过；后者本地API/Agents借21基础设施、三条PG合成告警起步，未重跑Fusion/Kafka且未发布 |
| Router领域分支→模板Markdown | [本地Router](investigation-functional-20261021.md)公开叙述例NR→Identity/Cloud→TP→模板MD，3回复2917tokens | 本地已观察。领域Agent无工具循环、schema无NR，不等价于完整取证/响应计划；Phishing/Insider未作真实模型实测 |
| Deep结构工具调用→下一轮材料 | [本地Deep](investigation-functional-20261021.md)6轮回复、7次真实工具执行，call id与下一轮ToolMessage逐项匹配 | 21540/20000停止、无最终narrative；最后请求的网络工具未执行。占位/缺源和成功空结果分别保留 |
| UEBA异常→Fusion评分/解释 | [真实联合](../handoff/ueba-fusion-joint-20261021.json)原基线/消费者、真实PG/Redis/Kafka，3档异常与5条新告警及OFF对照 | 本地源码＋21隔离topic/group；常驻Fusion联动开关仍false。历史full的1样本与本批异常不是同一验证 |
| 知识/记忆/只读来源→模型 | [R01](integrity-investigation-r01.md)同一KB块进入4份prompt；[candidate04](integrity-citations-tools.md)引用parser与七权限只读身份接通；[full](full-support-migration.md)湖仓/UEBA等基本读取 | 已部署的PG全文与只读服务身份有证据；未证明所有向量知识/真实历史SOP、厂商SIEM或全部来源覆盖，知识不等于本案观察 |
| 原链/图→模型摘要→Run工件 | [链图回执](attack-chain-path-local-20261021.md)Neo4j11节点15边、PG链5候选、同一摘要进入4次实际输入，3类链图工件和MD读回200 | 本地已验未发布，候选含同tenant其他Case；原链算法/编排保持。Router/Deep链图消费为直接测试，持续同步/旧边清理未验 |
| Markdown按Case/Run持久读取 | [R01](integrity-investigation-r01.md)、[B4](integrity-autonomy-r01.md)、[链图](attack-chain-path-local-20261021.md)均有真实持久/读取证据；链图成功例的MD与report_md逐字一致 | 当前报告交付已具备代表证据。PDF暂缓、HTML非前置；内容质量单独判定，不重调报告模型 |

自动C2总用量22568=分诊2117＋graph20451。它证明该Run实际记账关系；graph用量超过节点预算的旧事实仍保留。不能将后续本地质量修正描述成此前I2持久用量修复未部署。

## 已发布与本地差异

本轮没有重新访问21盘点运行态。下列是[最近一次full发布回执](full-support-migration.md#运行与验证)记录的版本，不是2026-10-22新健康检查：API `1be37c38`、Fusion `c52b9aac`、Agents `aec3c54f`（candidate05上仅复制full所需bundle）、UEBA `8b04bc64`、enrichment `eb59af97`、TI `c15d75f4`。完整SHA及来源以原回执/清单为准；旧`4ccf3a6d`不是full后最新记录的Agents整镜像。

| 本地内容 | 验证 / 审查状态 | 发布状态 |
| --- | --- | --- |
| UEBA→Fusion联合例及观察脚本 | 真实联合结束独审ACCEPT，已有[本地版本](../../.local/versions/ueba-fusion-20261021-1c84658ebb88/manifest.json) | 仅测试与交接；未开启常驻联动 |
| authentication_events的IPv6空值过滤、单IOC的ioc_type字段 | [本地实测](investigation-functional-20261021.md)局部直接测试及真实服务接缝通过，独审ACCEPT；[13文件增量版本](../../.local/versions/investigation-functional-20261021/manifest.json) | 未部署；线上typed认证入口未由本地SQL验证代验 |
| 链图投影/读取/Bundle消费/Run工件 | [本批](attack-chain-path-local-20261021.md)API109通过/7既有livePG跳过，Agents120及新增2项、最终22合同复核（重叠不累加）；结束独审限定ACCEPT | 未部署；本次补[本地manifest](../../.local/versions/attack-chain-path-20261022/manifest.json)及归档 |
| 此前C2 graph/deep质量修正、关闭原因文案 | [原记录](integrity-graph-correctness.md)及PROGRESS保留157项/39项等实录；最新源码尚未完成最终独审 | 未部署，继续按既定口径后置，不因保版或链图独审自动获整包发布验收 |

链图本地版本是Git基线 `0806c52e80b5724666951c265e3e2a388f3610f1` 上的选定完整文件副本、依赖声明/lock、测试和回执。manifest逐文件记录hash，源码归档与副本比对；不包含`.local`私有环境、HTTP观察或凭据。它依赖基线中未复制的文件，**不是独立安装包、部署镜像或已审发布包**。整文件可能含早先本地修改，链图限定独审不扩张为对这些修改的发布审查。

## 按一个Run读取过程与结果

链图成功例：Case `82b1246f-9f34-463c-8c2d-27d2b075c741`，Run `e998308a-a353-4647-99f6-10f94ced0ecf`。下列是已有读取证据的索引，本轮未再次发HTTP；本地测试API/隧道已停止，新接口未发布到21。

| 需要读取的内容 | 原接口（均在/api/v1下） | 已有结果 |
| --- | --- | --- |
| 状态、次数、用量 | `GET /investigations/{run_id}` | completed、4轮、18388tokens；不代替内容质量结论 |
| 每步发生什么 | `GET /investigations/{run_id}/events?since=-1&limit=200` | seq0—28共29事件 |
| 本次模型可见链/图摘要及完整有界结构 | `GET /investigations/{run_id}/artifacts`，再GET具体artifact_id | attack_chain/attack_path/alert_graph及相同model_summary；工件记录当时材料 |
| 持久Markdown | `GET /cases/{case_id}/investigations/{run_id}/report.md` | HTTP200，与report_md逐字一致 |

逐节点实际输入/可见输出及代码采用在[原完整案例](attack-chain-path-local-20261021.md)；本地观察目录为`.local/aisoc21/attack-context-20261021/case-v2/observation/`。当前图查询返回现在的状态，不能替代Run工件中当时的输入。

## 原任务的剩余责任

保持restore **5/15**。这是原完整产品任务的进度，不否认前述第一步接通和局部交付；本轮不因补文档/版本而勾任务或归档。

| 现有任务 | 本阶段已覆盖与保留事项 |
| --- | --- |
| 2.1、4.1 清单/交接 | 以本表连接原功能对照、架构、回执和本地版本；所有功能的发布状态仍各按原证据，整项不提前勾完 |
| 2.2、2.3 身份/正常用量 | candidate03及前序直接测试/实际拒读、C2用量材料已有；待整个change收口逐项按原责任确认，不新加全入口模型矩阵 |
| 3.1、3.2 工具/知识消费 | 已配置只读身份、PG全文及full基本来源有证据；两处接口合同与链图仅本地，向量未消费不充作当前主链前置 |
| 3.3、3.4 自动/人工结果 | 第一条主链和关闭/人工样例可复用；旧partial/质量失败及未验分支保留，不回填旧Run或重调输入 |
| 4.2、4.3 总体独审/归档 | 本次阶段交接独审只覆盖本轮产物；完整change未结束，不代替最终独审或归档条件 |

外部HTTP Tool仍是[设计](../architecture/third-party-search-contract.md)：真实厂商method/path/auth/字段/时间/响应合同未指定，独立connectors查询服务未迁入，不自动实施假设adapter、发外部查询或新增模型。深度工具的not_ingested、厂商/Feed、持续图同步、算法/质量及可用性等已有边界继续放在[原问题清单](upstream-issues.md)，不另建任务树。

后续阶段发布以实际选入的差异包为单位，保留tenant/权限、预算、unknown和积压保护。当前交接不改变运行开关、不发布，也不为发布准备再做一次全量冻结或重跑全部模型路径。机器摘要见[交接回执](../handoff/investigation-stage-handoff-20261022.json)。

本轮结束独审：未参与编写的stage_handoff_audit限定**ACCEPT，0剩余阻塞**。独立核对原证据、36份原件/副本/归档及manifest、Git基线、无私有环境/HTTP观察、导航与链接；README遗留“下一项分诊”已修正并确认。OpenSpec strict和diff检查通过；本轮仅文档/保版检查，无新业务测试。审查不构成完整change完成、常驻准入或此前C2发布批准。
