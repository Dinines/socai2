# 前后端对接可行性评估

用户随后明确只以数据库数据承载作为推进标准；最新结论见[页面数据覆盖核对](page-data-coverage-20261106.md)。下文实时接口/页面接线问题保留为技术参考，不作为数据层阻塞项。

2026-11-06，基线源码`5eacb314`，工作区含尚未提交的R1—R8规划。用户要求评估能否对接。本批仅核源码、接口合同、既有测试与本机只读HTTP；未修代码/配置、改页面、启动模型或写业务数据库。

**结论：能够按既有页面继续对接，核心数据和接口已经具备；当前真实导出展示可用，原页面完整实时读写尚未完成。** R1—R8可以在后端内部演进，前提是稳定业务字段及语义，并对内部工件版本做投影适配；不能仅凭JSON顶层字段同名就保证页面完全不受影响。

## 已具备的接线

下表HTTP路径均以`/api/v1/socai2`为前缀；有接口不等于当前原页面已经调用，也不等于真实模型判断正确。

| 功能 | 后端出口/保存来源 | 原页面及接入状态 |
| --- | --- | --- |
| Case队列/四指标 | `GET /cases`，CaseQueuePage | 服务模式有请求/呈现；原模式由保存导出适配，尚非统一实时数据入口 |
| 案件资料/当前判断 | `GET /cases/{id}`；cases.description与current_assessment.value.conclusion | 真实导出可读，服务模式有读取；必须保持背景、当前判断、执行原因分字段 |
| 历史/每轮结果/过程材料 | `/cases/{id}/history`、`/runs/{run}`、`/results/{result}`及Run下artifacts/materials | 两种模式均有对应读取能力；unknown、partial、覆盖/依据状态有合同 |
| 关系图/故事/对象证据 | 保存的C5图工件、原始材料、Result/H/活动及来源 | 原模板能用导出展示；服务模式Case故事/图/证据及Run图入口尚未接成对应画面，不能称全页实时对接完成 |
| H人工任务及版本 | `/cases/{id}/tasks`的GET/POST、`/{task}`的GET/PUT及revisions | 后端合同与服务模式表单已有；完成范围、双版本和冲突有测试，实际C→H→下一C质量仍未验收 |
| 创建Case/关联/移动/准备启动 | `POST /cases`、`/associations`、`/members/move`、`/baseline/prepare`、`/runs/{run}/start` | 服务模式已调用，原导出页本地操作不能声称写回服务；启动比较参数仍有J2缺口 |
| 告警/事件及A/I详情 | `/alerts`、`/incidents`及详情/records/analysis/trace/artifacts | 后端有出口，原导出页可展示；服务模式根入口只实现Case工作区，不等于告警/事件全部实时接入 |
| 管理字段和Q | Case已存负责人/状态/严重程度等可读；Q三个入口501 | 当前没有完整Case管理更新接口；Case公开合同无classification，导出“未设置”不是模型结论映射；Q保持明确暂缓 |

依据：[Case合同](../../../services/api/app/socai2/case_contracts.py)、[Case路由](../../../services/api/app/api/v1/endpoints/socai2_cases.py)、[H路由](../../../services/api/app/api/v1/endpoints/socai2_tasks.py)、[告警事件路由](../../../services/api/app/api/v1/endpoints/socai2_pages.py)。

## 对接缺口及影响

| 编号 | 已核事实 | 影响与建议 |
| --- | --- | --- |
| J1 / 实时连接前必修 | 本机API `/livez`、`/readyz`均200，OpenAPI可读；从`http://127.0.0.1:4174`请求Case API的OPTIONS返回400、`Disallowed CORS origin`、无Allow-Origin | 后端在运行，浏览器跨域会被阻断，属于允许来源配置。正式联调时配置明确页面origin或同源代理，核GET及JSON写请求的预检、认证与权限；不放宽为任意来源。本次未改配置或重启 |
| J2 / 服务模式多轮比较必修 | `service-workspace.js:248`启动参数固定`comparison_result_id:null`；`baseline_delivery.py:50`在已有历史而未选比较时返回not_selected | H后虽可开新轮，却不能由此入口取得明确的指定轮次比较。当前驱动/API可先显式传入合法Result；服务入口后续需绑定明确比较基线并冻结，不按“最新时间”猜测，也不把未比较显示成无变化 |
| J3 / 同案增量读回需明确策略 | `socai2-recorded-import.js:199`按ID只追加，重复Case不更新；内存探针确认新Run可加入、旧Case判断仍保留 | 这是保护本地编辑的已定行为，不是入库失败。固定完成快照可验收；若同案多次刷新需定义只读来源快照更新与用户本地编辑的分离，保持Case身份及旧版本，不清浏览器或覆盖编辑来伪造同步 |
| J4 / 完整实时页面待接 | `app.js:4`的service分支先返回，使用独立service渲染器；共享外框不等于复用全部原页面。`service-workspace.js:129`禁用story/attack/evidence/activities/comments，Run graphs也未开放 | 保留原页面布局，优先让读取适配服务于原组件；无需建立第三套页面。补实时读取是后续范围，本阶段仍可通过真实导出完成产品回查，不把这些禁用页说成已接通 |
| J5 / 内部算法演进须保适配 | 导出器`runView`直接识别C3/C5/C6及`baseline-graph.v1`，读取`analysis.summary`；部分公开嵌套结构仍是通用dict | 新主张Schema/图版本不能直接替换旧工件后就假设原页无影响。按R7把新旧内部版本投影到稳定业务视图，冻结结论、发现、图节点/边/来源、H、coverage/freshness及空值语义，用新旧例做契约检查；不是要求新增数据库或重做页面 |
| J6 / 功能范围和数据质量独立 | 创建时可设置部分管理值，但现有Case路由未实现完整管理更新；Q仍501；R1事实扩大及R2 H容量未修 | 这些分别是功能边界和算法质量问题，不能由连接通畅推定完成。当前判断不得代替管理分类/状态，已显示结论不等于结论正确；继续按既有tasks验收 |

代码依据：[服务工作区](../../../prototypes/security-pages-v2/service-workspace.js)、[页面入口](../../../prototypes/security-pages-v2/app.js)、[导出适配](../../../prototypes/security-pages-v2/socai2-recorded-import.js)、[比较输入](../../../services/api/app/socai2/baseline_delivery.py)、[CORS配置](../../../services/api/app/core/cors.py)。J1只证明本次检查时该origin被拒，不宣称所有服务地址或同源部署均不能连接。

## 稳定的前后端分工

前端消费“当前判断、逐轮结果、图谱/材料、任务与操作状态”。模型/提示词/Tool只生成内部工件；后端负责校验、持久化及版本投影。尤其保持：

- Case背景＝`cases.description`；当前判断＝当前采用版本的`case_assessments.conclusion`；技术原因＝Run/Step/工件。不能用最新原答或错误消息替代判断。
- 相同ID继续指向相同来源实体；源环境/租户、Run/Result/H版本及引用不串联。图边保来源，共现不变成因果。
- coverage只讲适用成员，freshness只讲已跟踪依据是否变化；unknown不补零，系统收尾不冒充模型accepted，管理状态与调查结果分离。
- 新增内部工具和主张不迫使页面认识新执行细节；reader/export负责版本适配，旧结果保持可读。含义或公开结构确需改变时先更新接口合同和适配验证。

因此，后续修改提示词、增加查询、换模型可以保持前端布局；保障来自这层稳定业务合同及实际兼容验证，当前代码尚未把全部内部依赖隔离完。

## 本次核查与推进建议

1. 原导出读回套件6项通过；服务工作区12项通过，合计18个不同用例。首次服务套件8项因沙箱不允许监听本机端口而失败，授权同一模拟HTTP夹具监听后12项通过，未改代码。这是测试环境限制，不能归为API业务故障；模拟测试也没有验证真实API的CORS。
2. 本机只读HTTP：API livez/readyz/OpenAPI均200，OpenAPI登记33条socai2路径；无凭据Case GET为401，静态页面4174为200；指定origin跨域预检400，已读明确拒绝原因。初用不存在的`/healthz`得到404，按实际注册的`/livez`复核200，不作为服务故障。未使用凭据、未读业务响应、未调用模型。
3. 一项内存探针复现J3：相同Case ID重导出不刷新判断、新Run被追加、本地标题保留；无持久副作用。本轮没有浏览器全页检查或真实服务写入，不能宣称全链实时验收。
4. 下一实施仍优先R1/R2。读取层同时固定上述字段映射及新旧版本适配；按既有阶段目标先用完整新快照走原页回查。需要实时联调时先解J1，再补J2与同案刷新策略、复用原组件接其余读取；无需等待更复杂后台架构，也不把实时表单改为当前导出验收前提。

对应现有任务3.10/3.16（质量与容量）、3.7（真实模型/H链）及3.12（对接/回查）。19/26与48/50不变，无归档/提交推送；J1—J6是评估发现，尚未实施。

独立评估复核：未参与撰写的`/root/review_design_audit`只读核对J2—J6与源码、9个相对引用、strict及diff检查，结论 **ACCEPT，0必须修**。J1实时HTTP和18项测试沿用本次核查回执，独审未重复连接服务或运行模型；此结论只确认评估准确，不核销对接实现、模型质量或4.1结束审计。
