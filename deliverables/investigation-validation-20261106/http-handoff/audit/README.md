> 既有JSON接口字段审计原文；原文47/53操作仅指原审计时点。本批当前59操作，CSV接口/104列见[E54–E56](../endpoints.md#e54)；新增统计/12字段见[E57](../endpoints.md#e57)。

# HTTP 字段审计与当前增量

当前为53个操作、542个固定输出字段出现位置、28组动态结构，对应125项产品功能。E02/E26/E27已补齐列表筛选、排序与游标；告警/事件封套仅新增filtered_total和next_cursor，行字段及数据库结构保持。当前输入输出见[接口字段](interfaces.md)、[固定字段](response-fields.md)及[Swagger交接](../http-handoff/README.md)。运行证据见[本轮验收](../../../openspec/changes/archive/2026-11-13-query-investigation-lists/validation.md)。

以下是首次静态审计及Case增量的历史记录，其中docs1、43/47操作和当时缺口不代表当前部署；当前实现状态以交接包为准。

# 既有功能与HTTP交接遗漏核对

2026-11-12。本轮按负责人要求，先从现有页面设计整理需要的功能，再对照既有三份资料和现有代码审计接口。**原资料已覆盖主要功能分组、接口路径及存储来源；遗漏主要在HTTP动态返回、字段语义和不同接口之间的差异。** 本轮没有据接口数量扩大产品范围。

本轮只静态核对源码与文档，没有调用业务API、数据库或模型，没有权限测试，没有改业务代码或发布新文档版本。已部署Swagger docs1保持原样；本目录是本地审计补充，不能把它当成21已经同步。

## 先对齐功能范围

唯一产品功能清单继续使用[原逐页清单](../frontend-feature-list.md)，已集中为三类：

| 类别 | 功能项 | 已设计的页面与功能范围 |
| --- | --- | --- |
| 告警 | 22 | 列表/预览、概况、检测信息、分诊/解释/过程、人工判定及历史参考、对象/相关告警、事件/Case关联、时间线、原始数据、响应建议 |
| 事件 | 15 | 列表/指标/预览、管理、概览和当前诊断、时间线、关联图、成员告警、对象资产匹配、活动、进入/创建/关联Case |
| 调查 | 88 | Case列表、资料、故事、概览、历史、成员、关系图/探索、对象证据、人工任务、活动/评论附件、同案助手，以及单轮发现/分析/查询/图/报告 |

共125项。原型、服务页面、后端能力和验收状态仍分别记录。对照本轮指定资料，没有发现需要新增一个业务大类；已经列出的未实现功能仍是缺口，不能因有表、按钮或相似接口而核销。资产基础资料、人员目录及真实响应审批/执行由业务后端承接，不增加旧AiSOC平台功能。

## 原资料已有的内容，继续保留

| 原资料 | 已有内容 | 本轮处理 |
| --- | --- | --- |
| [F01–F28字段/接口/跳转附录](../frontend-data-navigation-contract.md) | 功能用途、关键字段、来源、J01–J14跳转及缺值处理 | 保留原附录，补充HTTP精确路径差异及D07语义；不以另一份新需求替换 |
| [原始OpenAPI](../../../docs/design/socai2-independent-api-v2.openapi.json) | 调查路径、请求方法、路径/查询/JSON参数、固定类型和枚举 | 静态对照现有43个路由，未发现路由遗漏；原导出保留来源，动态结构在审计补充展开 |
| [业务数据交接](../../../docs/investigation/socai2-page-data-handoff-20261106.md) | 字段来源、存储关联、分页、读取和保存后回查 | 保留数据解释；明确业务后端走HTTP，并补投影差异，不要求直连库 |
| [docs1接口交接包](../http-handoff/README.md) | 125项映射、43操作参数、合成输入输出和典型错误 | 继续作为已有操作说明；本轮补齐语义审计，尚未重新发布 |

## 审计发现与补齐位置

| 编号 | 遗漏或容易误接的地方 | 本轮明确的结论 | 文档落点 |
| --- | --- | --- | --- |
| A01 | 原OpenAPI许多输出仅为dict/任意对象；E18冻结材料成功响应甚至没有结构 | 固定响应按模型列出522个字段出现位置；另按实际select/装配整理28组动态结构，不用数据库全表直接冒充HTTP投影 | [固定字段](response-fields.md)、[动态结构](dynamic-fields.md) |
| A02 | Case材料/工件与A/I内容接口容易套同一包装 | Case工件用artifact；A/I用metadata；E31正文包装raw_json/ocsf_json/enrichment及content_text；E18直接返回冻结材料整行且含tenant_id，没有availability包装 | dynamic-fields的材料/工件小节 |
| A03 | 附录统一列run.limits，会使Case页面读取不存在的DTO字段 | Case RunView没有limits，读取execution_summary.limits或其实际计划工件；A/I TraceView.run是原行公开投影，可以含limits；精简StageRunView也不含limits | 已修原字段/跳转附录；[E12/E32审计](interfaces.md) |
| A04 | 同名字段/投影没有明确区分 | TriageView.confidence是0..1；SubjectView.triage.confidence_percent已乘100。Task读source_refs为EvidenceRef，写仅type/id。Case详情current_assessment.sources剔除内部字段，page_data.assessment.sources保留tenant_id；Case活动E17含operation_id而A/I活动E30剔除 | response-fields及dynamic-fields |
| A05 | 计算统计的实际字段与分母说明不够集中 | overall_stats平铺，无by_state；事件new_alerts_24h数事件，assets.total数对象资产匹配边；Case metrics不受队列筛选影响，但待分配/高等级/待人工三项仅统计new/in_progress，待分配还要求owner_id为空；高等级仅high，筛选total和当前页长度分开 | dynamic-fields的overall-stats/records-assets，固定CaseQueueMetrics |
| A06 | HTTP200与正文可用/完整性错误没有逐接口区分 | Case工件内容完整性失败抛409 artifact_integrity_invalid；A/I工件返回200但availability=content_integrity_mismatch、正文null；解释使用available/reason | dynamic-fields结尾，固定ArtifactContent/ContentView |
| A07 | D07取消独立问题管理后，结果仍有questions[].state，容易被理解为旧管理流程 | 这是当轮冻结内容的open/answered/unresolved/not_attempted状态，不增加负责人/关闭/跨轮合并；需要人工确认由用户建H任务 | 原附录补充；固定Question.state |
| A08 | 只看OpenAPI默认值不足以理解写入语义 | E04分类/期限都必传，null清空；E07是完整替换；E40 PUT需携带未改字段；completed有正文/范围条件；版本冲突保留输入后再确认；E13同步等待，未知先GET而非重派 | [43操作用途/输入/输出](interfaces.md)；已有请求示例继续复用 |
| A09 | 动态集合被截断后是否还能翻页未说明透彻 | 列表按各自游标/offset分页；Case Run内部成员/步骤/工件/结果有上限，当前无后续集合分页接口；sources/coverage截断时比较可能返回null | 原业务交接补充；固定字段、current-assessment |
| A10 | 3个服务操作没有独立页面子功能，容易反向添加需求 | E07成员完整替换、E36手动A分诊、E37手动I诊断属于现有支撑能力。125清单未单列删除成员或重跑A/I按钮；本轮不据此新增。E36/E37生产启用状态未核实 | interfaces目录及对应小节 |
| A11 | 文档有接口，容易被误认为功能已经完成 | Q发送/保存/采用仍501；Q.scope与adopt.reason尚无DTO；管理、探索、协作附件、真实响应等缺口仍保留；故事/对象浏览/全局Run目录需要组合 | 原125清单与interfaces实现边界 |
| A12 | 工件content_json含多种历史/厂商正文，无法用一个固定示例解释全部字段 | 固定HTTP外壳和已知动态投影逐项说明；正文按kind/schema_version及既有JSON合同读取。未知厂商字段保留，不在审计中猜字段或重写历史原件 | dynamic-fields“版本化正文” |

## 每个接口怎么查

[43操作审计](interfaces.md)逐项写明：对应功能、业务目的、源码路由、路径/查询/请求体字段、必填及约束、顶层输出、嵌套字段入口、动态字段和使用限制。它引用既有示例，不新建第二份互相冲突的OpenAPI。

[固定输出字段](response-fields.md)逐字段写类型/枚举、required、可空性、业务含义和已有语义/代码来源；[动态字段](dynamic-fields.md)补实际公开行、计算值、版本和截断。522是模型中的字段出现位置数，含多个DTO重复出现的字段，不是522个独立业务字段。

源路由与原OpenAPI对照结果、功能数和未绑定页面子项见[静态覆盖记录](coverage.json)。没有业务请求，不对生产当前开关、实际数据质量或页面验收作新结论。

## 已知实现缺口继续保留

告警/事件完整服务端筛选和管理、告警正式人工反馈写回、Case通用管理/结案重开、人工采用、Q、真实图探索与保存、完整Case评论附件、响应审批执行均不能按现有资料标为完成。故事、对象浏览、跨主体运行目录还需调用组合与页面接线。这里只对照并记录，不把它们变成新范围或安排本轮实现。

本项已完成未参与实现者的限定文档复阅，四项实际错述已修正。结论仅针对指定资料及现有HTTP实现，不宣称原设计绝无遗漏，也不替代运行或模型验收。


2026-11-12 Case管理增量：追加E44–E47及10个固定输出字段出现位置，当前47操作、532固定字段、28动态结构；原43操作审计继续有效。新增功能及验证见`manage-investigation-cases`，本审计文件仍只说明字段，不代替运行验收。
