# 调查模块逐项功能、数据与测试矩阵

2026-11-26。由4173功能盘点、调查核心数据规划及实际HTTP合同按原88个F编号合并。普通范围78项，其中6项含后置子范围；整项后置10项。全部为规划，**没有在本轮逐项执行或宣布通过**。

[总规划与整页迁移标准](investigation-test-plan-20261126.md) · [结构清单](../../../docs/operations/evidence/investigation-test-plan-20261126-01/function-test-matrix.json) · [完整接口字段目录](../../../docs/operations/evidence/investigation-test-plan-20261126-01/http-function-contracts.json)

接口采用调查服务完整路径；8181还经过平台转发，差距按每项记录。`connected`仅指源码/合同有能力，不代表当前页面通过。`partial`含缺字段、旧接线或外部依赖。所有写功能均需保存后独立读回；模型质量另验。

## 数据包速查

| 编号 | 内容 |
| --- | --- |
| `PKG_FROZEN` | 既有冻结状态与工件复用包 |
| `PKG_HOST_CANDIDATE` | 候选主机告警与活动输入包 |
| `PKG_CASE_WORKSPACE` | 同案工作区与成员变化包 |
| `PKG_HUMAN` | 普通人工任务、修订与备注包 |
| `PKG_RESULT_EVOLUTION` | 同案后轮、比较与采用包 |
| `PKG_EXPLORATION_EVIDENCE` | 对象、证据索引与探索状态包 |
| `PKG_FILES_AND_RESPONSES` | 附件、报告与已有响应回执包 |

## 逐页功能

## Case 列表与公共页头

### F09-01 四项案件指标

安排负责人和人工跟进。入口：案件列表的待处理案件概况，点击待分配、处理中、高严重程度或待人工跟进。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P5 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>符合各指标的案件<br>新建、处理中、已关闭和未知状态<br>未分配与已分配负责人<br>人工未完成任务<br>可与指标叠加的筛选字段<br>接口最小前提：固定列表包含正在处理、待分配、高等级及至少一个有未完人工任务的 Case。 |
| 覆盖情况 | 默认不随表格条件计数，各指标可重叠，关闭和未知按规格排除 |
| 测试操作/方法 | 独立按案件核卡片计数，带已有搜索条件切换指标，核结果集合与条件保留<br>接口核对：点一项指标核请求只替换 metric，保留其他条件。按既有列表回执对照指标与筛选后的总数。 |
| 实际接口 | `GET /api/v1/socai2/cases` |
| 关键字段/关系 | `metric`<br>`metrics.awaiting_assignment`<br>`metrics.in_progress`<br>`metrics.high_severity`<br>`metrics.awaiting_human`<br>`total`<br>按租户统计 Case。待人工跟进依据存在未完人工任务的 Case，列表项的 open_task_count 是任务数。 |
| 保存与读回 | 保存/读取来源：`cases`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases`<br>刷新案件列表并保持现有筛选。metrics 是全租户四项指标，total 是当前筛选总数。 |
| 页面通过标准 | 卡片给出案件数，点击切换指标，列表回到首页且保留无关条件<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 待分配、处理中、高严重程度、待人工跟进均按案件计数；点击替换指标条件，其他筛选保留<br>刷新只是读取，不代表后台自动调查；当前管理设置占位保持占位 |
| 实现差距/依赖 | 4173：原型按已加载案件计数，点新指标会清其他条件。保留基线规定的只替换指标。<br>8181：四个指标和服务端计数已有接线。需以真实总体范围核卡片数和指标切换后的其他条件。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/http-real-data-20261120-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-02 搜索筛选和分页

在真实案件库定位案件。入口：案件列表搜索框、添加筛选及表格页码。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P5 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>可区分标题与完整 ID 的案件<br>状态、等级、负责人身份及分配状态<br>至少两页的筛选结果<br>接口最小前提：至少有可区分标题、状态或负责人的固定案件，且一次有效筛选可以产生续页或验证末页。 |
| 覆盖情况 | 加载、无命中、分页、条件变化回首页 |
| 测试操作/方法 | 按标题和完整 ID 各找一案，叠加负责人和状态，翻页后改条件并核回首页<br>接口核对：对照已有完整筛选结果，核一次正常搜索和一档续页，检查不漏不重及总数与行数的关系。 |
| 实际接口 | `GET /api/v1/socai2/cases`<br>`GET /api/v1/socai2/people` |
| 关键字段/关系 | `q`<br>`handling_status`<br>`severity`<br>`owner_id`<br>`assignment_state`<br>`metric`<br>`classification`<br>`cursor`<br>`next_cursor`<br>`total`<br>`items[].case.id`<br>列表限定同租户。搜索按 Case 标题或完整 Case ID。游标根据当前筛选和排序使用。 |
| 保存与读回 | 保存/读取来源：`cases`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases`<br>`GET /api/v1/socai2/people`<br>切换条件重读第一页。保持同一组条件读下一页。 |
| 页面通过标准 | 列表显示标题或完整 ID 命中的同范围案件，显示当前条件及结果数<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按标题／完整 ID、状态、等级、负责人 ID、分配状态、指标查；换条件回首页<br>刷新只是读取，不代表后台自动调查；当前管理设置占位保持占位 |
| 实现差距/依赖 | 4173：原型对本地已载入集合筛选分页，负责人条件使用展示口径。真实名单与分页范围需单独确认。<br>8181：有关键词、状态、等级、负责人、分配状态和游标。完整 ID 与跨页重新查询待现场核。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>同租户业务人员目录 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/http-real-data-20261120-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-03 列选择与排序

按工作习惯阅读。入口：案件列表自定义列与可排序的列头。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P5 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>不同业务更新时间、创建时间与等级的案件<br>可排序字段与并列值<br>接口最小前提：不同更新时间或等级的两条已保存 Case，优先带一个排序同值用于确认顺序稳定。 |
| 覆盖情况 | 最少一列，升序、降序和清除排序 |
| 测试操作/方法 | 按三个指定维度各读一次排序，开关列后核案件身份及条件一致<br>接口核对：用一次合法升降序切换及一次列显隐核对见到的记录与请求参数。 |
| 实际接口 | `GET /api/v1/socai2/cases` |
| 关键字段/关系 | `sort_by`<br>`sort_order`<br>`cursor`<br>`items[].case.severity`<br>`items[].case.created_at`<br>`items[].case.business_updated_at`<br>同租户案件以服务端支持的列排序，列显隐为页面状态。 |
| 保存与读回 | 保存/读取来源：`cases`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases`<br>更改排序从第一页读取，显示列设置直接作用于当前页面数据。 |
| 页面通过标准 | 选列只影响显示，排序按照选定字段改变案件顺序<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 选择业务更新时间、创建时间或等级及升降序；列选择只改变显示，不改变数据<br>刷新只是读取，不代表后台自动调查；当前管理设置占位保持占位 |
| 实现差距/依赖 | 4173：原型使用客户端表格设置，联调需确认数据排序范围。<br>8181：有选列及业务更新方向切换。创建时间、等级的排序选择在现有列表未见对应接线。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 显示列选择 |
| 可复用证据 | `docs/operations/evidence/http-real-data-20261120-01/README.md`<br>`openspec/changes/archive/2026-11-13-export-investigation-lists/audit.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-08 日期范围与导出

按工作时段查找并交接案件。入口：案件列表日期范围和导出。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P5 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>业务更新时间与创建时间不同的案件<br>时间边界记录<br>多页命中<br>公开可导出列<br>接口最小前提：既有固定日期窗口覆盖多页的筛选集合，或复用原 CSV 精确回执。 |
| 覆盖情况 | 最近时段、自定义起止、无匹配及无效起止 |
| 测试操作/方法 | 用业务更新时间校验区间，切换列后导出并核列和跨页案件集合<br>接口核对：比对列表筛选全范围的 Case 身份、已选公开列及顺序，取正常导出一次。 |
| 实际接口 | `GET /api/v1/socai2/cases`<br>`GET /api/v1/socai2/cases/export` |
| 关键字段/关系 | `time_from`<br>`time_to`<br>`columns`<br>`sort_by`<br>`sort_order`<br>`total`<br>`next_cursor`<br>`Content-Disposition`<br>`X-Export-Count`<br>`X-Export-Observed-At`<br>CSV 和列表按同租户 Case 的业务更新时间及相同筛选排序。CSV 面向完整命中集。 |
| 保存与读回 | 保存/读取来源：`cases`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases`<br>`GET /api/v1/socai2/cases/export`<br>GET export 返回 CSV 附件。列表切换日期后仍用对应列表条件读取。 |
| 页面通过标准 | 筛选后的案件和所选列进入 CSV，覆盖全部符合条件案件<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 选择最近时段或自定义范围，E56按业务更新时间筛选并导出全部命中，可选公开列<br>刷新只是读取，不代表后台自动调查；当前管理设置占位保持占位 |
| 实现差距/依赖 | 4173：原型按本地日期及已加载集合生成 CSV。基线的业务更新时间和服务端全部命中需验。<br>8181：有业务更新时间筛选和导出调用。当前导出参数未带所选列，全集范围需正式核。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `openspec/changes/archive/2026-11-13-export-investigation-lists/audit.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-09 手动与自动刷新

保持列表便于持续查看。入口：案件列表刷新按钮和自动刷新开关。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P5 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>同查询条件的两个可读快照<br>已有筛选、页码、编辑焦点<br>接口最小前提：已知保存时间和状态的 Case 列表。 |
| 覆盖情况 | 手动、定时重绘、本地开关关闭 |
| 测试操作/方法 | 观察手动刷新时是否重读，单独核原型定时重绘保留条件和焦点<br>接口核对：核手动刷新产生一次正常 GET，保留筛选。自动刷新按 4173 现有交互核对。 |
| 实际接口 | `GET /api/v1/socai2/cases` |
| 关键字段/关系 | `items[].case.id`<br>`items[].case.business_updated_at`<br>`metrics`<br>`total`<br>`next_cursor`<br>页面刷新读取同一租户筛选。原型自动刷新是当前集合的展示行为。 |
| 保存与读回 | 保存/读取来源：`cases`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases`<br>手动刷新调用案件列表，展示同一筛选内实际读回的状态。 |
| 页面通过标准 | 列表更新读取或重绘显示，保持当前查询上下文<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 手动刷新重读；原型自动刷新定时重绘当前集合，不代表后台持续取新数据或自动调查<br>刷新只是读取，不代表后台自动调查；当前管理设置占位保持占位 |
| 实现差距/依赖 | 4173：原型手动是重绘，自动为定时重绘当前集合。自动调查和后台取新不从该开关推断。<br>8181：手动和定时读取已有接线，筛选弹窗、预览及创建时暂停自动读取。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 原型自动重绘 |
| 可复用证据 | `docs/operations/evidence/http-real-data-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-10 案件预览

不离开队列先了解案件。入口：案件行标题、预览图标或可打开的预览入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P5 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>可区分的相邻案件<br>摘要字段<br>预览身份和详情身份<br>接口最小前提：一个有已保存标题、状态和成员的现存 Case。 |
| 覆盖情况 | 已有案件、已失效案件、从预览进入详情 |
| 测试操作/方法 | 打开一案摘要并点进入资料，核身份及返回队列路径<br>接口核对：核列表行、路由参数与详情响应 Case ID 相同，并对照摘要字段。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases` |
| 关键字段/关系 | `items[].case.id`<br>`case.id`<br>`case.title`<br>`case.handling_status`<br>`case.owner_id`<br>`member_count`<br>`current_assessment`<br>`page_data`<br>选中行 Case ID 贯穿预览、关闭预览及打开同案详情。 |
| 保存与读回 | 保存/读取来源：`cases`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases`<br>打开预览和详情读取同一个 Case。刷新按同 ID 读回。 |
| 页面通过标准 | 右侧摘要及打开案件资料链接指向同一案件<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 从行／预览入口看摘要，再进入默认案件资料；保持选中案件身份<br>刷新只是读取，不代表后台自动调查；当前管理设置占位保持占位 |
| 实现差距/依赖 | 4173：预览面向同一主体，排序分组只影响队列位置。<br>8181：按 sel 取对应预览，详情链接进入同一案件资料。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 展开、关闭与返回预览 |
| 可复用证据 | `docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-11 调查运行与管理设置入口

提供跨案运行入口并说明占位边界。入口：案件列表「查看调查运行」与「案件管理设置」。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P5 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>跨主体运行目录可读记录<br>案件列表入口<br>接口最小前提：至少一条实际主体明确的现存 Run，优先复用目录历史回执。 |
| 覆盖情况 | 全局目录可达，管理设置为占位 |
| 测试操作/方法 | 从列表点运行入口并返回，源码确认设置为占位<br>接口核对：核入口进入统一目录且点选能到实际 Run。另核设置占位显示。 |
| 实际接口 | `GET /api/v1/socai2/analysis-runs`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}` |
| 关键字段/关系 | `items[].run_id`<br>`items[].subject_type`<br>`items[].subject_id`<br>`items[].detail_url`<br>`next_cursor`<br>全局调查入口定位到统一 Run 目录。每行保留实际主体和 Run。全局案件管理设置只是原型占位。 |
| 保存与读回 | 保存/读取来源：`cases`<br>`tasks`<br>读回：`GET /api/v1/socai2/analysis-runs`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>按目录行的 detail_url 打开主体对应轮次。 |
| 页面通过标准 | 前者进入独立运行目录，后者没有业务保存结果<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 查看调查运行进入全局目录；案件管理设置当前只是占位，不据按钮增加设置功能<br>刷新只是读取，不代表后台自动调查；当前管理设置占位保持占位 |
| 实现差距/依赖 | 4173：设置占位保持边界，不另立设置功能。<br>8181：全局目录有独立页面，当前案件列表未见 4173 的直达运行按钮。设置仍按占位边界。<br>HTTP：现有 8181 列表仍请求旧 Q08 路径。Case 和告警的页头 Run 上下文缺少本版通用接入证据。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 案件管理设置占位 |
| 可复用证据 | `docs/operations/evidence/run-directory-http-20261114-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>`docs/operations/evidence/incident-saved-diagnosis-read-20261126-01/independent-closeout.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-04 新建 Case

为明确材料建立工作区。入口：案件列表「创建」及告警或事件的加入调查新建入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P3、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>候选告警和事件<br>显式成员关系<br>新案分配回执<br>首轮 task、尝试与 Run 身份<br>接口最小前提：一组已批准的同来源选择及原建案首轮受理、Case、Run 和 Result 固定回执。 |
| 覆盖情况 | 至少一个合规告警或事件，受理可有 task 无 Run |
| 测试操作/方法 | 用已批准创建回执追到实际案和首轮任务，核不同阶段的页面落点<br>接口核对：优先复用既有一次正常建案 PG/HTTP/页面证据，核受理及完成各自时间和身份。后续需要补验只选一组。 |
| 实际接口 | `POST /api/v1/socai2/cases`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/alerts`<br>`GET /api/v1/socai2/incidents`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}` |
| 关键字段/关系 | `operation_key`<br>`title`<br>`alert_ids`<br>`incident_ids`<br>`primary_case_id`<br>`receiving_case_id`<br>`allocations[].case_id`<br>`allocations[].scope_revision`<br>`allocations[].initial_task.status_url`<br>同租户的显式选择经分配形成 case_alerts/case_incidents。首轮以实际接收 Case 及 initial_task.task_id 为准。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>先沿 allocations[].case_url 读实际案件，再用 initial_task.status_url 读任务。产生 Run 后沿 attempts[].run_url，Result 沿 results[].url。 |
| 页面通过标准 | 进入真实分配的案件资料和首轮任务，后续才出现 Run 和结果<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 输入名称并选择至少一项告警／事件；保存后打开实际新案及首轮任务，不能创建成功就报调查完成<br>Case 管理状态、调查执行状态与业务判定分开 |
| 实现差距/依赖 | 4173：4173 列表创建为占位，事件有原型新建/关联入口。局部演示不能证明首轮任务受理。<br>8181：列表新建和候选选择已接写入。实际分配、首轮 task 到页面的完整落点待核。<br>HTTP：原生建案及首轮已验证。8181 当前选择对话框仍取旧 receipt.case_id，需按实际分配和首轮任务身份联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-allocation-http-20261115-01/README.md`<br>`docs/operations/evidence/case-initial-http-20261115-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-05 资料页头与刷新

随时知道当前案件及管理状态。入口：案件详情公共页头和刷新入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P5 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>案件身份与管理字段<br>负责人名称或空态<br>显式事件关联<br>可空优先级<br>接口最小前提：一个带显式事件和已知负责人或真实未分配状态的 Case。 |
| 覆盖情况 | 当前同案、无优先级、未分配、零个或多个显式事件 |
| 测试操作/方法 | 进同一案件多个页签并刷新，核页头与显式事件链接，核无优先级留空<br>接口核对：对照同一请求的页头字段及事件跳转，未供优先级按合同空态核对。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/people`<br>`GET /api/v1/socai2/incidents/{incident_id}` |
| 关键字段/关系 | `case.id`<br>`case.title`<br>`case.severity`<br>`case.handling_status`<br>`case.owner_id`<br>`case.priority_value`<br>`case.priority_state`<br>`linked_incidents[].incident_id`<br>Case 页头和显式事件关系以当前保存值读取，负责人展示使用已有目录同一用户身份。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/people`<br>`GET /api/v1/socai2/incidents/{incident_id}`<br>刷新同 Case GET。已关联事件沿 incident_id 定位 E29。 |
| 页面通过标准 | 显示标题、状态、等级、负责人、可用优先级和事件链接，刷新仍定位同案<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 显示标题、等级、状态、负责人和显式关联事件；刷新读真实状态，未知优先级不造值<br>刷新只是读取，不代表后台自动调查；当前管理设置占位保持占位 |
| 实现差距/依赖 | 4173：原型公共刷新只重绘。实际读取范围和显式事件关系仍按合同核对。<br>8181：页头、刷新及显式关联事件已接详情。可空管理信息和事件链接需对照实际响应。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>同租户业务人员目录 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`docs/integration/subject-risk-pages-s4-20261120.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F23-04 管理 Case

调整责任与管理信息。入口：案件页头管理、结案和重开入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P3、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>可修改案件<br>当前版本<br>活跃或不明运行<br>未完任务<br>结案说明及活动记录<br>接口最小前提：一个可管理案件，带同租户可分配人。关案条件复用含已确认未完任务或阻断记录的固定回执。 |
| 覆盖情况 | 运行中和执行不明禁止结案，有未完成任务需提示并记录说明，重开不自动运行 |
| 测试操作/方法 | 正例保存后重读案例字段，按既有结案门禁及重开回执逐一核任务和 Run 状态<br>接口核对：复用已有一轮管理及关案/重开存取。对照阻断或确认的单一代表，后续只补现产品未验证的正常操作。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/management`<br>`PATCH /api/v1/socai2/cases/{case_id}/management`<br>`POST /api/v1/socai2/cases/{case_id}/close`<br>`POST /api/v1/socai2/cases/{case_id}/reopen`<br>`GET /api/v1/socai2/people`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>`GET /api/v1/socai2/cases/{case_id}/tasks` |
| 关键字段/关系 | `operation_key`<br>`expected_row_version`<br>`owner_id`<br>`handling_status`<br>`severity`<br>`severity_reason`<br>`tags`<br>`priority_value`<br>`priority_reason`<br>`blocking_runs`<br>`open_task_count`<br>`requires_open_task_confirmation`<br>`acknowledge_open_tasks`<br>`reason`<br>`case.row_version`<br>管理、关闭和重开以同一 case_id 的行版本及明确操作键保存。未完人工任务与仍运行的尝试有各自条件。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>读回：`GET /api/v1/socai2/cases/{case_id}/management`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>`GET /api/v1/socai2/cases/{case_id}/tasks`<br>保存后读 E44 管理、E03 详情与 E17 活动，核变更前后值、行版本及真实任务状态。 |
| 页面通过标准 | 案件资料和活动读到标题、说明、负责人、状态、等级、标签及操作结果<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 管理名称／说明、负责人、状态、等级和标签；运行中／执行不明不能结案；未完任务提醒后可说明理由结案且任务原状保留；人工重开不自动启动调查，D01 已确认<br>Case 管理状态、调查执行状态与业务判定分开 |
| 实现差距/依赖 | 4173：有管理表单和本地演示。D01 结案门禁及重开语义沿正式需求单独验。<br>8181：管理、资料变更、结案与重开有表单及命令。D01 的运行门禁和未完任务原状待按正式回执核。<br>HTTP：原生管理齐备。当前产品中案件负责人的正式正例及管理分支需按 Case 单独读回。<br>同租户业务人员目录 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-management-20261112-01/delivery-summary.json`<br>`docs/integration/subject-risk-pages-s4-20261120.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F14-01 跨页执行提示

切页后仍知道调查进行到哪。入口：案件各页公共执行横幅，从「查看进度」返回原任务或运行。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>保存的 task 及尝试状态<br>可空 run_id<br>原 Case 和 Run<br>本次错误码或限制<br>接口最小前提：一个曾只有受理且后来关联实际 Run 的原任务回执，另有已存失败记录可复用。 |
| 覆盖情况 | 已受理未有 Run、执行中、失败、执行不明，人工任务单独 |
| 测试操作/方法 | 从概览切资料和成员页，沿同 task 回到进度，核未分配 Run 时仍明确受理<br>接口核对：按原任务记录的受理及终态轮次核对页头和提示，保留每次 attempt 身份。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}` |
| 关键字段/关系 | `task_id`<br>`status`<br>`status_url`<br>`latest_run_id`<br>`active_step`<br>`attempts[].run_id`<br>`attempts[].run_url`<br>`results[].url`<br>记住同一 Case 的分析 task_id。受理后 Run 可为空。人工核实任务使用不同 API。 |
| 保存与读回 | 保存/读取来源：`analysis_attempts`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`results`<br>`run_steps`<br>`runs`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>跨页或恢复视图从原 status_url 读任务，存在实际 Run 后沿 run_url。 |
| 页面通过标准 | 跨页可用同 task 续读状态，有 Run 后查看其过程<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按原task_id找回受理、执行或失败状态；有Run后沿链接查看过程，人工任务另行展示<br>HTTP 202 只表示受理；有工件不等于调查或正文质量通过 |
| 实现差距/依赖 | 4173：原型横幅围绕已有 Run。先有 task、后有 Run 的可见档仍需联验。<br>8181：各页横幅主要读基线 Run。task 暂无 Run 时的跨页回查仍需明确。<br>HTTP：跨页提示仍需按主体分析任务状态完成产品接入，baseline_records 单独无法覆盖未产生 Run 的任务。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/analysis-task-http-20261114-01/README.md`<br>`docs/operations/evidence/analysis-task-times-s5-20261120-01/independent-acceptance.json`<br>`docs/operations/evidence/case-initial-http-20261115-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 案件资料

### F09-06 案件说明和范围概况

先理解背景，再深入调查。入口：案件资料的案件说明和范围概况卡片。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_HOST_CANDIDATE`<br>`PKG_CASE_WORKSPACE`<br>`PKG_FROZEN`<br>案件说明<br>当前成员、对象、证据及历史计数<br>正文和时间可空<br>完整性字段<br>接口最小前提：一个有说明、成员、显式事件和已存原件索引的 Case。 |
| 覆盖情况 | 有说明与无说明、可用计数、时间或证据未记录 |
| 测试操作/方法 | 逐卡与同案已有来源核范围和跳转，区分未知与实际无记录<br>接口核对：对照返回的实际可用计数、时间和目标跳转，缺供字段标记未供。记录截断边界。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}` |
| 关键字段/关系 | `case.description`<br>`member_count`<br>`members_truncated`<br>`linked_incident_count`<br>`case.created_at`<br>`case.business_updated_at`<br>`page_data.evidence`<br>`items[].run`<br>当前 Case 成员、显式事件、人工任务与历史分别来自所属关系。库存资产、证据索引及轮次输入版本分开计。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>案件概况读 E03，任务和历史沿各自集合。资产仅沿既有主体资产关联读取。 |
| 页面通过标准 | 说明、成员、对象、材料、调查数量和时间集中显示，卡片能进入相应页签<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 阅读说明、成员、资产、材料、记录数量和活动时间；进入成员／对象／历史<br>阶段标签仅说明检测涉及范围，不证明完整攻击链；去重和空态按合同 |
| 实现差距/依赖 | 4173：导入视图的证据计数以保存口径为准，原型对象指标不可替作资产真值。<br>8181：案件说明、范围、阶段及管理资料入口在同页。对象、证据、时间和运行总量要逐项对照供给。<br>HTTP：当前 Case 无全案独立资产数和统一材料计数合同。已有列表长度不能代替全量。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F10-01 案件分类与截止时间

支持管理标记和跟进时限。入口：案件资料管理信息中的分类与期限编辑。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P3、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>当前分类、期限和 null<br>操作者权限和行版本<br>一条已知过期版本回执<br>接口最小前提：一个有旧版本及更新后分类/到期日的保存回执，另可用现有未设置状态。 |
| 覆盖情况 | 未分类、未设期限、保存成功、版本冲突保留用户输入 |
| 测试操作/方法 | 编辑分类或期限后回读，复用单次旧版本回执核冲突结果<br>接口核对：对比保存之前与之后的实际字段、版本和可读空态。复用现有版本错误回执。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`PATCH /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/cases/{case_id}/activities` |
| 关键字段/关系 | `classification`<br>`due_at`<br>`source`<br>`source_note`<br>`expected_row_version`<br>`operation_key`<br>`row_version`<br>分类及期限写入同 Case 行并留活动，版本来自当前 Case。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>读回：`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>PATCH page-data 后读 GET page-data、Case 详情及活动，与写回的 row_version 对照。 |
| 页面通过标准 | 资料和列表同步读到保存后的分类和期限，过期版本不覆盖<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 保存分类、期限后重新读取；无值显示未分类／未设期限，版本冲突不能覆盖<br>Case 管理状态、调查执行状态与业务判定分开 |
| 实现差距/依赖 | 4173：原型提供字段和本地管理表现，真实版本控制由产品合同验收。<br>8181：有分类期限的独立编辑与版本写入。查回持久值及冲突状态仍待实证。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-management-20261112-01/delivery-summary.json`<br>`docs/operations/evidence/http-real-data-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F11-01 当前采用判断

确认案件当前认可什么。入口：案件资料的「当前案件判断」。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>当前采用记录与版本<br>来源 Result、人工修订或工件<br>形成及采用时间<br>有 Run 但未采用的案件<br>接口最小前提：有可回链模型 Result 的已采用 Case，或有明确人工版本引用的固定回执，另可复用尚无判断的案件。 |
| 覆盖情况 | 已有采用、尚无判断、来源暂不可读，形成和采用时间按供给区分 |
| 测试操作/方法 | 比较有采用和无采用两案对照，确认正文来自采用记录且跳转可核原来源<br>接口核对：依据保存的指针和来源身份核判断、形成/采用时间和业务判定。变更当前 history 选中项仍保持当前采用来源。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `case.current_assessment_id`<br>`current_assessment.value`<br>`current_assessment.sources[]`<br>`page_data.assessment.conclusion`<br>`page_data.assessment.formed_at`<br>`page_data.assessment.adopted_at`<br>`page_data.assessment.business_verdict`<br>`result.source_run_id`<br>单一当前采用指针关联同 Case 判断与原 Result、人工修订或工件。业务判定沿唯一已采用模型 Result。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`case_assessment_members`<br>`case_assessment_sources`<br>`case_assessments`<br>`result_members`<br>`results`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`<br>E03/E05 读采用身份，用原来源去 E14、E43、E15 或 E16。后续采用的写入和读回见 F11-03。 |
| 页面通过标准 | 展示保存结论、作者或采用来源及时间，保持当前采用指针<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 阅读结论、形成／采用时间和来源；没有就显示尚无判断，不取最近 Run 标题拼接<br>引用合法与正文真实分开；待复核不等于执行失败<br>未决问题保留原文/范围，不自动变成人工任务 |
| 实现差距/依赖 | 4173：导入路径读取已保存判断。无采用时不从近期运行补出结论。<br>8181：由 current_assessment 与页面投影读当前判断，区分系统说明。正式来源和时间待同案核。<br>HTTP：来源和业务判定字段可读。8181 当前采用、来源正文与缺项空态仍需同源联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/assessment-basis-sf06-20261120-01/README.md`<br>`docs/operations/evidence/assessment-source-http-sf06-20261120-01/README.md`<br>`docs/operations/evidence/c173-bounded-json-20261121-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F12-01 判断覆盖与依据变化

知道结论能否用于当前成员。入口：案件资料当前判断下的原范围、成员覆盖和依据状态。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>保存判断及采用时成员<br>后来加入或移除的成员<br>依据状态与可核材料<br>覆盖分子分母<br>接口最小前提：原判断形成后曾增加或移出成员、或材料变了的一案。若无真实实例用原受控回执。 |
| 覆盖情况 | 覆盖完整或部分、新成员未分析、current/stale/unverified |
| 测试操作/方法 | 用发生范围变化的保存记录核三种口径，旧判断和原范围仍可回查<br>接口核对：核旧判断保留、已覆盖/未覆盖列表与新鲜度理由。集合被截断时核不可得状态。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `current_assessment.members`<br>`current_assessment.members_truncated`<br>`current_assessment.scope_revision_changed`<br>`current_assessment.covers_current_members`<br>`current_assessment.uncovered_current_alert_ids`<br>`current_assessment.no_longer_current_alert_ids`<br>`current_assessment.input_freshness`<br>`page_data.assessment.validity`<br>`result.findings[]`<br>采用判断覆盖由保存的 Assessment 成员决定。当前 Case 范围、轮次冻结范围及材料新鲜度分别核对。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`case_assessment_members`<br>`case_assessment_sources`<br>`case_assessments`<br>`result_members`<br>`results`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`<br>E03 对照当前成员和采用原范围，E14/E43/E15/E16 读取原依据。变更后重新读 E03 和 E05。 |
| 页面通过标准 | 同一判断保留原采用范围，另显示该判断对当前范围的覆盖与依据检查<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 分开显示判断覆盖、尚未调查成员及依据 current／stale／unverified；保留旧判断并指出限制<br>引用合法与正文真实分开；待复核不等于执行失败<br>未决问题保留原文/范围，不自动变成人工任务 |
| 实现差距/依赖 | 4173：导入原型已有分开展示。正式总量和覆盖算法由核心确认。<br>8181：有依据状态和当前成员覆盖信息，需核采用时原范围、当前范围与已有覆盖的三方对照。<br>HTTP：候选投影已验，正式产品的覆盖、新鲜度及来源全文还需和同一 Case 对照。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/assessment-basis-sf06-20261120-01/README.md`<br>`docs/operations/evidence/assessment-source-http-sf06-20261120-01/README.md`<br>`docs/operations/evidence/c6-adoption-comparison-d5b-20261118-01/independent-final-review.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F12-02 回查判断来源

让判断可复核。入口：当前判断的来源 Result、工件和人工版本入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>采用来源类型和标识<br>Run/Result 对照<br>不可变工件<br>人工任务修订<br>受限或缺失状态<br>接口最小前提：固定来源至少一个真实可定位引用。多种来源可分别复用既有回执。 |
| 覆盖情况 | 来源可读、仅摘要、原件不可用或越界 |
| 测试操作/方法 | 各选一种真实来源从判断打开，核锁定版本，缺源或受限有明确提示<br>接口核对：对照原来源版本、父 Case 及 Run。当前任务已编辑时仍跟随原 revision_id。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `current_assessment.sources[].result_id`<br>`current_assessment.sources[].task_id`<br>`current_assessment.sources[].task_revision_id`<br>`current_assessment.sources[].artifact_id`<br>`current_assessment.sources[].run_id`<br>`result.source_run_id`<br>同 Case 来源由已保存指针绑定。人工来源用原 task_id/revision_id，Run 级工件用原 run_id，Case 级工件的 run_id 为空。 |
| 保存与读回 | 保存/读取来源：`case_assessment_members`<br>`case_assessment_sources`<br>`case_assessments`<br>`result_members`<br>`results`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`<br>Result 读 E14，人工版本读 E43，Run 工件读 E15，Case 工件读 E16。原告警或事件的阶段结果沿具体主体及 Run。 |
| 页面通过标准 | 进入形成时原 Run、固定人工版本或工件抽屉，错误留在来源位置<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 点击 Result、工件、人工版本回到形成时的记录；不能用今天的任务内容替换旧依据<br>引用合法与正文真实分开；待复核不等于执行失败<br>未决问题保留原文/范围，不自动变成人工任务 |
| 实现差距/依赖 | 4173：真实导入已有部分来源链。跨类型精确定位与返回应作为独立检查。<br>8181：来源抽屉能读取 Result、引用内容及指定任务版本。精确来源与无原件状态需联验。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/assessment-source-http-sf06-20261120-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F11-02 结论中的未解决问题

说明当前判断仍有哪些事实未查清。入口：案件资料当前采用来源的依据与未决项。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>采用 Result 的 questions/findings<br>人工作业原文及冻结范围<br>独立的执行停止原因<br>未保存问题的结果<br>接口最小前提：有未决问题和已回答问题的固定已采用 Result；任一缺少时复用对应候选回执。 |
| 覆盖情况 | 未解决、已回答或被撤回的事实结论，仅系统停止原因时保留执行语义 |
| 测试操作/方法 | 对照每一条问题的原文、状态和来源，核执行结束码在 Run 详情<br>接口核对：按原状态、文本、范围和来源读回。执行停止原因只在执行栏，后续普通人工任务走 F22-09。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `current_assessment.sources[].result_id`<br>`result.questions[].text`<br>`result.questions[].state`<br>`result.questions[].answer`<br>`result.questions[].scope`<br>`result.questions[].evidence_refs`<br>`result.questions[].limitations`<br>未决项属于指定来源 Result 的原范围。人工待办是另一个 Case 任务实体。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`case_assessment_members`<br>`case_assessment_sources`<br>`case_assessments`<br>`result_members`<br>`results`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`<br>E03 找采用来源后读 E14。原引用按 E43/E15/E16 查看。 |
| 页面通过标准 | 随采用判断显示未决项和范围，打开相应结果，任务仍需人工创建<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 随当前采用判断展示未解决问题及限制，回查对应调查；需要人工确认时由用户创建任务，不单独管理问题或计入任务待办<br>引用合法与正文真实分开；待复核不等于执行失败<br>未决问题保留原文/范围，不自动变成人工任务 |
| 实现差距/依赖 | 4173：问题、发现和限制随采用来源阅读，沿已确认的无独立问题队列方向。<br>8181：已读候选来源的未回答问题与限制。多类采用来源及已回答问题的独立表现需逐项核。<br>HTTP：候选已验采用来源投影，8181 的采用判定与未决项仍需用同一 Result 联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/assessment-basis-sf06-20261120-01/README.md`<br>`docs/operations/evidence/assessment-source-http-sf06-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F09-07 ATT&CK 阶段与详细信息

看成员检测涉及哪些阶段。入口：案件资料的 ATT&CK 阶段覆盖与管理资料。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_HOST_CANDIDATE`<br>`PKG_CASE_WORKSPACE`<br>`PKG_FROZEN`<br>成员告警和其检测战术标签<br>同一告警的多标签与重复标签<br>无标签成员<br>案件资料<br>接口最小前提：一个有保存检测标签和实际来源材料的 Case 成员。 |
| 覆盖情况 | 有检测阶段、来源未提供、同一告警有多阶段 |
| 测试操作/方法 | 按阶段对同案成员去重核计数，检查标签缺失及攻击链语义<br>接口核对：核成员、材料与已存标签同源。若页面做 Case 分组，沿已有产品定义核每告警计一次。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}` |
| 关键字段/关系 | `members[].alert_id`<br>`facts.id`<br>`derived.tactics[].label`<br>`derived.tactics[].alert_count`<br>`triage.attck_mappings`<br>`material.content_url`<br>从同案真实成员告警与其当前或冻结材料追溯标签。已确认的系统分诊映射按所属 A Run 读取。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>Case 详情链接到 E28 及该告警材料。历史轮次按冻结材料和指定 A Run 回查。 |
| 页面通过标准 | 同层级阶段卡以成员告警为计数单位，详细资料显示正式字段<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 同层级展示阶段、告警数及管理资料；阶段标签不证明完整攻击链<br>阶段标签仅说明检测涉及范围，不证明完整攻击链；去重和空态按合同 |
| 实现差距/依赖 | 4173：原型演示可读标签，验收需使用同源已保存检测标签。<br>8181：案件资料已有阶段组件和管理信息。需要同源成员检测标签正例核 count。<br>HTTP：Case 详情没有专属整体 ATT&CK 聚合。成员取数可复用，正式 Case 页面聚合列及来源待核。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F11-03 显式采用其他结果

有意改变当前案件判断。入口：案件资料查看当前判断后选择并确认采用其他结果。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>当前判断和候选 Result<br>候选范围、结论、未决项和依据<br>理由<br>未完成任务<br>版本和采用回执<br>接口最小前提：既有可采用的完整范围 Result 及尚未结束工作的一条已验证场景。 |
| 覆盖情况 | 旧与候选比较、未完工作、局部/过期范围、确认或取消 |
| 测试操作/方法 | 以已保存候选比较覆盖与依据，沿既有采用回执核当前指针和旧记录<br>接口核对：复用成功和原拒绝回执。核新旧指针、预览 token 及原任务、Run、状态的对照。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/results/{result_id}/adoption-preview`<br>`POST /api/v1/socai2/cases/{case_id}/results/{result_id}/adopt`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/assessments`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks` |
| 关键字段/关系 | `result_id`<br>`review_token`<br>`can_adopt`<br>`unfinished_tasks`<br>`unfinished_analysis_tasks`<br>`unfinished_runs`<br>`expected_review_token`<br>`operation_key`<br>`reason`<br>`acknowledge_pending_work`<br>`assessment_id`<br>`previous_assessment_id`<br>待采用 Result 和来源 Run 必须归同一 Case。通过资格、有效覆盖和预览版本后写入新 Assessment 并保留旧版。 |
| 保存与读回 | 保存/读取来源：`case_assessment_members`<br>`case_assessment_sources`<br>`case_assessments`<br>`result_members`<br>`results`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/assessments`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>先 GET adoption-preview，再 POST adopt。随后读取 E03、E64 和 E17，确认新当前判断、旧版本和活动。 |
| 页面通过标准 | 采用后案件资料展示新指针，旧判断及来源仍可回查<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 先比较旧判断与候选结论、未解决问题、覆盖和依据；填写理由并确认未完工作，采用后保留旧判断。局部或过期结果不能覆盖全案，任务/Run/处理状态保持<br>引用合法与正文真实分开；待复核不等于执行失败<br>未决问题保留原文/范围，不自动变成人工任务 |
| 实现差距/依赖 | 4173：4173 主要展示已采用结果，未找到直接的候选比对和确认入口。8181 已有采用弹窗，需求仍按 F11-03。<br>8181：有候选比较、范围确认和采用命令。旧记录与保存后采用指针待正式联验。<br>HTTP：原生采用已验。8181 当前对话框未使用服务端预览 token，提交体仍为旧合同。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-result-adoption-release-20261113-01/README.md`<br>`docs/operations/evidence/c6-adoption-comparison-d5b-20261118-01/independent-final-review.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 案件故事

### F20-01 事实与认识时间线

理解事情和调查怎样发展。入口：案件故事页的事实和工作记录时间线。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通部分纳入，所列子范围后置；普通告警/Run/人工修订时间线纳入；助手问答保存记录暂缓。；P1、P3、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>事件时间可空的成员告警<br>运行开始、结束及状态<br>已保存回答<br>人工完成时间和版本<br>接口最小前提：故事固定回执中存在告警、调查和至少一条人工完成事件，优先复用原有读取。 |
| 覆盖情况 | 有时间倒序、未知时间单列、活跃轮只显示进展 |
| 测试操作/方法 | 用同案不同类型记录核排序、无时间位置与活跃无结论表现<br>接口核对：核相对时序、无时间空态及运行中条目的实际状态。AI 保存记录不纳入现行可执行用例。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/story`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |
| 关键字段/关系 | `items[].kind`<br>`items[].occurred_at`<br>`items[].time_source`<br>`items[].alert`<br>`items[].run`<br>`items[].results`<br>`items[].task_revision`<br>`next_cursor`<br>故事按 Case 范围关联告警发生、Run 及保存 Result、完成人工修订。时间和来源身份沿原记录。 |
| 保存与读回 | 保存/读取来源：`alerts`<br>`results`<br>`runs`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/story`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>GET story 分页读取。按告警、结果、Run 或修订的实际身份回查。 |
| 页面通过标准 | 告警发生、调查开始/结束、保存回答及人工结果汇合并保留来源入口<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 倒序组合告警发生、Run 开始／结束、已保存回答和人工完成；无时间排后，活跃轮不提前给结论<br>共同对象只作关联线索；助手问答条目属于暂缓子范围 |
| 实现差距/依赖 | 4173：故事组合已记录事实与进展，未核运行时完整分页。<br>8181：故事直接消费分页时间线和来源类型。时间未知与进行中不出结论需用真实记录核。<br>HTTP：原生故事合同已验。8181 仍存在与旧参数和旧行结构绑定的读取。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-story-20261113-01/README.md`<br>`docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F20-02 搜索与等级筛选

从长故事找相关活动。入口：案件故事搜索和严重程度筛选。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>带告警名称和对象名称的成员<br>可分等级<br>筛选无命中组合<br>接口最小前提：同一故事有两条可凭标题、主机或账号区分的既有告警和等级覆盖。 |
| 覆盖情况 | 名称、主机/账号命中，无命中，组合筛选 |
| 测试操作/方法 | 按告警名、主机和账号验证故事匹配，再叠加等级并清空<br>接口核对：使用一组原生筛选读回核命中及重置，等级条件和结果类型按原合同观察。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/story` |
| 关键字段/关系 | `q`<br>`severity`<br>`cursor`<br>`limit`<br>`items`<br>`next_cursor`<br>`total`<br>搜索和等级限制当前 Case 故事读回。筛选不变更成员。 |
| 保存与读回 | 保存/读取来源：`alerts`<br>`results`<br>`runs`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/story`<br>换筛选用无 cursor 的 GET story，续页沿返回 cursor。 |
| 页面通过标准 | 只缩小故事阅读范围，原有成员和结果仍可经源入口访问<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按告警名、主机、账号及等级缩小阅读，不改变正式成员或已存历史<br>共同对象只作关联线索；助手问答条目属于暂缓子范围 |
| 实现差距/依赖 | 4173：原型对本案载入集合筛选，正式分页语义另核。<br>8181：关键词和等级已进入故事查询。告警名、主机和账号命中口径由传入字段与接口共同确定。<br>HTTP：8181 的 kind、severity_groups、offset 并非原生故事查询字段。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-story-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F20-03 单选／多选告警

结合焦点告警与本案其他告警的共同对象理解关联。入口：单击聚焦；复选集合独立用于已后置的提问范围。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>至少两条含共同对象的成员<br>分别关联和共用的调查<br>原告警详情<br>接口最小前提：现有故事含两个告警及对应调查输入，其中可复用有共有对象的记录。 |
| 覆盖情况 | 单选、多选、无匹配及移除选择 |
| 测试操作/方法 | 单击切换焦点后核活动详情、共同对象及包含该告警的调查；复选两条并清除，确认复选集合与焦点相互独立<br>接口核对：核焦点告警、本案其他成员及固定Run成员范围，不能按复选集合改成共有对象交集。若缺共同对象正例记录未验。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/story`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}` |
| 关键字段/关系 | `items[].alert`<br>`items[].run`<br>`items[].results`<br>`facts.id`<br>`section_urls.objects`<br>选中行绑定故事内真实 alert_id。共同对象和当轮范围沿已有原件证据回查。 |
| 保存与读回 | 保存/读取来源：`alerts`<br>`results`<br>`runs`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/story`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>打开告警用 E28，进入结果沿相应 Case/Run/Result 身份。 |
| 页面通过标准 | 右侧显示选中告警的对象及相关调查，原告警可打开<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 右侧看焦点告警、与本案其他告警的共同对象及包含此告警的调查；可开原告警<br>共同对象只作关联线索；助手问答条目属于暂缓子范围 |
| 实现差距/依赖 | 4173：复选集合与焦点独立，右栏以焦点告警计算。<br>8181：旧StorySelection按复选集合读取，须迁回焦点语义，不为旧交集额外开发合同。<br>HTTP：原生故事与告警读回可用，焦点告警与本案成员的共同对象、包含该告警的完整调查范围仍需明确正式读取。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 故事条目单选和多选 |
| 可复用证据 | `docs/operations/evidence/case-story-20261113-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F20-04 围绕条目或全案提问

让问题有明确上下文。入口：故事页全案、告警或活动条目的提问入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>具备告警、Run 结果、人工记录的同一案件<br>各来源的可选范围结构<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 意图打开、范围预填、人工可修改，等显式发送 |
| 测试操作/方法 | 只审入口和未来数据结构，恢复范围后核各入口只预填<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的全案或故事条目的提问结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 助手同案草稿出现所选全案、告警、结果或人工版本<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 带入全案、多条告警、某轮结果或人工结果至同案助手；打开和选择均不执行<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：保留原型入口，沿既定 AI 对话整项暂缓。<br>8181：故事已有带范围打开助手的接线。沿已确认的整项暂缓。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F20-05 回到结果和人工版本

从摘要追到形成依据。入口：故事条目的 Run、调查结果或人工历史链接。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>有多个版本的人工任务<br>所引用的 Run/Result<br>原记录身份和时间<br>当前与历史成员<br>接口最小前提：一条带结果的故事 Run 和一条有后续修订的旧完成人工事实。 |
| 覆盖情况 | 历史版本存在、缺源、范围后续变化 |
| 测试操作/方法 | 点开故事的调查和人工条目，核源身份与版本，修改后旧引用保持<br>接口核对：点选两种原行，核目标身份、原范围、显示时间及原文来源。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/story`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}` |
| 关键字段/关系 | `items[].results`<br>`items[].run`<br>`items[].task_revision`<br>`result.id`<br>`run.id`<br>`task_id`<br>`id`<br>故事内选中的结果或人工修订由其父 Case 与原版本唯一定位。 |
| 保存与读回 | 保存/读取来源：`alerts`<br>`results`<br>`runs`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/story`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>用 E14/E12 或 E43 打开详情。 |
| 页面通过标准 | 返回原轮次或特定任务修订，显示当时范围、时间和结果<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 点击指定 Run／任务修订，保留当时范围、时间与结果<br>共同对象只作关联线索；助手问答条目属于暂缓子范围 |
| 实现差距/依赖 | 4173：故事已有跳回记录。人工条目直达特定修订及返回上下文需核。<br>8181：故事和历史修订都有深链组件。逐条核故事目标是否带当时 Run 或 revision。<br>HTTP：服务端跳转身份已存，当前 8181 故事参数和版本跳转需要同源核对。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-story-20261113-01/README.md`<br>`docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 调查概览

### F14-02 活跃与待启动分开

不把排队当执行或丢失下一轮。入口：调查概览「当前工作」和待启动区。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>具有不同生命周期的分析 task<br>task 与尝试、Run 映射<br>终态或未知回执<br>待更新范围<br>接口最小前提：一个受理未启动回执和同类已运行或已结束回执，原 unknown 保留。 |
| 覆盖情况 | accepted 可无 Run、running、待启动、完成/失败、已收尾 unknown |
| 测试操作/方法 | 按冻结任务证据核活跃和待启动区，核终态下架及固定 Run 仍保留<br>接口核对：沿已存时序核区分待启动、活跃、终态。没有 Run ID 的任务只显示任务。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}` |
| 关键字段/关系 | `items[].task_id`<br>`items[].status`<br>`items[].active_step`<br>`items[].attempts`<br>`items[].latest_run_id`<br>`update_state`<br>Case 的分析任务可先存在而无 Run。失败尝试保留 Run 的 unknown 与本地结束信息。 |
| 保存与读回 | 保存/读取来源：`analysis_attempts`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`results`<br>`run_steps`<br>`runs`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>读主体任务页和原任务详情。已进入执行才按 attempts 中的实际 Run 查阅。 |
| 页面通过标准 | 活跃和待启动并行分区显示，历史保存 unknown 保留，已收尾不常驻活跃<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 分别显示accepted、running及终态；准备中可无Run，本地已收尾unknown不常驻执行中，原Run结果仍unknown<br>HTTP 202 只表示受理；有工件不等于调查或正文质量通过 |
| 实现差距/依赖 | 4173：原型能分开显示导入 Run 与 pending，真实 task 独立身份仍需核。<br>8181：已有活跃和待启动 Run 两类。受理但未产生 Run、已收尾 unknown 的 task 状态仍要对接正式来源。<br>HTTP：8181 仍有按 baseline_records 分类的概览，尚需按主体任务读回完成对照。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/analysis-task-http-20261114-01/README.md`<br>`docs/operations/evidence/analysis-task-times-s5-20261120-01/independent-acceptance.json`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F14-03 检查更新

判断当前材料是否需要新一轮调查。入口：调查概览的检查更新动作。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>可作比较的上一轮与当前范围/人工版本<br>检查回执<br>变化或 no_changes<br>接口最小前提：已有同案一组已完成快照与无变化检查，另有变更后续轮的固定回执。 |
| 覆盖情况 | 可检查、有变化、无变化，以及受理与读取错误 |
| 测试操作/方法 | 复用同案一次 no_changes 与一次有变化回执，比对任务后续和 Run 有无<br>接口核对：复用一次无变化和一次有效变化的保存链。检查任务身份、状态和是否存在后轮 Run。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`POST /api/v1/socai2/cases/{case_id}/investigations`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}` |
| 关键字段/关系 | `operation_key`<br>`mode`<br>`task_id`<br>`status`<br>`status_url`<br>`reason_code`<br>`latest_run_id`<br>`attempts`<br>`update_state`<br>Case 显式 check 写入分析任务。领取时依据保存的成员、材料与有效人工结果判定变化。 |
| 保存与读回 | 保存/读取来源：`analysis_attempts`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`results`<br>`runs`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>读取同一 status_url。无变化返回实际 skipped/reason_code，有变化沿 attempts/run/result 读回。 |
| 页面通过标准 | 提交后读分析 task，检查无变化可跳过，发现变化进入准备<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 提交检查后读取分析任务；无变化跳过，有变化由核心准备本轮材料<br>HTTP 202 只表示受理；有工件不等于调查或正文质量通过 |
| 实现差距/依赖 | 4173：原型读待更新及任务演示，未找到正式检查更新入口。8181现有动作不能反推4173需求。<br>8181：已有准备调查操作。需确认当前连接是否承载 check/no_changes 和独立 task 合同。<br>HTTP：原生异步提交存在，当前 8181 检查入口仍有旧 prepare 接线。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-updates-20261115-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/analysis-task-http-20261114-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F14-04 启动调查

建案后调查所选材料，需要时明确再次调查。入口：新建有效案件后的首轮，以及调查概览显式再调查入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>合法案件分配<br>冻结输入、scope_revision 和 task<br>尝试、Run、交付与结果<br>接口最小前提：已有一案首轮受理至结果链，另可复用后续 rerun 受理回执。 |
| 覆盖情况 | 已受理、准备冻结、实际运行及结束 |
| 测试操作/方法 | 从既有建案受理或明确再次调查回执核任务到当轮冻结及结果<br>接口核对：按回执核受理、执行、冻结范围、Result 与读回 URL。对照 8181 是否使用当前异步入口。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`POST /api/v1/socai2/cases/{case_id}/investigations`<br>`POST /api/v1/socai2/cases`<br>`GET /api/v1/socai2/cases/{case_id}` |
| 关键字段/关系 | `allocations[].initial_task`<br>`operation_key`<br>`mode`<br>`task_id`<br>`status`<br>`status_url`<br>`attempts[].run_id`<br>`results[].url`<br>`run.input_artifact_id`<br>`result.source_run_id`<br>新案初轮随真实分配受理。已存在 Case 的再次调查用原生 investigations。任务、尝试、冻结 Run 与 Result 逐层绑定。 |
| 保存与读回 | 保存/读取来源：`analysis_attempts`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`results`<br>`runs`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>新案读 initial_task.status_url，后续提交读返回 status_url。待有关联时读 E12 及 E14。 |
| 页面通过标准 | 按首轮任务或新任务链接进入 Run 和结果，受理先于完成<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 新案登记首轮任务，后台冻结输入并执行；读取任务、Run和结果<br>HTTP 202 只表示受理；有工件不等于调查或正文质量通过 |
| 实现差距/依赖 | 4173：原型历史读取与本地启动演示不代表正式任务触发。当前实施合同单独对齐。<br>8181：已有建案及明确启动接线，当前界面有基于 Run 的入口。首轮分配与后续受理按独立 task 校验。<br>HTTP：生产 HTTP 已具备。8181 当前仍有退役 start 路径接线。后续只补正确入口的直接产品读回。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-initial-http-20261115-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/analysis-task-http-20261114-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F16-01 已有结果摘要

判断下一步应看哪一轮。入口：调查概览已有分析结果区域，打开某次完整调查。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>较早采用结果<br>新的成功、部分或失败运行<br>每轮保存摘要、问题、比较与限制<br>接口最小前提：同案一组有正式 Result 及可读失败尝试的固定历史。 |
| 覆盖情况 | 有结论与待核问题、失败/部分交付、当前采用单列 |
| 测试操作/方法 | 比较两轮结果卡和同轮完整详情，失败卡只显示实际已存内容<br>接口核对：核摘要、未决项和实际交付，失败没有 Result 时沿 Run 及已保存工件。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `items[].run.id`<br>`items[].result.id`<br>`result.conclusion`<br>`result.change_summary`<br>`result.questions[]`<br>`result.case_impact`<br>`run.stop_reason`<br>选定同 Case 的历史 Run 和 Result。当前采用判断单独沿指针读取。 |
| 保存与读回 | 保存/读取来源：`analysis_attempts`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`results`<br>`runs`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>先读 Case history，按其 Run 和 Result 身份直接取回正文。 |
| 页面通过标准 | 显示该轮保存的结论、变化和影响，详情仍读该轮原材料<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 先读结论（含未解决问题）、变化、影响，再开完整结果；不另设问题队列；失败轮保留已存材料，已有采用判断单列<br>HTTP 202 只表示受理；有工件不等于调查或正文质量通过 |
| 实现差距/依赖 | 4173：源于历史记录的概览卡，展示完整性与采用状态应分开。<br>8181：已有结果卡与详情读取。摘要、比较、影响和受限内容需同轮对照。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/assessment-basis-sf06-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F22-01 人工摘要与待办

知道还缺哪些人工确认。入口：调查概览人工摘要或案件资料待办区。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>同案不同行为状态的人工任务<br>任务摘要与完整记录<br>成员范围<br>接口最小前提：一个含待办和已完成/取消任务的已存 Case。 |
| 覆盖情况 | 未开始、进行中计待办，完成与取消保留历史 |
| 测试操作/方法 | 按未开始和进行中核待办数，打开一项核原任务<br>接口核对：按人工任务状态逐项对照徽标。核总数范围及进入同一任务。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases` |
| 关键字段/关系 | `items[].current.state`<br>`items[].id`<br>`total`<br>`next_offset`<br>`items[].open_task_count`<br>人工任务按 Case 和任务当前版本计数。待办采用未开始及进行中状态。 |
| 保存与读回 | 保存/读取来源：`analysis_attempts`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`results`<br>`runs`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases`<br>GET tasks 读分类及分页，任务详情用所选 id。 |
| 页面通过标准 | 显示待办数量、事项及任务详情入口<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 未开始／进行中计待办，完成／取消不计；进入任务详情，不把任务数写成案件数<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：这是任务数量，案件列表的人工待跟进指标仍按案件计。<br>8181：已有待办概要和人工任务链接。需核任务汇总数与真实状态。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-human-http-20261111-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F14-05 历史与故事入口

从当前工作切回演变过程。入口：调查概览「查看全部调查历史」和「查看案件故事」。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>同案的历史、故事及空案<br>导航身份<br>接口最小前提：同案同时有已保存历史轮次与故事条目。 |
| 覆盖情况 | 有历史或尚无记录，保持案件身份 |
| 测试操作/方法 | 从概览打开两个入口，核关联案件和返回路径<br>接口核对：核两个入口对应的实际请求和切换期间 Case ID。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/story` |
| 关键字段/关系 | `items[].run.id`<br>`items[].result.id`<br>`items[].kind`<br>`items[].occurred_at`<br>`next_cursor`<br>历史和故事在同一 Case 下用不同记录视图，沿原 Run 或修订身份回链。 |
| 保存与读回 | 保存/读取来源：`analysis_attempts`<br>`analysis_subject_state`<br>`analysis_tasks`<br>`results`<br>`runs`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/story`<br>历史入口读 E10，故事入口读 E65。 |
| 页面通过标准 | 分别进入同案调查历史列表和案件故事<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 全部历史进入轮次列表，故事进入事实时间线<br>HTTP 202 只表示受理；有工件不等于调查或正文质量通过 |
| 实现差距/依赖 | 4173：超页入口与运行详情下方的回链一并核对。<br>8181：案内历史和故事路由都存在，需按概览来源检查可达性及同案返回。<br>HTTP：两个入口均有原生读取。8181 故事入口仍带旧参数，历史和故事需按各自返回同案联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 同案页签和路由切换 |
| 可复用证据 | `docs/operations/evidence/case-story-20261113-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 调查历史

### F14-06 历史记录分类与选择

区分首次、更新和保存的 AI 结论。入口：调查历史的记录卡、运行选择器及直接 Run 链接。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>同案两轮及保存的问答记录<br>目标、类别、请求时间和范围<br>运行/结果身份及可选视图<br>接口最小前提：已保存的两轮 Case 历史，其中可包含无正式结果的正常失败尝试。 |
| 覆盖情况 | 首次、范围/版本更新、保存回答、失败、未知；切轮保留当前视图 |
| 测试操作/方法 | 从历史打开轮次，在查询或报告视图切到另一轮，核视图与 Run 同步<br>接口核对：核切换轮次及翻页不改变其他任务或当前采用指针，选中视图保持所读结果身份。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}` |
| 关键字段/关系 | `items[].recorded_at`<br>`items[].run.id`<br>`items[].run.trigger`<br>`items[].run.purpose`<br>`items[].run.scope_kind`<br>`items[].run.state`<br>`items[].result.id`<br>`next_cursor`<br>同案历史按真实 Run 或已存结果分类。告警/事件目录仍以自己阶段的主体 ID 读取。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`result_members`<br>`results`<br>`run_members`<br>`runs`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>GET history 沿 cursor 查所选轮次。Case 进 E12/E14，A/I 按各自所选 Run 读。 |
| 页面通过标准 | 列表展示原因、时间、原范围和状态，打开精确轮次，切轮保持阅读视图<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按目标、原因、时间、范围、状态选择指定轮次；切轮保留阅读视图<br>模型变化结论必须由新增事实/人工版本支持；没有证据就保留限制 |
| 实现差距/依赖 | 4173：原型用记录卡和选择器分类，尚无独立历史筛选需求声明。<br>8181：有案内历史、运行目录、选中上下文及固定 Run 嵌入。切轮保持原视图待核。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F15-01 状态、交付与投入

判断哪轮可用及为何未完整交付。入口：调查历史记录卡的执行指标和交付标签。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>成功、部分交付、失败和 unknown 历史<br>原计量与空字段<br>保存工件和停止原因<br>接口最小前提：有已知部分交付与实际用量的一轮，以及已有用量未知的固定回执。 |
| 覆盖情况 | 执行态、交付态、失败和 unknown 分立，耗时/用量可缺失 |
| 测试操作/方法 | 逐轮对照保存状态及计量，确保费用或用量未知没有显示成 0<br>接口核对：对照状态、交付、停止原因与计时。未知用量按原空态。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps` |
| 关键字段/关系 | `run.state`<br>`run.delivery_state`<br>`run.stop_reason`<br>`run.started_at`<br>`run.ended_at`<br>`duration_seconds`<br>`usage`<br>`analysis_counts`<br>`tool_calls`<br>`delivery`<br>一次 Run 的执行状态、服务保存交付、Result 和用量各有来源。输入或统计摘要用同一冻结 Run。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`result_members`<br>`results`<br>`run_members`<br>`runs`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>E12/E14 对照同一 Run 和 Result，必要时沿完整步骤核投入。 |
| 页面通过标准 | 卡片和详情显示该轮状态、完整性、停止及耗时/调用/Tokens<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 分开执行状态、完整性、停止原因、耗时、模型次数及 Tokens；未知值不记零<br>模型变化结论必须由新增事实/人工版本支持；没有证据就保留限制 |
| 实现差距/依赖 | 4173：原型有指标，旧导入的缺用量和结束原因展示需要按现行口径核。<br>8181：历史可进详情读状态、停止与耗时。目录层的模型次数及未知 token 表现需按实际供给确认。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/run-records-20261114-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F16-02 结果比较

看这次增加了什么认识。入口：调查历史选择有比较关系的新轮，打开其调查发现。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>至少两版结果<br>comparison_result_id 及比较文本/结构<br>后出且无关结果<br>原输入差集<br>接口最小前提：三轮固定回执，覆盖上一轮有结果以及上一轮无可比较结论。 |
| 覆盖情况 | 有明确比较、无比较、比较记录不可读或后续另有新结果 |
| 测试操作/方法 | 先核当轮比较身份，再刷新或切换较新轮，确认旧比较仍指原 Result<br>接口核对：对照比较链接和保存的对象身份，核空比较保持真实。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}` |
| 关键字段/关系 | `run.comparison_context`<br>`result.comparison_context`<br>`result.comparison_result_id`<br>`previous_run_url`<br>`comparison_result_url`<br>`result.change_kind`<br>`result.change_summary`<br>比较取系统冻结的 previous_run_id 和 comparison_result_id。前轮无可比较 Result 时仅保留原轮身份。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`result_members`<br>`results`<br>`run_members`<br>`runs`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>E12/E14 读固定链接，以实际前轮身份查阅。刷新保持选择。 |
| 页面通过标准 | 新增输入、发现和判断沿当轮保存的比较对象展示，可回查被比较的旧结果<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 以明确 comparison_result_id 比对新增输入、发现和判断；不随当前最新结果漂移<br>模型变化结论必须由新增事实/人工版本支持；没有证据就保留限制 |
| 实现差距/依赖 | 4173：原型已显示变化和比较摘要。显式比较 Result 绑定与缺失状态要单独验。<br>8181：已有比较概要及 comparison_result_id 深链，需核后续其他运行不会改变旧比较落点。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/c6-adoption-comparison-d5b-20261118-01/independent-final-review.json`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F12-03 历史范围与冻结引用

避免用当前成员误读旧结论。入口：历史卡及运行详情的当轮输入或工件引用。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>旧 Run 冻结包<br>成员材料版本<br>人工任务版本与时间范围<br>后来更新或移除的数据<br>接口最小前提：一轮有冻结成员与至少一个材料/人工版本，且后续当前材料或人工任务已经变化的回执。 |
| 覆盖情况 | 当时成员、历史版本、后来变化、当前引用不可读 |
| 测试操作/方法 | 从历史打开旧轮引用，核该轮材料版本和后续变化边界<br>接口核对：将原输入与后续当前指针对照，确认旧轮证据不漂移。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |
| 关键字段/关系 | `run.scope_revision`<br>`run.scope_kind`<br>`run.input_artifact_id`<br>`members[].alert_id`<br>`members[].material_id`<br>`members_truncated`<br>`artifact.id`<br>`task_id`<br>`id`<br>Run input 与 run_members 固定当轮告警材料版本及人工 task_revision 引用。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`result_members`<br>`results`<br>`run_members`<br>`runs`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>E12 取当轮 ID，沿 E18、E15 和 E43 查冻结原件、输入工件及原人工版本。 |
| 页面通过标准 | 读旧轮冻结输入、任务修订与来源，不被当前材料替换<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 打开当轮输入、任务版本及来源；后续成员和人工编辑不改旧引用<br>模型变化结论必须由新增事实/人工版本支持；没有证据就保留限制 |
| 实现差距/依赖 | 4173：精确来源以冻结记录为准，当前入口能打开的范围仍需读回。<br>8181：有冻结输入、人工版本和材料回链。用一条前后范围已变化的旧轮核源。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>`docs/operations/evidence/assessment-source-http-sf06-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 成员告警

### F13-04 当前成员及事件

清楚哪些材料正式属于本案。入口：案件成员告警页、页头显式事件入口和分页提示。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P4、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>当前成员关系<br>一个显式关联及仅共享成员的事件<br>分页与服务端计数<br>成员来源材料<br>接口最小前提：本案有直接成员和一条显式事件关联。共享事件正例可单独复用既有分配回执。 |
| 覆盖情况 | 有成员、没有关联事件、部分载入、仅共享告警 |
| 测试操作/方法 | 核列表、实际成员标识及事件入口，检查无显式关联的间接关系不混入<br>接口核对：核数据身份、数量与截断提示，确认同一告警和事件可相互返回。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}`<br>`GET /api/v1/socai2/cases/{case_id}/related-cases` |
| 关键字段/关系 | `members[].alert_id`<br>`members[].latest_material_id`<br>`members[].membership_source`<br>`member_count`<br>`members_truncated`<br>`linked_incidents[].incident_id`<br>`linked_incident_count`<br>`linked_incidents_truncated`<br>同案直接告警成员走 case_alerts，显式事件关系走 case_incidents。共享告警或共享事件属于另一个关系。 |
| 保存与读回 | 保存/读取来源：`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>`incident_alerts`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}`<br>`GET /api/v1/socai2/cases/{case_id}/related-cases`<br>E03 读现有成员和显式事件。沿实际 ID 打开 E28/E29。需要互查案组时另读 related-cases。 |
| 页面通过标准 | 同案成员表和显式事件链接可回查，间接关系有独立标记<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 阅读成员和显式事件，区分间接共享告警关系；分页／截断显示数量<br>范围与关联由程序核对，不由模型推断；冻结告警交接字段合同保持 |
| 实现差距/依赖 | 4173：原型有成员和显式事件入口。正式分页与间接关系区分需专验。<br>8181：有显式关联事件链接和成员表。分页总量及间接共享关系需核实际页面。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-allocation-http-20261115-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F13-05 添加告警／事件

扩大正式调查范围。入口：成员页或公共页头「添加告警 / 事件」选择对话框。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P4、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>可选告警及事件全量成员<br>已加入记录<br>候选不合规来源或租户<br>范围版本及保存回执<br>接口最小前提：一次已有同租户关联正例与一次重复关联回执，优先选既有 Case 和事件。 |
| 覆盖情况 | 候选、重复已加入、跨范围不可选、取消与确认 |
| 测试操作/方法 | 选一条告警及一个包含重复成员的事件，沿受控已授权回执核并集和新增数<br>接口核对：核实际新增、去重、版本、显式事件关系及首轮任务归属。 |
| 实际接口 | `GET /api/v1/socai2/alerts`<br>`GET /api/v1/socai2/incidents`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`POST /api/v1/socai2/cases/{case_id}/associations`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/activities` |
| 关键字段/关系 | `alert_ids`<br>`incident_ids`<br>`expected_scope_revision`<br>`operation_key`<br>`allocations[].added_alert_ids`<br>`allocations[].existing_alert_ids`<br>`allocations[].case_id`<br>`incident_receivers`<br>`receiving_case_id`<br>显式选择合并到实际分配 Case。整事件及该事件当前成员对照，续建和唯一自动接收者取真实回执。 |
| 保存与读回 | 保存/读取来源：`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>`incident_alerts`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>E08 保存后从 allocations[].case_url 读每个实际案件和范围。事件接收案由 E29/E30 对照，存在首轮任务时读其 status_url。 |
| 页面通过标准 | 确认后回到同案成员表或原入口，看到实际新增及待更新提示<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 搜索、选择并确认，整体校验同来源同租户；并集去重，重复加入不重复更新，回查新增数<br>范围与关联由程序核对，不由模型推断；冻结告警交接字段合同保持 |
| 实现差距/依赖 | 4173：导入案只读，候选校验和保存以正式数据验。<br>8181：添加对话框有候选搜索、关联写入及范围版本。验收事件成员并集和重复响应。<br>HTTP：原生关联、去重和实际分配已有回执。8181 成功导航仍依旧回执字段，需核真实接收案。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-allocation-http-20261115-01/README.md`<br>`docs/operations/evidence/case-initial-http-20261115-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F13-06 移动成员

将告警明确交给另一案件。入口：成员表勾选成员，再选择「移动所选告警」的目标案件。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P4、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>同数据范围的源案和目标案<br>选中成员和目标已含成员<br>两案版本<br>历史 Run<br>移动回执<br>接口最小前提：同租户源案、目标案和一条已移动成员的保存回执，已有旧 Run 可查。 |
| 覆盖情况 | 来源与目标有效、两案版本一致、取消或不合规 |
| 测试操作/方法 | 以一次正常移动证据核双方集合和旧 Run，核未确认不会改变成员<br>接口核对：对照源移除、目标新增以及移动前 Run 输入，确认受影响成员范围。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`POST /api/v1/socai2/cases/{case_id}/members/move`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}` |
| 关键字段/关系 | `target_case_id`<br>`alert_ids`<br>`expected_source_scope_revision`<br>`expected_target_scope_revision`<br>`operation_key`<br>`source.case_id`<br>`source.removed_alert_ids`<br>`source.scope_revision`<br>`allocation.allocations`<br>`moved_alert_ids`<br>E09 原子移出源案并向目标案串分配。按目标实际分配及源案各自范围版本核对。 |
| 保存与读回 | 保存/读取来源：`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>`incident_alerts`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>用 E03 读源案和所有实际接收目标案，E17 核活动。旧 E12/Result 的冻结输入保留。 |
| 页面通过标准 | 源和目标成员集合都更新，旧轮输入及历史引用保留<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 指定源成员和目标案，核两案版本，同步更新两案范围；原历史不变<br>范围与关联由程序核对，不由模型推断；冻结告警交接字段合同保持 |
| 实现差距/依赖 | 4173：原型本地可移动指定成员，缺正式双案版本和读取回执。<br>8181：有目标案选择、双版本提交和冲突后双案读取。真实移动后两案与旧轮需联验。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-allocation-http-20261115-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F13-07 管理所选告警

对明确范围统一维护处理信息。入口：成员表选择告警后使用管理所选入口，或从成员打开原告警管理。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P4、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>多个同案成员<br>选择身份<br>告警当前处理字段与版本<br>批量管理回执<br>接口最小前提：本案至少一个已勾选的成员，另一个历史对照为未勾选。 |
| 覆盖情况 | 无选择、勾选、编辑、取消及实际保存 |
| 测试操作/方法 | 比较选择范围和提交对象，读回选中与未选中告警状态及原成员集合<br>接口核对：复用告警管理的真实已验结果，核保存回执、已选读回及未选的对照。 |
| 实际接口 | `POST /api/v1/socai2/alerts/management-batch`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/people` |
| 关键字段/关系 | `items[].alert_id`<br>`items[].expected_row_version`<br>`changes`<br>`operation_key`<br>`changed_count`<br>`items`<br>`section_urls.activities`<br>批量请求使用实际所选告警的身份和期望版本，管理结果归对应告警。 |
| 保存与读回 | 保存/读取来源：`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>`incident_alerts`<br>读回：`GET /api/v1/socai2/alerts/{alert_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>E51 保存后读所选 E28 与 E30 activities。重新读 E03 确认案件成员关系。 |
| 页面通过标准 | 只在所选告警上读到处理信息变更，案件范围不因管理改变<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 仅影响勾选告警，不借“添加”从别案移走，不把选中视为提交<br>范围与关联由程序核对，不由模型推断；冻结告警交接字段合同保持 |
| 实现差距/依赖 | 4173：原型共用告警表和管理动作。成员页完整批量入口及所选范围需要回核。<br>8181：成员页已有勾选批量管理入口，沿告警管理调用，需要核只修改所选范围。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/alert-git-21-release-20261125-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F13-08 成员变化后的提示

防止新增材料被误认为已分析。入口：成员保存后查看调查概览待更新提示及当前判断覆盖。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P4、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>加入或移除前后范围<br>派生待更新状态<br>冻结的旧 Run 输入<br>当前采用覆盖<br>接口最小前提：已存较旧完成轮之后添加成员的 Case，或现有两轮增量历史。 |
| 覆盖情况 | 新成员、移除成员、已执行轮仍用旧范围、尚无新轮 |
| 测试操作/方法 | 用已有成员变化记录对照待更新及当前/旧轮成员，检查无自动完成<br>接口核对：核当前成员、未覆盖成员与旧轮冻结范围，再对照既有后轮任务读回。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`POST /api/v1/socai2/cases/{case_id}/investigations` |
| 关键字段/关系 | `case.scope_revision`<br>`current_assessment.uncovered_current_alert_ids`<br>`run.scope_revision`<br>`run.input_artifact_id`<br>`update_state`<br>`latest_run_id`<br>`reason_code`<br>新成员改变当前范围。已冻结 Run 按原 scope_revision 与 run_members 读取。后续新材料由 check 选取。 |
| 保存与读回 | 保存/读取来源：`analysis_subject_state`<br>`analysis_tasks`<br>`case_alerts`<br>`case_incidents`<br>`cases`<br>`incident_alerts`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>变更后读 E03、E12 和 Case 分析任务。后续调查按 F14-03 的异步状态链。 |
| 页面通过标准 | 概览出现新增/变化提示与未覆盖部分，旧 Run 可打开其固定输入<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 显示待更新及未覆盖成员，保留当前轮固定输入，引导准备／启动下一轮<br>范围与关联由程序核对，不由模型推断；冻结告警交接字段合同保持 |
| 实现差距/依赖 | 4173：与 F14-02 共用待启动提示，业务验证重点是成员变化产生的范围差集。<br>8181：有范围变化待启动提示和待更新读回，需对照加入后的范围差集和旧轮保存。<br>HTTP：已有范围变化和后续服务 API，8181 提示与现行异步入口需联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-allocation-http-20261115-01/README.md`<br>`docs/operations/evidence/case-updates-20261115-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 案件关系图与关联探索

### F19-01 当前底图与阅读

理解案件内对象如何关联。入口：案件关系图首次进入、已保存底图与回到最新选项。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_CASE_WORKSPACE`<br>`PKG_FROZEN`<br>已完成且有图的合格结果<br>只有文本的结果<br>导入无图和成员关系<br>已保存探索的基图与 Run<br>接口最小前提：原回执一案有完整选定图，另一例使用现有当前成员底图来源或缺图。 |
| 覆盖情况 | 可用当前图、无合格图、仅成员来源图、已有探索、文本答复后 |
| 测试操作/方法 | 同案对照两种来源和无图表现，验证文本结果不替换底图，已保存探索可回<br>接口核对：核底图选择身份、关联来源、节点边稳定性和缺图提示。界面调整复用已具备的图交互。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-base` |
| 关键字段/关系 | `kind`<br>`scope_revision`<br>`graph_state`<br>`graph_artifact_id`<br>`run_id`<br>`result_id`<br>`graph`<br>`sources`<br>`fingerprint`<br>`result.graph_artifact_id`<br>当前底图以 E67 给出的 graph_state 及图身份为准。已存 Result 图绑定原 Run 和工件。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_objects`<br>`alerts`<br>`artifacts`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-base`<br>GET exploration-base 读当前底图。选定历史图用 E14 result.graph_artifact_id 跟到 E15。 |
| 页面通过标准 | 读当前合格图或明确成员关系来源，历史图及已保存探索仍能打开<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 使用有资格的已完成调查图；无完成调查按成员关系；纯文本答复不换底图，缺图不借其他轮伪补<br>关系线、同值、时间接近都不是攻击因果；战术节点不是实体查询起点 |
| 实现差距/依赖 | 4173：普通原型无合格轮可画成员关系，实际导入缺图有明确空态。底图选用规则需按产品口径联验。<br>8181：默认成员关系，可手选结果图。与 4173 当前合格运行底图的默认选择存在差别。<br>HTTP：原生底图可用。8181 当前探索读取仍存在旧入口，真实 Case 底图联验待补。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-exploration-state-20261113-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F19-02 筛选、布局与节点详情

从复杂关系定位对象和依据。入口：案件关系图的类型/告警条件、布局缩放、节点和边。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_CASE_WORKSPACE`<br>`PKG_FROZEN`<br>多类型对象和多条成员告警<br>可区分等级/状态/来源<br>关系边和可读源引用<br>接口最小前提：同案图含可定位节点、关系及其材料来源。 |
| 覆盖情况 | 按状态等级来源筛选、无节点、焦点被过滤、分组和重置 |
| 测试操作/方法 | 切换布局、过滤和选择，检查可见集合、节点/边源入口和重置<br>接口核对：用一份已存图核筛选、布局和点选来源，确认与底图、历史读取一致。 |
| 实际接口 | `GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-base` |
| 关键字段/关系 | `graph`<br>`sources`<br>`section`<br>`items`<br>`artifact`<br>`availability`<br>`content_json`<br>页面操作修改当前图的显示状态，节点及边的证据仍绑定既有主体／工件。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_objects`<br>`alerts`<br>`artifacts`<br>读回：`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-base`<br>沿 E67 底图和 E30/E15 来源取详情。只有用户明确保存时使用 F25-03。 |
| 页面通过标准 | 从图和右栏核已选对象与来源，回到合适视角，连线语义以材料为依据<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 筛选等级／状态／来源，缩放、分组、布局、重置视角；点节点或边看来源，不认定因果<br>关系线、同值、时间接近都不是攻击因果；战术节点不是实体查询起点 |
| 实现差距/依赖 | 4173：原型有两类图呈现，共用布局和筛选控件并非在每个底图模式都齐全。<br>8181：有图、进程视图和读节点来源的接线。布局、来源筛选、缩放、分组和重置仍需逐底图对齐。<br>HTTP：现有 E67 提供底图，统一 Case 对象接口缺失。前端选中态、聚合与原件路由仍按 4173 直接核。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 图筛选、布局、缩放、分组和重置视角 |
| 可复用证据 | `docs/operations/evidence/case-exploration-state-20261113-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F25-01 推荐线索与候选预览

找到值得进一步核查的案外材料。入口：案件图「推荐线索」或选告警/对象后查看关联线索。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_CASE_WORKSPACE`<br>`PKG_FROZEN`<br>同租户同范围告警及对象<br>有效起点与无匹配起点<br>候选时间、关联依据和归属字段<br>接口最小前提：已有一案带有效种子、命中候选及来源原件的固定证据。 |
| 覆盖情况 | 可用起点、无候选、已在画布、当前范围限制 |
| 测试操作/方法 | 用一个现有起点只读查看一层候选，核材料来源与未选择不写入<br>接口核对：按一次有效候选读取对照种子、匹配原件、范围和现有归属。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/exploration-candidates`<br>`GET /api/v1/socai2/alerts/{alert_id}` |
| 关键字段/关系 | `alert_id`<br>`object_id`<br>`time_from`<br>`time_to`<br>`scope`<br>`items[].alert`<br>`items[].matches`<br>`items[].case_ids`<br>`items[].incident_ids`<br>`items[].already_in_case`<br>`items[].time_delta_seconds`<br>`next_cursor`<br>从同案合法种子出发，候选以实际告警、对象和材料绑定。候选结果的归属和成员状态分别返回。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_objects`<br>`alerts`<br>`artifacts`<br>读回：`GET /api/v1/socai2/cases/{case_id}/exploration-candidates`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>GET exploration-candidates 可按真实种子及窗口读回。预览原告警走 E28。 |
| 页面通过标准 | 侧栏候选显示关系依据、时间差及归属，预览候选来源<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 从当前案件成员或指定真实告警/对象查一层候选，显示匹配原件、时间差、范围和归属<br>关系线、同值、时间接近都不是攻击因果；战术节点不是实体查询起点 |
| 实现差距/依赖 | 4173：原型从本地已加载告警选候选，正式候选资格及分页单验。<br>8181：已有候选/预览查询和错误读取入口。正例的原材料、时间差和归属需要实际供给。<br>HTTP：原生候选已读回。8181 当前携带旧 offset，需切换到原生 cursor 合同后联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-exploration-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F25-02 实体扩展与撤销

逐步探索而不立即扩大案件。入口：关联线索侧栏的预览、展开、撤销和重置。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_CASE_WORKSPACE`<br>`PKG_FROZEN`<br>有可用候选的真实对象<br>不可扩展战术节点<br>候选边及基图范围<br>接口最小前提：同案图有一个可扩展实体和至少一个匹配候选的固定回执。 |
| 覆盖情况 | 可展开对象、战术节点不可展开、候选已显示、撤销后消失 |
| 测试操作/方法 | 预览后展开并撤销一次，核画布和成员读取，确认战术节点没有扩展动作<br>接口核对：核预览、展开、撤销后图及 Case 成员读回。用既有窗口参数和合法种子。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/exploration-candidates`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-base`<br>`GET /api/v1/socai2/cases/{case_id}` |
| 关键字段/关系 | `alert_id`<br>`object_id`<br>`items[].matches`<br>`scope`<br>`graph`<br>`graph_state`<br>`fingerprint`<br>`sources`<br>原底图与临时扩展关联在页面区分。种子来自真实成员或对象。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_objects`<br>`alerts`<br>`artifacts`<br>读回：`GET /api/v1/socai2/cases/{case_id}/exploration-candidates`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-base`<br>`GET /api/v1/socai2/cases/{case_id}`<br>读 E67 与 E66 后预览或展开，撤销/重置用当前页面状态。保存见 F25-03。 |
| 页面通过标准 | 画布显示新增节点与关系，撤销或重置只移除对应探索内容<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 预览后展开节点，区分新增关系，可撤销／重置；战术节点不能当实体扩展起点<br>关系线、同值、时间接近都不是攻击因果；战术节点不是实体查询起点 |
| 实现差距/依赖 | 4173：原型写入仅限本地探索状态，正式成员变更使用独立动作。<br>8181：有候选、画布和预览状态接线。逐节点一层扩展、撤销及战术禁用尚需比对。<br>HTTP：原生底图和候选齐备，当前产品仍使用旧探索预览合同的路径。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 未保存扩展的撤销和重置 |
| 可复用证据 | `docs/operations/evidence/case-exploration-state-20261113-01/README.md`<br>`docs/operations/evidence/case-exploration-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F25-03 保存／恢复探索

中断后继续当前思路。入口：案件图保存探索，返回同案或恢复已保存探索。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_CASE_WORKSPACE`<br>`PKG_FROZEN`<br>已保存探索快照<br>基图身份及原范围<br>画布分支和选择<br>后续新调查记录<br>接口最小前提：有可读底图与一个已保存探索的 Case，依现有冲突回执核版本。 |
| 覆盖情况 | 未保存、已保存、后出有资格的底图、重置 |
| 测试操作/方法 | 保存并重进核恢复，已有较新 Run 时比对基图不漂移<br>接口核对：复用旧本地写读证据。后续产品联验核保存、刷新及恢复的快照身份和实际图来源。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/exploration-base`<br>`GET /api/v1/socai2/cases/{case_id}/exploration`<br>`PUT /api/v1/socai2/cases/{case_id}/exploration`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/history` |
| 关键字段/关系 | `base_run_id`<br>`base_fingerprint`<br>`base_snapshot_id`<br>`expected_snapshot_id`<br>`operation_key`<br>`expanded_links`<br>`view_state`<br>`snapshot.id`<br>`snapshot.base`<br>`snapshot.expanded_sources`<br>保存的图身份、候选联结及画布状态绑定同 Case 和原底图。版本由明确保存提供。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_objects`<br>`alerts`<br>`artifacts`<br>读回：`GET /api/v1/socai2/cases/{case_id}/exploration`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/history`<br>E67 读底图，E69 读取既有快照，E68 PUT 后用 E69 读回同一 snapshot。再次查案件成员及 Run 目录验证范围。 |
| 页面通过标准 | 重新进入读到原基图、起点与已选/展开状态，图中仍保留原来源<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 保存起点和画布状态，不生成 Run、不改变成员；新结果不偷偷替换已有探索<br>关系线、同值、时间接近都不是攻击因果；战术节点不是实体查询起点 |
| 实现差距/依赖 | 4173：原型可保存本地快照。正式持久读取及跨会话恢复需核。<br>8181：启用探索历史和保存接口。需核恢复仍用原底图，重置符合预期。<br>HTTP：调查原生路径是单数 GET/PUT exploration。8181 当前客户端仍走复数旧合同。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-exploration-state-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F25-04 正式加入本案

把查到的有效告警纳入调查。入口：探索画布选中候选告警后使用「加入本案」确认。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_CASE_WORKSPACE`<br>`PKG_FROZEN`<br>案外可加入告警<br>候选原案关系<br>目标范围版本及保存回执<br>待更新状态<br>接口最小前提：一个原已确认加入的非成员候选及原有成员对照回执。 |
| 覆盖情况 | 仅预览、选择未提交、不合规或重复、确认关联 |
| 测试操作/方法 | 先读预览/探索状态确认未加入，沿一次已有正式加入回执对照两案成员<br>接口核对：核确认前后成员和分配身份，来源案的旧成员关系可沿原证据核实。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/exploration-candidates`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`POST /api/v1/socai2/cases/{case_id}/associations`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/activities` |
| 关键字段/关系 | `items[].alert`<br>`items[].already_in_case`<br>`alert_ids`<br>`expected_scope_revision`<br>`operation_key`<br>`allocations[].added_alert_ids`<br>`allocations[].case_id`<br>候选预览与正式成员新增是不同动作。明确确认后复用案件关联分配。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_objects`<br>`alerts`<br>`artifacts`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>E66 选中实际候选后按 E08，读各实际 Case 及对应首轮任务，活动同案查阅。 |
| 页面通过标准 | 成员表出现实际新增，调查概览标待更新，候选原案继续保留<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 明确确认后以关联加入，不从原案移走；记录实际新增及待更新；只预览／保存探索不会加入<br>关系线、同值、时间接近都不是攻击因果；战术节点不是实体查询起点 |
| 实现差距/依赖 | 4173：确认后走 F13-05 的关联语义，和 F13-06 移动区分。<br>8181：探索加入走案件关联命令，后续待更新有显示。用实际回执确认未搬走原案成员。<br>HTTP：原生确认加入可用。8181 候选读入口及保存后的实际分配和版本仍需合并联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-exploration-20261113-01/README.md`<br>`docs/operations/evidence/case-allocation-http-20261115-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F26-01 询问所选对象

针对关系提出具体问题。入口：案件图所选真实对象或告警的「询问」入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>具备稳定对象身份及来源告警的图<br>真实候选与只预览节点<br>同案助手范围结构<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 可选实体、仅预览或无完整对象记录不可作为起点 |
| 测试操作/方法 | 只审现有入口与预填，恢复后核选择对象不自动扩图、加入或发送<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的所选对象与相关告警提问结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 同案助手预填对象及来源告警范围，用户可编辑再决定是否发送<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 将对象及关联告警带入同案助手，打开不扩展、不加成员、不发送<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：原型可演示入口，正式对话整项暂缓。<br>8181：可定位图节点提问入口及助手意图，保留整项暂缓。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 对象与证据

### F21-01 按对象浏览

直接回答某台主机有什么依据。入口：对象与证据的「按对象查看」侧栏、搜索和类型筛选。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>对象实际名称、类型和引用键<br>同案成员告警及结果<br>独立证据<br>可空外部资产字段<br>接口最小前提：有已存成员对象及 Case 证据目录。共享对象和库存匹配若已有同源回执可复用。 |
| 覆盖情况 | 有对象、无匹配、未关联对象的独立证据、外部资产未供 |
| 测试操作/方法 | 按名称和类型定位对象，核右侧所有来源属同案及缺资料状态<br>接口核对：核对象类型、原告警、原材料和已供字段，缺正例按未验处理。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/alerts/{alert_id}` |
| 关键字段/关系 | `members[].alert_id`<br>`section_urls.objects`<br>`section_urls.assets`<br>`items`<br>`page_data.evidence`<br>对象与 alert/material 关联从主体记录页读取。库存资产由正常关联分区提供，证据索引为 Case 级存量。 |
| 保存与读回 | 保存/读取来源：`alert_objects`<br>`artifacts`<br>`results`<br>`run_members`<br>读回：`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/alerts/{alert_id}`<br>E03 找真实成员，按既有告警/事件 E30 objects/assets 定位原对象与来源。Case 证据见 E05。 |
| 页面通过标准 | 右侧显示对象资料、关联告警与调查，缺库存资料有明确状态<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 左侧搜索、按类型筛选和相关告警数；选中后右侧看资料、来源告警及调查<br>材料数量不等于有效威胁数；证据有来源且保留适用范围 |
| 实现差距/依赖 | 4173：原型浏览可用，资产详情中外部资料与已保存证据各用自己的供给口径。<br>8181：对象浏览、资产匹配和同案来源入口已有。库存资料缺失及对象计数范围须以正式读取核。<br>HTTP：本服务未实现 Case 专用 objects 聚合，库存/共享对象的完整产品正例需单独确认。<br>业务资产库存 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F21-02 按调查浏览

保留难以归类到对象的材料。入口：对象与证据的「按调查查看材料」。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>无当前对象而有历史的案件<br>至少一轮查询、报告和工件<br>原 Run 与各材料身份<br>接口最小前提：一轮已有查询及报告工件的固定 Case Run。可复用后续移出对象的历史。 |
| 覆盖情况 | 当前无对象但有历史、有工件或报告、该轮无记录 |
| 测试操作/方法 | 在无对象案切调查材料，逐个核去向属于该轮，空材料留空<br>接口核对：按同一 Run 对照证据目录、Result 引用与查询页跳转。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `items[].run.id`<br>`result_ids`<br>`run.input_artifact_id`<br>`result.report_artifact_id`<br>`steps_url`<br>`artifacts_url`<br>`artifacts[].id`<br>`artifact`<br>调查证据按历史 Run、Result 及其工件目录定位，与当前对象集独立。 |
| 保存与读回 | 保存/读取来源：`alert_objects`<br>`artifacts`<br>`results`<br>`run_members`<br>读回：`GET /api/v1/socai2/cases/{case_id}/history`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>沿 E10/E12/E14 选定轮次，再用 E15 或本轮 artifacts_url 读对应工件。 |
| 页面通过标准 | 按 Run 分列查询、报告、工件，直接进入所选原轮查询/证据或报告<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按 Run 看查询、报告、工件；无当前对象仍可读历史，打开对应轮次查询页<br>材料数量不等于有效威胁数；证据有来源且保留适用范围 |
| 实现差距/依赖 | 4173：与 F28-01 共用具体查询入口，保留按案索引的独立验收。<br>8181：已有按调查切换和结果材料入口。核无对象时能进对应历史 Run。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F21-03 证据、威胁与覆盖

区分材料数量和有效判断。入口：对象与证据概况及案件资料中的独立证据和威胁指标。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>有效证据条目及范围<br>去重威胁身份与性质<br>空索引和未建立索引<br>覆盖/限制<br>接口最小前提：优先复用已有有效证据目录和未记录目录。有效空目录可沿已有回执。 |
| 覆盖情况 | 未建立索引、已建立空、有效非空、部分覆盖与限制 |
| 测试操作/方法 | 与同案、同采用范围的证据投影核计数及限制，区分空索引和未知<br>接口核对：区分无索引、有索引空集及有内容，核相同工件的覆盖与可用性。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/page-data`<br>`POST /api/v1/socai2/cases/{case_id}/evidence-index`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `expected_row_version`<br>`expected_current_artifact_id`<br>`index.entries`<br>`index.availability_state`<br>`operation_key`<br>`current_evidence_artifact_id`<br>`evidence.state`<br>`evidence.evidence_count`<br>`evidence.threat_count`<br>`evidence.covered_alert_ids`<br>`evidence.uncovered_alert_ids`<br>`evidence.limitations`<br>Case 专用证据索引随当前工件指针读取。覆盖、威胁数和原件引用沿该索引保存。 |
| 保存与读回 | 保存/读取来源：`alert_objects`<br>`artifacts`<br>`results`<br>`run_members`<br>读回：`GET /api/v1/socai2/cases/{case_id}/page-data`<br>`GET /api/v1/socai2/cases/{case_id}`<br>E06 发布后以 E05/E03 读指针和投影，沿 Case 原件或实际 Run 工件查具体依据。 |
| 页面通过标准 | 显示证据与威胁身份计数、覆盖和限制，对象数和资料数各自呈现<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 展示有效证据、威胁身份、覆盖及限制；无索引为未记录，有效空索引才为 0<br>材料数量不等于有效威胁数；证据有来源且保留适用范围 |
| 实现差距/依赖 | 4173：原型导入显示保存的缺失与部分计数。威胁和覆盖全量来源仍需合同确认。<br>8181：证据页读取证据状态、覆盖和计数。需真值区分未记录、有效零、部分及非空。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/http-real-data-20261120-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F21-04 原件和引用回查

检查材料是否支持结论。入口：证据卡片、来源告警、调查材料和引用，从右侧打开原件。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_EXPLORATION_EVIDENCE`<br>`PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>同案不同来源引用<br>冻结的工件、查询、人工修订、回执<br>摘要/受限/缺失标记<br>接口最小前提：一个能回查正文的固定引用和一个原有仅摘要、受限或缺失引用。 |
| 覆盖情况 | 有原件、只有摘要、受限、缺失或不属当前范围 |
| 测试操作/方法 | 选有原件与只有摘要各一，核链接绑定及受限/缺失提示<br>接口核对：核所指身份和正文可用性。历史原件按原材料与当轮引用取回。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{identity}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/incidents/{identity}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `source_refs[].type`<br>`source_refs[].id`<br>`source_refs[].role`<br>`source_refs[].source_path`<br>`source_refs[].row_keys`<br>`artifact.id`<br>`availability`<br>`content_json`<br>`content_text`<br>`members[].material_id`<br>引用定位同租户父 Case、Run、主体材料或任务修订，保留来源角色及当时版本。 |
| 保存与读回 | 保存/读取来源：`alert_objects`<br>`artifacts`<br>`results`<br>`run_members`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{identity}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/incidents/{identity}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>按引用类型走实际 E15/E16/E18/E31/E33 至 E35 或 E43，结果来源走 E14。产物不可得时沿自己的 availability。 |
| 页面通过标准 | 跳同告警、同 Run 查询、历史人工版本或响应回执，展示准确不可用状态<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 定位来源告警、查询、结果、人工版本或回执；只有摘要、受限、缺原件分别显示<br>材料数量不等于有效威胁数；证据有来源且保留适用范围 |
| 实现差距/依赖 | 4173：原型实有阅读入口覆盖主要材料，跨来源和受限状态需要分别验。<br>8181：可打开同对象条目与统一引用抽屉。核受限及仅摘要和固定 Run/任务版本。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`docs/operations/evidence/assessment-source-http-sf06-20261120-01/README.md`<br>`docs/operations/evidence/run-records-20261114-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 人工任务

### F22-02 列表、状态和待办数

知道谁还需要确认什么。入口：人工任务页及导航待办徽标。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>一组不同状态的任务<br>分页/汇总标识<br>可空期限、负责人和结果<br>接口最小前提：同一个 Case 有未完、完成或取消的已保存任务，数量满足所需分页覆盖。 |
| 覆盖情况 | 未开始、进行中、完成、取消、无任务 |
| 测试操作/方法 | 核各任务字段，并对照导航/概览待办只计未开始和进行中<br>接口核对：核状态、待办数、列表总数及详情当前版本。已有分页回执可直接复用。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}` |
| 关键字段/关系 | `limit`<br>`offset`<br>`items[].id`<br>`items[].current.title`<br>`items[].current.assignee_id`<br>`items[].current.due_at`<br>`items[].current.state`<br>`items[].current.result_text`<br>`total`<br>`next_offset`<br>`items[].open_task_count`<br>同案人工核实任务读当前修订。开放任务数可沿 Case 列表项或未完成状态集合核对。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>E39 列任务，E41 读所选任务。统计和显示使用各自范围。 |
| 页面通过标准 | 任务卡展示标题、说明、负责人、期限、状态和结果，徽标是未完成数<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 显示事项、说明、负责人、期限、状态和结果；徽标表示未完成数量，不等于总数<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：原型已区分待办数量与任务列表。<br>8181：已有任务读取及待办汇总。四态与刷新后计数仍需对照。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-human-http-20261111-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F22-03 用户新建与分配

承接需要人工确认的业务事实。入口：人工任务页「添加任务」和 Run 后续跟进的创建入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>任务可写的案件<br>有效负责人和来源调查<br>可选参考<br>任务保存回执<br>接口最小前提：已保存案件范围、可用人员和带原 Result/发现引用的历史任务。 |
| 覆盖情况 | 未提交、输入必需事项、可选负责人/期限/来源、取消与保存 |
| 测试操作/方法 | 打开一条已有任务创建证据，核标题、同案、来源及保存后同页可读<br>接口核对：复用原创建读回，另核现产品的正常分配及来源留存。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}`<br>`POST /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/people`<br>`GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |
| 关键字段/关系 | `operation_key`<br>`expected_scope_revision`<br>`title`<br>`description`<br>`assignee_id`<br>`due_at`<br>`origin_result_id`<br>`origin_finding_id`<br>`source_refs`<br>`task.id`<br>`task.row_version`<br>`task.current_revision_id`<br>人工任务保存于同 Case 的 tasks 与 task_revisions。来源 Result 和发现沿明确提交。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>E38 保存后用 E39/E41/E43 核同任务与当前修订。分配使用已有有效目录身份。 |
| 页面通过标准 | 返回同案任务列表看新任务及来源，按实际状态计入待办<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 用户阅读结论后明确创建任务，填事项，按需填说明、负责人、期限、来源调查及参考；保存后在同案任务页出现，不自动从未解决问题生成任务<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：原型有本地表单，正式外部负责人目录、附件仅沿已供合同。<br>8181：任务新建和可选来源可提交。关联条件、负责人及保存后列表读回待核。<br>HTTP：原生人工任务及人员读取可用，正式 Case 人工任务分配正例需连同当前供给方联验。<br>同租户业务人员目录 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-human-http-20261111-01/README.md`<br>`docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F22-04 编辑、取消及状态更新

在同一事项内继续协作。入口：人工任务卡的编辑入口与状态选择。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>可编辑任务<br>原版本与新版本<br>四种状态及取消操作活动<br>接口最小前提：一个旧状态及修订已知的任务，另有已保存编辑或取消记录。 |
| 覆盖情况 | 任意状态可编辑、取消不删除、保存后新修订 |
| 测试操作/方法 | 用既有任务新修订核原字段带入、修改身份和取消后历史<br>接口核对：对照任务 ID、行版本和旧修订内容。正常编辑和已存取消语义用同一条任务证据覆盖。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`PUT /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |
| 关键字段/关系 | `expected_scope_revision`<br>`expected_row_version`<br>`operation_key`<br>`state`<br>`title`<br>`description`<br>`assignee_id`<br>`due_at`<br>`task.current_revision_id`<br>`task.row_version`<br>在同 task_id 追加修订，同时更新任务的当前引用和行版本。取消保留历史。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>E40 保存后 E41 读当前版本，E42/E43 核原修订和新增修订。 |
| 页面通过标准 | 同一任务读到新状态、原记录可在历史版本回查<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 所有状态均可编辑，取消不删除历史；编辑带入原值，明确保存产生新版本<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：本地原型编辑覆盖当前对象，导入记录可读版本。正式写侧需验证生成新版本。<br>8181：支持编辑任务及读版本。各状态编辑及取消保留历史待正式核。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-human-http-20261111-01/README.md`<br>`docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F22-05 完成结果与适用范围

防止一句人工确认被推广到全案。入口：人工任务从编辑进入完成结果和适用范围。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>结果文本<br>当前成员与对象键<br>可空成对时间<br>任务修订和保存回执<br>接口最小前提：一份有已保存正文、明确成员及对象范围或成对时间窗的任务完成回执。 |
| 覆盖情况 | 非空结果、明确成员或对象范围、时间成对可选，范围不存在提示 |
| 测试操作/方法 | 沿已有有效完成回执核结果和冻结范围，再核无结果或无范围的表单限制<br>接口核对：核已保存正文、范围和完成者，再按既有错误样例验证缺范围或时间窗约束。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`PUT /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |
| 关键字段/关系 | `state`<br>`result_text`<br>`result_scope.kind`<br>`result_scope.alert_ids`<br>`result_scope.object_keys`<br>`result_scope.window_start`<br>`result_scope.window_end`<br>`source_refs`<br>`task.current.completed_at`<br>`task.current.completed_by`<br>完成事实保存于指定 task_revision，范围绑定本案明确成员或对象。原陈述与来源角色保留。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>E40 保存后 E41/E43 读取同一完成修订及原范围。 |
| 页面通过标准 | 任务结果随新修订保存，详情明确可适用的成员/对象及时间<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 完成须有非空结果及明确成员范围；对象范围需对象键；时间可不填，填写须成对；不强制工单或附件<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：原型要求完成有结果。严格成员范围、对象键和成对时间的保存校验需另核。<br>8181：表单处理结果、范围和成员版本的结构。对象键、双时间和服务端完成校验需直接核。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-human-http-20261111-01/README.md`<br>`docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F22-06 完成人、修改人与历史

能复核是谁在何时确认什么。入口：任务详情中的当前记录与「历史版本」。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>多个任务修订<br>委派负责人、完成者、修改者和时间<br>原冻结结果及适用范围<br>接口最小前提：一个完成后又编辑元数据、留有两份修订的任务。 |
| 覆盖情况 | 首次、完成或修改、元数据编辑、来源缺失 |
| 测试操作/方法 | 比较原确认版本与后续元数据编辑，原结果/范围及完成身份保持<br>接口核对：核实际完成者、修改者和原事实范围，检查指定旧修订保持。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/story` |
| 关键字段/关系 | `current_revision_id`<br>`items[].revision`<br>`items[].changed_by`<br>`items[].changed_at`<br>`items[].completed_by`<br>`items[].completed_at`<br>`items[].assignee_id`<br>`id`<br>`task_id`<br>负责人、完成人、修订者来自不同保存字段，旧版本通过任务和修订双身份读取。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/story`<br>E41 当前，E42 历史列表，E43 指定版本。可从故事按原修订回查。 |
| 页面通过标准 | 分别显示负责人、实际完成者、修改者，指定修订能回查确认范围<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 分开负责人、实际完成者、修改者；看指定修订，元数据编辑不改变原事实或扩大范围<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：导入可读历史。原型本地编辑不足以验证多角色和版本关系。<br>8181：有历史与选中版本读回、引用深链，需对照保存人物角色和范围。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>`docs/operations/evidence/case-human-http-20261111-01/README.md`<br>`docs/operations/evidence/case-story-20261113-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F22-07 并发冲突处理

不丢自己的输入也不覆盖他人。入口：人工任务提交遭遇版本冲突后查看最新版本。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>可复用的一次旧版本冲突回执<br>原草稿<br>最新任务版本<br>正式版本字段<br>接口最小前提：已有任务版本冲突回执，或一个过期版本与可读当前版本的受控任务。 |
| 覆盖情况 | 旧版本一次提交、409、用户草稿保留、明确重编 |
| 测试操作/方法 | 用已有冲突证据或一次受控旧版本请求核手工恢复逻辑，复杂并发留出本轮<br>接口核对：复用一次正常过期版本冲突，核输入保留、当前版本无覆盖和读回。 |
| 实际接口 | `PUT /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}` |
| 关键字段/关系 | `expected_scope_revision`<br>`expected_row_version`<br>`operation_key`<br>`row_version`<br>`current_revision_id`<br>写入以案件范围版本及任务行版本为准，过期输入返回 409。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>冲突后请求 E41/E03 读取最新。明确重新编辑后才作下一次保存。 |
| 页面通过标准 | 编辑器保留输入并提示冲突，查看最新不触发保存<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 409 保留输入，查看最新；明确重新编辑才装入最新值，不自动重提交<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：原型本地对象更新无服务版本冲突。8181 有版本接线，仍需据合同验证。<br>8181：前端有版本及冲突处理入口，仅规划单次遇到冲突后草稿保留与显式恢复。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-human-http-20261111-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F22-08 保存后的调查影响

让人工事实进入后续判断。入口：保存人工结果后查看任务详情、案件故事和后续调查材料。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>人工结果的新旧修订<br>当前采用判断<br>含新人工事实的后续冻结运行<br>故事活动<br>接口最小前提：同案原完成人工事实及后续完整轮次已保存引用，优先有元数据编辑的同组回执。 |
| 覆盖情况 | 新的人工版本、原采用判断、有后续引用或尚无后续运行 |
| 测试操作/方法 | 核保存事实出现，比较保存前后当前判断，追已有后续 Run 引用到该版本<br>接口核对：复用现有后轮输入对照，验证人工事实的原版本、范围和独立采用指针。 |
| 实际接口 | `PUT /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`POST /api/v1/socai2/cases/{case_id}/investigations`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/story`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `task.current_revision_id`<br>`task.current.result_scope`<br>`task.current.result_text`<br>`status_url`<br>`latest_run_id`<br>`run.input_artifact_id`<br>`items[].task_revision`<br>有效人工任务完成、修订或撤回经既有核心进入后续 check。Run 输入存明确的 task_revision 身份。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/story`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>E40 保存读 E41/E43 和 E65。未来明确 check 后沿 task/attempt/Run/input artifact 查看引用。 |
| 页面通过标准 | 故事读到保存事实，后续明确引用版本，当前判断和结案由独立动作决定<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 保存只确认人工结果；后续调查可引用，故事和助手后续可见；不自动改当前判断或结案<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：原型可演示任务和故事更新。有效人工版本进入真实后续运行需核心回执。<br>8181：任务修订、故事和人工版本读取各有接线。该修订进入后续 Run 和不改变当前判断需真实闭环。<br>HTTP：后轮冻结已验。当前 8181 的 check 路径和人工事实入案回链仍待联验，助手续接已后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>`docs/operations/evidence/case-updates-20261115-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 处理活动、评论与附件

### F23-05 处理活动与目标

交接时说明谁做过什么。入口：处理活动页筛选或展开活动，打开关联目标。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P3、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>多个活动类型<br>操作者、目标身份和时间<br>前后值与结果<br>分页策略<br>接口最小前提：同案有已保存管理或成员变动与人工任务活动，含前后值。 |
| 覆盖情况 | 管理、成员、人工任务活动，缺目标或仅摘要，有前后值时区分 |
| 测试操作/方法 | 选一条管理和成员活动打开目标，对照同案实际变更和无目标状态<br>接口核对：核一次真实活动的操作者与目标、前后值、返回和跳转身份。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/activities` |
| 关键字段/关系 | `limit`<br>`offset`<br>`items[].id`<br>`items[].matching_targets`<br>`items[].targets_truncated`<br>`items[].matching_targets[].before_value`<br>`items[].matching_targets[].after_value`<br>`total`<br>`next_offset`<br>活动账本及匹配目标以同 Case 归属读取，目标反查原 Case、告警、任务或 Run。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`artifacts`<br>`comments`<br>读回：`GET /api/v1/socai2/cases/{case_id}/activities`<br>管理、成员或任务保存后用 E17 查同一操作和目标变化。 |
| 页面通过标准 | 时间、动作、操作者及目标可回查，前后值和结果按实际保存显示<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 展示管理、成员、人工变更的时间、操作者、前后值、结果；展开目标并回原对象<br>Case 管理状态、调查执行状态与业务判定分开 |
| 实现差距/依赖 | 4173：原型主要显示动作摘要和目标，结构化前后值及完整活动回链需核。<br>8181：已有活动读取、按类型筛选及关联目标。结构化前后值和活动结果供给需核。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-management-20261112-01/delivery-summary.json`<br>`docs/operations/evidence/case-allocation-http-20261115-01/README.md`<br>`docs/operations/evidence/case-human-http-20261111-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F24-01 评论阅读与提交

记录协作说明，不混入 AI 结论。入口：评论与附件的评论列表和输入框。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P2、P3、P5 |
| 准备数据 | `PKG_CASE_WORKSPACE`<br>`PKG_HUMAN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>同案作者信息与评论记录<br>新增备注回执<br>时间<br>审批/事实分区口径<br>接口最小前提：同案一条已有评论提交回执及其原作者、时间和正文读回。 |
| 覆盖情况 | 空列表、已保存评论、有草稿、提交成功或失败 |
| 测试操作/方法 | 用批准的已有评论回执核写后读，确认评论未写入 AI 判断或确认事实<br>接口核对：优先复用原评论写读，补产品同一案件实际列表和刷新对照。 |
| 实际接口 | `POST /api/v1/socai2/cases/{case_id}/comments`<br>`GET /api/v1/socai2/cases/{case_id}/comments`<br>`GET /api/v1/socai2/cases/{case_id}/activities` |
| 关键字段/关系 | `body`<br>`operation_key`<br>`id`<br>`case_id`<br>`author_id`<br>`author_name_snapshot`<br>`created_at`<br>`row_version`<br>`items`<br>`next_offset`<br>评论独立保存在同案 comments。活动和评论按各自接口读取。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`artifacts`<br>`comments`<br>读回：`GET /api/v1/socai2/cases/{case_id}/comments`<br>`GET /api/v1/socai2/cases/{case_id}/activities`<br>E58 写入后读 E59 同案列表，再核 E17 实际活动和作者身份。 |
| 页面通过标准 | 提交成功后同案评论区读到作者、正文和时间，仍归协作资料<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 查看作者、正文、时间；提交后形成同案备注，不能自动作为已核实事实<br>Case 管理状态、调查执行状态与业务判定分开 |
| 实现差距/依赖 | 4173：原型有本地评论保存，实际持久读取按正式接口验。<br>8181：有同案评论读取、编辑与保存。验收只影响评论分区。<br>HTTP：有调查原生服务和 8181 组件/桥接代码，专页的当前正式读回尚未独立确认。<br>无；按本项边界处理 |
| 责任/当前验收 | SpiritHub后端（文件服务）＋调查HTTP（关联）＋前端（整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-comments-20261113-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F24-02 已有附件查看／下载

回看补充资料的原件。入口：评论与附件的已有附件、查看和下载入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通部分纳入，所列子范围后置；完整功能规则保留；本期只核有效附件引用/关联和元数据，业务后端真实文件字节上传/下载联调继续后置。本次完整规划不恢复字节操作。；P3 |
| 准备数据 | `PKG_FILES_AND_RESPONSES`<br>`PKG_CASE_WORKSPACE`<br>已登记的同案 file_id 与附件元数据<br>原始文件<br>失效文件或可读状态<br>接口最小前提：已有合法 file_id 和指定 Case 附件元数据的历史回执。 |
| 覆盖情况 | 可下载、文件不可用或所属案不一致 |
| 测试操作/方法 | 检查一次已登记附件元数据和原件摘要指纹，核失效提示<br>接口核对：只验原生列表和身份/元数据读回。本期界面只按既有范围核对下载占位。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/attachments`<br>`GET /api/v1/socai2/cases/{case_id}/attachments/{attachment_id}` |
| 关键字段/关系 | `id`<br>`case_id`<br>`file_id`<br>`file_name`<br>`mime_type`<br>`size_bytes`<br>`sha256`<br>`availability`<br>`items`<br>`next_offset`<br>Case attachment 行提供业务系统 file_id 与可用性元数据。字节由业务后端文件系统提供。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`artifacts`<br>`comments`<br>读回：`GET /api/v1/socai2/cases/{case_id}/attachments`<br>`GET /api/v1/socai2/cases/{case_id}/attachments/{attachment_id}`<br>E61 列同案引用，E62 读指定附件元数据，文件下载需已确认外部合同。 |
| 页面通过标准 | 看到文件元数据并下载原件，无法读取有清楚提示<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 查看文件名、类型、大小和所属案件，业务后端按file_id提供下载并报告文件失效<br>普通引用/关联成功不代表文件字节已上传、可下载或已核哈希<br>完整设计仍要求先保存文件再登记关联；上传/登记/下载各自结果不能互相追认 |
| 实现差距/依赖 | 4173：4173 下载演示内容，不能用于证明正式原件按 file_id 提供。<br>8181：有元数据和原件下载调用，按 file_id 实际读回和失效文案待核。<br>HTTP：后端文件字节下载联调已后置。GET 附件详情返回元数据。<br>业务后端文件下载，已后置 |
| 责任/当前验收 | SpiritHub后端（文件服务）＋调查HTTP（关联）＋前端（整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-attachments-20261113-01/README.md`<br>`docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F24-03 上传补充附件

让协作材料能持久交接。入口：评论与附件中的选择文件、上传与登记。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通部分纳入，所列子范围后置；完整功能规则保留；本期只核有效附件引用/关联和元数据，业务后端真实文件字节上传/下载联调继续后置。本次完整规划不恢复字节操作。；P3 |
| 准备数据 | `PKG_FILES_AND_RESPONSES`<br>`PKG_CASE_WORKSPACE`<br>受控文件与类型、大小<br>上传回执<br>附件登记回执及 Case 归属<br>登记失败状态<br>接口最小前提：一个先有业务后端文件标识且已有附件登记回执的案件。 |
| 覆盖情况 | 未选、文件已上传待登记、登记成功或失败 |
| 测试操作/方法 | 分步追已有上传和登记凭据，核仅登记成功进入同案列表<br>接口核对：复用引用登记的原证据，文件上传和失败分支本期沿已明确后置。 |
| 实际接口 | `POST /api/v1/socai2/cases/{case_id}/attachments`<br>`GET /api/v1/socai2/cases/{case_id}/attachments`<br>`GET /api/v1/socai2/cases/{case_id}/attachments/{attachment_id}` |
| 关键字段/关系 | `file_id`<br>`file_name`<br>`mime_type`<br>`size_bytes`<br>`sha256`<br>`operation_key`<br>`id`<br>`case_id`<br>`availability`<br>调查服务只登记同 Case 已有文件引用。原始字节写入由业务后端拥有。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`artifacts`<br>`comments`<br>读回：`GET /api/v1/socai2/cases/{case_id}/attachments`<br>`GET /api/v1/socai2/cases/{case_id}/attachments/{attachment_id}`<br>已有 file_id 时 E60 保存引用，E61/E62 核同一附件身份和元数据。 |
| 页面通过标准 | 登记成功后同案附件列表可重新读取对应 file_id，下载沿文件服务<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 业务后端先上传保存，随后登记案件关联；登记成功可再查文件ID供后端下载，失败不能显示关联已保存<br>普通引用/关联成功不代表文件字节已上传、可下载或已核哈希<br>完整设计仍要求先保存文件再登记关联；上传/登记/下载各自结果不能互相追认 |
| 实现差距/依赖 | 4173：4173 有样例附件列表和下载，没有正式上传加关联流程。8181 有接线，正式联验另核。<br>8181：有选文件、上传及登记两步。缺登记或登记失败不报已关联。<br>HTTP：业务后端上传、字节持久化及端到端文件联调已后置。<br>业务后端文件上传及字节保存，已后置 |
| 责任/当前验收 | SpiritHub后端（文件服务）＋调查HTTP（关联）＋前端（整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-attachments-20261113-01/README.md`<br>`docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## Case 案件助手

### F26-02 同案统一对话

各页面提问能接续同一上下文。入口：公共页头、故事、结果或图打开同案案件助手。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>同一案件多入口<br>两个案件的独立会话与消息范围<br>保存会话映射<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 同案多入口、切案、旧会话、无会话、只读导入 |
| 测试操作/方法 | 当前只审入口和会话隔离结构，恢复后核切案不串历史<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的跨页面同案会话结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 同案入口呈现已有历史及预填范围，切案加载不同上下文<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 页头／故事／结果／图进入同案对话；切案切换历史与范围，不串案<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：原型有同案会话和导入只读入口，正式 AI 对话保留暂缓。<br>8181：源码有同案助手意图与聊天查询，整体仍按暂停执行。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F26-03 范围选择与问题编辑

让 AI 知道要回答什么。入口：案件助手中的范围选择、当前上下文和文本草稿。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>有效的 Case/成员/Run/对象/人工版本引用<br>草稿<br>已失效范围<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 全案、指定告警/Run/对象/人工版本、范围无效、草稿可改 |
| 测试操作/方法 | 只核输入和选择结构，待启用后分别检查范围预填及必需约束<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的范围选择与问题编辑结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 助手显示真实范围摘要和用户可编辑问题，打开时保持未发送<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 可带全案、告警、Run、对象、人工事实；范围展示且问题可编辑；打开不执行<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：既有原型可编辑范围，暂缓期间只保留规划。<br>8181：有初始意图、范围编辑和引用选择。暂缓正式联验。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F26-04 建议问题

帮用户发现值得问的问题。入口：案件助手「建议问题」选择区。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>有历史对话及建议生成所需的来源类别<br>自然语言草稿<br>无建议条件<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 新会话、有历史、可编辑建议与无建议 |
| 测试操作/方法 | 只对照建议区域的显示条件及回填代码，恢复后核有历史时仍可建议<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的建议问题结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 点击只回填问题草稿，用户继续编辑或显式发送<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 历史对话存在时仍显示建议；点击只填输入框，由用户修改后发送<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：原型提供建议；有历史的持续显示和正式来源口径仍保留待验。<br>8181：可见建议入口及范围控制。暂缓期留设计，后续再核有旧历史的显示。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F26-05 发送与只读分析

直接处理用户问题。入口：从助手输入问题后明确点击发送。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>有效对话及问题范围<br>分析 task/Run 或消息状态<br>已保存回答及引用<br>需澄清或受限状态<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 待发送、受理、进行中、需澄清、已保存回应、失败 |
| 测试操作/方法 | 本轮仅规划消息到执行和读回路径。启用后用正常发送的真实回执核全链<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的问题发送和只读分析结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 同案消息部分展示进度、结论、依据、影响和限制，保留已记录查询来源<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 发送后分析已有材料或按需查询，显示进度、结论、依据、影响及限制；需澄清则询问<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：原型演示响应，实际导入禁止发送。整项暂缓。<br>8181：源码有发送与请求状态回查。接口可用性和真实分析仍照暂缓边界。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F26-06 失败与人工事实续接

不把失败当无风险，并补齐缺事实。入口：助手已记录失败/事实缺项旁的重读、人工确认和继续入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>有限定范围的已失败或待确认消息<br>原问题输入与 Run<br>人工任务和修订<br>后续会话引用<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 未查、失败、人工确认待完成、保存人工作业后继续原上下文 |
| 测试操作/方法 | 当前仅审失败/续接结构，恢复后用一条既有失败和补充事实验证，避免自动重发<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的失败澄清及人工事实续接结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 失败保留原状态，必要时建立人工任务并沿原问题开启续接草稿<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 显示未查／失败原因；需要人确认时建立事项，收到事实后续接原问题<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：原型有失败和人工入口的一部分。真实因果链及不重复发送需在恢复后验证。<br>8181：有按冻结问题预填人工任务/续问及原请求恢复。正式续接暂缓。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F26-07 保存到调查记录

保留有价值的答复用于交接。入口：已回答消息的「保存到调查记录」表单。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>已保存会话与回答<br>问题、来源材料和范围<br>保存后的记录/版本及操作身份<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 源回答已存在、改标题结论、确认/取消、重复请求 |
| 测试操作/方法 | 只审原型保存行为，恢复后核确认、取消和已有记录重复回执<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的保存回答和冻结来源结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 保存后同案故事/历史出现冻结问答和材料，原回答可重复读<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 确认标题与结论后冻结问题、回答及材料；进入故事／历史；取消不保存、重复不重建、不再执行<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：本地演示存在。正式对话和保存入口按已确认暂缓。<br>8181：已有保存表单和调用点。实际保存问答及回链属于暂缓项。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages/{message_id}/save`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F26-08 引用与继续追问

复核回答并延续问题。入口：助手答复引用、任务来源和继续提问入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>保存答复、来源工件及当时范围<br>任务先后修订<br>新问题的实际选择<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 旧快照可读、当前任务另可见、引用未供、新提问变范围 |
| 测试操作/方法 | 仅定位已有引用和续问控件，恢复后核旧快照身份及草稿范围<br>接口核对：复用已确认后置决定及 Schema 中的保留路由，静态核对范围。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>保留原型中的原引用和继续追问结构与同案关联要求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>现有两条保留入口无业务保存和读回。 |
| 页面通过标准 | 带原引用的答复可回查，继续提问打开可编辑内容，旧范围保持<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 展开当时来源，允许回查当前任务但保留旧快照；新问题按新范围处理<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：原型按会话选材料，正式来源快照和任务修订的准确性保留待验。<br>8181：已有来源引用和继续入口。暂缓期保留历史读取，正式续问另验。<br>HTTP：助手对话及保存回答已明确后置。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 调查运行列表

### F14-07 跨主体运行目录

找到没有 Case 或不同案件的既有执行。入口：全局调查运行目录、案件列表「查看调查运行」和指定 Run 深链。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>告警 A、事件 I、Case 及无 Case 运行<br>主体和轮次键<br>运行状态/时间<br>候选与实际案关联区别<br>接口最小前提：固定目录包含至少两个主体类型，最好已有一次终态且无 Result 的原 Run。 |
| 覆盖情况 | 不同主体/轮次、部分或失败、有主体无 Case、指定运行找不到 |
| 测试操作/方法 | 按三类入口打开同一已知轮次并核身份，无案轮只显示已有主体<br>接口核对：已有统一目录回执核筛选、下一页及两种主体跳转。给 8181 只补目录和一条正确详情的接线验收。 |
| 实际接口 | `GET /api/v1/socai2/analysis-runs`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/incidents/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks` |
| 关键字段/关系 | `subject_type`<br>`subject_id`<br>`run_kind`<br>`intent`<br>`state`<br>`time_from`<br>`time_to`<br>`limit`<br>`cursor`<br>`items[].run_id`<br>`items[].task_id`<br>`items[].subject_id`<br>`items[].detail_url`<br>`items[].results[].url`<br>`total`<br>`next_cursor`<br>统一列表行属于真实告警、事件或 Case 的 Run。task_id 只来自真实任务关联。尚无 Run 的任务在各主体任务目录。 |
| 保存与读回 | 保存/读取来源：`alerts`<br>`cases`<br>`incidents`<br>`runs`<br>读回：`GET /api/v1/socai2/analysis-runs`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/incidents/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>GET analysis-runs 后按 detail_url 打开 E24/E25/E12，并按真实结果 URL 读回。 |
| 页面通过标准 | 从独立目录或深链进入准确 Run，再回其告警、事件或真实案件<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按主体、轮次、状态、时间查看并打开指定 Run；不将候选 Case ID 当实际业务案<br>不为4173原型未提供的搜索筛选控件增加测试范围 |
| 实现差距/依赖 | 4173：原型有跨主体目录和精确详情，无搜索过滤控件。8181 已有筛选，仅作为差距对照。<br>8181：有全局目录、过滤和运行 context 读取。需核三类主体、无 Case 和不认错 Run。<br>HTTP：调查原生目录有合同和历史回执。8181 全局 Q08 上游使用旧路径，通用详情依赖应沿真实主体。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-directory-http-20261114-01/README.md`<br>`docs/operations/evidence/analysis-task-http-20261114-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F15-02 运行统计和卡片摘要

了解已有运行及其交付情况。入口：全局调查运行目录的统计卡和记录卡。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>多种交付的运行目录<br>已知输入数及时间<br>实际关联 Case<br>空计量或摘要<br>接口最小前提：已有同一筛选结果含部分交付、未升级及真实关联 Case 的固定目录回执。 |
| 覆盖情况 | 完整、部分、未升级及关联 Case，缺摘要或耗时 |
| 测试操作/方法 | 核各统计分母和卡片字段，同一运行跳转一致，未知不补值<br>接口核对：核统计和分页的口径以及卡片的真实摘要和身份。沿 4173 页面实际控件验收。 |
| 实际接口 | `GET /api/v1/socai2/analysis-runs`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}` |
| 关键字段/关系 | `statistics.total_runs`<br>`statistics.by_state`<br>`statistics.by_delivery_state`<br>`statistics.not_escalated_count`<br>`statistics.related_case_count`<br>`statistics.without_related_case_count`<br>`items[].input_member_count`<br>`items[].requested_at`<br>`items[].results`<br>`next_cursor`<br>Run 统计与筛选范围相同，卡片以同一 run_id 读状态、输入与可用结果摘要。关联案身份来自实际案件关系。 |
| 保存与读回 | 保存/读取来源：`alerts`<br>`cases`<br>`incidents`<br>`runs`<br>读回：`GET /api/v1/socai2/analysis-runs`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>读统一目录及真实结果和主体详情链接。全范围统计在列表响应中读取。 |
| 页面通过标准 | 统计和每卡状态、输入数量、时间、保存摘要、Run ID 按各自范围展示<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 统计运行记录、部分交付、未升级调查及关联 Case；卡片展示状态、输入数量、时间、摘要和 Run ID；当前原型没有搜索筛选控件<br>不为4173原型未提供的搜索筛选控件增加测试范围 |
| 实现差距/依赖 | 4173：有原型卡片和统计。目录搜索不是该项原型要求。<br>8181：现以表格、时间轴和侧栏为主，需核原型的四类统计及保存摘要能否从同范围数据取得。<br>HTTP：当前 8181 统一目录接线缺口影响卡片和统计。原生 API 正例可复用。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-directory-http-20261114-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 调查发现

### F16-03 目标、结论、发现与限制

先知道这一轮得到什么及哪些仍未查清。入口：固定 Run 的「调查发现」。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>冻结 Run 输入与目标<br>正式 Result 与结构化问题/发现<br>系统收尾及状态<br>可选比较与限制<br>接口最小前提：有保存结论、发现和限制的现有 Case 结果。另可复用已完成或无有效判定的事件历史。 |
| 覆盖情况 | 有正式结论、待核问题、运行中、无正式结果与系统解释 |
| 测试操作/方法 | 选择正式结果和无结果各一，核正文、来源角色和待核问题的原范围<br>接口核对：按保存的原 Result 或阶段记录对照目标、依据、未解决问题及限制。执行收尾与业务结论在各自归属展示。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}` |
| 关键字段/关系 | `run.id`<br>`run.purpose`<br>`run.scope_kind`<br>`result.conclusion`<br>`result.business_verdict`<br>`result.findings[]`<br>`result.questions[]`<br>`result.case_impact`<br>`result.change_summary`<br>`result.closing_note`<br>同一阶段的主体、Run 及其保存结果绑定。Case Result 含业务正文、影响和保存范围，A/I 各读自己的 StageEntry。 |
| 保存与读回 | 保存/读取来源：`alert_assessments`<br>`alert_materials`<br>`alert_source_refs`<br>`artifacts`<br>`incident_diagnoses`<br>`result_members`<br>`results`<br>`run_members`<br>`run_steps`<br>`runs`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}`<br>Case 查 E12/E14 及所指报告或输入工件。A/I 查 E24/E25，不可借不同轮次。当前事件采用另沿 E29。 |
| 页面通过标准 | 在所选轮次显示目标、原范围、判断、发现、依据、比较/影响和限制，各来源可回查<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 阅读原始范围、结论（含未解决问题）、依据、变化与案件影响；未解决问题保留在本轮结论中，无独立处理状态；系统收尾和模型判断分别标明<br>正文结论必须有本范围证据；不足允许待复核；系统收尾不冒充模型判断 |
| 实现差距/依赖 | 4173：已覆盖主要内容。部分字段缺口保留到合同联验。<br>8181：有正式结果、系统交接、发现及问题入口。要核采用范围、证据与影响真实来源。<br>HTTP：阶段字段可读，8181 指定 Run 的结论、来源及场景空态仍有分项联验缺口。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/c173-bounded-json-20261121-01/README.md`<br>`docs/operations/evidence/assessment-basis-sf06-20261120-01/README.md`<br>`docs/operations/evidence/incident-saved-diagnosis-read-20261126-01/independent-closeout.json`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F15-03 执行、交付及用量

判断结果可用程度及停止原因。入口：固定 Run 状态区、调查发现和运行详情与用量。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>运行和交付字段<br>部分覆盖及限制<br>已知与未知用量<br>失败/unknown 及已保存工件<br>接口最小前提：一轮有任务尝试、交付标记及用量快照，并保留一轮旧未知或失败的原回执。 |
| 覆盖情况 | 执行、交付、覆盖、停止、unknown 和可空用量各自独立 |
| 测试操作/方法 | 同轮逐项对照状态和计量，一条有工件的失败或部分交付仍按保存状态呈现<br>接口核对：对照任务时间线、Run 结束和结果覆盖。保持 unknown/缺用量及已本地结束状态。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/incidents/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps` |
| 关键字段/关系 | `run.state`<br>`run.delivery_state`<br>`run.stop_reason`<br>`usage`<br>`execution_summary`<br>`duration_seconds`<br>`analysis_coverage`<br>`status`<br>`attempts[].local_state`<br>`attempts[].outcome`<br>`attempts[].timing`<br>`timing`<br>`active_step`<br>Task/attempt 反映受理及本地执行过程，Run 和 Result 提供该轮执行及保存交付。覆盖来自相应阶段。 |
| 保存与读回 | 保存/读取来源：`alert_assessments`<br>`alert_materials`<br>`alert_source_refs`<br>`analysis_attempts`<br>`analysis_tasks`<br>`artifacts`<br>`incident_diagnoses`<br>`result_members`<br>`results`<br>`run_members`<br>`run_steps`<br>`runs`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/incidents/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>从主体任务读 attempt 和 Run 链接，再从 E12 或 E24/E25/E32 读用量、交付、覆盖与停止信息。 |
| 页面通过标准 | 状态可分别读到，计量未知留未记录，不从有工件倒推成功<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 状态、完整性、覆盖、用量分别展示；unknown 保持待核实，有工件不代表成功<br>正文结论必须有本范围证据；不足允许待复核；系统收尾不冒充模型判断 |
| 实现差距/依赖 | 4173：已有运行详情与用量。未知字段、冻结计量来源和独立覆盖仍需核。<br>8181：执行、交付、停止、时间及能力各有位置。计量未知、覆盖及失败有工件应据正式记录验证。<br>HTTP：当前 21 Schema 已有 S5 字段。跨主体产品转发与任务提示、完整步骤关联仍需分主体联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/analysis-task-times-s5-20261120-01/independent-acceptance.json`<br>`docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/incident-saved-diagnosis-read-20261126-01/independent-closeout.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F12-04 查看当轮原始输入

确认这轮究竟调查了谁。入口：调查发现的「本次调查范围」与打开冻结输入元数据或原件。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_HUMAN`<br>冻结成员、材料版本和人工事实<br>运行引用<br>当前与原范围差集<br>缺失状态<br>接口最小前提：一份包含材料版本和保存输入的旧轮记录，同时有较新的当前材料或后续成员以作对照。 |
| 覆盖情况 | 当轮成员、当前成员变化、来源版本存在或未记录 |
| 测试操作/方法 | 点该轮原输入并核其成员/版本，随后查看当前成员差集<br>接口核对：对照冻结 ID 及输入范围，确认读取指定轮次而非当前指针。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |
| 关键字段/关系 | `run.input_artifact_id`<br>`members[].alert_id`<br>`members[].material_id`<br>`result.input_material_id`<br>`input_selection`<br>`artifacts_url`<br>`artifact.id`<br>`availability`<br>Case Run 冻结成员材料和人工修订。A 通过结果里的 input_material_id，I 通过当轮输入选择和原件。主体身份和材料版本不可互换。 |
| 保存与读回 | 保存/读取来源：`alert_assessments`<br>`alert_materials`<br>`alert_source_refs`<br>`artifacts`<br>`incident_diagnoses`<br>`result_members`<br>`results`<br>`run_members`<br>`run_steps`<br>`runs`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>Case 按 E12→E18/E15；A 按 E24→E31；I 按 E25→E32/E33。原人工修订沿 E43。 |
| 页面通过标准 | 同轮冻结告警和人工输入可读，当前新增成员仅另列<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 查看被冻结的告警版本、范围和人工事实；当前新增成员不并入旧轮<br>正文结论必须有本范围证据；不足允许待复核；系统收尾不冒充模型判断 |
| 实现差距/依赖 | 4173：共用 F12-03 冻结源。此项从所选运行的发现页发起。<br>8181：有冻结输入和工件入口。具体告警、材料版本和人工事实仍需比较。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`docs/operations/evidence/case-human-persistence-20261113-01/README.md`<br>`docs/operations/evidence/incident-saved-diagnosis-read-20261126-01/independent-closeout.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F22-09 用户创建人工任务／询问结果

对结论中需要核实的内容开展后续工作。入口：调查发现的案件跟进、按原结果创建人工任务或准备提问。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通部分纳入，所列子范围后置；用户显式创建人工任务纳入；打开助手并询问结果暂缓。；P1、P3、P4、P5 |
| 准备数据 | `PKG_HUMAN`<br>`PKG_CASE_WORKSPACE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_FROZEN`<br>已有 Run 和未决问题<br>任务来源引用<br>保存回执<br>可选助手范围结构<br>接口最小前提：一份有待核事项的保存 Result，以及一条已明确创建并关联来源的人工任务回执。 |
| 覆盖情况 | 任务待填写、来源有效、确认/取消，提问草稿等待发送 |
| 测试操作/方法 | 核打开任务带固定 Run，沿已有保存证据核同案读回。助手分支只作暂缓规划<br>接口核对：对照任务确由用户确认创建及同案来源。助手只查原型边界。 |
| 实际接口 | `POST /api/v1/socai2/cases/{case_id}/tasks`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}` |
| 关键字段/关系 | `expected_scope_revision`<br>`operation_key`<br>`title`<br>`description`<br>`origin_result_id`<br>`origin_finding_id`<br>`source_refs`<br>`task.id`<br>`task.current_revision_id`<br>用户明确提交后，人工任务才关联原 Result/发现及 Case。结论内的问题没有独立任务生命周期。 |
| 保存与读回 | 保存/读取来源：`activities`<br>`activity_targets`<br>`task_revisions`<br>`tasks`<br>读回：`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>E38 创建后 E41/E43 读回，沿 E14 回到原 Result。助手问题保留既定后置状态。 |
| 页面通过标准 | 人工保存后在任务页出现并回链本轮，打开助手仅预填<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 需要人工确认时由用户创建任务并带来源；也可打开助手带本轮范围，明确发送后处理；不自动生成任务，不设置问题转派或关闭流程<br>不自动从未决问题生成任务；人工陈述与原始证据角色分开 |
| 实现差距/依赖 | 4173：人工任务部分按计划，助手分支随 F26 暂缓。无自动派发或独立问题状态流。<br>8181：待核问题有任务及草稿跳转。核是否完整传固定 Run/Result 来源，助手分支按暂缓。<br>HTTP：普通人工任务已实现，助手询问结果后置。产品从结果带来源创建的完整链待联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/operations/evidence/case-human-http-20261111-01/README.md`<br>`docs/operations/evidence/assessment-basis-sf06-20261120-01/README.md`<br>`docs/integration/product-api-data-requirements-20261114.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## AI 分析与执行明细

### F17-01 已保存分析过程

理解结论如何从材料得到。入口：固定 Run「AI 分析」的阶段说明、采用材料和历史问答。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通部分纳入，所列子范围后置；已有普通分析过程、材料与引用读取纳入；正式助手问答保存记录暂缓。；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_EXPLORATION_EVIDENCE`<br>阶段采用输出及保存依据<br>原来源工件<br>已保存问答和引用快照<br>部分/缺失状态<br>接口最小前提：一轮已有已保存分析步骤及实际输入/输出工件，或有失败仍保留材料的固定证据。 |
| 覆盖情况 | 有保存阶段、只有账本、部分正文缺失、正式保存问答 |
| 测试操作/方法 | 选本轮一段正文、材料和一条已存问答，核属于该轮及后续修改边界<br>接口核对：对照步骤序号、实际保存原件的归属及可用性。旧内容无法读取时保留实际错误。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `run.id`<br>`run.input_artifact_id`<br>`steps_url`<br>`artifacts_url`<br>`items[].kind`<br>`items[].input_artifact_id`<br>`items[].output_artifact_id`<br>`items[].content_url`<br>`artifact`<br>`availability`<br>已保存分析绑定父 Run 和实际步骤原件。历史 AI 保存记录有独立来源，现行新增保存回答后置。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`run_steps`<br>`runs`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>Case E12 或 A/I E32 返回目录 URL，按完整步骤、工件页及实际 content_url 查原件。 |
| 页面通过标准 | 按所选 Run 呈现分析段和引用，可进入执行明细或历史快照<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 阅读已保存分析、采用材料与引用；正式 AI 保存记录应显示当时问题及回答<br>未查、失败、查空不同；查空不证明安全；当前配置不回算历史能力/费用<br>读取产品已保存输入输出，不展示隐藏推理 |
| 实现差距/依赖 | 4173：原型已有阶段、对话快照及账本入口。读取已存问答不要求启用提问。<br>8181：阶段和保存输出读取已有，历史问答的原问题、回答和冻结来源展示待核。<br>HTTP：调查服务目录已接。平台统一读取目前按已验告警范围，通用 Case 和事件查看及助手保存分支仍有缺口。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 保留但不执行的接口 | `POST /api/v1/socai2/cases/{case_id}/ai/messages/{message_id}/save`<br>501或后置入口不计已实现。 |
| 可复用证据 | `docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F17-02 步骤账本

定位哪一步失败或未产出。入口：AI 分析的次级「执行明细」，按记录或类别查看。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_EXPLORATION_EVIDENCE`<br>保存步骤、序号和父子键<br>错误/状态和来源<br>分页或截断<br>同 Run 回链<br>接口最小前提：固定 Run 有层级、重试或失败步骤，至少一次可定位单步。 |
| 覆盖情况 | 计划、执行中、成功、跳过、失败、截断、可有父子步骤 |
| 测试操作/方法 | 用已有多步骤及失败记录核顺序/父子、类型筛选和返回，核部分载入语义<br>接口核对：复用既有完整步骤分页回执来核顺序与父子。产品只补一条正常的实际步骤跳转。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/alerts/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/incidents/{subject_id}/analysis-tasks/{task_id}` |
| 关键字段/关系 | `kind`<br>`limit`<br>`cursor`<br>`items[].id`<br>`items[].run_id`<br>`items[].seq`<br>`items[].parent_step_id`<br>`items[].retry_of_step_id`<br>`items[].state`<br>`items[].error`<br>`items[].artifact_refs`<br>`next_cursor`<br>`active_step`<br>同一 Run 的所有步骤按 seq 保存，父子和重试关系按实际 step_id。任务当前步骤关联该 Run 和步骤。 |
| 保存与读回 | 保存/读取来源：`analysis_attempts`<br>`analysis_tasks`<br>`artifacts`<br>`run_steps`<br>`runs`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks`<br>`GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/alerts/{subject_id}/analysis-tasks/{task_id}`<br>`GET /api/v1/socai2/incidents/{subject_id}/analysis-tasks/{task_id}`<br>GET steps 翻完整页，单步 GET 核归属，再用工件目录或原件 URL。摘要截断时继续读完整目录。 |
| 页面通过标准 | 同一 Run 的步骤顺序、父子和状态逐项读到，返回仍在该轮 AI 分析<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按本轮顺序和父子层级展开步骤、错误、状态及来源；不把运行结束当分析全通过<br>未查、失败、查空不同；查空不证明安全；当前配置不回算历史能力/费用<br>读取产品已保存输入输出，不展示隐藏推理 |
| 实现差距/依赖 | 4173：原型账本按已有顺序显示并支持筛选，真实层级与分页供给需要明确。<br>8181：有执行明细视图和步骤状态。正式排序、父子层级及截断继续核。<br>HTTP：完整原生账本已接。8181 Case/I 共用原件目录代理受现有主体限制。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/analysis-task-times-s5-20261120-01/independent-acceptance.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F18-01 步骤输入／输出原件

复核实际收到与返回的内容。入口：执行明细选择步骤的输入、输出、复用材料或初始工件。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_EXPLORATION_EVIDENCE`<br>冻结初始材料<br>步骤输入、输出、复用工件身份<br>工件可用性和内容格式<br>父步骤<br>接口最小前提：至少一个有实际输入与输出引用的固定步骤，已有受限或复用工件可用作对照。 |
| 覆盖情况 | 可读原件、仅目录、限制、未产出和缺失分别显示 |
| 测试操作/方法 | 从一个步骤分别打开可读工件与目录，仅返回条目时核空态等其他记录保持<br>接口核对：核同一 artifact 的身份、可用性和内容指纹在受控环境内相符。缺原件保留真实状态。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `step_id`<br>`items[].artifact_refs`<br>`items[].input_artifact_id`<br>`items[].output_artifact_id`<br>`items[].reused_artifact_id`<br>`items[].content_url`<br>`artifact`<br>`availability`<br>`content_json`<br>`content_text`<br>步骤实际输入、输出和复用来源各指原 artifact_id。跨 Run 复用按来源的父主体和 Run。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`run_steps`<br>`runs`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>从真实 step 或 artifacts?step_id 查元数据，沿 content_url 至 E15/E33 等相应读取。 |
| 页面通过标准 | 打开同轮对应工件，明确是参数、输入、输出或复用来源<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 打开所选工件，区分初始输入、步骤参数、复用原件；正文受限／缺失分别提示<br>未查、失败、查空不同；查空不证明安全；当前配置不回算历史能力/费用<br>读取产品已保存输入输出，不展示隐藏推理 |
| 实现差距/依赖 | 4173：原型资料目录与节选/全量可读。步骤参数和工件角色精准区分需核。<br>8181：步骤输入、输出、复用和工件查询均有入口。需核 URL 与产物角色及受限状态。<br>HTTP：底层完全可分页，当前产品跨主体统一目录及原件跳转需联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/assessment-source-http-sf06-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F17-03 当轮能力与投入

解释该轮能做什么和实际花费。入口：AI 分析或执行明细「运行详情与用量」和当轮能力。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_EXPLORATION_EVIDENCE`<br>冻结能力及配置快照<br>实际调用、token/费用和耗时<br>缺单位或可用性标志<br>当前配置变动<br>接口最小前提：已有冻结能力材料和已知使用量的 Run，未知用量按原历史回执。 |
| 覆盖情况 | 能力快照供给、版本不可用，调用次数和费用/用量分别可空 |
| 测试操作/方法 | 对照同轮历史能力和用量，核当前配置变化不会改旧记录<br>接口核对：只对照当时冻结版本和实际用量，界面空态对应缺字段。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `run.executor_version`<br>`run.input_artifact_id`<br>`usage`<br>`tool_calls`<br>`items[].provider`<br>`items[].implementation_version`<br>`items[].usage`<br>`items[].artifact_refs`<br>`items[].content_url`<br>显示同一 Run 保存的执行信息和工件中的冻结能力或配置来源。历史统计依据已记录用量。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`run_steps`<br>`runs`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>E12/E32 读摘要及引用，完整目录核实际步骤、provider 和原始工件。 |
| 页面通过标准 | 展示该轮能力、耗时和已保存消耗，保留当轮来源<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 阅读冻结能力摘要、调用和已知用量；未知费用不记零，不按当前配置回算旧轮<br>未查、失败、查空不同；查空不证明安全；当前配置不回算历史能力/费用<br>读取产品已保存输入输出，不展示隐藏推理 |
| 实现差距/依赖 | 4173：原型显示投入和 Deep 指标，冻结能力/费用未知的完整联验待安排。<br>8181：有冻结能力及部分计量展示。历史快照的完整消耗及费用缺供要逐字段核。<br>HTTP：调查服务已供保存来源，当前产品完整跨主体回链及能力摘要显示待验。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 查询与证据

### F28-01 查询目录和结果

知道访问了哪些来源。入口：固定 Run「查询与证据」目录、从正文引用精确进入查询。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_EXPLORATION_EVIDENCE`<br>同轮工具步骤及查询身份<br>参数、源、回执和工件<br>正文到查询的引用<br>不属于该轮的引用<br>接口最小前提：一个有已保存工具步骤、输入及结果或失败回执的实际 Run。 |
| 覆盖情况 | 未选择、指定查询、无查询、结果未导出或失败 |
| 测试操作/方法 | 从结论和 AI 分析打开同一个查询，核请求/回执及返回路径，另核错误引用<br>接口核对：读回同一步骤的真实参数、状态与原结果。标注工程对照结果，业务参数留受控环境。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `kind`<br>`items[].name`<br>`items[].actual_args`<br>`items[].state`<br>`items[].error`<br>`items[].returned_rows`<br>`items[].input_artifact_id`<br>`items[].output_artifact_id`<br>`items[].artifact_refs`<br>`items[].content_url`<br>查询记录属于已经执行或计划的工具步骤。步及工件在原 Run 下绑定来源、回执和原件。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_source_refs`<br>`artifacts`<br>`response_links`<br>`run_steps`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>从 steps 以 kind=tool 读目录，打开指定 step 和工件的 content_url。归档材料可复用。 |
| 页面通过标准 | 选定工具步骤展示实际类型、来源、参数、状态及返回，链接回原 Run<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按实际工具步骤查看来源、参数、状态、返回及错误，定位同轮请求／结果<br>未查、失败、查空不同；查空不证明安全；当前配置不回算历史能力/费用<br>读取产品已保存输入输出，不展示隐藏推理 |
| 实现差距/依赖 | 4173：原型可精确定位 query 并返回。正式结果只沿保存回执。<br>8181：工具表及结果抽屉可读保存参数/回执。按同 Run 和 query 复核正文精确落点。<br>HTTP：原生已有完整工具步骤目录。8181 Case/事件的完整读取及原始回执展示仍需配套核对。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F28-02 查询状态区分

避免“没查到”被误读为安全。入口：查询目录和证据详情中的真实工具状态。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_EXPLORATION_EVIDENCE`<br>各类已保存工具状态<br>计数 0、正数或未知<br>复用来源<br>未执行和缺正文回执<br>接口最小前提：复用历史跳过/失败、成功空集、复用或未查状态的固定回执，选现有可用代表。 |
| 覆盖情况 | 未执行、已跳过、失败、成功零行、有结果、复用/受限 |
| 测试操作/方法 | 同一组保存样本逐状态对照，成功零行和查询失败保留各自状态<br>接口核对：核同轮状态、是否有已执行证据及真实行数。成功零行、失败、未查和复用分别显示。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `items[].state`<br>`items[].error`<br>`items[].returned_rows`<br>`items[].reused_artifact_id`<br>`items[].output_artifact_id`<br>`availability`<br>以实际 Run 的执行状态、行数、复用来源和保存可用性共同描述查询。缺少执行回执时保持实际未知范围。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_source_refs`<br>`artifacts`<br>`response_links`<br>`run_steps`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>读工具步骤、对应原件及明确的外来源引用。失败或未执行保留原记录及理由。 |
| 页面通过标准 | 状态分列展示，并保留实际计数、错误或复用来源<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 分别显示未执行、跳过、失败、成功零行、复用；来源可用不代表本轮查过<br>未查、失败、查空不同；查空不证明安全；当前配置不回算历史能力/费用<br>读取产品已保存输入输出，不展示隐藏推理 |
| 实现差距/依赖 | 4173：原型有失败、空、跳过和未导出标签。复用与未知状态按正式字段独立验。<br>8181：源码区分复用、0 行、失败和跳过。需按 Run 类型及真实回执核未知和未执行表现。<br>HTTP：步骤状态和可用性已有，当前跨主体代理与页面实际空态需分项核验。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F18-02 摘要、原文与引用

让引用能够逐项复查。入口：查询与证据从条目、引用路径或材料目录打开原文。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P2、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_HOST_CANDIDATE`<br>`PKG_RESULT_EVOLUTION`<br>`PKG_EXPLORATION_EVIDENCE`<br>保存证据引用、原文工件及格式<br>节选/摘要状态<br>关联 Run 和查询<br>受限和缺失<br>接口最小前提：原 Run 有可读原文，另有现有的只存摘录、受限或正文缺失状态。 |
| 覆盖情况 | 完整、节选、仅摘要、受限、缺失或错误来源 |
| 测试操作/方法 | 分别打开有原文和只有摘要的引用，核精确轮次、路径与可用状态<br>接口核对：用选定的引用验证正文和引用位置。受控环境对照内容指纹与对应原始版本。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{identity}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/incidents/{identity}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` |
| 关键字段/关系 | `items[].artifact_refs`<br>`items[].content_url`<br>`source_refs[].source_path`<br>`source_refs[].row_keys`<br>`artifact`<br>`availability`<br>`content_json`<br>`content_text`<br>摘要、原始材料、任务修订与工件来源各自绑定其真实父主体、Run 与版本。 |
| 保存与读回 | 保存/读取来源：`alert_materials`<br>`alert_source_refs`<br>`artifacts`<br>`response_links`<br>`run_steps`<br>`task_revisions`<br>读回：`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{identity}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/incidents/{identity}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>`GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}`<br>沿步骤和引用走相应工件 Content、具体冻结 material 或历史 task revision。 |
| 页面通过标准 | 原件位置显示同一冻结范围的内容与限制，有返回同轮路径<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 打开证据原件、冻结材料或引用路径；只有摘要就说明，不换其他轮材料<br>未查、失败、查空不同；查空不证明安全；当前配置不回算历史能力/费用<br>读取产品已保存输入输出，不展示隐藏推理 |
| 实现差距/依赖 | 4173：与 F21-04 共用下钻，但此项从具体 Run 工具与证据入口验证。<br>8181：可打开来源引用和受限工件，需核摘要、缺失路径及同轮身份。<br>HTTP：正式原件读取可用。现产品跨主体来源解析及完整目录范围需定向补证。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/run-records-20261114-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>`docs/operations/evidence/assessment-source-http-sf06-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 调查关系图

### F19-03 历史图只读与来源

重现当轮实际关系范围。入口：固定 Run 的「调查关系图」，选择节点或边并查看来源材料范围。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_EXPLORATION_EVIDENCE`<br>`PKG_RESULT_EVOLUTION`<br>历史 Result 图和对应节点/边<br>来源工件与对应输入<br>无图记录<br>当前案较新图<br>接口最小前提：一份有图的历史结果及一份曾缺图的现存原回执。 |
| 覆盖情况 | 保存图、仅部分图、缺图、当轮跳过，历史只读 |
| 测试操作/方法 | 打开旧轮有图和另一无图轮，核节点来源及缺图提示，比较当前图不会替换旧图<br>接口核对：核换轮后的真实图身份、原节点边及来源并查看缺图空态。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `result.id`<br>`result.source_run_id`<br>`result.graph_artifact_id`<br>`artifact.id`<br>`availability`<br>`content_json`<br>历史图绑定所选 Result 的 graph_artifact_id 与来源 Run。图内引用保持原来源。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`results`<br>读回：`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>GET E14 后使用 E15 读该图源工件。 |
| 页面通过标准 | 呈现该次结果的图，节点、边、来源及范围可读，缺图保留空态<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 读所选 Result 的图、节点和边，聚焦／回查来源；缺图显示缺图<br>关联线不证明攻击因果，图结构不能冒充已确认结论 |
| 实现差距/依赖 | 4173：原型导入按当轮有无显示。保存与扩展属于当前案件探索。<br>8181：从固定 Run 图工件读取，空态显式。源材料仍需对照原轮。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/case-exploration-state-20261113-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F19-04 转入当前案件探索

继续查线索而不改历史。入口：历史关系图区或运行页的同案返回／当前案件关系图入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FROZEN`<br>`PKG_EXPLORATION_EVIDENCE`<br>`PKG_RESULT_EVOLUTION`<br>可回案的历史运行<br>主体无 Case 的运行<br>原图和当前图<br>当前案件关系图入口<br>接口最小前提：同一 Case 有历史图和当前底图的现成记录。 |
| 覆盖情况 | 保留历史、显式离开、无实际关联案、当前探索未保存 |
| 测试操作/方法 | 从历史只读查看来源，再显式转到当前案件图，核旧图的记录和返回路径<br>接口核对：核跳转前后父 Case、历史图工件及当前底图身份，复用原只读证据。 |
| 实际接口 | `GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-candidates`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-base`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `result.case_id`<br>`result.source_run_id`<br>`case_id`<br>`graph_state`<br>`graph`<br>`fingerprint`<br>`items[].matches`<br>历史图到当前探索以所选 Result 的实际 Case ID 跳转。当前图由当前底图入口提供。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`results`<br>读回：`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-candidates`<br>`GET /api/v1/socai2/cases/{case_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/exploration-base`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>打开 Case 后读 E67，按需 E66。回到历史保持原 E14/E15。 |
| 页面通过标准 | 当前案件图用于后续探索，历史 Run 与其图仍可回看<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 明确离开历史图进入案件关系图；历史图不扩展、不重写，关联线不证明攻击因果<br>关联线不证明攻击因果，图结构不能冒充已确认结论 |
| 实现差距/依赖 | 4173：原型有公共回案件/当前关系图分区。历史图直达当前探索的入口一致性仍待核。<br>8181：历史图已有「转入当前案件探索」链接和现案区分。验证不改历史。<br>HTTP：主体身份可经 E14 取得。当前 8181 通用 Run 上下文与探索旧入口仍有接线缺口。<br>无；按本项边界处理 |
| 责任/当前验收 | 前端（功能/交互/视觉）＋平台后端（转发）＋调查HTTP/核心（数据和保存）；本轮未执行，只完成规划 |
| 页面内操作 | 从历史图跳转到当前案 |
| 可复用证据 | `docs/operations/evidence/case-exploration-state-20261113-01/README.md`<br>`docs/operations/evidence/product-http-navigation-20261120-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 报告与响应

### F16-04 阅读报告及收尾说明

向同事交接该轮结果。入口：固定 Run「报告与响应」的调查报告及收尾材料入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FILES_AND_RESPONSES`<br>`PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>保存报告与 run_id<br>无正式 Result 的保存系统说明<br>失败工件和停止原因<br>接口最小前提：已有正确关联的报告一份，已有失败但保留系统材料的记录可复用。 |
| 覆盖情况 | 有报告、部分交付、无报告、失败或只有系统收尾 |
| 测试操作/方法 | 比较一条有报告与失败无正式结果的运行，核可读材料及无报告空态<br>接口核对：核报告正文和选择的 Run 一致，以及不完整记录的提示。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `result.report_artifact_id`<br>`result.source_run_id`<br>`result.closing_note`<br>`run.stop_reason`<br>`artifacts[].kind`<br>`artifact`<br>`availability`<br>`content_json`<br>`content_text`<br>报告绑定指定 Result/Run。失败时查该 Run 原有的保存报告或系统说明。Result 正文按实际保存状态读取。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`response_links`<br>`results`<br>读回：`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>若 E14 有报告指针读 E15。无 Result 时从 E12 或完整目录按原 Run 工件身份读取。 |
| 页面通过标准 | 显示该轮报告和实际保存收尾/失败材料的可读入口<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 打开本轮报告；无正式 Result 时仍可读已保存系统说明及失败材料，不补造结论<br>建议不等于已执行；无回执、失败、执行不明保留真实状态 |
| 实现差距/依赖 | 4173：原型报告区读原报告及缺失，系统收尾也可在调查发现/步骤读。入口关系需核。<br>8181：有原报告及缺报告提示，系统说明在调查发现，失败材料跨页入口需核。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 可复用证据 | `openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>`docs/operations/evidence/streaming-fullflow-20261116-02/final-validation.json`<br>`docs/operations/evidence/run-records-20261114-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F18-03 下载已有报告

便于离线交接和留存。入口：报告与响应中的「下载 Markdown」。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FILES_AND_RESPONSES`<br>`PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>已存报告内容、格式和 Run 身份<br>另一个无报告 Run<br>可在环境内核的文件摘要<br>接口最小前提：一个可读的已保存报告和原文件元数据。 |
| 覆盖情况 | 报告已保存、报告缺失、当前切轮 |
| 测试操作/方法 | 从有报告 Run 下载并核正文指纹，再打开无报告轮核下载不可用<br>接口核对：读回已存内容并对照下载文件正文、轮次与可用性。已有浏览器证据只覆盖原批动作。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` |
| 关键字段/关系 | `result.report_artifact_id`<br>`result.source_run_id`<br>`artifact.file_name`<br>`artifact.mime_type`<br>`artifact.sha256`<br>`availability`<br>`content_json`<br>`content_text`<br>下载由前端从已有可读报告内容生成文件，仍绑定原 Result/Run/工件。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`response_links`<br>`results`<br>读回：`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>依 E14/E15 获取原报告内容，前端下载按实际格式和可用性处理。 |
| 页面通过标准 | 下载指定 Run 的已存正文，缺报告无下载成果<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 下载已保存内容，保持轮次和来源；缺报告不能导出伪造的完整成果<br>建议不等于已执行；无回执、失败、执行不明保留真实状态 |
| 实现差距/依赖 | 4173：原型用已加载报告生成下载文件，实际正文保持同轮。<br>8181：按已读报告内容给下载，验同一 Run 的内容摘要及缺失状态。<br>HTTP：无单独登记的接口缺口，仍需实际页面/保存读回验收。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心（业务及保存）＋调查HTTP（合同）＋前端/平台后端（接线和整页）；本轮未执行，只完成规划 |
| 页面内操作 | 浏览器下载已有报告 |
| 可复用证据 | `openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>`docs/operations/evidence/run-records-20261114-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F27-02 响应建议卡片

让建议目标、理由和影响可评估。入口：报告与响应的响应建议卡，展开依据与目标。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通范围纳入规划，尚未执行验收；P1、P4 |
| 准备数据 | `PKG_FILES_AND_RESPONSES`<br>`PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>保存的建议、动作和目标标识<br>理由/影响<br>审批要求三态<br>只有建议无回执<br>接口最小前提：一份有明确目标与已保存建议的 Result，另可用审批字段未记录的原回执。 |
| 覆盖情况 | 有建议、无建议、审批要求明确需要/不需要/未记录 |
| 测试操作/方法 | 核每卡来自同轮建议，区分未记录审批要求及明确不需要<br>接口核对：核建议与父 Run、目标、来源和存储状态同源。界面体现审批要求空值。 |
| 实际接口 | `GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}` |
| 关键字段/关系 | `result.id`<br>`result.source_run_id`<br>`result.recommendations[].action_type`<br>`result.recommendations[].targets`<br>`result.recommendations[].reason`<br>`result.recommendations[].approval_requirement`<br>`result.recommendations[].source_refs`<br>`result.recommendations[].limitations`<br>`availability`<br>建议来自现有阶段结果或绑定的报告工件。动作、目标、依据和审批要求是独立字段。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`response_links`<br>`results`<br>读回：`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}`<br>`GET /api/v1/socai2/cases/{case_id}`<br>指定 Case Result 用 E14/E15，采用展示先读 E03 当前来源。告警和事件走 E24/E25。 |
| 页面通过标准 | 显示动作、确切目标、依据和审批状态，建议不变成执行记录<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 展示具体动作、目标、依据、审批要求；未记录审批要求与无需审批分开<br>建议不等于已执行；无回执、失败、执行不明保留真实状态 |
| 实现差距/依赖 | 4173：原型卡片已有建议、依据与部分审批展示，明确否与未记录需要联验。<br>8181：有目标、依据和审批要求三态。正式建议与输出字段逐项对照。<br>HTTP：已保存建议可读且有页面代表。不同主体的目标、审批要求空态与来源尚无完整产品联验。<br>无；按本项边界处理 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；本轮未执行，只完成规划 |
| 可复用证据 | `docs/operations/evidence/recommendation-display-sf05-20261120-01/README.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F27-03 审批与意见

明确是否允许某个动作。入口：对所选响应动作和目标的审阅批准/拒绝入口。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 整项继续后置，不执行；后置 |
| 准备数据 | 无独立业务HTTP调用；见UI动作/后置说明<br>绑定动作和目标的审批记录<br>决定者、理由及版本<br>拒绝与批准等待状态<br>接口最小前提：本期无执行数据要求。 |
| 覆盖情况 | 等待决定、拒绝后改动重提、批准待执行、范围变更重审 |
| 测试操作/方法 | 只审原型审批控件与数据需求。D06 重新启用后核决定与执行分离<br>接口核对：复用后置决定和既有缺口回执，核原型边界。 |
| 实际接口 | 无独立业务HTTP调用；见UI动作/后置说明 |
| 关键字段/关系 | 无独立业务HTTP调用；见UI动作/后置说明<br>原型保留具体动作、目标、意见和审批关联的需求。 |
| 保存与读回 | 保存/读取来源：无独立业务HTTP调用；见UI动作/后置说明<br>读回：无独立业务HTTP调用；见UI动作/后置说明<br>当前调查服务未提供审批保存与查询。 |
| 页面通过标准 | 记录审批决定、理由、动作和目标，批准后仍可分辨待执行<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按具体目标批准／拒绝并说明；批准绑定动作／目标，改变须重审；拒绝后修改重提，批准仅变待执行，D06 已确认<br>501、占位或按钮存在均不算业务完成 |
| 实现差距/依赖 | 4173：原型有本地审阅，冻结导入不可执行业务。正式响应审批整项暂缓。<br>8181：本次只定位调查报告的响应提案入口。正式审批及外部执行台不在暂缓解除范围。<br>HTTP：审批和真实执行后置。<br>业务响应审批，已后置 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；后置 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

### F27-04 执行记录与回执

确认实际做了什么。入口：报告与响应的具体动作执行回执区和其他回执。

| 项目 | 规划 |
| --- | --- |
| 范围/阶段 | 普通部分纳入，所列子范围后置；已有真实响应记录/回执只读纳入；新执行、重试和审批链暂缓。；P1、P4 |
| 准备数据 | `PKG_FILES_AND_RESPONSES`<br>`PKG_FROZEN`<br>`PKG_RESULT_EVOLUTION`<br>同轮动作标识与真实回执<br>成功、明确失败、未知及无回执状态<br>无唯一动作关联的记录<br>审批独立字段<br>接口最小前提：仅复用确有实际响应关联或回执的既有记录。没有已存回执时保留未验。 |
| 覆盖情况 | 已执行、明确失败、执行不明、只有建议或未配置关联 |
| 测试操作/方法 | 核已存回执只匹配授权的动作身份，读未知/无回执不会触发执行或重试<br>接口核对：用已有动作身份对照原回执返回、时间和错误。建议可读不计执行验收。 |
| 实际接口 | `GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` |
| 关键字段/关系 | `section`<br>`items`<br>`artifact`<br>`availability`<br>`content_json`<br>`content_text`<br>`result.source_run_id`<br>已有响应关联按实际告警或事件主体归属读取。Case 按对应 Run 的保存工件查看真实回执来源。 |
| 保存与读回 | 保存/读取来源：`artifacts`<br>`response_links`<br>`results`<br>读回：`GET /api/v1/socai2/{subject}/{identity}/records/{section}`<br>`GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}`<br>`GET /api/v1/socai2/cases/{case_id}/results/{result_id}`<br>`GET /api/v1/socai2/analysis-runs/{run_id}/artifacts`<br>现有告警/事件 E30 responses 及同源 E15/E33 可读取记录。有效动作身份和回执需由对应业务后端提供。 |
| 页面通过标准 | 按明确动作身份显示实际回执，未绑定记录另列，未知先读回<br>并满足总规划的功能、交互、数据、视觉四项整页标准。 |
| 业务通过标准 | 按动作身份关联回执；执行不明先核回执，不自动重复；明确失败后由人决定重试，无回执不宣称已处置<br>建议不等于已执行；无回执、失败、执行不明保留真实状态 |
| 实现差距/依赖 | 4173：原型已有按唯一动作 ID 配对及未绑定项。未知读回和失败后的显式决策保留为单独验证。<br>8181：报告可进入既有响应计划记录。逐动作匹配回执和执行不明的完整读回需与响应接口核。<br>HTTP：调查服务无 Case 通用响应聚合。真实新执行后置，现行回执正例缺证时保留未验。<br>真实动作及其执行回执，由动作供给方提供 |
| 责任/当前验收 | 调查核心＋调查HTTP＋平台后端/前端；遵守具体后置范围；本轮未执行，只完成规划 |
| 可复用证据 | `docs/integration/product-api-data-requirements-20261114.md`<br>`openspec/changes/complete-socai2-investigation-chain/es-ocsf-test-chain-20261124.md`<br>`docs/operations/evidence/run-records-20261114-01/README.md`<br>先核环境/版本及原件适用范围，不能直接继承当前页面通过。 |

## 接口目录及输入结构

下列70个引用操作按已审Schema和当前源码定位，其中2个501保留入口不计功能已实现。更完整的响应模型、请求字段和源码位置见合同JSON。接口存在不等于已经经8181转发接通。

| 方法与路径 | 请求结构 | 响应/状态 | 源码 |
| --- | --- | --- | --- |
| `GET /api/v1/socai2/alerts` | 路径：；查询：limit, before_id, cursor, q, severity, handling_status, owner_id, assignment_state, time_from, time_to, sort_by, sort_order；正文：无  | 200 / SubjectPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:61` |
| `GET /api/v1/socai2/alerts/{alert_id}` | 路径：alert_id；查询：；正文：无  | 200 / SubjectView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:121` |
| `GET /api/v1/socai2/alerts/{alert_id}/analysis` | 路径：alert_id；查询：limit, before_run_id；正文：无  | 200 / StagePage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis.py:26` |
| `GET /api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}` | 路径：alert_id, run_id；查询：；正文：无  | 200 / StageEntry / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis.py:64` |
| `GET /api/v1/socai2/alerts/{alert_id}/materials/{material_id}` | 路径：alert_id, material_id；查询：；正文：无  | 200 / ContentView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:158` |
| `GET /api/v1/socai2/alerts/{identity}/artifacts/{artifact_id}` | 路径：identity, artifact_id；查询：；正文：无  | 200 / ContentView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:207` |
| `GET /api/v1/socai2/alerts/{subject_id}/analysis-tasks` | 路径：subject_id；查询：limit, cursor；正文：无  | 200 / AnalysisTaskPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis_tasks.py:30` |
| `GET /api/v1/socai2/alerts/{subject_id}/analysis-tasks/{task_id}` | 路径：subject_id, task_id；查询：；正文：无  | 200 / AnalysisTaskDetail / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis_tasks.py:38` |
| `GET /api/v1/socai2/analysis-runs` | 路径：；查询：subject_type, subject_id, run_kind, intent, state, time_from, time_to, limit, cursor；正文：无  | 200 / RunDirectoryPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/run_directory.py:31` |
| `GET /api/v1/socai2/analysis-runs/{run_id}/artifacts` | 路径：run_id；查询：limit, cursor, step_id；正文：无  | 200 / RunArtifactPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/run_records.py:47` |
| `GET /api/v1/socai2/analysis-runs/{run_id}/steps` | 路径：run_id；查询：limit, cursor, kind；正文：无  | 200 / RunStepPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/run_records.py:32` |
| `GET /api/v1/socai2/analysis-runs/{run_id}/steps/{step_id}` | 路径：run_id, step_id；查询：；正文：无  | 200 / RunStepView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/run_records.py:40` |
| `GET /api/v1/socai2/cases` | 路径：；查询：limit, cursor, q, handling_status, severity, owner_id, assignment_state, metric, classification, time_from, time_to, sort_by, sort_order；正文：无  | 200 / CaseQueuePage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:85` |
| `GET /api/v1/socai2/cases/export` | 路径：；查询：columns, q, severity, handling_status, owner_id, assignment_state, time_from, time_to, sort_by, sort_order, metric, classification；正文：无  | 200 /  / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/exports.py:97` |
| `GET /api/v1/socai2/cases/{case_id}` | 路径：case_id；查询：；正文：无  | 200 / CaseDetail / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:121` |
| `GET /api/v1/socai2/cases/{case_id}/activities` | 路径：case_id；查询：limit, offset；正文：无  | 200 / RecordPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:274` |
| `GET /api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}` | 路径：case_id, artifact_id；查询：；正文：无  | 200 / ArtifactContent / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:265` |
| `GET /api/v1/socai2/cases/{case_id}/assessments` | 路径：case_id；查询：limit, offset；正文：无  | 200 / AssessmentHistory / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:245` |
| `GET /api/v1/socai2/cases/{case_id}/attachments` | 路径：case_id；查询：limit, offset；正文：无  | 200 / CaseAttachmentPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/attachments.py:32` |
| `GET /api/v1/socai2/cases/{case_id}/attachments/{attachment_id}` | 路径：case_id, attachment_id；查询：；正文：无  | 200 / CaseAttachmentView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/attachments.py:41` |
| `GET /api/v1/socai2/cases/{case_id}/comments` | 路径：case_id；查询：limit, offset；正文：无  | 200 / CaseCommentPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/comments.py:32` |
| `GET /api/v1/socai2/cases/{case_id}/exploration` | 路径：case_id；查询：；正文：无  | 200 / ExplorationSaved / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/exploration_state.py:45` |
| `GET /api/v1/socai2/cases/{case_id}/exploration-base` | 路径：case_id；查询：run_id；正文：无  | 200 / ExplorationBase / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/exploration_state.py:33` |
| `GET /api/v1/socai2/cases/{case_id}/exploration-candidates` | 路径：case_id；查询：alert_id, object_id, time_from, time_to, limit, cursor；正文：无  | 200 / ExplorationPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/exploration.py:23` |
| `GET /api/v1/socai2/cases/{case_id}/history` | 路径：case_id；查询：limit, cursor；正文：无  | 200 / HistoryPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:198` |
| `GET /api/v1/socai2/cases/{case_id}/management` | 路径：case_id；查询：；正文：无  | 200 / CaseManagementView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:296` |
| `GET /api/v1/socai2/cases/{case_id}/page-data` | 路径：case_id；查询：；正文：无  | 200 / CasePageData / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:151` |
| `GET /api/v1/socai2/cases/{case_id}/related-cases` | 路径：case_id；查询：limit, cursor；正文：无  | 200 / RelatedCasePage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:131` |
| `GET /api/v1/socai2/cases/{case_id}/results/{result_id}` | 路径：case_id, result_id；查询：；正文：无  | 200 / ResultDetailWithComparison / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:218` |
| `GET /api/v1/socai2/cases/{case_id}/results/{result_id}/adoption-preview` | 路径：case_id, result_id；查询：；正文：无  | 200 / ResultAdoptionPreview / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:227` |
| `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}` | 路径：case_id, run_id；查询：；正文：无  | 200 / RunDetailWithDirectories / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:211` |
| `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | 路径：case_id, run_id, artifact_id；查询：；正文：无  | 200 / ArtifactContent / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:256` |
| `GET /api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}` | 路径：case_id, run_id, material_id；查询：；正文：无  | 200 /  / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:287` |
| `GET /api/v1/socai2/cases/{case_id}/story` | 路径：case_id；查询：q, severity, limit, cursor；正文：无  | 200 / StoryPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/story.py:22` |
| `GET /api/v1/socai2/cases/{case_id}/tasks` | 路径：case_id；查询：limit, offset；正文：无  | 200 / TaskPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/tasks.py:45` |
| `GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}` | 路径：case_id, task_id；查询：；正文：无  | 200 / TaskView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/tasks.py:58` |
| `GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions` | 路径：case_id, task_id；查询：limit, offset；正文：无  | 200 / TaskRevisionPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/tasks.py:63` |
| `GET /api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` | 路径：case_id, task_id, revision_id；查询：；正文：无  | 200 / TaskRevisionView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/tasks.py:77` |
| `GET /api/v1/socai2/cases/{subject_id}/analysis-tasks` | 路径：subject_id；查询：limit, cursor；正文：无  | 200 / AnalysisTaskPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis_tasks.py:30` |
| `GET /api/v1/socai2/cases/{subject_id}/analysis-tasks/{task_id}` | 路径：subject_id, task_id；查询：；正文：无  | 200 / AnalysisTaskDetail / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis_tasks.py:38` |
| `GET /api/v1/socai2/incidents` | 路径：；查询：limit, before_id, cursor, q, severity, handling_status, owner_id, assignment_state, time_from, time_to, sort_by, sort_order；正文：无  | 200 / IncidentSubjectPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:89` |
| `GET /api/v1/socai2/incidents/{identity}/artifacts/{artifact_id}` | 路径：identity, artifact_id；查询：；正文：无  | 200 / ContentView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:223` |
| `GET /api/v1/socai2/incidents/{incident_id}` | 路径：incident_id；查询：；正文：无  | 200 / IncidentDetailView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:126` |
| `GET /api/v1/socai2/incidents/{incident_id}/analysis` | 路径：incident_id；查询：limit, before_run_id；正文：无  | 200 / IncidentStagePage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis.py:45` |
| `GET /api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}` | 路径：incident_id, run_id；查询：；正文：无  | 200 / IncidentStageEntry / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis.py:73` |
| `GET /api/v1/socai2/incidents/{subject_id}/analysis-tasks` | 路径：subject_id；查询：limit, cursor；正文：无  | 200 / AnalysisTaskPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis_tasks.py:30` |
| `GET /api/v1/socai2/incidents/{subject_id}/analysis-tasks/{task_id}` | 路径：subject_id, task_id；查询：；正文：无  | 200 / AnalysisTaskDetail / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis_tasks.py:38` |
| `GET /api/v1/socai2/people` | 路径：；查询：q, user_id, offset, limit；正文：无  | 200 / OwnerDirectoryPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:48` |
| `GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}` | 路径：subject, identity, run_id, artifact_id；查询：；正文：无  | 200 / ContentView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:186` |
| `GET /api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace` | 路径：subject, identity, run_id；查询：；正文：无  | 200 / TraceWithDirectories / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:173` |
| `GET /api/v1/socai2/{subject}/{identity}/records/{section}` | 路径：subject, identity, section；查询：limit, offset；正文：无  | 200 / RecordPage / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/pages.py:132` |
| `PATCH /api/v1/socai2/cases/{case_id}/management` | 路径：case_id；查询：；正文：CaseManagementUpdate clear_priority_override, description, expected_row_version, handling_status, operation_key, owner_id, priority_reason, priority_value, severity, severity_reason, tags, title | 200 / CaseManagementReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:301` |
| `PATCH /api/v1/socai2/cases/{case_id}/page-data` | 路径：case_id；查询：；正文：CaseDataUpdate classification, due_at, expected_row_version, operation_key, source, source_note | 200 / CaseDataReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:142` |
| `POST /api/v1/socai2/alerts/management-batch` | 路径：；查询：；正文：AlertManagementBatch changes, items, operation_key | 200 / SubjectBatchReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/subject_management.py:63` |
| `POST /api/v1/socai2/cases` | 路径：；查询：；正文：CaseCreate alert_ids, description, incident_ids, operation_key, severity, tags, title | 201 / CaseAllocationReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:78` |
| `POST /api/v1/socai2/cases/{case_id}/ai/messages` | 路径：case_id；查询：；正文：AskCaseAI conversation_id, operation_key, question | 501 / AIUnavailable / reserved_501 | `services/api/investigation_http/external_routes/case_ai.py:46` |
| `POST /api/v1/socai2/cases/{case_id}/ai/messages/{message_id}/save` | 路径：case_id, message_id；查询：；正文：SaveCaseAIAnswer conclusion, operation_key, title | 501 / AIUnavailable / reserved_501 | `services/api/investigation_http/external_routes/case_ai.py:56` |
| `POST /api/v1/socai2/cases/{case_id}/associations` | 路径：case_id；查询：；正文：AssociationRequest alert_ids, expected_scope_revision, incident_ids, operation_key | 200 / CaseAllocationReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:176` |
| `POST /api/v1/socai2/cases/{case_id}/attachments` | 路径：case_id；查询：；正文：CaseAttachmentCreate file_id, file_name, mime_type, operation_key, sha256, size_bytes | 200 / CaseAttachmentView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/attachments.py:27` |
| `POST /api/v1/socai2/cases/{case_id}/close` | 路径：case_id；查询：；正文：CaseCloseRequest acknowledge_open_tasks, expected_row_version, operation_key, reason | 200 / CaseManagementReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:312` |
| `POST /api/v1/socai2/cases/{case_id}/comments` | 路径：case_id；查询：；正文：CaseCommentCreate body, operation_key | 200 / CaseCommentView / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/comments.py:27` |
| `POST /api/v1/socai2/cases/{case_id}/evidence-index` | 路径：case_id；查询：；正文：EvidencePublish expected_current_artifact_id, expected_row_version, index, operation_key | 200 / CaseDataReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:156` |
| `POST /api/v1/socai2/cases/{case_id}/investigations` | 路径：case_id；查询：；正文：AnalysisSubmitRequest mode, operation_key | 202 / AnalysisTaskReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis_submissions.py:31` |
| `POST /api/v1/socai2/cases/{case_id}/members/move` | 路径：case_id；查询：；正文：MoveMembers alert_ids, expected_source_scope_revision, expected_target_scope_revision, operation_key, target_case_id | 200 / CaseMoveReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:187` |
| `POST /api/v1/socai2/cases/{case_id}/reopen` | 路径：case_id；查询：；正文：CaseLifecycleRequest expected_row_version, operation_key, reason | 200 / CaseManagementReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:323` |
| `POST /api/v1/socai2/cases/{case_id}/results/{result_id}/adopt` | 路径：case_id, result_id；查询：；正文：ResultAdoptionRequest acknowledge_pending_work, expected_review_token, operation_key, reason | 200 / ResultAdoptionReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/cases.py:238` |
| `POST /api/v1/socai2/cases/{case_id}/tasks` | 路径：case_id；查询：；正文：TaskCreate assignee_id, description, due_at, expected_scope_revision, operation_key, origin_finding_id, origin_result_id, result_scope, result_text, source_refs, state, title | 200 / TaskMutation / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/tasks.py:31` |
| `POST /api/v1/socai2/incidents/{incident_id}/diagnose` | 路径：incident_id；查询：；正文：AnalysisSubmitRequest mode, operation_key | 202 / AnalysisTaskReceipt / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/analysis_submissions.py:39` |
| `PUT /api/v1/socai2/cases/{case_id}/exploration` | 路径：case_id；查询：；正文：ExplorationSave base_fingerprint, base_run_id, base_snapshot_id, expanded_links, expected_snapshot_id, operation_key, view_state | 200 / ExplorationSnapshot / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/exploration_state.py:39` |
| `PUT /api/v1/socai2/cases/{case_id}/tasks/{task_id}` | 路径：case_id, task_id；查询：；正文：TaskEdit assignee_id, description, due_at, expected_row_version, expected_scope_revision, operation_key, result_scope, result_text, source_refs, state, title | 200 / TaskMutation / present_in_audited_schema_and_source | `services/api/investigation_http/external_routes/tasks.py:36` |
