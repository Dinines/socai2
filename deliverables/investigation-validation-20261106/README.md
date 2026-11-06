# 告警、事件与 Case · 前后端联调第一版

版本标签为 `frontend-backend-integration-v1`。本版供前后端使用同一批已保存的案例，核对页面字段、主体之间的跳转，以及调查成功、部分交付和调用失败时的展示。

| 交接对象 | 从这里开始 |
| --- | --- |
| 业务后端 | [服务端数据交接 V1](../../docs/investigation/socai2-page-data-handoff-20261106.md)给出业务字段、权威表、联表键、读取权限和四段只读 SQL。 |
| 前端和产品 | [页面功能清单 V1](frontend-feature-list.md)按页面列出 28 项功能和 14 项跳转，包含输入 ID、目标页、关联字段和空态。 |
| 联调验收 | 解压[四案预览与原件](21-qwen9b-handoff-cases-20261106.zip)，打开 `preview/index.html`，按[案例签收](frontend-feature-list.md#案例签收)复查跨页链路和已知显示问题。 |

## 调查运行记录页

[打开本机调查工作台](http://127.0.0.1:4177/)。调查人员可以在这里查看处理过程、重建当时的输入输出，或把某个步骤的日志文件交给同事。

生产模式读取 21 业务库 `aisoc` 的 `socai2` 表，默认租户为 `00000000-0000-0000-0000-000000000001`。在有 21 内网 SSH 配置的工作站上，用项目 Python 环境从仓库根目录启动本机页面。

```sh
python docs/operations/serve_processing_workbench.py --source aisoc
```

也可使用 21 上的工作台。它只监听服务器的 `127.0.0.1:4177`。本机 4177 空闲时，运行 `ssh -N -L 127.0.0.1:4177:127.0.0.1:4177 sting-infra21`，再打开同一个本机地址。

首页直接查当前租户最近更新的五个 Case。列表按案件、Run、步骤及工件的最近时间排序，点“加载更多”每次再取五个。选中 Case 后，每 15 秒检查数据库里已提交的相关记录。新增一步，或已有步骤的状态、输入输出有变化，就更新该案详情。每案只保留一份最新快照，快照包含库里保存的各轮调查。服务器版保存在 21 的 `/opt/sting-aisoc-socai2/data/production-workbench/`，工作站版保存在仓库的 `.local/processing-workbench/aisoc/<租户>/`。已生成的网页和日志可在数据库连接中断后继续查阅。

生产告警先由 Fusion 写入同库 `public.alerts`。接入进程按告警和事件 ID 保存调查侧材料与成员关系。告警分诊、事件诊断和 Case 调查分别由有权限的调用者启动。只有创建 Case 后，此案才会进入最近案件列表。4177 刷新使用只读账号，与处理作业分别运行。[生产落库、触发与安装](../../FRONTEND_BACKEND_HANDOFF.md#21-21-生产环境)

| 要核对什么 | 在哪里看 | 数据从哪里来 |
|---|---|---|
| 一条告警为什么得到当前判断 | 从已打开的 Case 进入关联告警，或选择“告警 ID”，输入快照中的完整 ID。查看主记录、原始材料、分诊及处理历史。 | `alerts.id` 关联材料、对象、分诊和 `runs.alert_id`。快照收录了告警时，即使尚未启动分诊也能看到主记录。 |
| 一个事件有哪些成员、做过哪些诊断 | 从已打开的 Case 进入关联事件，或选择“事件 ID”，输入快照中的完整 ID。查看事件、成员和逐轮诊断。 | `incidents.id` 关联 `incident_alerts`、`incident_diagnoses` 和 `runs.incident_id`。 |
| 这个 Case 每一轮走到了哪里 | 在左表按最近执行更新时间选案，在详情中切换轮次和流程节点，核对输入、输出、原答、错误及交付。 | `runs.case_id` 关联调查轮次，`run_steps.run_id` 关联步骤，步骤和工件 ID 关联读回的原件。 |

告警和事件 ID 入口搜索已发布的主体快照。查找某条刚入库的告警时，先打开其所属 Case，或在独立资料页导入主体快照。同一个 ID 出现在多份材料时，按批次和关联 Case 选择。Case 流程图保留直接查询、问题深查、构图建议和人工确认等设计分支。成功、失败、部分交付、跳过及尚无执行记录各有状态；点击有记录的节点可以定位到实际步骤。页面末尾的调用回执和事后查询可与当时保存的材料分别核对。

**查看步骤文件。** 打开 Case 的运行日志目录，默认展开最近更新的三个实际步骤。每份步骤 JSON 标明 Run ID、步骤 ID、状态、时间、错误和输入输出工件的相对路径。目录中的 `manifest.json` 汇总各轮、各步及工件；复制整份日志目录可保留相对链接。文件在发布站点的 `logs/<内容指纹>/` 下，依据取样时已经提交的数据库记录生成。数据库里没有相应步骤时，流程图保留空态，不会补造一份执行日志。

### 从本机资料文件夹更新

此入口供离线资料页使用。需要查看采集或测试人员交付的文件夹时，在持有资料的机器上从项目根目录执行下列命令，再刷新静态资料页。页面右上角“从目录更新”也可查看命令。生产工作台按上节自动取数，静态资料页与生产缓存分别保存。

```powershell
python docs/operations/update_processing_audit.py --folder "E:\调查资料\本次导出"
```

| 可以选择的文件夹 | 完整性要求 |
|---|---|
| 已登记批次根目录（含 `plan.json` 和 `readback/`） | 各卡的 29 表快照、输入新鲜度文件、批次清单和校验值齐全。例如仓库的 `docs/operations/evidence/ie-audit-20261106-r300`。三张卡一同验证；已退役三案的执行记录不会重新登记。 |
| 单份页面导出（含 `manifest.json` 与 `database.json`） | 清单格式为 `socai2.page-export.v1`，记录租户、批次、逐表行数、文件名及 SHA-256。支持只有一条告警，或只有一个事件及其成员的完整主体快照；空表保留空数组。 |
| 驱动或采集器目录（含 `exports/<取样时间>/`） | 一次选择一个主体的目录，读取清单中取样时间最新的一份。同目录内的快照应使用同一租户、批次和主体。独立测试另用新批次。 |
| 解压后的多案包（含 `cases/<案例>/export/`） | 每个子目录都需有自己的完整导出清单。数据库读回是执行依据，包内已登记的页面读回和回执可辅助核查。 |

来源目录以只读方式打开。程序先核对文件校验值、29 表行数和主体范围，再更新现有站点；文件缺失、凭据检查或关联校验失败时保留当前索引。重复导入同一份资料会更新同一条记录。不要把运行环境配置放入发布目录。仅有单个模型原答、普通文本日志或任意 JSON 文件时，应先取得有清单的主体快照。

### 部署后按 Case 采集

在可以访问调查 PostgreSQL 的机器上，给采集进程配置 `SOCAI2_AUDIT_DATABASE_URL`。使用可对 V1 的 29 张表进行 SELECT 且受租户隔离约束的只读账号。连接串由部署环境提供。将下面的租户和 Case ID 替换为实际 UUID，并给这个 Case 指定独立的资料目录。

```powershell
python docs/operations/capture_processing_case.py --tenant "<租户UUID>" --case "<Case UUID>" --folder "E:\调查资料\本案" --follow 15 --site "deliverables/investigation-validation-20261106/processing-audit"
```

`--follow 15` 每 15 秒读取一次已提交的状态，有变化时替换本案的快照，按 Ctrl+C 停止。省略此参数会采集一次。`--site` 同时刷新工作台，省略时只更新本案的资料目录。已提交的步骤和工件会随快照展示。

已保存的批次也可使用 `update_processing_audit.py --batch "已保存的测试批次"`。21 合成测试只有登记计划时，使用 `update_processing_audit.py --plan "本次目录/plan.json"` 按计划导出后更新。用下列命令单独启动静态资料页，然后打开[本机离线资料预览](http://127.0.0.1:4179/)。

```powershell
python -m http.server 4179 --bind 127.0.0.1 --directory deliverables/investigation-validation-20261106/processing-audit
```

## 测试材料

**三案处理审计。** 21 的 r3 已用三个案例逐阶段实测，43 提供真实模型推理。开发时打开[本版运行记录页](processing-audit/index.html)核对步骤输入输出。[审计结论与每步落库](processing-functional-audit.md)记录了发布、超时与系统收尾；[三案测试证据快照](ie-processing-audit-20261106.zip)保留当次测试的数据库读回、作业回执和采样时的页面。

**复查三案测试环境。** M01/S02/U03 的原始记录来自独立数据库 `socai2_processing_handoff` 和按需作业 `processing-20261106-r3`。可在单独端口运行 `python docs/operations/serve_processing_workbench.py --source 21 --port 4178` 复查该环境，或直接使用包内原件。主机检查、命令及合成样本 UUID 见[三案部署与交接手册](processing-deployment.md)。页面字段签收继续使用下方的四案和历史正例。

**前端和产品先看[前端功能清单与签收顺序](frontend-feature-list.md)。** 按告警、事件、独立调查和 Case 列出原页入口、页签、功能编号、取值字段与案例，也可直接找到模型失败时页面该显示什么、正式签收前需关闭哪四项显示差异。

**核对数据先看[告警、事件与调查字段取数清单](page-field-samples.md)。** 主表列出 81 个字段在四个内网小模型案例中的实际取值情况，每行可定位到原包文件和具体 JSON 字段。另列模型结论、分类、证据计数、人工任务的有值样例，以及在两包历史快照中只见空值或未产生业务记录的项目。

[21 内网 Qwen3.5-9B 四案交接包](21-qwen9b-handoff-cases-20261106.zip)覆盖账户清点、凭据转储、卷影删除和运维外连。完整解压后打开 `preview/index.html`，每案可直接查看告警、原件、事件及已有 Case 或执行记录。包内 `cases/` 为真实 API 读回、29 表快照、模型回执和冻结计划，`checks/` 区分字段对照、原页实际可见状态与未通过项。SHA-256 为 `73f108f1c6b62dd3f82540b05f59e7009691501f33553c0fd644481d1262ffaf`。[本阶段交接验收](../../docs/investigation/investigation-test-handoff-20261106.md#下一阶段的前后端交接验收)

[21 内网 Qwen3.5-9B 单案包](21-qwen9b-pilot-20261106.zip)包含告警、事件、独立调查三页的静态预览、27 份 GET（25 个不同路径）、29 表实际读回及三份模型原答。解压后从 `preview/` 打开对应的 HTML 入口。两条告警和一次事件诊断已发布，Case 模型调用前因输入容量停止，原页可用这份样例接系统收尾状态。[对应的字段和结果](../../docs/investigation/investigation-test-handoff-20261106.md#21-内网小模型实测)

前端开发按[联调取数说明](../../docs/investigation/investigation-test-handoff-20261106.md#前后端联调从这里开始)从本包提取 48 份真实保存的 GET 响应体和 4 份字段样例。仓库中的离线检查可复核后端取值和原页面显示，使用既有案例即可开始。

本目录是2026-11-06已完成测试材料的分发入口，随`codex/case-baseline-history-20261103`提交。先读[测试结果、F01—F28字段对应及下一轮计划](../../docs/investigation/investigation-test-handoff-20261106.md)，再按[提交范围与剩余问题](../../openspec/changes/complete-socai2-investigation-chain/publication-20261106.md)继续推进。

[下载交接包](socai2-investigation-tests-20261106.zip)：10,079,558字节，1272文件，SHA256：

```text
361eb5b37d89bf31663f813f991c373f5f65173a80789963e40bef2142b8170a
```

ZIP保持原已核验包逐字不变；解压后先打开`START_HERE.md`。包含13个本机模型批次的已保存材料、4个无模型数据合同样例、原页面和固定候选代码，以及本轮数据/语义审阅。较早失败导出和校验器问题保留。它是数据与复现资料，不是自动部署包；旧21环境m/k/r原件继续通过主报告中的仓库索引查阅。

本轮三案15次DeepSeek、累计63次，三案C6均保存；48GET/674项数据比较、557项页面检查/87视图通过。**模型语义质量仍未通过**，两次C3范围拒收、效果扩大、知识未实际消费等问题不以成功保存代替修复。独立审计仅接受已保存的数据与交接范围。

完整运行配置、API Token和密码没有纳入。原包内`committed_or_pushed_this_turn=false`及`uploaded=false`记录测试和打包当时的状态；代码发布以 Git 和远程分支为准。21 已保留四案小模型实测回执，独立处理库另有当次建案与准备的读回。生产连接、角色和操作入口见[根目录交接指南](../../FRONTEND_BACKEND_HANDOFF.md)。
