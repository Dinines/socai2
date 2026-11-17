# D2质量继续的独立复核

2026-11-16。对应TC-N03/D-N02；D2在本机单点、真实模型/PG/Redis及当前ASGI HTTP读回范围内通过独立验收，可按本步收口。单点21/21；新批保存证据44项、HTTP证据69项独立核对通过。调查模块负责核心实现，协调模块接管唯一真实链，测试模块未修改核心、未重复派发业务Run、未进入D3–D6或部署21。

配置以r3发布清单引用的`streaming-release-20261116-02/analysis/investigation-policy.toml`和当前源码为准。新测试显式选择该policy，C3/C6输出各16384；重用的既有断言在此fixture下运行，不沿旧测试文件的本机policy。测试文件见[独立检查](../../../../services/api/tests/test_socai2_d2_quality_independent.py)及调查模块的[六类直接检查](../../../../services/api/tests/test_socai2_quality_continuation.py)。

## 离线检查及保留失败

- [attempt-01](attempt-01/execution.json)：18项中14通过、4失败，23份源码/配置/来源摘要运行前后不变，0数据库/模型/部署调用。六类限制说明、既有七项引用及身份/执行保护、报告展示通过。
- 其中3项是独立测试假设错误：Deep按当前问题筛选C3内容，并不要求总摘要进入。已改为Deep核对应问题原答、C6核总摘要；[定向复核](harness-correction-01/result.json)3/3通过，未修改核心，首次失败保留。
- 第4项为真实r3首轮C6原答的新增程序阻断：六类限制说明已转为诊断，但F1的32项冻结原始字段由程序装配为1218字，超过`Text`的1200字上限，被`observed_original_fields_exceed_statement_contract`拒收。原答没有模型生成的`statement`；32项都在同一C6输入的来源目录，原值逐项一致。见[长度定位](attempt-01/assembly-boundary.json)、[原答及字段对应](attempt-01/f1-assembly-detail.json)。调查模块已将此作为D2必要装配阻断修正；本项描述修前事实，不覆盖首次失败。

[attempt-02](attempt-02/execution.json)最终21/21通过：六类说明缺失6项、装配/正文保护3项、既有引用及身份/执行保护7项、独立提示/报告/真实原答重放5项。24份源码/配置/来源运行前后摘要不变，测试时源码归档在`attempt-02/tested-sources.zip`。真实F1全部1218字与32引用保持，正文SHA与修前独立还原的预期一致；原结论、判定和范围保持。生成Schema仍限制模型正文1200字，见[独立检查](schema-check.json)；模型冒写observed.statement、篡改装配、inferred/unresolved超长仍拒收。此结果只覆盖当前离线接收/装配/输入与报告，不替代真实保存链。

离线测试的预设答复只用于稳定触发质量/保护规则；原r3真实答复的回放是新接收器检查，不是新真实模型调用。冻结快照`e4c3bdd0bd21d1c7fd730ad484623224242be2dbee4c6d5d88d05ab8193bcdc5`及历史`rejected/unavailable`保持，不追改旧Run。

## 保存和HTTP交接

用户最新要求使用真实模型，保存/HTTP链已改为当前配置下的新批真实调用，原计划的固定返回链未执行。协调模块执行real-02后，测试模块完成同批实际输入、原答、诊断、Result/报告及HTTP回执的只读独立复核，未重复调用。

协调模块接管后，[real-01只读复核](real-01-review/review.json)确认首次失败停在夹具准备：14个来源对象的`match_basis`原本为空，将Python `None`作为JSONB值写入会形成JSON `null`并触发类型约束。该租户导出的19张业务表均为空，模型调用0次、Case/Run均未建立；租户/账号在另一事务先提交，不称全库无写入。源快照字节摘要与既有冻结相同，驱动的`source_sha256`是规范化JSON摘要，两者并非原件变化。修正应保留SQL NULL语义，另开新批；旧失败不覆写。21项测试所覆盖的24份文件摘要仍一致，无须重复执行。

本步真实链采用本机隔离PG、当前真实模型与Redis任务入口；旧Kafka批次原始告警/材料复制到新身份，未重新执行Kafka或A/I，可选外部查询源禁用时须如实记未查询。HTTP驱动使用当前应用和真实PG的进程内ASGI请求，不是21/TCP服务或4177浏览器验收。新批由协调模块唯一执行，测试侧只读核对保存回执。

正文质量仍独立记录，规则测试通过不代表模型质量通过。随机截断、超时/断连、21新版本、4177新能力和完整change结束审计均不由本步提前核销。

## real-02最终独立验收

Case `5816b0b1-ab0a-5102-8688-2c92ffe5f1cc`，Run `6e831f66-c141-4ea8-ab48-9a761c9b6e45`，Result `c20dab79-4e0e-4c56-848c-65fdd78f7e98`。C3、Deep、C6共3次真实请求均stop，1任务/1attempt/1Run/1Result，4成员、17步骤、47工件。实际输入均无后台tenant_uid；Deep/C6保留前序引用问题提示。新配置保持既定模型预算，仅tokenizer经本机转发，Case日志查询上限按当前r3执行器对齐为50。

- [保存证据独立复核](real-02-review/database-review.json)：44项通过。4份材料与14对象的原字段/空值逐值保持，新身份和成员关系正确；请求/响应原件、摘要、结论/判定/范围、限制说明、完整delivery_report和compact report/Result同源。复核脚本为[review_saved.py](real-02-review/review_saved.py)。
- [HTTP独立复核](real-02-review/http-review.json)：69项通过。同一Run的50次唯一GET均200，17步骤/47工件完整读回，Result及delivery.detail.citation_review与保存原件一致；19表GET前后摘要不变，Redis占用释放为0。复核脚本为[review_http.py](real-02-review/review_http.py)，原始HTTP回执见[real-02-readback-03](../quality-continuation-d2-20261116-01/real-02-readback-03/result.json)。测试侧只读文件，未另连数据库或请求HTTP。
- 真实质量问题：C3一项`member_source_coverage_missing`；C6两项`unapplied_domain_needs_limitations`。均保留原结论/状态/范围，C6空限制列表保持，问题独立登记后继续。最终`accepted / uncertain / partial`，`prose_quality=not_checked`，不报模型质量通过。

原real-02驱动的`KeyError: delivery`、首次只读补验把alias和UUID直接比较、第二次把质量诊断当HTTP顶层字段，均是验证脚本沿旧结构取值的错误，分别保留在原批及readback/readback-02。最终按当前合同验证：完整报告在source_snapshot；report_json是紧凑核心；HTTP质量位于delivery.detail；范围按同次请求冻结映射恢复。业务保存记录未改变，补验新增模型0次、业务写入0次；原失败不覆写。

静态4177导出由协调模块另行更新，本独立验收未访问浏览器，不将其算作当前21 HTTP 4177已展示。TCP发布、Kafka/A/I整链、外部查询上下文、D3–D6以及完整change结束审计仍在本步之外。
