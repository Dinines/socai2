# 告警、事件与 Case 联调资料

前后端统一合同从[交接指南](../../FRONTEND_BACKEND_HANDOFF.md)进入。本目录提供功能清单、字段有值／空值样例和固定测试原件；环境、接口及开放状态以当前合同为准。

| 使用目的 | 入口 |
| --- | --- |
| 页面功能与跳转 | [F01–F28／J01–J14](frontend-feature-list.md) |
| 表、关联键和读取 | [服务端数据交接](../../docs/investigation/socai2-page-data-handoff-20261106.md) |
| 字段及空态 | [字段取数样例](page-field-samples.md) |
| 当前两案生产读取 | [299 次 GET 与 13,098 项核对](../../docs/operations/evidence/current-release-20261110-01/readback-03/summary.json) |
| 待完成功能 | [问题清单](../../docs/investigation/current-issues.md) |

## 调查运行记录页

[4177 调查工作台](http://127.0.0.1:4177/)用于查看 Run、步骤、实际输入、原答、错误、交付及保存的工件。21 当前发布为 `v1.2-20261110-r2`，只监听 `127.0.0.1:4177`。本机沿[SSH 接入说明](../../docs/operations/mac-ssh-relay-20261107.md)转发：

```sh
ssh -N -L 127.0.0.1:4177:127.0.0.1:4177 sting-infra21
```

生产模式从 `aisoc.socai2` 按授权租户读取最近 Case，每批五案，详情每 15 秒检查已提交变化。生产缓存位于 21 的 `/opt/sting-aisoc-socai2/data/production-workbench/`。独立静态条目保留测试来源；21 已登记 16 份，本机保留 47 份，两者不混计。当前新增的 9 份 C1/C3/Deep/C6 导出来自真实隔离 PG，模型及工具使用替身；481 份发布文件及 482 项 HTTP／字节核对通过。[发布回执](../../docs/operations/evidence/current-release-20261110-01/workbench-publication.json)

| 查阅对象 | 关联依据 |
| --- | --- |
| 告警材料与分诊 | `alerts.id`、材料指针、`runs.alert_id`；无分诊仍展示主体和原件 |
| 事件成员与诊断 | `incidents.id → incident_alerts/incident_diagnoses`、`runs.incident_id` |
| Case 各轮处理 | `runs.case_id → run_steps.run_id`，按 `seq/parent_step_id` 展开，输入输出用该步工件 ID |
| 原件与日志 | `logs/<内容指纹>/manifest.json`、逐步 JSON 和工件相对路径；复制整个日志目录保留引用 |

告警和事件 ID 入口搜索已发布主体快照。新主体可从所属 Case 加载，或导入完整主体快照。系统没有保存的步骤保留空态，不补造执行日志。页面阅读不会执行模型、工具或业务写入。

### 从导出更新静态资料

单份页面导出须包含 `manifest.json`、`database.json`，清单格式为 `socai2.page-export.v1`，有租户、批次、29 表行数及逐文件 SHA-256。批次身份取导出清单，直接导入完整导出目录：

```sh
python docs/operations/update_processing_audit.py --batch '<导出目录>'
```

也支持含 `plan.json/readback/` 的登记批次、含 `exports/<取样时间>/` 的单主体采集目录及含 `cases/<案例>/export/` 的多案包。工具先核内容指纹、行数、凭据及关联；失败保留现有索引。来源只读，重复同一份资料更新同一登记，原失败和其他批次保留。

在能够访问目标 PG 的环境，用只读连接 `SOCAI2_AUDIT_DATABASE_URL` 采集指定 Case。租户和案件均使用真实 UUID，连接串留在私密配置：

```sh
python docs/operations/capture_processing_case.py --tenant '<租户UUID>' --case '<Case UUID>' --folder '<本案导出目录>' --follow 15 --site deliverables/investigation-validation-20261106/processing-audit
```

省略 `--follow` 采集一次；省略 `--site` 只生成导出。离线预览：

```sh
python -m http.server 4179 --bind 127.0.0.1 --directory deliverables/investigation-validation-20261106/processing-audit
```

静态发布到 21 使用[当前发布配置](../../deploy/aisoc21/workbench-current.json)，保存新增批次回执后运行 `publish_processing_audit_batch.py --config <配置> --publish`。此入口只更新静态材料和登记，不重启服务，不写调查数据库，不调用模型。

## 固定样例包

下列 ZIP 按生成时的指纹保留，提供可复现的字段及失败样例；不能作为当前部署包或运行状态。当前生产的样例优先使用上方两案读回。

| 材料 | 用途 |
| --- | --- |
| [四案预览与原件](21-qwen9b-handoff-cases-20261106.zip) | 解压后打开 `preview/index.html`；Q01–Q04 的 GET、29 表快照、模型回执及字段样本。SHA-256：`73f108f1c6b62dd3f82540b05f59e7009691501f33553c0fd644481d1262ffaf` |
| [单案包](21-qwen9b-pilot-20261106.zip) | 告警、事件、独立调查静态页，包含系统容量收尾与未产出 Case 模型结果的空态 |
| [逐阶段处理审计](ie-processing-audit-20261106.zip) | 独立测试库保存的输入、步骤和实际落库；结论见[处理审计](processing-functional-audit.md) |
| [完整调查测试包](socai2-investigation-tests-20261106.zip) | 已保存的模型批次、无模型合同样例、页面与回执；解压从 `START_HERE.md` 开始。SHA-256：`361eb5b37d89bf31663f813f991c373f5f65173a80789963e40bef2142b8170a` |

原测试中的 failed、unknown、partial、截断及质量未通过全部保留。有模型正文与工件不等于结论正确；待复核和交付完整性分别展示。私密运行配置、密码与访问凭据不进入资料包。
