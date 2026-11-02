# Case资料与调查图谱设计对齐回执

2026-11-02，仅本地V2呈现与阅读状态。先复现点击Attack Path后来源材料收起；原fix-investigation-source-material-disclosure仅建立方案未改代码，用户扩展要求后更名并形成当前三项规格，strict通过后实施。改前11文件见`.local/versions/graph-source-disclosure-before-20261102/`，此前工作和后台未提交文件保持。

## 交付

- 21个Case使用同一案件资料模板：成员告警/对象/告警证据/调查记录口径统一，原17420摘要卡呈现与详细信息/ATT&CK卡保留。背景、成员、材料和人工跟进只汇总现有内容，不造Case联合结论或用工件充告警证据。
- 所有Case案件图只显示当前成员告警—对象显式关联，原圆形三栏、筛选/分组/布局/缩放/来源详情保持；旧扩张状态强制关闭。历史Path/Chain/可达范围及原输入留Run。工作模型源文件和事件行为未修改。
- Run图前置四种图谱入口，模式实际驱动候选图层及告警列表；来源details状态独立于重绘，原生toggle只更新临时阅读状态，同Run模式切换保留滚动，其他导航仍回顶。内层详情和断开/其他Run的toggle不改变当前外层状态；不写store。

## 检查

语法检查通过；完整115项全通过。首次旧112项有6处与新布局/范围相冲突的断言失败，按新合同改为统一资料、当前成员关系及来源块内候选计数，保留原Run历史/节点/边检查。追加3项后114/115，原因是调整旧case-info断言时漏了if花括号导致断言误跑attack分支；修正后最终115/115。日志`/tmp/case-align-tests-final.log`；失败不计通过。

新增直接检查覆盖所有21Case资料同结构/相同指标语义和无写入，所有Case当前成员显式图关系且Run保持，来源展开/手动收起/重绘/跨Run/外来toggle/滚动谓词。独立current_workspace_review运行case-reading、investigation-graph、persisted-case共22项，补充VM验证All/Chain/Path/range实际图层/列表切换、历史Case路径全节点仍可达、detached/foreign toggle隔离；代码限定ACCEPT、0剩余必须修。10份受保护源/模型文件与HEAD逐字一致，V1及services无差异，diff-check通过。

## 浏览核查

- 原Path点击后外层收起已复现；修后Path→Chain、来源告警打开/关闭、手动收起后缩放均正确；改Path自动展开且候选图层关闭。内层“查看保存的关系数据”只展开自身。另核关联范围及其原文展开，外层持续展开。
- CUA核Case17420为11成员/8对象/8证据/2调查，用户指定local-socai2-7bde0c0b-0d18-4abc-9382-9752f2ae5e98为2/4/0/2，两者同布局和相同指标口径。长ID换行、实际缺项保持；核两案当前成员图，17420无跨事件/潜在路径扩张。
- 700px wrapper核实际案件摘要单列、四指标双列、Run类型入口及候选列表/图层可读；原控件保持。浏览只读，无重置或保存。原用户标签在浏览中被用户导航，随后新建独立隐藏QA标签，资料截图重新获取并覆盖错误画面，未据该导航改业务逻辑。
- 截图：`.local/versions/case-info-demo-aligned-20261102.png`、`case-info-actual-aligned-20261102.png`、`case-member-graph-aligned-20261102.png`、`case-info-aligned-narrow-20261102.png`、`run-graph-tabs-after-20261102.png`、`run-graph-tabs-narrow-after-20261102.png`、`run-source-disclosure-after-20261102.png`。

临时59249只监听127.0.0.1；已核PID47038、2026-11-02 13:04:32和完整命令后终止本轮服务。4174保留；未重启或修改后端。原78告警/21事件/21Case/18Run及13实际Run保持，没有模型、业务查询、响应、部署、Git提交或推送。

## 结束交接

第38节、README、AGENTS/PROGRESS已同步；代码及最终文字/截图结束独审均限定ACCEPT、0必须修。独立查看6张最终截图并核同模板、成员图边界、700px与内外details展开；交接未扩成后台或AI质量验收，可归档。已正常归档并同步3条新增需求；封后all 9项、archived 65项通过，0失败。既有长需求/skip_specs INFO保持。diff-check通过，59249无监听、4174 PID16292继续监听。
