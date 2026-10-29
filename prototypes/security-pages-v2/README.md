# AiSOC 前端 V2：事件与 AI 调查工作区

**2026-10-29 整合版入口：[全部 Case 数据](http://127.0.0.1:4174/#/cases?data=all)**；[仅看 AiSOC 调查](http://127.0.0.1:4174/#/cases?data=aisoc)。保留 12 个原设计案例，合并展示 3 个当前流程本地 Case、3 个原版历史本地 Case、1 个历史联合 Case。详情、查询、工件、报告和事件按同一来源关联。以下较早章节的数量是当时范围，当前总量见末节。

2026-10-29最新追加3个本地Case并补齐案件材料，见末节。此前2026-10-28同步21保存结果：3个事件、6个Run的92条过程与77份工件，详见末节。此前追加 AiSOC20 历史处理结果，详见下方“历史数据填充”；原有样例保留。2026-10-27更新：本轮融合修改见[功能分析第13节](../../docs/design/incident-investigation-page-analysis.md#13-2026-10-27-v2-融合修改)。2026-10-26用户授权先冻结 V1，再在新端口优化事件和整个 Case 工作区。版本入口与冻结校验见[版本说明](../FRONTEND-VERSIONS.md)，功能设计见[逐项分析](../../docs/design/incident-investigation-page-analysis.md)。

## 启动

```bash
cd /Users/lychee/Documents/project/socai2/prototypes/security-pages-v2
python3 serve.py --port 4174
```

无需安装依赖，也可运行 `npm start`；只监听 `127.0.0.1`。V1 使用 4173，V2 使用 4174 和独立的 `aisoc-workspace-v2` 本地状态键；不清理原版浏览器状态。

## 页面入口与本批变化

| 入口 | 内容 |
| --- | --- |
| [原设计事件概览](http://127.0.0.1:4174/#/incidents/262144/summary) | 汇总告警、判定、基础调查来源与关联AI调查；“告警阶段与时间线”进入原资料概况 |
| [原设计基础调查](http://127.0.0.1:4174/#/incidents/262144/triage) | 按告警查看已有判定、解释、关联调查并筛选；空值不生成材料 |
| [原设计事件 Attack Chain](http://127.0.0.1:4174/#/incidents/262144/chain) | 按种子告警、共享实体、前后时间窗口查看候选关系；无因果或恶意概率假设 |
| [全部 Case 工作区](http://127.0.0.1:4174/#/cases?data=all) | 首屏突出发现、依据、实际工作与后续处理；案件材料与协作保留 |
| [全部调查运行](http://127.0.0.1:4174/#/investigations) | 2 条原设计样例、6 条 socai2 实际运行与 6 条 AiSOC20 历史运行；无 Case 的 Run 可独立打开 |
| [实际运行](http://127.0.0.1:4174/#/investigations/d141b0e3-16cc-5a0b-8d7f-35159342efe6/overview) | 保存的输入、调查发现、阶段分析/Deep、查询与证据、攻击链与路径、可筛选调查记录、报告与响应 |
| [告警](http://127.0.0.1:4174/#/alerts) | 原设计和交互保持，52 条样例、6 条 socai2 记录加 6 条 AiSOC20 历史记录 |

选择一次 Run 后，所有调查页签使用同一 Run。Case 当前成员与本次输入分别展示；新增或移动成员不回写旧 Run 输入。明确指定不存在或不在当前范围内的 Run 时显示空态。Case 的调查计数、历史与正文使用同一关联规则。

Run 是否结束、交付是否完整、最终判定、首次分诊、停止原因、调用和 Tokens 分别展示。建议动作与实际执行分别展示。报告使用保存的 Markdown 原文，支持下载；原报告内的历史 `running` 等字段不重写为当前状态。

## 数据来源与边界

- `data.js`、`workspace-model.js` 为既有设计样例；不重新编造模型分析、调用时间、Token 或报告。
- `replayed-alerts.js` 保留 2026-10-25 六条重放的实际告警资料。
- `investigation-data.js` 从本地既有 `observed-final.json` 白名单投影 6 条 Run，不再次访问 20/21 或调用模型。实际输入取该次 `run.raw_alert`，摘要取 `run.alert_summary`，不由当前 Alert 重建。未输出凭据或完整模型 prompt。
- 调查链图读取同 Run 保存的 `attack_chain`、`attack_path`、`alert_graph`，分别显示状态、来源、时间、查询范围及原始结果。链为空、未关联 Case、查询失败、未记录分别表达，不以空图推断安全。
- 事件的 Chain 筛选仅演示已加载样例中的共享实体关系；不等同于 PostgreSQL 的服务端候选链算法，不生成服务端分数。调查中的实际链图保持原值。
- 图可达范围与 blast-radius 原始评分不等于确认受害范围或恶意概率。原有关系图、潜在路径及新 Run 工件视图分别保留。
- v1 工具轨迹可能只有 200 字符摘要，完整模型轨迹、实时服务更新、后端调查 v2 profile 和响应执行不在本批交付范围。实际样例 5 条 partial、1 条未升级调查，不能据页面完整推断调查质量通过。
- 所有管理交互仍只在浏览器本地保存；本批没有后端写回、创建实际 Case、启动调查或执行响应。

## 文件与验证

V2使用 `investigation-data.js`、`investigation-workspace.js` 和 `investigation.css`；本轮更新工作区、Case导航样式与 `app.js` 接线，`index.html`为本轮修改资源加版本号避免旧缓存。原数据、基础样式及旧工作区模块保持；本次告警候选检索增加来源环境/租户隔离，避免20与21同名主机互相混入。

```bash
npm run check
npm test
```

36 项定向测试通过，包括同输入下 291 次 V1/V2 告警 HTML 一致比较、15个 Run 的各6种视图、范围隔离、源字段及保存输入独立性。测试在仓库中与冻结的 `../security-pages-v1` 对照；单独复制本目录仍可预览，跨版本测试需要保留相邻 V1 目录。浏览器核验与独立审阅见[交付回执](../../docs/design/frontend-v2-verification.md)。

## 历史数据填充（2026-10-28）

新增入口：[Office脚本与可疑外联](http://127.0.0.1:4174/?review=20261028-data#/cases/local-aisoc20-1/overview)、[凭据访问与远程服务](http://127.0.0.1:4174/?review=20261028-data#/cases/local-aisoc20-2/overview)、[服务账号读取与归档外传](http://127.0.0.1:4174/?review=20261028-data#/cases/local-aisoc20-3/overview)。三个 Case 均标明“本地整理”；源后端六告警的 Case 均为空，不据此创建后端 Case 或改变各 Run 的单告警输入。

`aisoc20-data.js` 为离线投影，`recorded-examples.js` 追加到浏览器状态，不替换原样例或本地编辑；`aisoc20-data.manifest.json` 保存来源文件摘要。六条记录是2026-10-24合成演示输入的真实处理结果，包含6 Run、71条过程记录、34条查询记录、27份工件目录、5份原文报告、36次调用/117286 tokens。5次partial、1次分诊后关闭；不表示真实攻击或模型结论质量通过。

阶段 skipped 单独展示；工件目录没有ID/hash/保存时间的部分显示未记录。源记录无单次Run图工件，案件关系页展示已有全局图中对应告警的直接关系（21节点24边的受限集合，按当前成员再筛选），不当作Run使用的证据或因果。无Explain、库存关系、附件、人工活动时保持空态。

离线重建（源原件仅保留于本机，不随前端包导出）：

```bash
python3 tools/testdata/export_aisoc20_ui.py \
  --source .local/verification/alert-reset-replay-20261025/source20.json \
  --evidence .local/aisoc20/showcase-20261024/evidence \
  --output prototypes/security-pages-v2/aisoc20-data.js \
  --collected-at 2026-10-27T23:54:11Z
```

从仓库根目录运行。`collected-at` 是本地整理时间，不是后端Case创建时间。来源和字段逐项映射见[功能分析第14节](../../docs/design/incident-investigation-page-analysis.md#14-2026-10-28-aisoc20-历史结果填充)。只读来源，未新发业务请求、模型、重放或部署；所有交互仍在浏览器本地。


## 历史实际 Case 联合调查（2026-10-28追加）

[打开原Case的攻击路径](http://127.0.0.1:4174/?review=20261028-case-r1#/cases/82b1246f-9f34-463c-8c2d-27d2b075c741/investigations?run=e998308a-a353-4647-99f6-10f94ced0ecf&view=graphs&graph=attack_path)。这是2026-10-21已创建Case的三条测试输入及实际联合调查；保留原Case/Run关系，成员后续变更不抹去历史。包含5攻击链候选、11节点15边路径、16图可达对象、4阶段、29过程、7工具记录、4工件及报告。Run已结束，交付完整性未记录，3建议无执行记录。原20无Case记录和旧样例继续保留；总计67告警/16Case/15Run。

`persisted-case-data.js`由已有本机回执离线导出；Agent内部Run ID与持久Run不同，已通过29条audit/事件完整一致和报告核对关联。原事件时间与Run起止存在8小时差异，未推测修改。具体字段与边界见[功能分析第15节](../../docs/design/incident-investigation-page-analysis.md#15-2026-10-28-已持久化-case-的联合调查样例)。

从仓库根目录重建：

```bash
python3 tools/testdata/export_persisted_case_ui.py \
  --source .local/aisoc21/attack-context-20261021/case-v2 \
  --output prototypes/security-pages-v2/persisted-case-data.js
```

只读取历史文件，不调用业务服务或模型。原件不随前端目录交付；manifest保留来源hash。

## 2026-10-28 告警流程数据同步

[查看本批三个事件](http://127.0.0.1:4174/#/incidents?q=DEMO)。将10月25日21环境保存的六条告警按Fusion incident_id追加为3组；原12个事件保留，总计15个。详情按成员展示来源、分诊、对象、关联链、调查入口和处理活动；事件状态/负责人未记录，优先级空。名称、说明与最高严重程度是成员事实的展示聚合。

六个Run补齐92条过程（原81条，新增6个模型调用记录、5个用量记录），77份工件提供31份完整内容、40份节选、6份仅元数据；原49个工具记录保持。提示词和隐藏推理不导出；来源hash指向完整原件。五次Graph部分交付、一次分诊关闭，五份Path未关联Case的跳过状态保留；没有自动补Case或后端写入。原20和历史联合Case样例分别保持。

本次是本机保存结果的离线同步，采集于2026-10-25 11:59:33（上海），不是实时后端接入。重建命令（在仓库根目录执行）：

```bash
python3 tools/testdata/export_alert_flow_ui.py \
  --source .local/verification/alert-reset-replay-20261025/replay/observed-final.json \
  --output prototypes/security-pages-v2/alert-flow-data.js \
  --organized-at 2026-10-28T23:51:56Z
```

源原件不随公开前端输出。投影清单见 `alert-flow-data.manifest.json`；逐区域说明见[功能分析第18节](../../docs/design/incident-investigation-page-analysis.md#18-2026-10-28告警流程数据同步到-v2)。52项测试通过，其中9项覆盖本批；仅改标题保留未知字段，重置立即恢复三个真实组。浏览器查看与独审回执见[验证文档](../../docs/design/frontend-v2-verification.md)。

## 2026-10-29 本地Case材料补齐

[打开3个新增Case](http://127.0.0.1:4174/#/cases?q=local-socai2)。按已保存Fusion组整理，源Case仍为空；本地ID显式带local前缀，原16个Case保留，共19个。没有改变6条原告警和6个Run的源归属，没有执行新调查。

案件首页汇总每次Run的分诊、调查判定、输入和partial状态；证据页可按Run展开原工件，查看工具和报告；关系图按当前成员显示原始对象；处理活动回查源Run。合计92过程/49工具/77工件/5报告。当前成员与初始引用分开，移除成员不抹去已有Run，源输入保持。

任务、评论、附件和执行没有源记录时不生成。初始状态New是本地集合状态；组织时间、源采集时间分开。日期预置截至已保存案件最新创建日期（本批10月29日），自定义时间保持。上方离线重建命令须保留 `--organized-at`，该值为组织时间而非后台Case创建时间。

59项前端测试通过，字段与验证边界见[功能分析第19节](../../docs/design/incident-investigation-page-analysis.md#19-2026-10-29将已有材料补入本地-case-工作区)及[V2回执](../../docs/design/frontend-v2-verification.md)。


## 数据整合交付（2026-10-29）

以这个目录和 4174 为统一版本，不需要切换另一个前端。

| 数据 | 已保存 AiSOC 材料 | 原设计案例 | 合计 |
| --- | ---: | ---: | ---: |
| Case | 7（6个本地集合、1个源系统历史Case） | 12 | 19 |
| 告警 | 15（当前6、原版20的6、历史联合3） | 52 | 67 |
| 事件 | 6（当前3、20历史3） | 12 | 18 |
| Run | 13 | 2 | 15 |

13个保存Run共有192条过程、90条工具记录、108份工件目录、11份报告；各自保留原输入、首次分诊、分析判定、停止原因和完整性。工件目录不保证都有正文：当前流程77份保留先前正文/节选规则，20部分仅目录，已有报告和查询返回通过对应Run查看，不新增/补造prompt或结果。

- Case列表全部数据共存，AiSOC排在前面，可按AiSOC/原设计筛选；列表指标以当前筛选为准。
- 全部7个保存Case的案件证据页汇集告警来源、逐Run工具记录/工件/报告；活动汇集192条已保存过程，不补人工操作。6个本地Case概览展示其全部Run；历史联合Case保留原联合分析首页。
- 20新增3个事件视图按告警原incidentId/环境/租户汇集，成员分别2/2/1；第6条没有事件ID，保持未关联。历史联合Case也未补造事件。未知事件管理值保持未知。
- Case与实际成员事件双向跳转。当前6条replay告警缺顶层来源元数据，互链由alertFlowData的精确成员/事件/租户/环境投影核对。失效Case/事件详情地址显示未找到，不能回到第一个原样例。
- 原Run引用不随成员删除而消失；20集合补充已保存来源Run引用和租户锚点，本地成员/标题/管理编辑保持。sourceCaseId、原Alert.caseId和Run输入不改写。

本批65项直接测试通过，包含原告警291次HTML一致比较；浏览器核列表、历史Case材料、工具、双向事件入口和历史Path。无后端连接更新、Case写入、模型调用、部署或Git提交。当前数据是既有测试输入的实际处理结果，不是新同步的线上库存。
