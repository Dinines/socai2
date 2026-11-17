# 阶段一步骤5：补查目标与能力分流

2026-11-14。状态：**步骤5本地实现、真实来源查询及保存读取通过，未发布程序**。目标、步骤和判据先写入[阶段一设计](../../../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#本轮步骤5补查目标与能力分流)，[实施前OpenSpec严格校验](openspec-before.txt)通过后实施。主change仍31/41，模型质量仍NOT_PASSED。

## 本轮范围与实现

沿已有query/Deep/human/graph执行路径，明确业务目标与实际能力的对应，保留原计划和已有结论，单独记录程序真正做了什么。没有增加查询工具、业务权限、预算、自动任务或新的输出字段要求。

| 环节 | 本轮改变 |
| --- | --- |
| C3选择目标 | profile新增`socai2.followup-routing.v1`：工具能回答的单次问题才选query；已有材料有明确分析价值可选Deep；目录外授权等材料用human待补；graph只用保留来源。提示进入正常C3和冻结补答上下文 |
| Deep选择动作 | 冻结同一分流说明，按现有材料和实际工具能力选择query/answer/handoff；无候选仍允许材料分析，不能以分析回答冒充新增取证。C6建议中的Deep说明同步为材料分析或按结果续查 |
| 实际分流记录 | C4路由和Deep汇总增加`activity`，版本`socai2.followup-activity.v1`。每项真实查询保留原答/投影工件、工具、状态、返回数量、是否复用及data/empty/not_queried/failed/unknown；重复读取不重复计新调用 |
| 保存及读取 | 原followup方式、目标、绑定、顺序和原结论不改写；human不自动建任务，graph不记外部查询。后台回执不作为新的模型事实，不将执行台账整包加入模型 |

代码只改6个现有文件并新增`followup_activity.py`，见[本轮差异](implementation.patch)和[范围核对](scope-checks.json)。所有运行TOML、C3七部分/8192/最多5发现、一次补答策略及C6预留实现保持；无数据库迁移或告警交接字段变化。

## 湖数据及用户补充授权

最初[来源预检](source-probe.json)查空；[原演练计划](../production-multialert-20261107-01/plan.json)明确`no_additional_lake_events=true`。该查空保留，不当成取得新事实。

负责人随后明确“写入湖”，并要求“测试的话需要把上下文也写入，才能tool查询到”。据此在21的`aisoc.raw_events`单次写入**6条明确标注的合成演练数据**：原三条告警事实的副本，加三条仅在湖内的认证、进程、网络上下文。租户、主机和时间窗固定为配置中的`000…001`、`socai2-flow-20261107-01`、`2026-11-07T06:33:27Z–06:44:07Z`；不修改原Case/Run和三条告警材料。

写入复用Fusion `event_to_row`映射和既有`socai2_lake`账号；读回用既有只读账号，凭据留在21。每条记录使用本批稳定UUID、测试来源标记；写前六个ID均不存在，写后六条原文、ID、主机及类型一致。没有再次写入、清理其他记录、启动消费者或重启服务。输入及投影见[lake-seed-plan.json](lake-seed-plan.json)，实际写入回执见本目录`lake-insert-*.json`；[配置](config.json)、[写入脚本](seed_lake.py)和[受限远端写入](seed_lake_worker.py)可追溯。

新增上下文没有真实授权或预设良恶标签。原告警副本不算独立佐证，新增上下文也只是测试事实，不能据此报告模型准确率或生产调查质量。

## 实际业务路径与保存读取

成功运行是`attempt02`，使用现有完整C1–C6执行器。查询由真实C3的原计划经正常C4分流触发，未插入人工替代计划；模型和湖查询均无替身。

| 项目 | 实际结果 |
| --- | --- |
| Case / Run | `54b8bb69-8d03-511a-9f4a-8eb4becd5d67` / `cd83551f-3be3-43e7-9c72-c47cc490db5a` |
| 初始输入 | 仍为既有三条演练告警；C3实际请求中不含新增会话信息或上下文时间 |
| C3原计划 | 1项human确认授权材料，1项绑定B1的query；原计划和引用问题完整保留 |
| 真实查询 | `authentication_activity`读取2条记录，其中1条为新增湖上下文；原件、业务投影及`activity.outcome=data`分别保存。进程/网络上下文已写湖，但本Run没有查询它们 |
| 后续分析 | 新增上下文事件`c8ad1f00-2f86-5aaf-99dc-44ce1d063de5`的来源关联进入C6请求；实际提示包含新增`06:38:20`及会话字段，C3原输入中没有这些值 |
| 保存结果 | Run completed，Result accepted / uncertain / partial。原结论、发现、问题、建议、影响和原计划关联均可读取；partial和质量未通过继续保留 |
| 模型及工具 | 本成功Run真实C3+C6共2次、26,953tokens；C2两次真实库查询查空，C4一次真实湖查询；0次Deep、0次模型替身、0个自动人工任务 |
| HTTP读取 | 47次GET覆盖Case、Run、工件和Result；原件JSON/文本与数据库一致，Result的结论/状态/发现/问题/建议/影响等11项直接字段一致，GET前后快照不变 |
| 预算 | Run仍6次模型/4次工具/131,072tokens/1500秒；C6仍预留2次/51,200tokens/300秒。未放宽预算换取通过 |

实际证据：[checks.json](attempt02/checks.json)、[database.json](attempt02/database.json)、[HTTP回执](attempt02/api-responses.json)、[实际模型请求及原答](attempt02/model)、[实际湖查询](attempt02/lake)、[文件清单](attempt02/manifest.json)、[Result及来源核对](result-verification.json)。HTTP走真实路由的ASGI鉴权/依赖覆盖，不冒充生产TCP发布验收。

## 保留的失败与质量边界

`attempt01`的真实C3成功保存后，验收脚本在发送湖查询前调用驱动`escape_params`缺少`context`参数，产生TypeError。原Run `705081f0-ac31-46e4-9656-3fbd93a486ec`及查询步骤保持unknown；原模型回复不改、不重派、不恢复。该次真实模型1次、11,622tokens，实际湖调用0次；33次只读GET已核保存状态，见[首轮检查](attempt01/checks.json)及该目录的原始异常。

仅修正测试传输参数后创建新Case/Run做`attempt02`；没有因模型正文质量反复采样。合计两Run共3次真实生成、38,575tokens；费用未知，不记零。湖只写一次六条。

实际C3的query目标仍同时提及认证/网络/进程，而B1只提供认证记录；这项目标描述过宽仍登记为模型质量问题，没有自动扩大查询或把一项查询说成三类已查。C6原结论和引用诊断保留，不据accepted或有工件宣称推理正确。无查询Deep、失败/unknown等直接边界由离线检查覆盖，本批不新增故障矩阵。流程在unknown处停止、尚未生成汇总时，沿原Step/Run及工件读取，不补造`activity`或已完成的路由。

## 直接检查、交接与停止位置

**44项不同直接检查通过**：[27项分流/配置/既有C3合同及Deep动作检查](offline-tests.txt)，加[16项第四步补答和1项预算/unknown预留兼容检查](compatibility-tests.txt)。只补受影响行为，没有全仓回归或模型替身验收。[Ruff](ruff.txt)和[最终OpenSpec严格校验](openspec-final.txt)通过，[最终核对](final-checks.json)保留源码、存取与预算边界。

已同步设计、任务、规格状态、PROGRESS、前后端交接、问题清单和部署说明。使用既有运行记录工具追加成功和unknown两份静态记录，10条中旧8条及372份非索引文件保持，见[audit-readback.json](audit-readback.json)。实际4177仍为SSH转发，没有发布本批页面。

本轮止于步骤5。步骤6原件超限存取、步骤7页面修复尚未推进；不勾选主change整体完成，不归档、部署、提交或推送。21唯一新增数据是上述经用户明确授权的六条湖演练记录。
