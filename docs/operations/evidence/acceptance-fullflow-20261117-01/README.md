# 任务4a：新场景材料和当前21核对

本轮完成新材料准备，**尚未发送首段或追加段，`ready_to_execute=false`**。实际业务目标仍为21正式`aisoc.socai2`；本机禁网Docker准备不等于21完整流程验收。实施范围见[统一设计§12.13](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1213-任务4整体安排与4a材料环境核对2026-11-17)。

| 执行段 | 新材料 | 计划动作 | 当前实际状态 |
| --- | --- | --- | --- |
| part1 | 1条进程启动告警、2条父子进程上下文 | 上下文写入并读回后发送告警，等待A/I，再创建1个整事件Case | 仅prepare，未发送、未建案 |
| part2 | 1条后续网络告警、1条网络上下文 | 首段结束并核对后显式append，检查同一Case后轮，预期成员1→2 | 仅prepare，未发送 |

材料是本批作者配置经既有生成器生成的5条新业务观察，采用原生[scenario.json](materials/scenario.json)合同。控制旁路保存选材位置、批次和计划；业务材料没有测试批次或期望答案。后台租户、来源及父子进程关联保留。实际A/I/C3/Deep/C6请求过滤必须在4d核对保存输入，本轮没有模型请求，不能据此称模型输入验收通过。固定告警Case复用3c.2已有验证，不额外建第二个Case。

已有3d04镜像的5条真实Docker命令全部退出0：inspect、prepare、status、EOF退出session、report。使用`linux/amd64`、显式UID501:GID20、`network=none`、材料/配置只读和结果持久目录；容器移除后另容器读回同一execution。5条业务原值和时间、来源指向、父子关系、`false`/有效空列表、新身份及文件摘要均已核；未创建Run。[离线回执](offline-preparation.json)、[作者回执](authoring-receipt.json)、[未执行报告](results/report01/report.md)和[冻结清单](preparation-freeze-01.json)保留。

21只读观察见[current-environment-03.json](current-environment-03.json)：HTTP/Fusion/4177健康均200；目标库、角色和租户匹配；来源已登记且类型匹配；2个新告警ID、3个新来源事件ID和新关联范围在所查调查表中均未占用；观察时无accepted/waiting/running任务，调度上限仍1。模型窗口65536，A/I/Deep输出8192、C3/C6输出16384、原Run总预算均保留。服务ID、启动时间和重启次数前后一致，没有业务写入、Kafka发送或模型生成。

只读驱动的两次核对问题保留原件：01误用了`analysis_tasks.status`，实际字段是`state`；02又误把连接器`is_enabled=true`加入通过条件，03完整展示其实际为false。现有验收入口`Postgres.preflight`和Fusion持久化按来源ID、租户及类型核验，未要求启用采集连接器；本批直接投递测试材料不需要启用它。**没有为通过检查而改来源配置或数据库。** [环境解释及后续缺口](preparation-assessment.json)按现有合同判断来源登记，03的原始差异字段不改写。

当前21处理/HTTP仍r4、页面r6，C1和viewer.js摘要与本机候选不同，未包含本机已验修正/布局。后续依赖按顺序推进：

1. 4b补报告到具体主体/Run的链接及由实际结果生成紫色来源映射，复用已有02/01证据，0新模型。
2. 4c统一目标版本和显式连接配置，并从最终验收容器实测HTTP、PG、湖、Kafka advertised broker及必要运行配置。本轮仅在现有服务容器只读查询，不能替代该准入。
3. 4d先首段保存/读回检查，再明确追加一段；查看实际工作台、模型原答与质量问题，最后独审。

本轮没有部署、重启、清数据、修改业务/HTTP/数据库合同或模型预算；32份3d最终冻结文件保持不变。旧失败、未知和质量问题保持原结论。测试模块独立核对及最终结果在[本步验证](preparation-validation.json)登记；不以准备通过勾销任务4或整个change。
