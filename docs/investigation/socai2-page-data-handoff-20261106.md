# 页面数据交接：Case分类、期限、判定与证据

后续追加测试见[统一测试与功能字段交接](investigation-test-handoff-20261106.md)：本机API已重启加载本批代码，3个新模型Case的page-data实际GET/原页读回通过。本文的0模型、未重启、14Case及48/50是本次数据增量交付当时的记录，现累计63次；不改写以下原验收范围。

2026-11-06，`codex/case-baseline-history-20261103`。本批实现[现有OpenSpec数据优先设计](../../openspec/changes/complete-socai2-investigation-chain/design.md#页面数据合同优先推进2026-11-06)中D1—D3，作为任务3.12的数据部分单独交接。目标是原页面所需数据能保存、关联、读回，不以模型推理质量或完整实时表单为前提。

增量126已应用本机专属`socai2_local_20261105`，现29表462列；未重建数据库或改写旧业务记录。原页面布局保持，仅改字段绑定、缺值/五种判定状态显示，并追加4个明确标注的合成数据合同样例。新增模型调用0；19/26任务、48/50模型尝试保持。新路由已有源码和ASGI权限/参数测试；本批没有重启常驻API，不把源码验收说成在线接口部署完成。

## 字段—保存—读取

| 页面数据 | 数据库存储 | 读取合同与缺值 |
| --- | --- | --- |
| Case分类 | `cases.classification`，126新增 | true_positive/informational/false_positive；null为未设置，不借Incident/Alert |
| Case截止时间 | `cases.due_at`，126新增timestamptz | 输入有时区，可清空；独立于H任务期限和执行超时 |
| 当前案件判断/列表判定 | `cases.current_assessment_id → case_assessments.conclusion` | 取同一个已采用版本，带来源、时间、范围；无判断为null，不取最新Run代替 |
| 当前证据目录 | `cases.current_evidence_artifact_id → artifacts`，126新增指针 | kind=case_evidence_index，schema=socai2.case-evidence.v1；同租户/Case约束 |
| 每条证据及判断依据 | 工件`content_json.entries[]` | 稳定ID、成员/对象、source_refs、verdict_sources、命名空间威胁身份/来源、可空处置回执、active/withdrawn |
| 独立证据数 | 共用读取器投影 | 当前有效active条目数；多成员条目只要一个成员移出就整条排除，历史不缩范围 |
| 关联威胁数 | 共用读取器投影 | malicious/suspicious且有明确威胁身份的条目，按(namespace,key)去重；clean/unknown/conflicting不计入 |
| 操作人、来源、前后值 | 既有`activities`/`activity_targets` | 与管理字段或指针同事务写入，不另造审计表 |

列表`items[].page_data`、Case详情`page_data`、`GET /api/v1/socai2/cases/{case_id}/page-data`和`case-page-data.json`共用实现。新增`PATCH .../page-data`及`POST .../evidence-index`支持明确写入；写请求含幂等键及预期row_version，证据发布还需预期当前指针、实际前版和范围版本，过期写入拒绝。Case锁、追加工件、更新指针和活动在同一事务内完成；不启动Run、不改变处理状态和成员范围。

无索引、不可得或无效引用返回null；有效空索引/全撤回返回0。partial返回已知计数和范围限制，不能把0解释成全案无威胁。原始告警、来源快照、Run图谱不会因没有独立证据而消失，也不混入独立条目计数。

## 来源边界

来源必须实际指向已保存行和JSON Pointer，租户、Case、成员范围和对象材料键一致。v1登记Alert材料、C1冻结citation_roles、Result段落/条目范围、已完成人工反馈及有实际response_links关联的专用响应回执。原始材料只有登记的OCSF行为叶路径及标量值可作为observation，其他路径保守为source_label；普通模型请求不能作为处置回执。对既有C1的prior_analysis/human_statement不提升为原始观测。未登记工件格式拒绝作为新证据来源，仍保留原件供读取；将来补充适配不要求改页面结构。

校验保证保存来源和范围，不保证来源标签或模型结论在语义上正确。本批14案中没有单独的human来源当前判断，该来源未作真实PG采用验收；已有H来源/版本兼容沿用原定向测试。本批没有从旧模型正文猜造恶意标签或威胁身份，也没有自动给旧Case补证据索引。专用响应回执格式的正向业务执行、任意厂商原始字段映射及外部身份目录没有在本批验收。

原材料页可查看条目及其来源告警，案件资料可进入告警原件。完整source_refs、索引版本、全部成员/对象、JSON路径均保存在数据库和导出中；现有证据详情抽屉仍仅显示原有摘要及首个关联告警/实体，**没有新增完整来源目录界面**。这属于后续呈现/接线工作，数据已经可取。

## 保存的样例与验证

在[原Cases页面](http://127.0.0.1:4174/#/cases)搜索“数据合同样例”。批次`page-data-20261106T013645Z`：

| 合成样例 | Case ID | 证据/威胁 | 用途 |
| --- | --- | --- | --- |
| 正常授权 | 7dfdf1ed-1bfa-45f8-b8b5-a8b6c01b143c | 2 / 0 | clean证据存在，不计威胁；分类informational |
| 恶意样例 | 80b07fe5-3493-4b4d-80e5-032e190b2ccd | 2 / 1 | 两条不同证据共享同一个威胁身份；分类true_positive |
| 尚待核查 | 5167554d-6cb5-40ea-9fb4-524a5c7b91d6 | 2 / 0 | unknown不计威胁，保留原来源 |
| 尚无记录 | a8f6bca9-fa1f-44ed-b14f-456dfc5a3d20 | null / null | 没有当前判断和证据索引；不显示假0 |

这4案/8告警/6当前证据没有Run、没有模型调用。前三个结论是明确标注的固定导入文本，保存为legacy/legacy_unverified，只用于验证数据库—读取—页面字段；不是正常/恶意模型能力评估的新结果。

| 验收 | 实际完成与证据 |
| --- | --- |
| DA01 | 本机PG写入/清空/恢复分类期限，幂等与过期版本检查；actor/source/before/after保留。10个旧Case新增三列均null，原处理状态/范围和历史Run保持 |
| DA02 | 14个当前Case列表/详情一致，包含4个model、3个system、3个legacy当前判断；页面旧案例判定改读原已采用结论；无判断仍空 |
| DA03 | 本机保存版本、撤回、重发、错误前版/来源反例；旧索引保留。纯测试进一步核租户、路径、范围、标签角色、对象及处置来源拒绝 |
| DA04 | PG核同威胁去重、clean/unknown、空/全撤回、缺索引、部分成员排除；纯测试补四条目/一威胁、同名不同身份、conflicting及无效引用 |
| DA05 | 四案同一只读快照导出与直接读取逐值一致；浏览原列表、恶意案件资料/证据详情、缺记录案件；24个导入/生成/原页定向测试通过 |
| DA06 | 同步字段字典、结构化合同、JSON Schema、OpenAPI、SQL及本交接；[独立结束复核](../../openspec/changes/complete-socai2-investigation-chain/page-data-review-20261106.md)ACCEPT/0必须修，仅限本表已验证数据范围 |

首次PG运行完成保存检查后，在导出比较发现UTC的`Z`与`+00:00`字符串差异而失败，未重派写入；已用类型化时间统一，保留原失败目录，随后只读回查通过。再加入旧Case兼容检查时，验证脚本误按对象访问字典返回值而失败；修正后14案通过。这两项原因分别是投影格式与验证脚本，均非模型或数据库不可用。测试补充期间的fixture缺select导入、CurrentUser构造参数及drawer函数名错误均修正后重跑，不记作产品成功证据。

公开回执见[page-data-summary.json](../operations/evidence/page-data-20261106/summary.json)，详细本机原件留`.local/local-investigation/page-data-20261106T013645Z/`；最新兼容读回为`readback-20261106T015728Z`。本批不把DA交接标成整项3.12或4.1/4.2完成；C6/H容量、模型事实约束、知识消费、VPN服务器模型对照及实时表单接线仍独立推进。

## 后续对接顺序

1. 前后端按[字段字典第8节](../design/socai2-field-dictionary-20261103.md#8-页面数据合同126增量)、[OpenAPI](../design/socai2-independent-api-v2.openapi.json)、[只读SQL](socai2-page-data-readback-20261106.sql)固定读取字段及null/0/partial规则；现有Case资料、结论、图谱和历史可继续接线。
2. 部署/加载126对应的新读取与写入代码后，再接原页面保存动作，明确PATCH的两个字段需要同时传值；不改原页面模板。证据详情完整来源目录可使用已保留字段扩展。
3. 调查模块后续只需产出同一结构；模型、提示词、工具/调度改动另按R1—R8验收，不要求前端跟随改版。本批合成证据不回填成历史模型的输出。
