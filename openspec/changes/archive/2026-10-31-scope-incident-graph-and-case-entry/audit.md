# 事件单图、Case入口及追加队列口径：结束回执

日期：2026-10-31。本批仅4174本地页面与交接，不改后台、源数据、真实Run、模型或部署，不提交推送。

## 已交付

- 概览保留事件说明、ATT&CK阶段、时间线/关联依据，撤重复“有哪些关系”图；关联分析仅一个当前事件图，无链切换、跨事件范围或潜在路径控件。旧chain及view=chain链接兼容单图。
- renderer限制事件范围，残留associated/blast/path状态不能扩范围。Case/Run的Attack Chain、Attack Path及原材料保留。
- 无Case按钮“新建Case”默认new表单、事件标题和全部当前成员；可改选关联已有。仅显式确认保存本地并集，保其他成员与历史，不启动Run；已有Case进入或选择。
- 用户随后追加：告警/事件及同名Case摘要统一“涉及资产”，只改名字、不变取值。首卡改“处理中的事件”，按effective In progress计数，初始5；说明“已开始处理，尚未解决”。原7是关联调查口径，已移除。原右侧四统计15/4/0/13保持。

## 历史与直接验证

改前6文件及SHA：.local/versions/incident-scope-before-20261031；追加前4文件及SHA：.local/versions/incident-labels-before-20261031。V1、原样例、67告警/18事件/19Case/15Run（13实际保存）保持。

语法检查通过，88项前端测试通过；新增2项覆盖所有事件新旧路由/残留范围、无Case默认与确认/取消/重载。原统计合同改为有效处理状态，不查询Run；V1/V2的291告警呈现只允许列头“涉及资产”这一授权变化，其余逐字保护。补负责人取消分配后仍按处理中计数的断言，最终1项定向复核通过。

过程中保留两次测试修正：新Case重载会恢复原来源Case，进入入口可为“选择Case”，因此初稿仅允许“进入Case”的断言更新；追加资产列名导致旧V1逐字合同首轮87/88，改成仅列头定点转换后88/88。没有为通过测试重置或改源数据。

IAB：Office概览0图/关联分析1图、当前2告警与8条已有关系、旧chain深链显示同一图；Case17420原始Chain2候选/Path8节点10边可读。700px图详情下移，文档宽及scrollWidth均685。首卡5与最终说明、告警/事件资产列名可见，追加卡片窄屏同样685无页面横溢出。截图graph-final.png、narrow.png、queue-final.png、queue-narrow.png在.local/verification/incident-scope-20261031。

初始18事件均已有Case，无Case写入流程只在隔离VM验证；浏览器不删Case/不创建测试数据、不重置既有编辑。验证使用独立后台tab，未继续操作用户正在使用的tab。

## 独立审计

未参与实现者current_workspace_review主批限定ACCEPT/0必须修：5定向合同、6备份SHA；162次真实注册残留handler调用保持事件范围；114个Case页及75个Run图视图与改前逐字等价；15Run及源数据不变；确认创建/取消/重载、不启Run通过；已看图宽窄截图。此结果不替代旧统一图谱change整体或后台验收。

追加窄审首轮发现字幕“已分配负责人，尚未解决”不能覆盖后续取消分配但状态仍处理中的合法事件；改为“已开始处理，尚未解决”，未改生命周期。最终限定ACCEPT/0剩余必须修：8定向校验、4追加备份SHA、76处页面/侧栏除授权文案及首卡外等价、18事件context及store/Run/原四统计保持。规格、README、分析22.9/22.10及验证记录已同步。

## 归档

2026-10-31已执行openspec archive scope-incident-graph-and-case-entry --yes，3条MODIFIED合同同步成功，tasks全完成；封后frontend-versioned-investigation-workspace主规格strict及git diff --check通过。只归档本批，不追认其他未完成change。
