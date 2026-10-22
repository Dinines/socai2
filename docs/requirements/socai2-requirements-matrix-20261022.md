# socai2 标书功能需求逐条评估矩阵

2026-10-22。配套 [模块评估与推进文档](../operations/tender-requirements-assessment-20261022.md)。本矩阵从 [需求原件](AI%20SOC2.docx) 直接提取第 3.3 节 35 个子组、164 条功能细项，保留原文和 REQ-P 定位，重新评估当前 socai2；没有沿用旧 SOCAI 的覆盖状态。第 2 章目标、架构/技术选型、第 4 章技术及第 5 章成效见主文，不计入这 164 条。

原件 SHA-256：`18880085144dbe2222a1eb8a17539b3bf1c7b452a23b1fa680d1a467869f2697`。Pnnn 是原件正文 XML 段落序号，不是页码。源码、代表实测和交付范围按行限定，不按条数计算完成率。

“已满足子项”只覆盖行内已验行为；“部分满足”仍有需求条件未完成；“未满足”有明确缺口或失败；“未验收”表示证据不足，不断言源码不存在；“范围外待交付”仍是标书要求，由其他模块或后续阶段承担。当前已部署与本地未发布状态详见主文第 5 节；本地链图/两处工具修正不能当作当前线上功能。

表中下一步是后续建议，不授权本轮新代码、模型、消息、厂商动作或部署。所有旧失败、worker OFF、restore 5/15 与 R02 0/17 保持。

| 模块 | 子组 | 功能细项 |
| --- | --- | --- |
| 日志采集与管理 | 4 | 17 |
| 智能检测与去噪 | 5 | 22 |
| 攻击链构建与调查 | 8 | 42 |
| 处置方案与响应管理 | 5 | 20 |
| 安全态势可视化 | 7 | 37 |
| 系统管理 | 6 | 26 |
| 合计 | 35 | 164 |

## 3.3.1 日志采集与管理

### 多源数据接入

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p139"></a>[REQ-P139](ai-soc2-requirements.md#p139) 支持通过 Syslog UDP/TCP 接收防火墙、IPS、网络设备及其他安全设备日志； | 范围外待交付 | **上游采集**：当前已有告警入口不证明Syslog UDP/TCP采集；由数据接入模块交付。 | [职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p140"></a>[REQ-P140](ai-soc2-requirements.md#p140) 支持通过 REST API 对接奇安信天擎 EDR 等终端安全产品； | 范围外待交付 | **上游/厂商**：未有奇安信天擎真实API接入证据；先确定厂商版本、接口与样例。 | [职责边界](../operations/alert-processing-scope.md)、[外部工具设计](../architecture/third-party-search-contract.md) |
| <a id="req-p141"></a>[REQ-P141](ai-soc2-requirements.md#p141) 支持接入资产信息、漏洞信息、组织信息，支持配置资产重要等级等上下文数据； | 部分满足 | **上游＋服务端**：资产/权限/漏洞只读视图与评分已有合成实证；真实组织/资产同步和完整配置待交付。 | [PG上下文](../operations/2c-processing-context.md) |
| <a id="req-p142"></a>[REQ-P142](ai-soc2-requirements.md#p142) 提供数据源配置、启停控制、连接测试和接入状态监控。 | 未验收 | **平台接入管理**：已有连接配置不等于数据源启停、测试和监控闭环；需接入模块与管理端联合验收。 | [职责边界](../operations/alert-processing-scope.md)、[官方与实现对照](../operations/alert-function-alignment.md) |
| <a id="req-p143"></a>[REQ-P143](ai-soc2-requirements.md#p143) 边界设备探针采集的进程、网络、服务及敏感配置信息。 | 范围外待交付 | **上游/探针**：探针需指定厂商支持；当前调查工具或UEBA不能替代设备采集。 | [职责边界](../operations/alert-processing-scope.md) |

### 日志解析与标准化

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p145"></a>[REQ-P145](ai-soc2-requirements.md#p145) 对不同厂商、不同类型日志进行字段提取、格式转换和标准化映射； | 范围外待交付 | **上游规范化**：source-v1接收合同不代表不同厂商原始日志解析已完成。 | [职责边界](../operations/alert-processing-scope.md)、[Fusion与B1](../operations/integrity-b1.md) |
| <a id="req-p146"></a>[REQ-P146](ai-soc2-requirements.md#p146) 统一时间、IP 地址、主机、账号、进程、文件、域名、URL 等关键字段； | 部分满足 | **上游＋服务端**：告警身份/正文/时间已保留；所有日志实体类型及端到端标准化尚未验收。 | [Fusion与B1](../operations/integrity-b1.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p147"></a>[REQ-P147](ai-soc2-requirements.md#p147) 对无法自动识别的数据支持人工配置解析模板； | 范围外待交付 | **上游规范化**：未交付完整人工解析模板工作流，按上游范围保留需求。 | [职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p148"></a>[REQ-P148](ai-soc2-requirements.md#p148) 对解析失败、字段缺失和数据异常情况进行记录和提示； | 部分满足 | **上游＋服务端**：告警schema/DLQ保护已有；原始解析错误和人员提示不由此全部覆盖。 | [分诊机制](../architecture/triage.md)、[官方与实现对照](../operations/alert-function-alignment.md) |
| <a id="req-p149"></a>[REQ-P149](ai-soc2-requirements.md#p149) 保留原始日志，确保标准化数据能够追溯至原始记录。 | 部分满足 | **上游＋服务端**：告警raw_event与首次材料可追溯；全量原始日志存储及回查仍依赖上游。 | [Fusion与B1](../operations/integrity-b1.md)、[full配套实测](../operations/full-support-migration.md) |

### 数据质量与上下文补充

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p151"></a>[REQ-P151](ai-soc2-requirements.md#p151) 对重复、缺失、异常和格式错误的数据进行识别； | 部分满足 | **上游＋服务端**：告警身份去重、坏schema和缺失/null保护已验；全部数据质量规则未验收。 | [Fusion与B1](../operations/integrity-b1.md)、[分诊机制](../architecture/triage.md) |
| <a id="req-p152"></a>[REQ-P152](ai-soc2-requirements.md#p152) 根据 IP、主机名、设备标识等信息关联资产； | 部分满足 | **上游＋服务端**：PG资产上下文/告警实体关联已有；真实CMDB匹配和多标识覆盖待交付。 | [PG上下文](../operations/2c-processing-context.md)、[链图本地实测](../operations/attack-chain-path-local-20261021.md) |
| <a id="req-p153"></a>[REQ-P153](ai-soc2-requirements.md#p153) 展示数据来源、采集时间、解析状态情况。 | 部分满足 | **服务端＋前端**：部分来源/时间/状态有持久字段；采集/解析状态完整展示未交付。 | [Fusion与B1](../operations/integrity-b1.md)、[结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |

### 日志检索与调用服务

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p155"></a>[REQ-P155](ai-soc2-requirements.md#p155) 支持按资产、账号、IP、域名、文件、进程和事件类型检索； | 部分满足 | **查询服务**：参数化实体/进程/网络等查询已接；所有字段组合、来源和文件类型检索未完整验证。 | [full配套实测](../operations/full-support-migration.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p156"></a>[REQ-P156](ai-soc2-requirements.md#p156) 支持查看原始日志、标准化字段及关联上下文； | 部分满足 | **查询服务＋前端**：告警原文、湖仓结果与上下文可读；全部原始日志及界面尚未验收。 | [Fusion与B1](../operations/integrity-b1.md)、[full配套实测](../operations/full-support-migration.md)、[结果与版本交接](../operations/investigation-stage-handoff-20261022.md) |
| <a id="req-p157"></a>[REQ-P157](ai-soc2-requirements.md#p157) 为检测规则、大模型研判和调查智能体提供统一日志查询能力； | 部分满足 | **查询服务**：API SQL和typed工具可供调查使用；多个数据类仍not_ingested，厂商合同待落实。 | [full配套实测](../operations/full-support-migration.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[外部工具设计](../architecture/third-party-search-contract.md) |
| <a id="req-p158"></a>[REQ-P158](ai-soc2-requirements.md#p158) 支持检索结果导出。 | 未验收 | **查询服务＋前端**：现有查询和报告读取不等于日志检索结果导出；需明确导出对象与权限。 | [full配套实测](../operations/full-support-migration.md)、[职责边界](../operations/alert-processing-scope.md) |

## 3.3.2 智能检测与去噪

### 多源告警统一管理

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p166"></a>[REQ-P166](ai-soc2-requirements.md#p166) 统一接入 EDR、IPS、防火墙等安全产品产生的告警； | 部分满足 | **上游＋服务端**：已有统一告警合同与真实HTTP/Kafka链；指定厂商输入未实际接通验证。 | [Fusion与B1](../operations/integrity-b1.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p167"></a>[REQ-P167](ai-soc2-requirements.md#p167) 接收平台根据原始日志、IOC 或攻击行为特征自主生成的告警； | 部分满足 | **上游＋服务端**：已有告警可被受理；平台原始检测由其他模块承担，不能宣称检测产出已验。 | [职责边界](../operations/alert-processing-scope.md)、[Fusion与B1](../operations/integrity-b1.md) |
| <a id="req-p168"></a>[REQ-P168](ai-soc2-requirements.md#p168) 对不同来源告警进行标准化、分类和统一展示； | 部分满足 | **服务端＋前端**：source-v1、分类与API已有；统一展示属于前端交付。 | [Fusion与B1](../operations/integrity-b1.md)、[分诊机制](../architecture/triage.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p169"></a>[REQ-P169](ai-soc2-requirements.md#p169) 支持按照等级、来源、资产、时间、状态和事件类型查询； | 部分满足 | **告警API**：等级/状态/类别等可过滤；search未执行，来源/资产/时间区间缺少参数。后续定向补齐。 | [告警查询源码](../../services/api/app/api/v1/endpoints/alerts.py)、[现有问题登记](../operations/upstream-issues.md) |

### 平台检测能力

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p171"></a>[REQ-P171](ai-soc2-requirements.md#p171) 支持基于资产指纹、开放端口、运行服务、软件版本及CVE特征的内网资产安全扫描； | 范围外待交付 | **扫描模块**：风险上下文、UEBA和TI均不替代内网资产/CVE扫描。 | [职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p172"></a>[REQ-P172](ai-soc2-requirements.md#p172) 支持常见漏洞扫描、执行范围、运行周期及结果处置的配置管理； | 范围外待交付 | **扫描模块**：扫描范围、周期与结果管理未由当前告警迁移交付。 | [职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p173"></a>[REQ-P173](ai-soc2-requirements.md#p173) 支持对多个单独风险较低的行为进行组合分析。 | 部分满足 | **检测＋关联**：RBA/共享实体关联和UEBA信号有基础；不证明多低风险行为形成复合攻击识别。 | [Fusion设计](../architecture/fusion.md)、[UEBA实证与边界](../architecture/ueba.md) |
| <a id="req-p174"></a>[REQ-P174](ai-soc2-requirements.md#p174) 对黑盒设备日志的异常分析：网络外联、持久化等。 | 范围外待交付 | **上游/探针检测**：黑盒网络外联/持久化数据与检测未交付，相关占位工具不能代替。 | [职责边界](../operations/alert-processing-scope.md)、[full配套实测](../operations/full-support-migration.md) |

### 告警去重与聚合

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p176"></a>[REQ-P176](ai-soc2-requirements.md#p176) 根据时间窗口、告警类型、资产、账号、IP 等信息识别重复告警； | 部分满足 | **Fusion**：来源身份去重与固定窗口/实体关联已验；并非所有指定字段可组合匹配。 | [Fusion与B1](../operations/integrity-b1.md)、[Fusion设计](../architecture/fusion.md) |
| <a id="req-p177"></a>[REQ-P177](ai-soc2-requirements.md#p177) 将短时间内大量相同或相似告警归并为一个告警组； | 部分满足 | **Fusion**：Incident聚合已有；固定实体/战术归组不等于相似内容语义聚合。 | [Fusion与B1](../operations/integrity-b1.md)、[Fusion设计](../architecture/fusion.md) |
| <a id="req-p178"></a>[REQ-P178](ai-soc2-requirements.md#p178) 对同一资产、同一账号或同一攻击行为相关的告警进行关联； | 部分满足 | **Fusion＋调查**：同实体关联与PG候选链可用；同一行为的跨实体证据关联仍不足。 | [Fusion设计](../architecture/fusion.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p179"></a>[REQ-P179](ai-soc2-requirements.md#p179) 支持配置聚合时间窗口、匹配字段和归并规则； | 部分满足 | **Fusion**：窗口可配，匹配字段/归并键固定；不能宣称完整规则可配置。 | [Fusion设计](../architecture/fusion.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p180"></a>[REQ-P180](ai-soc2-requirements.md#p180) 保留归并前的原始告警，避免去噪造成证据丢失。 | 已满足子项 | **告警持久化**：新source-v1不同来源独立行并保原文与关联已有实证；旧legacy历史未重建。 | [Fusion与B1](../operations/integrity-b1.md) |

### AI 辅助研判

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p182"></a>[REQ-P182](ai-soc2-requirements.md#p182) 利用安全微调模型理解告警名称、描述和上下文； | 部分满足 | **分诊＋模型**：真实模型解释告警与上下文已有；安全SFT及中文业务效果没有本项目验收证据。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[人工调查实测](../operations/integrity-investigation-r01.md) |
| <a id="req-p183"></a>[REQ-P183](ai-soc2-requirements.md#p183) 提取 IP、域名、账号、文件、进程、哈希值等关键实体； | 部分满足 | **分诊＋调查**：规则/模型可提取实体；exe误判域名已出现，全部实体类型正确性未过。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p184"></a>[REQ-P184](ai-soc2-requirements.md#p184) 辅助判断告警真实性、潜在危害和进一步调查价值； | 部分满足 | **分诊**：分类、理由、自动升级已有；时间/授权及内容质量失败保持。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[分诊机制](../architecture/triage.md) |
| <a id="req-p185"></a>[REQ-P185](ai-soc2-requirements.md#p185) 对单点告警进行可信度评分和误报可能性分析； | 部分满足 | **分诊**：模型confidence和Fusion信号可用；不代表已校准的误报概率或完整准确率。 | [分诊机制](../architecture/triage.md)、[Fusion设计](../architecture/fusion.md) |
| <a id="req-p186"></a>[REQ-P186](ai-soc2-requirements.md#p186) 输出研判结论、判断依据、风险等级和待核实事项； | 部分满足 | **分诊＋报告**：有结论/理由/分数与缺证内容；已出现无据确认，不能认定正确完整。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[人工调查实测](../operations/integrity-investigation-r01.md) |

### 告警评分与优先级排序

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p188"></a>[REQ-P188](ai-soc2-requirements.md#p188) 综合告警可信度、资产重要性、漏洞情况、威胁情报和行为异常程度进行风险评分； | 部分满足 | **Fusion＋上下文**：资产/漏洞/历史IOC与UEBA部分评分已验；不同score语义不统一，常驻UEBA融合未开。 | [PG上下文](../operations/2c-processing-context.md)、[UEBA实证与边界](../architecture/ueba.md)、[Fusion设计](../architecture/fusion.md) |
| <a id="req-p189"></a>[REQ-P189](ai-soc2-requirements.md#p189) 对告警进行高、中、低等级划分和优先级排序； | 部分满足 | **告警API**：severity及排序可用；priority排序按等级/时间，不等于统一综合风险排序。 | [告警查询源码](../../services/api/app/api/v1/endpoints/alerts.py)、[Fusion设计](../architecture/fusion.md) |
| <a id="req-p190"></a>[REQ-P190](ai-soc2-requirements.md#p190) 展示影响评分的主要因素； | 部分满足 | **评分＋前端**：部分评分理由/贡献可读；全部因素端到端展示与业务解释待验。 | [PG上下文](../operations/2c-processing-context.md)、[Fusion设计](../architecture/fusion.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p191"></a>[REQ-P191](ai-soc2-requirements.md#p191) 支持将高风险告警升级为安全事件并启动调查流程。 | 部分满足 | **自动调查＋事件管理**：自动Run调查已发生；Fusion Incident不等于具完整人员生命周期的Case，事件交接仍需明确。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[对象与图边界](../architecture/attack-chain-path.md) |

## 3.3.3 攻击链构建与调查

### 调查任务触发

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p201"></a>[REQ-P201](ai-soc2-requirements.md#p201) 接收异常进程、可疑文件、恶意网络连接、单点告警和告警组等输入； | 部分满足 | **调查入口**：Alert/Case输入已接；独立进程/文件/连接及告警组的全部受理合同未验。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p202"></a>[REQ-P202](ai-soc2-requirements.md#p202) 支持由高风险告警自动触发或由安全人员手动发起调查； | 部分满足 | **自动/人工调查**：自动C2与人工R01有实证；常驻未开、完整质量未过，不是只能手工调查。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[人工调查实测](../operations/integrity-investigation-r01.md) |
| <a id="req-p203"></a>[REQ-P203](ai-soc2-requirements.md#p203) 根据事件类型、风险等级和已有上下文生成调查目标； | 部分满足 | **调查编排**：有策略选择、领域路由及deep工具选择；完整目标与风险/上下文合同未验。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[分诊机制](../architecture/triage.md) |
| <a id="req-p204"></a>[REQ-P204](ai-soc2-requirements.md#p204) 支持安全人员限定调查资产、账号和时间范围。 | 未满足 | **调查范围**：尚未形成资产/账号/绝对UTC窗口在API→工具→结果的统一强制约束。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[外部工具设计](../architecture/third-party-search-contract.md)、[现有问题登记](../operations/upstream-issues.md) |

### 调查任务规划与协同

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p206"></a>[REQ-P206](ai-soc2-requirements.md#p206) 根据调查目标拆解日志检索、资产核查和行为分析等任务； | 部分满足 | **调查编排**：Deep根据返回继续选工具；默认四节点固定，不是完整可审任务规划与动态分解。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[官方与实现对照](../operations/alert-function-alignment.md) |
| <a id="req-p207"></a>[REQ-P207](ai-soc2-requirements.md#p207) 根据不同任务调用相应的调查工具或专项智能体； | 部分满足 | **调查编排**：工具执行及Router选域已观察；部分数据后端缺失，专业分支没有取证循环。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[full配套实测](../operations/full-support-migration.md) |
| <a id="req-p208"></a>[REQ-P208](ai-soc2-requirements.md#p208) 支持任务执行状态、结果和异常情况记录； | 部分满足 | **Run与事件**：逐步状态/结果/错误已有持久记录；兜底completed和partial表达仍有差距。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[结果与版本交接](../operations/investigation-stage-handoff-20261022.md) |

### 告警上下文采集

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p210"></a>[REQ-P210](ai-soc2-requirements.md#p210) 自动收集告警发生前后的相关日志； | 未满足 | **事件查询**：现有typed工具多按now()-hours查询，不能完整兑现告警发生前后窗口及来源覆盖。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p211"></a>[REQ-P211](ai-soc2-requirements.md#p211) 获取涉及资产、账号、进程、文件和网络连接信息； | 部分满足 | **上下文/工具**：告警/资产/账号及部分进程网络资料可用；文件/进程树等来源与字段不完整。 | [PG上下文](../operations/2c-processing-context.md)、[full配套实测](../operations/full-support-migration.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p212"></a>[REQ-P212](ai-soc2-requirements.md#p212) 查询资产标签、位置、相关漏洞及历史事件； | 部分满足 | **上下文/工具**：PG资产/漏洞/既往告警及湖仓补查已接；位置标签与真实资料覆盖未全验。 | [PG上下文](../operations/2c-processing-context.md)、[full配套实测](../operations/full-support-migration.md) |
| <a id="req-p213"></a>[REQ-P213](ai-soc2-requirements.md#p213) 检索同类告警和相关安全活动； | 部分满足 | **关联查询**：PG既往告警、调查候选链可用；语义同类/全部相关活动识别未验收。 | [Fusion设计](../architecture/fusion.md)、[链图本地实测](../operations/attack-chain-path-local-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p214"></a>[REQ-P214](ai-soc2-requirements.md#p214) 形成可供后续分析的事件上下文集合。 | 已满足子项 | **上下文Bundle**：同Run上下文集合及实际模型输入已证；各子源缺失/不可用仍显式保留。 | [调查知识消费](../operations/integrity-b2b3.md)、[链图本地实测](../operations/attack-chain-path-local-20261021.md) |

### RAG 知识增强

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p216"></a>[REQ-P216](ai-soc2-requirements.md#p216) 检索企业内部或已有的历史事件报告、处置记录和应急预案； | 部分满足 | **知识服务**：默认runbook/playbook/sop路径已有；实际历史报告/处置记录全类型消费尚未证明。 | [调查知识消费](../operations/integrity-b2b3.md)、[KB检索源码](../../services/api/app/api/v1/endpoints/knowledge_base.py) |
| <a id="req-p217"></a>[REQ-P217](ai-soc2-requirements.md#p217) 检索 ATT&CK、CVE、威胁情报及安全分析知识； | 部分满足 | **知识/TI**：ATT&CK、IOC及部分知识可用；CVE等知识覆盖与所选路径实际消费不齐。 | [调查知识消费](../operations/integrity-b2b3.md)、[full配套实测](../operations/full-support-migration.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p218"></a>[REQ-P218](ai-soc2-requirements.md#p218) 为攻击行为解释、调查步骤和响应建议提供参考； | 部分满足 | **知识采用**：片段进入真实模型与建议已证；模型曾将知识背景当本案观察，正确采用未过。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[引用与身份接线](../operations/integrity-citations-tools.md) |
| <a id="req-p219"></a>[REQ-P219](ai-soc2-requirements.md#p219) 展示知识内容的来源、版本和关联程度；。 | 部分满足 | **知识溯源**：来源、文本hash、引用解析已有；完整版本/相关度展示与可靠引用待补。 | [调查知识消费](../operations/integrity-b2b3.md)、[引用与身份接线](../operations/integrity-citations-tools.md)、[KB检索源码](../../services/api/app/api/v1/endpoints/knowledge_base.py) |

### 分布式调查分析

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p221"></a>[REQ-P221](ai-soc2-requirements.md#p221) 提取并验证事件中的 IOC； | 部分满足 | **IOC工具**：提取及增强调用可运行；exe误提、无provider与历史弱证据不等于IOC已验证。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[full配套实测](../operations/full-support-migration.md) |
| <a id="req-p222"></a>[REQ-P222](ai-soc2-requirements.md#p222) 分析异常进程的父子关系、执行参数和关联文件； | 未满足 | **终端取证**：process_tree为not_ingested；告警中的进程文本不足以兑现真实父子/文件联合分析。 | [full配套实测](../operations/full-support-migration.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p223"></a>[REQ-P223](ai-soc2-requirements.md#p223) 分析账号登录、权限使用和横向访问行为； | 部分满足 | **身份取证**：认证查询已本地修正可执行；OAuth/邮箱等占位，权限使用/横移来源不齐。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[full配套实测](../operations/full-support-migration.md) |
| <a id="req-p224"></a>[REQ-P224](ai-soc2-requirements.md#p224) 分析源 IP、目标 IP、端口、域名及网络通信关系； | 部分满足 | **网络取证**：网络查询和实体字段已有；真实通信证据、端口/域名关联覆盖未完整验证。 | [full配套实测](../operations/full-support-migration.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p225"></a>[REQ-P225](ai-soc2-requirements.md#p225) 关联相同资产、账号、文件或网络指标涉及的其他告警； | 部分满足 | **关联调查**：同主机/账号/IP候选可查；文件与跨实体行为关联未完整验收。 | [链图本地实测](../operations/attack-chain-path-local-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p226"></a>[REQ-P226](ai-soc2-requirements.md#p226) 分析可能的攻击入口、持续驻留、横向移动和数据外传行为； | 部分满足 | **行为调查**：已有模型对可能行为的分析；入口/驻留/横移/外传所需来源和分析有效性未完整验证，假设不能写成确认事实。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p227"></a>[REQ-P227](ai-soc2-requirements.md#p227) 识别可能受到影响的其他资产和账号。 | 部分满足 | **影响分析**：图可提供潜在关联候选；blast经Technique扩展，不能当确认受影响资产账号。 | [链图本地实测](../operations/attack-chain-path-local-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md)、[现有问题登记](../operations/upstream-issues.md) |

### 证据校验与冲突处理

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p229"></a>[REQ-P229](ai-soc2-requirements.md#p229) 校验关键实体之间是否存在实际关联； | 部分满足 | **证据校验**：可信PG投影保来源；实体共现不等于实际行为关系，独立关联校验尚不足。 | [链图本地实测](../operations/attack-chain-path-local-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p230"></a>[REQ-P230](ai-soc2-requirements.md#p230) 校验攻击行为的时间顺序和逻辑关系； | 未满足 | **证据校验**：现有时间线/groundedness没有完整校验时间顺序、授权和逻辑，旧失败仍在。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[自动关闭与调查](../operations/integrity-autonomy-r01.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p231"></a>[REQ-P231](ai-soc2-requirements.md#p231) 将关键结论关联至原始告警或日志； | 部分满足 | **证据溯源**：原告警、工具、工件可按Run查；尚未保证每个关键结论逐项指向原始记录。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[人工调查实测](../operations/integrity-investigation-r01.md)、[自动关闭与调查](../operations/integrity-autonomy-r01.md) |
| <a id="req-p232"></a>[REQ-P232](ai-soc2-requirements.md#p232) 对证据不足的结论标记为待核实，不直接纳入已确认攻击链。 | 未满足 | **结果语义**：已有缺源标记，但C2仍出现缺现场证据的confirmed结论，不能判通过。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[现有问题登记](../operations/upstream-issues.md) |

### 攻击链构建与展示

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p234"></a>[REQ-P234](ai-soc2-requirements.md#p234) 根据时间顺序构建攻击活动时间线； | 部分满足 | **时间线**：有时间字段和报告时间线；事件时间与处理时间混用等失败保留。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p235"></a>[REQ-P235](ai-soc2-requirements.md#p235) 展示资产、账号、进程、文件、IP 和域名之间的实体关系； | 部分满足 | **图＋前端**：Alert/Host/User/IOC/Technique关系本地已验；进程/文件等行为关系及展示未齐。 | [链图本地实测](../operations/attack-chain-path-local-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p236"></a>[REQ-P236](ai-soc2-requirements.md#p236) 映射 ATT&CK 战术、技术及相关攻击阶段； | 部分满足 | **ATT&CK映射**：技术标签和lookup可用；知识映射不等于已观察行为/攻击阶段。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p237"></a>[REQ-P237](ai-soc2-requirements.md#p237) 标记可能的初始访问入口和关键攻击节点； | 部分满足 | **攻击判断**：模型可提出入口假设；缺少行为证据校验，不应直接确认关键攻击节点。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[自动关闭与调查](../operations/integrity-autonomy-r01.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p238"></a>[REQ-P238](ai-soc2-requirements.md#p238) 展示攻击扩散路径及潜在影响范围； | 部分满足 | **路径/影响＋前端**：Case关系及Alert可达候选可用；没有完整传播因果路径或确认影响。 | [对象与图边界](../architecture/attack-chain-path.md)、[链图本地实测](../operations/attack-chain-path-local-20261021.md) |
| <a id="req-p239"></a>[REQ-P239](ai-soc2-requirements.md#p239) 支持对攻击链节点进行人工确认、修正和补充。 | 未验收 | **图API＋工作台**：未有攻击节点确认/修正/补充及其版本审计的完整交付证据。 | [对象与图边界](../architecture/attack-chain-path.md)、[职责边界](../operations/alert-processing-scope.md) |

### 综合调查报告生成

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p242"></a>[REQ-P242](ai-soc2-requirements.md#p242) 事件概述和风险等级； | 部分满足 | **报告**：概述和风险字段可生成持久读取；风险语义和内容质量未全过。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[自动关闭与调查](../operations/integrity-autonomy-r01.md)、[结果与版本交接](../operations/investigation-stage-handoff-20261022.md) |
| <a id="req-p243"></a>[REQ-P243](ai-soc2-requirements.md#p243) 已确认的异常行为； | 未满足 | **报告**：已有无据确认反例；不能保证确认异常均由当前事件证据支撑。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p244"></a>[REQ-P244](ai-soc2-requirements.md#p244) 关键实体和 IOC； | 部分满足 | **报告**：实体/IOC可输出；类型误提及来源不足仍会影响内容。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[人工调查实测](../operations/integrity-investigation-r01.md) |
| <a id="req-p245"></a>[REQ-P245](ai-soc2-requirements.md#p245) 攻击活动时间线； | 部分满足 | **报告**：有时间线产物；事件/调查处理时间及因果顺序未可靠核验。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p246"></a>[REQ-P246](ai-soc2-requirements.md#p246) 可能的攻击入口及传播路径； | 部分满足 | **报告**：有入口/传播假设文字，尚无可靠行为路径支撑全部表述。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p247"></a>[REQ-P247](ai-soc2-requirements.md#p247) ATT&CK 战术和技术映射； | 部分满足 | **报告**：ATT&CK内容可生成；观察、映射知识与推测阶段需严格区分。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p248"></a>[REQ-P248](ai-soc2-requirements.md#p248) 受影响资产和潜在影响范围； | 部分满足 | **报告**：影响字段与图候选可输出；范围过强、可达等于受影响的风险仍在。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[对象与图边界](../architecture/attack-chain-path.md) |
| <a id="req-p249"></a>[REQ-P249](ai-soc2-requirements.md#p249) 关键证据及其来源； | 部分满足 | **报告引用**：Run工件/知识标记已有；关键结论到具体原始事实的对应尚不完整。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[引用与身份接线](../operations/integrity-citations-tools.md)、[结果与版本交接](../operations/investigation-stage-handoff-20261022.md) |
| <a id="req-p250"></a>[REQ-P250](ai-soc2-requirements.md#p250) 后续调查及处置建议。 | 部分满足 | **报告建议**：结构建议及dry-run可交付；前序事实质量与建议适用性未完整验收。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |

## 3.3.4 处置方案与响应管理

### 智能处置方案生成

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p256"></a>[REQ-P256](ai-soc2-requirements.md#p256) 明确处置对象、执行动作、执行参数和操作顺序； | 部分满足 | **响应方案**：四节点Responder有结构计划；完整对象/参数/顺序及厂商实际可执行合同未验。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[Actions基础与dry-run](../operations/1g-service-baseline.md) |
| <a id="req-p257"></a>[REQ-P257](ai-soc2-requirements.md#p257) 分析可能产生的业务影响和操作风险； | 部分满足 | **响应方案**：模型输出业务风险/工作量；与真实资产业务影响的准确性未验。 | [人工调查实测](../operations/integrity-investigation-r01.md) |
| <a id="req-p258"></a>[REQ-P258](ai-soc2-requirements.md#p258) 展示处置建议所依据的事件证据、知识内容和响应预案。 | 部分满足 | **响应方案**：可提供知识和材料；建议到事件证据/预案逐项引用尚不完整。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[引用与身份接线](../operations/integrity-citations-tools.md) |

### 处置方案审核与调整

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p260"></a>[REQ-P260](ai-soc2-requirements.md#p260) 支持调整处置对象、范围、参数和执行顺序； | 未验收 | **后续响应＋前端**：原实现保留，完整方案对象/范围/参数/顺序调整未专项验收。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p261"></a>[REQ-P261](ai-soc2-requirements.md#p261) 支持处置方案保存、版本比较和审核确认； | 未验收 | **后续响应＋前端**：有审批/动作基础，不证明完整方案版本比较和审核闭环。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[官方与实现对照](../operations/alert-function-alignment.md) |
| <a id="req-p262"></a>[REQ-P262](ai-soc2-requirements.md#p262) 对证据不足、对象不明确或影响范围较大的操作强制进行人工审核。 | 部分满足 | **响应权限/审批**：dry-run与审批保护保留；缺证/大范围方案到强制人工审核的完整链未验。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[人工调查实测](../operations/integrity-investigation-r01.md) |

### 安全产品联动

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p265"></a>[REQ-P265](ai-soc2-requirements.md#p265) 隔离终端； | 未验收 | **厂商响应**：保留终端响应实现不等于指定EDR隔离已执行及回读；需受控目标与审批。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p266"></a>[REQ-P266](ai-soc2-requirements.md#p266) 终止恶意进程； | 未验收 | **厂商响应**：未做真实恶意进程终止验收；需厂商动作参数及审批。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p267"></a>[REQ-P267](ai-soc2-requirements.md#p267) 隔离或处置恶意文件； | 未验收 | **厂商响应**：未验指定厂商文件隔离/处置及结果回读。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p268"></a>[REQ-P268](ai-soc2-requirements.md#p268) 封禁 IP 地址、域名和 URL； | 未验收 | **厂商响应**：未验IP/域名/URL封禁完整合同；建议不等于动作成功。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p269"></a>[REQ-P269](ai-soc2-requirements.md#p269) 下发防火墙或网络访问控制策略； | 未验收 | **厂商响应**：未验防火墙/网络策略下发及影响控制，不能随调查发布开启。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p270"></a>[REQ-P270](ai-soc2-requirements.md#p270) 锁定、停用账号或发起凭据重置； | 未验收 | **厂商响应**：未验账号停用/锁定/重置的授权、执行和回读闭环。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p271"></a>[REQ-P271](ai-soc2-requirements.md#p271) 创建漏洞修复、资产排查和补充取证任务； | 未验收 | **响应任务**：原任务/工单能力保留，三类业务任务实际创建与跟踪未专项验收。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[官方与实现对照](../operations/alert-function-alignment.md) |
| <a id="req-p272"></a>[REQ-P272](ai-soc2-requirements.md#p272) 通知相关人员并派发处置任务。 | 未验收 | **通知/派单**：外部通知执行器存在不等于实际人员派单工作流已交付。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |

### 分级响应控制

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p274"></a>[REQ-P274](ai-soc2-requirements.md#p274) 自动化响应：适用于对象明确、影响可控、证据充分且已有成熟预案的低风险操作； | 未验收 | **响应治理**：受控自动关闭告警不同于自动厂商响应；低风险动作完整准入未验。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[Actions基础与dry-run](../operations/1g-service-baseline.md) |
| <a id="req-p275"></a>[REQ-P275](ai-soc2-requirements.md#p275) 半自动化响应：由平台生成方案及执行参数，经安全人员审核后一键执行； | 未验收 | **响应治理＋前端**：审批代码/dry-run基础可复用，审核一键执行与结果回读未验。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p276"></a>[REQ-P276](ai-soc2-requirements.md#p276) 人工响应：涉及核心业务系统、关键账号、大范围网络策略等高风险场景时，由人工决策和实施。 | 部分满足 | **响应治理**：本轮保持高风险需明确授权审批；完整人工决策/实施/记录流程未交付。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |

### 响应预案与流程编排

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p278"></a>[REQ-P278](ai-soc2-requirements.md#p278) 支持响应预案的创建、编辑、启用、停用和版本管理； | 未验收 | **Playbook**：原码/依赖保留，预案CRUD/启停/版本完整工作流未专项验收。 | [官方与实现对照](../operations/alert-function-alignment.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p279"></a>[REQ-P279](ai-soc2-requirements.md#p279) 支持配置事件类型、风险等级及触发条件； | 部分满足 | **Playbook**：事件/severity/tags匹配源码已有；实际配置触发调查缺Case/认证等接缝待核。 | [对象与图边界](../architecture/attack-chain-path.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p280"></a>[REQ-P280](ai-soc2-requirements.md#p280) 支持流程暂停、终止、重试和人工接管； | 未验收 | **Playbook/运维**：完整暂停/终止/重试/人工接管未专项验收；恢复专项按既定口径后置。 | [职责边界](../operations/alert-processing-scope.md)、[现有问题登记](../operations/upstream-issues.md) |

## 3.3.5 安全态势可视化

### 全局安全态势大屏

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p286"></a>[REQ-P286](ai-soc2-requirements.md#p286) 展示总体安全风险等级和实时告警情况； | 范围外待交付 | **前端/态势**：服务端有风险告警数据，不代表总体态势/实时大屏已交付。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p287"></a>[REQ-P287](ai-soc2-requirements.md#p287) 展示告警数量、等级分布和变化趋势； | 范围外待交付 | **前端/态势**：告警数据可复用，数量/等级/趋势展示需独立产品验收。 | [职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p288"></a>[REQ-P288](ai-soc2-requirements.md#p288) 展示高风险资产、重点漏洞和主要威胁类型； | 范围外待交付 | **前端＋资产漏洞**：PG上下文并非高风险资产/重点漏洞全量运营视图。 | [PG上下文](../operations/2c-processing-context.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p289"></a>[REQ-P289](ai-soc2-requirements.md#p289) 展示威胁来源和攻击目标分布； | 范围外待交付 | **前端/态势**：来源与目标字段存在不等于分布图展示完成。 | [职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p290"></a>[REQ-P290](ai-soc2-requirements.md#p290) 展示重大事件、处置进展和待关注事项。 | 范围外待交付 | **前端/事件**：事件/响应进展和关注事项大屏未由当前迁移交付。 | [职责边界](../operations/alert-processing-scope.md) |

### 告警运营工作台

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p292"></a>[REQ-P292](ai-soc2-requirements.md#p292) 提供多源告警统一列表； | 部分满足 | **告警API＋前端**：多源独立告警列表基础可用，实际统一工作台未交付。 | [Fusion与B1](../operations/integrity-b1.md)、[告警查询源码](../../services/api/app/api/v1/endpoints/alerts.py)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p293"></a>[REQ-P293](ai-soc2-requirements.md#p293) 支持按照时间、来源、等级、资产、类型和状态筛选； | 部分满足 | **告警API＋前端**：等级/状态等已有，来源/资产/时间过滤和search执行缺口明确；前端另交付。 | [告警查询源码](../../services/api/app/api/v1/endpoints/alerts.py)、[现有问题登记](../operations/upstream-issues.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p294"></a>[REQ-P294](ai-soc2-requirements.md#p294) 支持告警批量确认、分派和状态调整； | 未验收 | **告警运营＋前端**：有原操作接口不代表批量确认/分派/状态流程及界面完整验收。 | [官方与实现对照](../operations/alert-function-alignment.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p295"></a>[REQ-P295](ai-soc2-requirements.md#p295) 展示 AI 研判结果、可信度和风险排序； | 部分满足 | **告警API＋前端**：研判/可信度可读；综合风险语义和展示完整性未验。 | [分诊机制](../architecture/triage.md)、[告警查询源码](../../services/api/app/api/v1/endpoints/alerts.py)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p296"></a>[REQ-P296](ai-soc2-requirements.md#p296) 展示归并关系、威胁情报和相关上下文； | 部分满足 | **上下文＋前端**：归并、TI和上下文已有读取基础；工作台联动展示未交付。 | [Fusion与B1](../operations/integrity-b1.md)、[full配套实测](../operations/full-support-migration.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p297"></a>[REQ-P297](ai-soc2-requirements.md#p297) 支持从告警进入事件调查流程。 | 部分满足 | **调查入口＋前端**：人工Case接口/自动调查可用；完整从告警进入事件工作流界面未验。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[自动关闭与调查](../operations/integrity-autonomy-r01.md)、[对象与图边界](../architecture/attack-chain-path.md) |

### 事件调查工作台

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p299"></a>[REQ-P299](ai-soc2-requirements.md#p299) 展示事件基本信息、负责人、状态和处理时限； | 部分满足 | **Case＋前端**：Case/Run有状态基础；自动Alert→事件负责人/期限等工作流未完整交付。 | [对象与图边界](../architecture/attack-chain-path.md)、[结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p300"></a>[REQ-P300](ai-soc2-requirements.md#p300) 展示关联告警、资产、账号、漏洞和调查任务； | 部分满足 | **上下文＋前端**：关联告警/实体/部分漏洞数据可读；完整调查工作台未交付。 | [PG上下文](../operations/2c-processing-context.md)、[链图本地实测](../operations/attack-chain-path-local-20261021.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p301"></a>[REQ-P301](ai-soc2-requirements.md#p301) 展示智能体调查步骤、工具调用结果和当前进度； | 部分满足 | **Run＋前端**：events/artifacts可读，有真实记录；工作台进度与异常展示未交付。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p302"></a>[REQ-P302](ai-soc2-requirements.md#p302) 展示已确认事实、分析判断、模型推测和待核实事项； | 部分满足 | **结果语义＋前端**：部分缺证信息已有；事实/分析/推测未可靠分离，界面展示亦未验。 | [自动关闭与调查](../operations/integrity-autonomy-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p303"></a>[REQ-P303](ai-soc2-requirements.md#p303) 支持人工补充信息、调整调查范围和复核调查结论。 | 未验收 | **调查API＋前端**：人工补充、改范围、复核与版本审计未有完整证据；不是重新点investigate即可替代。 | [职责边界](../operations/alert-processing-scope.md)、[现有问题登记](../operations/upstream-issues.md) |

### 攻击链可视化

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p305"></a>[REQ-P305](ai-soc2-requirements.md#p305) 以时间轴展示攻击活动和关键行为； | 部分满足 | **时间线＋前端**：报告/事件时间线基础可读；真实攻击时序与图交互尚未满足。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[对象与图边界](../architecture/attack-chain-path.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p306"></a>[REQ-P306](ai-soc2-requirements.md#p306) 展示 ATT&CK 战术、技术和攻击阶段映射； | 部分满足 | **ATT&CK＋前端**：标签/知识映射有基础，观察到的攻击阶段与展示未完整验。 | [三路径真实实测](../operations/investigation-functional-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p307"></a>[REQ-P307](ai-soc2-requirements.md#p307) 以关系图展示资产、账号、进程、文件、IP 和域名之间的联系； | 部分满足 | **图＋前端**：部分实体关系本地已验；进程/文件及关系图产品未齐。 | [链图本地实测](../operations/attack-chain-path-local-20261021.md)、[对象与图边界](../architecture/attack-chain-path.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p308"></a>[REQ-P308](ai-soc2-requirements.md#p308) 标识已确认节点、推测节点和证据不足节点； | 未验收 | **证据状态＋前端**：暂无三类节点状态可靠校验、人工修改和展示的完整验收。 | [对象与图边界](../architecture/attack-chain-path.md)、[职责边界](../operations/alert-processing-scope.md)、[现有问题登记](../operations/upstream-issues.md) |

### 响应任务与审批面板

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p310"></a>[REQ-P310](ai-soc2-requirements.md#p310) 展示待审批、待执行、执行中、失败和已完成任务； | 未验收 | **审批/响应＋前端**：服务端状态代码保留；完整任务面板及真实执行状态未验。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p311"></a>[REQ-P311](ai-soc2-requirements.md#p311) 展示处置对象、执行动作、风险提示和业务影响； | 部分满足 | **响应计划＋前端**：dry-run对象/动作/风险可输出；业务影响与面板交付未验。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p312"></a>[REQ-P312](ai-soc2-requirements.md#p312) 支持查看方案依据、审批记录和执行结果； | 未验收 | **审批/响应＋前端**：未证明依据→审批→执行回读在同一任务完整可查。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |

### 报告与运营分析

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p314"></a>[REQ-P314](ai-soc2-requirements.md#p314) 生成事件调查报告和响应处置报告； | 部分满足 | **报告服务＋前端**：调查Markdown生成/保存/读取已证；真实响应处置报告尚未验收。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[Actions基础与dry-run](../operations/1g-service-baseline.md) |
| <a id="req-p315"></a>[REQ-P315](ai-soc2-requirements.md#p315) 生成安全运营日报、周报及阶段性分析报告； | 未验收 | **运营报告**：单Run报告不等于日报、周报和阶段运营分析；需固定指标与数据口径。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p316"></a>[REQ-P316](ai-soc2-requirements.md#p316) 统计告警数量、归并比例、误报情况和风险分布； | 未验收 | **运营分析**：告警记录和单例结果不能证明正确的聚合比例/误报统计。 | [Fusion与B1](../operations/integrity-b1.md)、[自动关闭与调查](../operations/integrity-autonomy-r01.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p317"></a>[REQ-P317](ai-soc2-requirements.md#p317) 统计事件发现、研判、调查和处置时长； | 未验收 | **运营分析**：部分Run耗时已有；发现/研判/调查/处置全过程计时未验。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p318"></a>[REQ-P318](ai-soc2-requirements.md#p318) 统计 MTTD、MTTR、任务成功率及自动化响应使用情况； | 未验收 | **运营分析**：MTTD/MTTR与使用比例需要完整生命周期，当前没有业务验收统计。 | [职责边界](../operations/alert-processing-scope.md)、[Actions基础与dry-run](../operations/1g-service-baseline.md) |
| <a id="req-p319"></a>[REQ-P319](ai-soc2-requirements.md#p319) 支持报告模板配置、人工审核和导出； | 部分满足 | **报告＋前端**：Markdown读取可用；模板管理、人审版本和全部导出工作流未验，PDF当前暂缓。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p320"></a>[REQ-P320](ai-soc2-requirements.md#p320) 支持从报告结论追溯至对应事件和证据。 | 部分满足 | **报告溯源**：Case/Run/工件可定位；逐结论追溯原始证据未完整保证。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[人工调查实测](../operations/integrity-investigation-r01.md)、[引用与身份接线](../operations/integrity-citations-tools.md) |

### AI 安全运营助手

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p322"></a>[REQ-P322](ai-soc2-requirements.md#p322) 支持通过自然语言查询高风险告警和安全事件； | 范围外待交付 | **AI运营助手**：查询API不等于自然语言告警/事件助手，需明确产品入口与权限。 | [职责边界](../operations/alert-processing-scope.md)、[官方与实现对照](../operations/alert-function-alignment.md) |
| <a id="req-p323"></a>[REQ-P323](ai-soc2-requirements.md#p323) 查询指定资产或账号近期的安全活动； | 部分满足 | **查询＋AI助手**：实体查询工具可复用；自然语言会话端到端体验尚未验收。 | [full配套实测](../operations/full-support-migration.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p324"></a>[REQ-P324](ai-soc2-requirements.md#p324) 查询告警研判依据、攻击过程和影响范围； | 部分满足 | **查询＋AI助手**：已有结果/工件可读；自然语言查询依据/经过/影响尚未验收。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p325"></a>[REQ-P325](ai-soc2-requirements.md#p325) 查询待审批、执行失败和超时任务； | 未验收 | **AI助手＋响应**：未验助手对待审批/失败/超时任务的正确权限检索。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p326"></a>[REQ-P326](ai-soc2-requirements.md#p326) 开展安全知识、历史案例和处置预案问答； | 部分满足 | **知识＋AI助手**：PG知识检索基础可用，完整多轮知识/案例/预案问答产品未验。 | [调查知识消费](../operations/integrity-b2b3.md)、[KB检索源码](../../services/api/app/api/v1/endpoints/knowledge_base.py)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p327"></a>[REQ-P327](ai-soc2-requirements.md#p327) 辅助生成调查报告、处置报告和运营报告； | 部分满足 | **报告＋AI助手**：调查报告已证；自然语言协作生成处置/运营报告未验。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p328"></a>[REQ-P328](ai-soc2-requirements.md#p328) 涉及实际处置操作时执行权限校验和人工确认。 | 未验收 | **AI助手＋响应**：现有权限/审批保护不等于助手实际处置链已验，须另作受控联动。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |

## 3.3.6 系统管理

### 用户、角色与权限管理

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p334"></a>[REQ-P334](ai-soc2-requirements.md#p334) 支持用户、用户组和角色管理； | 未验收 | **系统管理**：已有用户/角色基础不等于用户组及全管理工作流验收。 | [官方与实现对照](../operations/alert-function-alignment.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p335"></a>[REQ-P335](ai-soc2-requirements.md#p335) 支持基于角色的访问控制（RBAC）； | 已满足子项 | **服务端权限**：所验Case/Run/工具及新图读写权限、跨租户拒读有直接证据；不外推全部平台接口。 | [引用与身份接线](../operations/integrity-citations-tools.md)、[人工调查实测](../operations/integrity-investigation-r01.md)、[链图本地实测](../operations/attack-chain-path-local-20261021.md) |
| <a id="req-p336"></a>[REQ-P336](ai-soc2-requirements.md#p336) 支持账号状态和登录安全策略管理。 | 未验收 | **账号管理**：服务身份认证不等于账号状态和完整登录安全策略管理验收。 | [官方与实现对照](../operations/alert-function-alignment.md)、[职责边界](../operations/alert-processing-scope.md) |

### 数据源与接口管理

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p338"></a>[REQ-P338](ai-soc2-requirements.md#p338) 配置 Syslog、API 和其他数据接入接口； | 范围外待交付 | **接入管理**：当前服务端配置不代表Syslog及全部采集接口管理完成。 | [职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p339"></a>[REQ-P339](ai-soc2-requirements.md#p339) 管理外部安全产品和调查工具的连接信息； | 部分满足 | **工具/连接管理**：现有URL、reader和工具配置可用；指定厂商连接管理及界面未验。 | [引用与身份接线](../operations/integrity-citations-tools.md)、[外部工具设计](../architecture/third-party-search-contract.md) |
| <a id="req-p340"></a>[REQ-P340](ai-soc2-requirements.md#p340) 监控数据接入状态、同步时间、异常和中断情况； | 未验收 | **接入监控**：已有健康检查不能替代数据同步时间、中断与质量监控。 | [full配套实测](../operations/full-support-migration.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p341"></a>[REQ-P341](ai-soc2-requirements.md#p341) 支持接口调用频率、超时和失败重试配置； | 部分满足 | **调用控制**：分诊retry0/截止与部分工具限制已验；所有接口频率/重试配置未统一验收。 | [官方与实现对照](../operations/alert-function-alignment.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p342"></a>[REQ-P342](ai-soc2-requirements.md#p342) 对接口调用和数据访问行为进行审计。 | 部分满足 | **访问审计**：工具/部分API查询有记录；全平台数据访问和导出审计未完整验。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[官方与实现对照](../operations/alert-function-alignment.md) |

### AI 模型管理

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p344"></a>[REQ-P344](ai-soc2-requirements.md#p344) 统计模型调用量、响应时间、失败情况和使用场景； | 部分满足 | **模型管理**：实际usage/部分延迟与失败记录已证；无回复用量未知，不能标零或全统计完备。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p345"></a>[REQ-P345](ai-soc2-requirements.md#p345) 通过人工复核结果评估研判准确性和报告可用性； | 部分满足 | **模型质量评估**：代表案例已有独立质量评审并保留失败；产品化人审反馈/统计闭环及真实试点评估未验。评估失败不等于没有评估能力。 | [人工调查实测](../operations/integrity-investigation-r01.md)、[自动关闭与调查](../operations/integrity-autonomy-r01.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |
| <a id="req-p346"></a>[REQ-P346](ai-soc2-requirements.md#p346) 支持提示词模板的版本管理和效果比较； | 部分满足 | **提示词管理**：版本/pin与记录已有；同条件效果比较及管理流程未完整验收。 | [官方与实现对照](../operations/alert-function-alignment.md)、[人工调查实测](../operations/integrity-investigation-r01.md) |

### 知识库与智能体配置

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p348"></a>[REQ-P348](ai-soc2-requirements.md#p348) 管理知识来源、分类、权限、版本和更新时间； | 部分满足 | **知识管理**：PG来源/版本/权限与cutoff有基础；全类知识及管理生命周期未验。 | [调查知识消费](../operations/integrity-b2b3.md)、[KB检索源码](../../services/api/app/api/v1/endpoints/knowledge_base.py) |
| <a id="req-p349"></a>[REQ-P349](ai-soc2-requirements.md#p349) 支持知识内容更新、失效和人工审核； | 未验收 | **知识管理＋人审**：检索cutoff和内容版本不证明更新/失效/审核全流程可用。 | [KB检索源码](../../services/api/app/api/v1/endpoints/knowledge_base.py)、[调查知识消费](../operations/integrity-b2b3.md) |
| <a id="req-p350"></a>[REQ-P350](ai-soc2-requirements.md#p350) 配置智能体可调用的工具、权限和适用场景； | 部分满足 | **工具权限**：只读服务身份、工具schema/registry已有；指定场景全部工具实际合同未验。 | [引用与身份接线](../operations/integrity-citations-tools.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[外部工具设计](../architecture/third-party-search-contract.md) |
| <a id="req-p351"></a>[REQ-P351](ai-soc2-requirements.md#p351) 限制单次调查范围、调用次数和资源使用； | 部分满足 | **预算/范围**：普通分诊持久额度与unknown保护已验；调查范围和Deep软预算越界问题未解。 | [预算与unknown保护](../operations/3a-triage-budget.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p352"></a>[REQ-P352](ai-soc2-requirements.md#p352) 保存智能体任务规划、工具调用和结果生成记录。 | 部分满足 | **调查审计**：调用、材料、结果记录已有；完整任务规划/所有入口状态仍不齐。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[三路径真实实测](../operations/investigation-functional-20261021.md) |

### 系统监控与运维

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p354"></a>[REQ-P354](ai-soc2-requirements.md#p354) 监控平台服务、接口、任务、存储和模型运行状态； | 部分满足 | **运维**：所迁服务健康和部分模型/任务记录已有；完整平台状态监控未验。 | [full配套实测](../operations/full-support-migration.md)、[结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p355"></a>[REQ-P355](ai-soc2-requirements.md#p355) 展示系统容量、资源使用和异常情况； | 未验收 | **运维＋前端**：依赖资源/接口可用不等于容量、资源、异常视图已交付。 | [职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p356"></a>[REQ-P356](ai-soc2-requirements.md#p356) 支持任务失败、接口异常、数据中断等运行告警； | 未验收 | **运维**：失败记录与日志不等于运行告警实际投递和处置闭环。 | [职责边界](../operations/alert-processing-scope.md)、[现有问题登记](../operations/upstream-issues.md) |
| <a id="req-p357"></a>[REQ-P357](ai-soc2-requirements.md#p357) 提供必要的参数配置、日志查询和运维管理能力。 | 部分满足 | **运维**：Compose/配置/日志和回执可用；完整运维管理、恢复等按后续范围验收。 | [full配套实测](../operations/full-support-migration.md)、[职责边界](../operations/alert-processing-scope.md)、[现有问题登记](../operations/upstream-issues.md) |

### 安全审计

| 原文定位与要求 | 当前判断 | 责任与后续重点 | 证据或源码 |
| --- | --- | --- | --- |
| <a id="req-p359"></a>[REQ-P359](ai-soc2-requirements.md#p359) 记录用户登录、查询、导出和配置修改行为； | 未验收 | **平台审计**：部分鉴权/访问记录有基础，全部登录、查询、导出和配置修改未专项验收。 | [官方与实现对照](../operations/alert-function-alignment.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p360"></a>[REQ-P360](ai-soc2-requirements.md#p360) 记录 AI 模型调用、智能体工具调用和生成结果； | 已满足子项 | **调查审计**：代表Run的模型可见输入输出、工具交接和生成结果已有记录；不宣称所有调用完整wire或隐藏推理。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[三路径真实实测](../operations/investigation-functional-20261021.md)、[人工调查实测](../operations/integrity-investigation-r01.md) |
| <a id="req-p361"></a>[REQ-P361](ai-soc2-requirements.md#p361) 记录处置方案生成、人工修正和审批过程； | 未验收 | **响应审计**：dry-run计划可存不等于人工修正及审批全过程已记录验收。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[人工调查实测](../operations/integrity-investigation-r01.md) |
| <a id="req-p362"></a>[REQ-P362](ai-soc2-requirements.md#p362) 记录响应动作、执行参数、操作人员和执行结果； | 未验收 | **响应审计**：未验真实厂商动作参数/人员/结果完整链。 | [Actions基础与dry-run](../operations/1g-service-baseline.md)、[职责边界](../operations/alert-processing-scope.md) |
| <a id="req-p363"></a>[REQ-P363](ai-soc2-requirements.md#p363) 支持按照用户、事件、时间和操作类型查询审计记录； | 部分满足 | **审计API**：Case/Run/events可读；按用户/事件/时间/操作类型全条件检索未验。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[官方与实现对照](../operations/alert-function-alignment.md) |
| <a id="req-p364"></a>[REQ-P364](ai-soc2-requirements.md#p364) 确保关键操作全过程可追溯。 | 部分满足 | **端到端审计**：调查局部可追溯；缺人审/真实响应全链，不能宣称关键操作全过程满足。 | [结果与版本交接](../operations/investigation-stage-handoff-20261022.md)、[Actions基础与dry-run](../operations/1g-service-baseline.md)、[现有问题登记](../operations/upstream-issues.md) |

## 核验范围

35 个子组与 164 条编号逐项对应本次原件，原文未删改；历史覆盖表未覆盖为新状态。主文、原回执和源码链接共同说明证据，不能用某条“已满足子项”外推整个模块符合标书。此表为需求与证据导航，不是新的实施任务树或产品验收证明。
