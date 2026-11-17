# r3新批S01入站与来源范围复验通过

2026-11-15，21候选`streaming-20261115-01`，新批`s01-ingress-20261115-02`。按[同一子步复验计划](../../../../openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md#t2后续子步s01分阶段kafka发送与即时持久化)，**真实Kafka→湖上下文→告警原生保存及来源范围→同批HTTP读取通过**，见[本步验收汇总](acceptance-01.json)。不把本步记成完整调查或模型质量通过。

## 当前配置与独立身份

- 以[最新r3就绪回执](../streaming-ingress-20261115-01/ready-02.json)及[本批配置快照](ingress.json)冻结，ready SHA256=`faab593f92cd9537a09bc0669469ea5ec82edba150b6738ff3212657ccf540e3`；实际镜像`sha256:859c34c4730956511f6fb1c3f54085eeafd48e09671c8ffb45d7a4e5cab9d12f`。
- [输入/预期](dataset/manifest.json)、[发送准备](prepared/manifest.json)、[源码/产物冻结](freeze-01.json)保持；prepared manifest SHA256=`0b02d0461d097cf2640a2c139bfed2daf836751772da082a9778ff880972aabe`。
- 归并IP为`192.0.2.11`，与旧失败批`192.0.2.10`分开；新host/account/source UUID随batch生成，base_time=`2026-11-15T10:14:18Z`。[新connector读回](connector-readback.json)为普通reader，同租户，health保持unknown。
- r3仅修Fusion两个入口，[直接新旧对照](../test-source-scope-fix-20261115-01/README.md)保留旧r2的6失败及修复后21通过；本批没有使用旧模型配置、旧public投影或旧业务ID替代新输入。

## 真实保存与读回

| 阶段 | 直接结果与证据 |
| --- | --- |
| 旧基线 | [preflight](readback/preflight-readback.json)核旧3A completed、1I resolved，旧4task仍accepted、0attempt/Run；原材料/6引用/3工件/12湖记录保持。只允许已记录的HTTP管理字段变化，未重复PATCH。新connector可读 |
| 上下文发送 | [12条ACK](prepared/receipts/S01-context.json)，raw_events分区0、offset 12–23；无unknown/未尝试 |
| 上下文保存 | [context](readback/context-readback.json)新增12条真实湖记录，PG增量全0；[湖快照](readback/context-lake.json)核原件、身份、毫秒、0/false/空数组及三类查询命中/排除，旧基线逐行保持 |
| 告警发送 | [3条ACK](prepared/receipts/S01-alerts.json)，raw分区0、offset 3–5；关联同批上下文通过摘要，无重复投递 |
| 告警保存 | [alerts](readback/alerts-readback.json)新增3A/3材料/3真实source_refs/3首次工件、1I/3成员、4 initial/accepted/source=ingress；0attempt/Run/Case/模型。原始raw_event/OCSF/raw_text和source_scope均保持；每条仅1条真实上下文引用，complete=true，不含告警自身ID |
| 同源HTTP | [35次实际TCP GET](../streaming-ingress-http-20261115-02/result.json)全部200；3A↔I、材料/原件内容、成员/来源各2页完整3条、4任务列表/详情及无Run/结果均与测试快照一致。仅GET，无业务写入、直查DB或模型 |

同候选当前总量为24条湖记录、6A/2I/8任务及9条来源引用，其中旧批6条错误引用仍原样保留；**本批正确增量只有3条来源引用**，不将旧错误清掉或追认为正确。

[通过的实际identity-map](readback/identity-map.json)来自[PG快照](readback/alerts-pg.json)，不是用预测ID填充。新事件`263a1c58-e9c6-4ba4-9204-3b0568970551`与旧事件不同。三条告警、四任务及材料/工件身份已一次性交HTTP方；其35次GET使用这份映射和快照，通过后再次核对四主体/task ID一致。首次HTTP离线断言误要求公开source_ref包含私有tenant_id，已按既有公开合同修正、复用保存响应通过；[原失败](../streaming-ingress-http-20261115-02/validation-01.json)保留，未改业务代码或重跑请求。

## 边界和保留

旧批失败材料、输入、expected、回执全部保持。旧批关闭由[HTTP原回执](../streaming-failed-batch-close-http-20261115-01/result.json)证明；本批预检和两道后读回逐行核旧基线未变。旧task仍accepted，尚未实际执行closed_before_start，不冒称已经skip。

临时运行包包含空receipts目录，容器按目录所有者运行；本批所有6次调用均成功，无重发、恢复或清理。原批准备失败没有覆盖。只读脚本使用普通PG reader/TLS与CH reader，[取回摘要核对](transfer-verification-01.json)通过。业务保存由正常Fusion/LakeWriter完成，测试没有直接INSERT调查表或湖表。

本批只证明日志上下文来源与告警入站，不代表真实C4工具已被调用。背景资产/账号和知识仍为数据包中的authored_not_imported/authored_not_indexed，需后续真实来源供给。A/I/Case调度关闭，真实模型0；S04、Case首轮/更新/上一轮比较、W2跨Run、W3/4177与W4均未推进。模型正文质量后续单独记录，不能用本批通过核销。
