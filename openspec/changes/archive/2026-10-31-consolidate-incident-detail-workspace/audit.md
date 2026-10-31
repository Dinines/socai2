# 2026-10-31 事件详情合并与职责聚焦回执

## 交付范围

事件主要展示多告警汇总、可核对的关联依据、对象关系；进一步判断进入 Case。移除事件切换，说明/信息合一，阶段/时间线入概览，攻击故事直接展开，关系/链统一为关联分析。当前导航收敛为5项，旧链接及原材料可回查。

新增无Case时的本地创建/关联入口，默认已有Case页签、最近7条可搜索、新名称默认事件名，确认并集加入当前成员并跳转。已有一个Case直接打开、多个选择；已有Case不重复新建，不自动启动Run、不修改告警判定或事件状态。实际来源Case同源约束保持。新Case按真实材料读取，任务/附件为空，partial不会变完整。

仅本地4174页面/测试/交接，不改后台、模型、真实查询/重放、部署或Git提交推送。历史完整样例和真实缺口均保留，未改图控制器。

## 直接验证

- `npm --prefix prototypes/security-pages-v2 run check` 通过。
- `npm --prefix prototypes/security-pages-v2 test`：81项通过、0失败。包括实际/演示Case创建及重载、并集关联、重复新建拦截、不同来源拦截、真实13Run保持；共享对象按ID及不同告警去重，旧context/chain链接、seed/window、实际发生时间缺值保持。
- 新建/保存写入只在VM合同中验证，未在用户浏览器中增加测试Case或改成员。浏览器实点事件→已有Case及返回、关联依据→告警侧栏、统一告警链种子切换和原Run对应；完整演示图谱中等级筛选15→2→15，控制器仍有效。
- IAB宽屏与700px检查通过，700px文档clientWidth/scrollWidth均685；原图及概览卡均在页面范围。宽屏和窄屏截图在 `.local/verification/incident-detail-20261031/`（overview-final、relationships-final、narrow-final、narrow-graph）。截图保留用户现有浏览器数据，不用重置样例抹除历史编辑。
- 初始集合仍67告警/18事件/19Case/15Run（13真实）。备份在 `.local/versions/incident-detail-before-20261031/`，8文件hash已复核。

## 失败与修正

初轮兼容加载测试未提供alertFlowWorkspace，概览的直接started引用已改沿现有assessment结果；后来职责收敛撤去判定指标，无额外依赖。旧布局断言按用户新语义更新；时间线改回既定最新在前、缺值置后。初轮新增测试跨VM数组原型比较差异改为Array.from，两边数据内容未改。

独审发现从事件新建Case走旧演示路径，误显示2个默认附件和Completed，修为明确incidentCreated本地身份、空协作资料及既有Run读取视图。继而发现演示事件没有来源身份，过严同源条件会丢2条设计Run；修为实际来源严格匹配，无源演示按精确成员关联。两项均补创建/重载/各视图合同并复审通过。

## 独立结束审计

未参与实现者 `/root/current_workspace_review` 最终限定 **ACCEPT / 0必须修**。7项定向合同及确认保存/跳转通过；18事件×12页=216渲染、15Run×6=90渲染无异常且无数据改写。8份历史hash一致；初始store、13实际Run、19既有Case概览及告警列表保持。最新宽窄屏和图截图无明显问题。

结论仅覆盖本批本地UI及Case关联交互，不代表后台创建/关联/调查服务已接通，亦不代替旧统一图谱change整体验收。

## 归档完成

已归档为2026-10-31-consolidate-incident-detail-workspace，同步1条主规格及4个场景。归档后全部当前规格/活动change校验9/9、历史归档46/46通过，git diff --check通过。未创建Git提交或推送。
