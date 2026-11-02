# 案件探索侧栏整理回执

2026-11-02。仅本地Case图侧栏呈现，不改数据、扩展算法、草案/成员持久逻辑、历史Run或后端。其余未提交工作与用户aaa。txt保持，无模型/业务查询/部署/提交推送。

## 实际变更

Case侧栏使用对象详情/关联线索两个视图，推荐/扩展进入线索，点击节点/边回详情，切回保pivot和候选；不把隐藏对象消息叠在线索上。规则/UTC+8时间收至ⓘ原生details说明，候选常驻两项共享对象，完整对象与分数按需查看，预览/展开操作原样。宽屏侧栏290px（中宽270px），窄屏候选一/两列。历史Run继续原selectedDetail路径。

改前case-exploration.js、investigation-graph.js/css、index.html及tests/case-exploration.test.cjs共5文件存.local/versions/exploration-sidebar-before-20261102。新资源版本sidebar-r1。

## 验证

- 实施前strict规格通过，npm run check通过；探索/阅读/图谱三文件40项定向全过，日志/tmp/exploration-sidebar-tests.log。新增1项核隐藏选中对象后线索无旧消息、切换详情/回线索保起点、时间格式化与无业务写入。无失败未修。
- CUA原用户标签5刷新前核0展开、0草案选择，刷新后打开关联线索，卡片不再含旧空态和长时间戳；ⓘ可展开，显示10/25 11:42:17（UTC+8）及排序语义。未保存/启动/清数据。
- 临时1800px iframe检查宽屏右侧栏，用户当前约905px视窗核下方候选双列；临时文件已删除，验证背景页已关闭。截图.local/versions/exploration-sidebar-current-20261102.png与exploration-sidebar-wide-20261102.png。
- git diff --check通过。原数据、历史和调查执行逻辑保持。

## 独立结束审阅

current_workspace_review结束独立审阅限定ACCEPT、0项必须修：独立运行40项定向全过；新旧双VM中21个历史Run图谱HTML逐字相同；补核预览、选边回详情、返回线索及保存探索，临时视图状态未写入快照，成员和Run保持；10个保护文件、后端及V1无差异。两张截图与第42节、README、交接及规格一致。本结论仅覆盖本批侧栏整理，不代表后台能力验收。

## 归档与封后校验

已归档为2026-11-02-simplify-case-exploration-sidebar，合入既有探索requirement及新增侧栏场景。封后all9/archived69均通过，0失败；其余未提交工作保持。
