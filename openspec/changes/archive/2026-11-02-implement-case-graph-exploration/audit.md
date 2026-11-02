# 案件图谱探索与调查草案回执

2026-11-02。本轮按用户先讨论再“详细整理、mock并实现”的授权实施本地V2；追加要求将“多告警案件 / 100%”换成处理中案件。源数据与原历史保留，不做后端、模型、响应、部署或Git提交推送。

## 范围

新增独立`case-exploration-data.js`和`case-exploration.js`，接入现有圆形三栏图、Case工作流和页头。详细功能/影响/原型规则在[主文档第40节](../../../../docs/design/incident-investigation-page-analysis.md#40-2026-11-02-案件图谱探索与调查草案)。当前Case默认Path和直接邻居底图，Chain原材料仍可查看；推荐与节点扩展只用同源同租户的完整载入记录和明确对象关系，来源不足不补造路径。保存探索、保存草案、加入成员、模拟执行四种作用分开。

新数据为10告警/3事件/9对象/2Case/3Run，原78/21/21/18及13实际Run全部保留，当前88/24/23/21。两个新Case分别覆盖探索和执行中下一轮草案，专用模拟状态明确；非演示Case仍无启动能力。第四卡“处理中的 Case”依Case处理状态计数，浏览初始7。

改前9个页面/配置文件与tests目录备份在`.local/versions/case-exploration-before-20261102/`。除当前前端与交接范围，其他已有脏工作和用户新建`aaa。txt`保持。

## 直接验证

- `npm run check`与135项前端测试全部通过，日志`/tmp/case-exploration-tests.log`。16新增检查包含来源和窗口、关系证据、连续扩展、预览/撤销/保存恢复、显式案外加入、实体-only草案、取消、冻结和单活跃、多个事件、指标独立、固定底图与时间范围、全局模拟提示、只读底图更新、候选空态与冻结标题。模拟运行的六视图也验证可读且无状态写回。
- 首轮119项109通过，10处失败来自新增计数/最新时间范围/分页和旧成员图期望；更新固定数据期望、让通用入口测试显式查看完整队列，并保原件断言。新增测试首轮129项127通过，2处期望不正确：独立实体仍可定位已在图中告警（应验证没有新增候选），原11部分交付不受新增完整Run影响。修正后各增量及最终135项均通过，没有隐藏失败。
- 两次在仓库根误运行npm因无package.json失败，未执行测试；改用前端目录或`npm --prefix prototypes/security-pages-v2`完成检查。
- 10源文件（data/replayed/investigation-data/alert-flow-data/aisoc20/persisted/design/page-showcase/recorded-examples/workspace-model）与HEAD无diff；services与V1无diff。新fixture没有覆盖旧源数据。
- `git diff --check`通过；实施前和结束规格`openspec validate implement-case-graph-exploration --strict --no-interactive`通过。

## 浏览核查

CUA在普通4174背景标签核推荐默认5/共6、展开新实体、紫色节点、实体选择和对象-only草案，明确保存边界，取消表单未写成员；Case02页头持续提示当前运行，待启动与取消草案分开，第二个模拟启动禁用；队列第四卡为“处理中的 Case / 已开始处理，尚未解决 / 7”。历史来源材料保持。

1800px wrapper核三栏及紫色新增节点，700px核操作栏、横向Case导航、告警列表/画布/详情上下布局。wrapper仅是临时布局文件，已删除；浏览未保存探索/草案、未启动模拟、未重置任何用户数据。交互写入/取消/单Run互斥由隔离VM核验，不冒称真实执行接入。

截图：`.local/versions/case-exploration-wide-20261102.png`、`case-exploration-narrow-20261102.png`、`case-exploration-narrow-graph-20261102.png`、`case-exploration-active-20261102.png`、`case-in-progress-metric-20261102.png`。

## 独立结束审阅

未参与实现者`current_workspace_review`首轮44项相关检查通过，并独立核旧13实际Run、21原Case历史归属、24小时边界/不同来源和租户、非法采用无写入。审查发现三项必须修，均已修正：

1. 新SIM的全局调查入口缺显著模拟提示：通用brief与所有simulation详情展示“本地演示”，推进按钮仅所属Case提供，全局链接返回所属案件；新增全局列表及6详情回归。
2. 只打开图谱也固定旧底图且误称已保存：仅真实探索或保存后固定；只读浏览跟随最新完成Run，未保存探索使用准确提示；新增两种状态回归。
3. Case默认底图不纳入Chain后，空列表误称未保存查询：改为当前画布无其他关联告警，并提示推荐或节点扩展；历史Run仍使用原真实来源状态。

独立修后27/27定向和五张截图复核通过。最后补模拟输入独立副本与完成Path标准properties，避免标题回读后来编辑的库存；新增第16项测试，独立冻结增量2/2通过，135全量日志尾已核。代码结束结论为**限定ACCEPT、0剩余必须修**。

最终文字补审同为**限定ACCEPT、0剩余必须修**：第40节、README、AGENTS/PROGRESS、audit与五张截图一致，允许按流程归档。仅覆盖本地前端探索、草案与模拟流程，不代表真实执行或服务端并发控制验收。

## 归档及封后校验

已归档为`2026-11-02-implement-case-graph-exploration`，主规格新增3项、修改2项；任务仅核实际已完成的归档前条件。`openspec validate --all --strict --no-interactive`为9/9，`--archived --strict --no-interactive`为67/67。既有长需求提示不影响校验，未改变其他活动change。无Git提交/推送。
