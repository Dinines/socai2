# 当前进度

更新于 2026-11-13。本批对外HTTP代码分离已完成本机/21发布、直接读回、独立审计及归档，53操作合同和docs7保持，证据见下表。当前逐步收固定 A/I→Case 的模型输入：先定义模型任务，再筛选有用字段，禁止原始结构整包透传；长期规则及[字段梳理](openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md)已更新。查询只给结果及 A/I/C3 字段筛选已由程序实现并离线核验；I 当前3,047字符，原冻结材料的 C3 仍7,680字符。完整 JSON 知识的新导入分块及 C3/Deep/C6 正文投影已本地修复，样例845字符原文生成448字符业务内容；新导入离线 C3 预览6,930字符，不能冒充旧 Run 的实际输入。Deep/C6 也已按各自任务筛选并由程序离线重建，正文分别8,768/14,080字符，必要前序及依据保持。另补普通工具结果的内部字段筛选及相同值共享展示；一条现有隔离库替身流程已核对A/I→C3→Deep补查→C6保存、引用及结果/当前评估GET。HTTP字段合同和数据库表不变，旧知识未重写；下一步仍需可采用的真实固定流程结论证据。本轮不新增真实模型调用。此前知识引用、A/I 引用纠正、C6 生成/反馈及输入检查修复和真实失败/保存读回见[验证](openspec/changes/complete-socai2-investigation-chain/fixed-flow-validation-20261112.md)；完整固定流程与模型质量仍未通过。上述模型修改未部署；独立HTTP入口另按下表已发布。本次Git同步仅包含HTTP边界与对齐文档，模型修改独立维护；源码提交不等于模型部署或质量验收。前批空表清理已独审归档，迁移127及28表边界保留；[交接指南](FRONTEND_BACKEND_HANDOFF.md)、[表职责](docs/investigation/investigation-table-scope.md)、[工作规则](AGENTS.md)。

## 当前运行状态

| 项目 | 已核验结果 |
| --- | --- |
| 分支与远端 | 本地 `V1.1`；本轮交付同步目标为 `origin/V1.1` 与 `origin/main`，父项目为 SpiritHub 的 `add-server-submoudle`，按其 `server` gitlink固定版本。源码提交与21已部署镜像分开核对；部署状态见下行 |
| HTTP交接文档 | [53个后端HTTP操作](deliverables/investigation-validation-20261106/http-handoff/README.md)，告警/事件/调查三类；docs7已同步两端，6入口200且摘要一致，50已实现/3预留501；E48–E53为告警人工判定及告警/事件单条、批量管理。[本机ARM64](http://127.0.0.1:18080/)、[21 AMD64](http://192.168.1.21:18080/)，[回执](deploy/api-docs/deployment-receipt.json) |
| API／处理发布 | 原主API `v1.2-20261112-r5`、处理镜像 `processing-20261112-r3`保持；独立API为`http-boundary-20261113-r1`，21内网18024，53操作，reader/writer实际同为`aisoc`；本机18024为`http-boundary-20261113-r1-local`、库`v12_upgrade_dev`。在subject-management基底叠加26个HTTP包/兼容文件，本机采用同源冻结代码；并行模型修改未带入，其他服务/消费者保持 |
| 工作台 | 一次独立源码发布 `workbench-20261112-graph-cleanup-r1`；当前查询28表、兼容旧29表快照；镜像、环境、命令、数据挂载及其他生产容器不变 |
| 正式数据 | `aisoc.socai2` 当前28表450列；24表有业务写入、comments/response_links有读取用途、conversations/messages仍有依赖。告警交接字段、枚举、JSON合同保持 |
| 本机数据 | `v12_upgrade_dev` 与 `socai2_local_20261105` 同样28/450；旧本机数据库容器恢复停止，其他历史验收库未清理 |
| 清理后直接读取 | 21实际读到1Case、4Run、36工件，4177的首页、状态、列表均200；三个目标保留目录指纹及既有告警/Case/Run/工件数量完全一致 |
| 知识功能 | 前批分诊保存后同步已交付归档，仍为开启/120秒；C2三目的检索、qwen3-embedding:0.6b/1024及专用集合保持，旧operation key不补派 |
| 模型与消费者 | Agents自动分析消费者关闭；Fusion、UEBA、调查数据整理消费组运行；固定01–04批的成功、拒收及系统收尾均保留。最新04批C3/两项Deep执行，C6超限零调用；Case为system_only/partial，不能当模型结论。字段梳理已有离线及隔离库替身接线/存取证据，真实模型质量NOT_PASSED |

[清理回执](docs/operations/evidence/graph-table-cleanup-20261112-01/delivery-summary.json)记录三个真实目标的结构与业务保留结果；[本项验收](openspec/changes/archive/2026-11-12-remove-unused-investigation-graph-table/validation.md)区分本机事务验证、专用空库新装、工作台装载与生产只读复验。冻结V1 SQL及迁移123–126未改，当前新装/增量/核验见[数据库入口](deploy/database/CURRENT.md)。独立运行脚本中的公共支撑结构不是业务后端需照搬的建表清单。

前批[知识同步回执](docs/operations/evidence/knowledge-sync-20261112-01/delivery-summary.json)仍是其直接流程证据。固定01批已证明知识进入请求、历史引用保存/GET读回，C6建议缺依据拒收；02–04批继续暴露I预算和C6完整输入超限，失败与系统收尾均真实保存读回，未追认成功。最后按原C3步骤取件核得04批C6正文63,262字符；当前仅调整查询/材料读取展示后离线为38,152字符，原记录及映射保持，不等于C6实际执行通过。本机运行记录静态包已导入至03批及本轮07批隔离库替身Case，共72份；04批尚未导入，在线4177未发布本轮内容。

产品文档已按现有设计重整为[逐页功能清单](deliverables/investigation-validation-20261106/frontend-feature-list.md)，逐项保留目的、操作结果，按后端实现状态和接口链接说明；事件另有展示字段与点击跳转表；[规则确认记录](docs/design/investigation-product-decisions.md)单列。D07 已由负责人确认：未解决问题随调查结论展示，不单独管理；需要人工确认时由用户创建任务。D01–D06 已按逐项讨论建议一并确认，七类规则均已同步产品说明；未实现功能的状态不变。原字段／跳转移到同目录技术附录，Case 写入及探索存储的过时说明已修正。前期产品规则整理仅改文档；本批按已确认规则实现告警反馈和告警/事件管理，不核销页面或模型未通过项。随后补齐[HTTP交接包](deliverables/investigation-validation-20261106/http-handoff/README.md)：125项功能当前映射53操作，参数、输入输出和错误保持，三项问答预留仍501。当前独立正式服务已有53操作，E36/E37已挂载/开启；具体测试和模型质量边界见下段。本轮同步目标为V1.1/main及SpiritHub的server引用；实际远端以Git提交和父项目gitlink核对。

## 未完项与下一步

HTTP当前53操作、540个固定输出字段出现位置、28组动态结构；[原43操作验证](openspec/changes/complete-socai2-investigation-chain/http-functional-validation-20261112.md)继续适用。[Case管理change](openspec/changes/archive/2026-11-12-manage-investigation-cases/validation.md)已独审归档，完成F23-04/D01：E44读取管理及结案条件，E45局部修改，E46结案，E47重开。两端各20次正常TCP HTTP、全部Case字段SQL及关闭/重开历史读回通过；运行中/unknown拦截、未完任务确认及理由、幂等/冲突有直接证据。实际镜像/源码/目标核对一致，原服务保持，未新增模型调用或迁移。随后[告警/事件管理change](openspec/changes/archive/2026-11-13-manage-alert-incident-operations/validation.md)已完成E48–E53：告警人工判定、告警管理、事件管理各单条/批量。两端各86次真实HTTP及6主体SQL逐值读回通过；D02关闭/反向恢复、人工关闭保留判定、事件分配/解决/等级覆盖、幂等与整批拒绝均有证据。原47操作/106个Schema保持，未新增表或模型调用。API及docs7已同步，限定独立结束审计通过并已归档，见[本批回执](docs/operations/evidence/subject-management-20261112-01/delivery-summary.json)。后续接口按[实施计划](docs/investigation/http-implementation-plan-20261112.md)补列表筛选/排序等；负责人已确认仅HTTP封套新增filtered_total/next_cursor，数据库和行字段保持。按最新要求先完成[对外HTTP与内部调查调用分离](openspec/changes/archive/2026-11-13-separate-investigation-http/validation.md)：53操作迁至独立HTTP包，原合同完全保持；本机候选34项及18子检查、24次TCP/SQL及2项A/I替身验证通过；旧入口导出/打包遗漏修正后6项定向复验和独立结束审计通过，已完成本机/21的18024发布。本机新Case/任务写读及SQL通过；21仅12次GET/9对象只读SQL，未新增正式库测试数据；两端docs7合同及6入口摘要保持；发布后独立审计通过并已归档。内部步骤和必要组件HTTP保留原归属；列表功能随后在原change继续，固定模型流程仍单独收口。

前批空表清理的结束审计和归档已完成；当前固定流程已通过[限定程序修复独审](openspec/changes/complete-socai2-investigation-chain/fixed-flow-audit-20261112.md)，不替代主调查完成。本次按用户要求提交已验收的HTTP边界源码、交接和非私密回执，推送V1.1/main并同步父项目引用；并行模型源码与未提交证据保留，Git同步不触发服务部署。

负责人最新顺序：**先做好固定范围调查，再推进更新/流式；输入按 A → I → C3 → Deep → C6 逐步筛选。** [A 离线回执](docs/operations/evidence/model-input-selection-20261112-02/rebuild-summary.json)与[I 完整输入](docs/operations/evidence/model-input-selection-20261112-03/I-model-input.txt)均由程序生成；I 移除160条纯目录历史匹配，保留成员事实、有效 A 判断/必要历史及原引用范围，8项直接检查及限定独审通过。新增 I 规则已限定在自身投影层；Case 共享的字段规则保持，整体配置摘要随文件更新。[C3 完整输入](docs/operations/evidence/model-input-selection-20261112-04/C3-model-input.txt)及[请求预览](docs/operations/evidence/model-input-selection-20261112-04/C3-request-preview.json)已由程序重建：正文30,573→7,680字符，空候选工具消息1,151→24字符，102来源的原主体/范围/角色及原件保持。6项直接检查通过；独审指出有效 I 整体结论引用遗漏，已补齐保留/可见短号/缺失说明并定向2项通过；人工姓名保留再定向1项通过，限定复阅通过。该批新增字段规则仅由 C3 使用。

[完整知识回执](docs/operations/evidence/model-input-selection-20261112-05/rebuild-summary.json)核对原完整资料与旧两段逐字相符，再由程序保留完整 JSON 块并选取业务字段。已识别技术知识的[模型正文](docs/operations/evidence/model-input-selection-20261112-05/knowledge-model-content.txt)在 C3/Deep/C6 一致；未知结构和旧碎片保持。5项不同的直接检查通过；独审发现 JSON 数值溢出可能阻断装配，已修复并定向2项通过，限定复核通过。原冻结 C3 仍7,680字符；[新导入 C3 预览](docs/operations/evidence/model-input-selection-20261112-05/C3-new-import-preview.txt)6,930字符，仅为离线合成回执，没有实际导入、索引或模型派发。HTTP 路由/字段与数据库表不变，新导入分块数量可能变化；旧切片后续使用完整原件重新导入/索引，不原地改写。[Deep/C6 输入整理](docs/operations/evidence/model-input-selection-20261112-06/README.md)已本地完成：先 Deep 指定问题，再 C6 全案综合，正文30,130→8,768、38,152→14,080字符；12/65项结构化依赖均恢复，原文/原主体/范围保持，7项不同的直接检查及限定独审通过。这里只复用冻结材料，没有新 Run 或模型调用；旧知识碎片仍留原样，输入体积不代表模型质量。[工具返回处理](docs/operations/evidence/model-input-selection-20261112-07/README.md)也已本地实现：保留查询容量边界，普通字段共享显示时仍逐一保留记录和引用，差异/冲突及被前序引用的内部ID保持。1项已有字段检查及1项隔离库替身正常固定流程通过，综合结论/当前评估GET一致；保存结果为accepted/partial，不是实际模型质量通过。前置脚本问题、旧合成数据和实际原请求均保留。下一步仍需有效A/I及可采用C6的真实固定流程证据，不为后置正文问题反复采样。[后续 OpenSpec](openspec/changes/schedule-streaming-investigation-updates/proposal.md)已写更新触发、队列合并、人工反馈 C6 复核和知识边界，尚未实施；当前不增加队列或自动接续，不以程序修复或失败结果读回核销完整固定流程。

本轮交接补充[组件/Kafka](docs/integration/component-handoff-current.md)、[可复用测试数据与操作](docs/integration/backend-test-guide.md)、[Swagger本地配置](deploy/api-docs/README.md)及[4173测试页面](docs/integration/test-page-4173.md)。21:18024已再核运行版本和53操作；Kafka组只读确认Fusion/UEBA/投影运行、Agents自动分析关闭；现有页面仅用于测试，用户明确本轮不要求修改页面。

正式告警级人工反馈现通过E48/E49保存；Case H任务版本和告警反馈保持各自用途，均不自动重派调查。Q问答、探索保存、完整评论附件、真实响应操作和自动消费仍不属于当前完整交付，不因旧AiSOC模块扩大范围，资产等基础数据由业务后端实现。

F02召回正文相关性／合理使用、F01完整语义质量仍未通过；P01–P04为历史页面事项，现有页面按用户最新说明仅作测试，不列为当前后端交付前置；M01-A/M01-B保持已知未修复、不反复采样。前批及本批模型partial/rejected、conclusion=null结论保留。主调查仍31/41，未完成整体任务不因本轮清理核销。[问题清单](docs/investigation/current-issues.md)。无关未跟踪 `tools/model-preflight/` 保持。
