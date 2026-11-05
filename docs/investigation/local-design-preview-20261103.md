# 远端产品页面本地预览与工作衔接

2026-11-04更新：按用户要求合并开发目录，预览现从`E:/aisoc/socai2/prototypes/security-pages-v2`运行，开发分支为`codex/case-baseline-history-20261103`，URL仍为http://127.0.0.1:4174。旧设计工作树已注销，以下11月3日分支和工作树记录仅作历史。当前重启命令：

```powershell
E:/aisoc/socai2/.venv/Scripts/python.exe E:/aisoc/socai2/prototypes/security-pages-v2/serve.py --port 4174
```

2026-11-03。用户要求依次完成：远端功能分支页面可在本地访问；本地提交当前进度；在独立分支继续对齐设计和功能。此前要求先理解三类调查流程、页面功能以及对当前存储和处理流程的影响，尚未要求直接实施新的调查架构。

## 本地页面

- 远端 `origin/codex/functional-analysis` 已从 `48f54abd` 更新到 `c71afb5c6c4f939bf0243b60e02f224d01c6249a`。仅 fetch，没有向当前后台工作区合并或覆盖文件。
- 独立分支：`codex/functional-alignment-20261103`，起点为上述远端提交。
- 独立工作目录：`E:/aisoc/socai2/.local/worktrees/functional-alignment-20261103`。不改动另一份已有 `codex/functional-analysis` worktree。
- 启动原型自带 `prototypes/security-pages-v2/serve.py --port 4174`，只监听 `127.0.0.1`；隐藏后台窗口运行。运行日志和进程信息在主工作区 `.local/preview/`，不提交。
- [告警](http://127.0.0.1:4174/#/alerts)、[事件](http://127.0.0.1:4174/#/incidents)、[案件列表](http://127.0.0.1:4174/#/cases)、[完整案件资料](http://127.0.0.1:4174/#/cases/outcome-case-01/case-info)、[故事与助手](http://127.0.0.1:4174/#/cases/outcome-case-01/story)、[人工任务](http://127.0.0.1:4174/#/cases/outcome-case-01/tasks)。

已确认首页 HTTP 200、页面引用的 27 个脚本／样式资源 HTTP 200；浏览器已呈现“财务终端脚本与跨主机活动核查”的案件资料、当前判断及 10 个 Case 页签。只核预览可达与页面呈现，没有提交页面表单、重置浏览器数据、发送 AI 问题或调用后台。原型中的示例回答与本地保存不能作为真实模型／数据库验收。

以下为原独立目录的历史启动方式，现请使用顶部命令：

```powershell
E:/aisoc/socai2/.venv/Scripts/python.exe E:/aisoc/socai2/.local/worktrees/functional-alignment-20261103/prototypes/security-pages-v2/serve.py --port 4174
```

## 当前理解与下一步

当前产品定义以新 `docs/design/alert-incident-case-product-requirements.md` 为主。旧分析文档 27—43 节为讨论过程；第 44 节仍有“草案”等较早表述，应使用当前产品文档 3、6、10 节的明确保存流程。新需求及相关页面源码的 [固定版本清单](../operations/evidence/product-workflow-understanding-20261103/source-manifest.json)已保存。原 85 项字段明细仍是 `48f54abd` 的历史对照，不能直接标为新版全部通过。

| 三类工作 | 触发与过程 | 保存内容及边界 |
| --- | --- | --- |
| 基础调查 | 首次进入案件调查及正式新增成员，形成首次／更新调查；执行中新增范围进入待更新 | 每轮独立 Run、固定输入、结果与差异；不改写上一轮输入，同案单活跃是新版要求 |
| AI 调查 | 从整案、告警、结果、人工事实或对象提问；打开／填建议不执行，发送后处理 | 对话先保留；用户明确保存答复后形成正式记录，冻结当时引用。保存不再次执行，不自动采用为全案判断 |
| 人工任务 | 人创建、分配、确认事实并填写完成结果；允许编辑同一任务 | 当前任务可更新；已保存调查引用的历史内容保持。完成本身不启动 AI 或解决案件 |

页面按职责继续对齐：案件资料展示当前判断及其覆盖；案件故事串联告警／调查／人工结果；调查概览展示正在做和待更新；历史展示每轮固定范围及结果；成员页管理正式范围；案件图保存探索并明确加入；对象与证据回查材料；任务页记录人工事实；活动页记录管理操作；评论附件承接交接。

已直接核过当前表与入口：`aisoc_cases`、`investigation_case_links`、`investigation_runs/events/artifacts` 可复用；人工任务 `aisoc_case_tasks` 已存在，当前不含新版的结果、完成时间、引用范围及取消状态；`aisoc_copilot_conversations` 已有租户级对话，但不是现成的 Case 绑定／正式结论保存合同。当前追加调查要求成员和窗口相同，不能直接当作新增成员的基础更新；现幂等针对 operation_key，不等于同案单活跃约束。详细方案在新分支继续核对，本轮不据此直接建表或改状态机。

## 本地提交边界

当前后台分支 `codex/investigation-review-20261024` 保存第 1—4 批字段修复、85 项对照、对应文档和证据，以及本次远端需求快照／预览交接。业务源码本轮未新改；已有 48 个服务源码／测试文件的最新批次指纹复核用于确认仍对应原验证记录，不重跑已通过的业务测试。

`START_HERE.md`、`START_HERE.x86_64.md`、`ding/`、`inv-review.md` 不在提交范围；`.local/` 中 worktree、进程和日志也不提交。用户仅要求本地提交，不推送远端、不部署后台、不执行新调查。报告问题继续保留，r13 不重试、5.3 未完成。
