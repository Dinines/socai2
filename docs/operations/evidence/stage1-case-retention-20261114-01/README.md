# 阶段一步骤2：Case原结论与引用诊断

2026-11-14。状态：**步骤2本地直接验收通过，未发布**。所属[OpenSpec change](../../../../openspec/changes/complete-socai2-investigation-chain/tasks.md)，实施前目标、步骤及验证安排见[阶段一设计步骤2](../../../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#本轮步骤2case原结论引用诊断流转及采用)。主change仍31/41，模型正文质量NOT_PASSED。

本轮仅处理C3/Deep/C6原结论保留、独立引用记录、下游流转和采用。复用步骤1诊断，先离线检查，随后新隔离PG批次走通C3→Deep→C6→报告/Result→现有HTTP读取与采用；模型和来源替身分别标明，不宣称正文质量、真实取证或生产验收。

C3额度、数量配置、补答机制保持当前状态。未知成员/结构、真实输入过期和人工选择保护保留；旧数据及失败不改写。本轮止于步骤2，不进入步骤3，不部署/提交推送。

## 实现与存取关系

- C3执行工件v3、Deep v2、C6 v2复用步骤1引用诊断。原始回复先保存，再装配派生结果；未知、空、重复、范围/角色错配和局部finding引用问题分别记录，不据此删除原正文或改业务状态。同列表保序去重有前后记录，未知编号不造来源，结构/主体/执行绑定仍严格检查。
- C3摘要、成员、问题、发现、领域理由、矛盾解释和后续需求继续保存。程序owned observed仅展示实际可解析的原观察；没有可解析观察时明确“未绑定”，原声明状态/范围及质量问题仍在，不能补造事实。Deep原问题回答继续进入C6，相关前序内容保持prior_analysis及简短质量提示。
- C6结论、影响、建议、报告和Result使用同一派生版本。实际来源链接独立于模型声明覆盖；纯引用问题不清空结论或改成not_analyzed，也不发起引用纠正。未决业务问题、未查来源等实际限制继续使本批delivery_state为partial，与supported/accepted及质量issues_recorded分别表达。
- 现有自动采用和人工预览/提交路径正常使用这些结果；本轮未修改数据库函数、表列或对外HTTP合同。老工件版本仍可读取，旧拒收和unknown不重新计算。共享C3再分析读取入口同步兼容新诊断/版本，本批未额外调用再分析。

读取路径沿现有Case Run工件接口：`model_response.content_json.payload`含`raw`、`derived`和`citation_review`；诊断链接原答`source_snapshot`、请求、步骤、原文hash和派生hash。C3汇总在`basis.citation_review`，Deep汇总及C6详细报告/report_json在`citation_review`。Case Result、当前判断、历史版本仍走原接口，未新增告警字段。

## 直接验收

| 检查 | 结果与证据 |
| --- | --- |
| 离线定向检查 | [59项通过、1项已知失败单独排除](offline-tests.txt)。含7项新增Case保留/诊断/流转/结构与绑定检查，其余复用C3、后续输入及A/I检查 |
| 原答与保存 | [attempt02](attempt02/execution.json)新建2条A、1条I、1个Case；C3→Deep→C6各1次替身。三阶段原答、派生hash、独立诊断、C3/Deep原内容进入后续请求、Result/report_json/markdown一致 |
| 读取和采用 | [attempt04-readback检查](attempt04-readback/checks.json)：54次GET、4次POST；原答/派生/报告逐值读回，GET前后无工件或业务写入，无新增模型调用；自动采用、人工采用和幂等重入、历史读回通过 |
| 采用保护 | 同Case旧预览令牌被409拒绝；自动重入保持新人工指针；新增材料revision=2后候选变stale且采用被409拒绝，原材料/Run/Result/工件和两条判断历史均保留 |
| 范围与额度 | [scope-verification.json](scope-verification.json)：最终126个运行源码文件与完成PG Run时hash一致；配置及JSON文件、C3提示未改。实际请求输出额度C3=4096、Deep=3000、C6=8192，无新补答逻辑 |
| 收口检查 | [completion-checks.json](completion-checks.json)：OpenSpec strict、修改文件Ruff、差异空白检查和快照hash通过；不代替主change完成时的独立结束审计 |

本批Case `45490018-8d5b-4ece-93cb-491cc5f5ceaf`，Run `53eae001-e042-453e-800d-46ccb9a75b75`，Result `dc7c2706-1a22-4d01-aba5-35baff4ab982`。隔离库为`v12_upgrade_dev`，显式配置见[config.json](config.json)。共6次模型替身（夹具2A+1I、本步C3+Deep+C6），**0次真实模型、0次外部来源调用**；后台空查询是明确替身，不是实际查空。HTTP采用真实核心用例和隔离PG，传输为ASGI且覆盖身份依赖，不冒充生产鉴权/TCP验收。

保存快照分别为[采用前](attempt04-readback/database.json)、[人工采用后](attempt04-readback/database-after-adoption.json)、[新材料过期保护后](attempt04-readback/database-after-freshness.json)；[接口原回执](attempt04-readback/api-responses.json)与[来源校验清单](attempt04-readback/manifest.json)保留。

## 尝试、既有失败与展示边界

1. attempt01仅验收脚本导入错误，尚未连接数据库，原[failure](attempt01/failure.txt)保留。
2. attempt02业务链和自动采用成功，首次读回脚本错误要求Run接口直接带结论；Run实际返回Result标识，故验收当时未通过。原[failure](attempt02/failure.txt)及完整数据库/请求/原答保留。
3. attempt03仅继续读取已结束Run，发现验收脚本需通过`current_assessment.value`取当前判断，未新增模型、采用或材料修改；原[failure](attempt03-readback/failure.txt)保留。
4. attempt04修正上述验收合同路径后继续同一已完成Run，通过读回和采用保护；没有重派旧Run或改写前三次失败。`run.py --readback-from`只装载已完成回执并验证，不能派发模型。

复用后续输入测试最初24项失败，在修改前源码同样出现，见[基线](baseline-tests.txt)；6处旧夹具改用当前程序补coverage入口后，27项通过，剩余历史查询重复展示断言在原源码仍失败（期望2条whole-row来源，当前选择为0），见[对齐后基线](baseline-aligned-tests.txt)。该输入展示断言登记后置，本轮未修改历史查询选择/去重实现；排除该项后59项直接检查通过，不宣称全套测试通过。

本机查阅静态文件已用现有`update_processing_audit.py`更新为6条记录，原5条保留。新记录使用[采用及过期保护后的快照](attempt04-readback/audit-export/manifest.json)，因此本批最后状态为当前人工判断仍保留、来源输入stale。实际4177仍由SSH转发占用，未换源或发布；RV12业务结论展示修复未实施，不能把静态更新说成21或4177已上线。
