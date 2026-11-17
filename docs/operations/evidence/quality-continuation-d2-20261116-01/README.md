# D2：质量问题登记后继续

2026-11-16，本机实施及真实保存/读取验证通过。六类缺少限制说明的问题进入独立质量诊断，保留模型原结论、业务判定和声明范围；不补造说明，不再因此整份拒收。未知身份、无效工具绑定及结构保护仍在。实现范围见[设计第9节](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#9-d2本轮实施边界与直接验证安排)，独立复核见[测试模块回执](../test-quality-continuation-d2-20261116-01/README.md)。

本步同时修正一项必要装配阻断：程序从32项冻结原始字段还原的1218字观察不再受模型撰写正文的1200字限制；原值、引用和防篡改校验保持，模型撰写字段及生成Schema的原限制保持。定向独立测试21/21通过，原始失败、修正后的测试源码及摘要均已保留。

## 真实执行与读回

本机隔离库 `127.0.0.1:28413/v12_upgrade_dev`，新租户、新告警及新Case身份。使用当前真实模型 `aisoc-investigation`、`chat_completions/vllm_grammar_v1`，当前65536窗口与C3/C6各16384、Deep8192的输出额度。配置预检见[preflight-real02.json](preflight-real02.json)。沿当前任务入口、真实Redis和PG执行；不是模型替身。模型专用SSH转发在执行与验证结束后关闭，未改21部署。

Case `5816b0b1-ab0a-5102-8688-2c92ffe5f1cc`，Run `6e831f66-c141-4ea8-ab48-9a761c9b6e45`。4告警、14对象、1任务/尝试/Run/结果、17步骤、47工件。任务与Run completed，结果 accepted / uncertain / partial。租户、告警和来源关联保留；3份实际模型请求均不含后台 `tenant_uid`。

[实际输入边界核对](actual-input-boundary.json)还检查了已知原租户值、新租户/人员ID、路由告警源、测试人员标签及批次名：三份实际模型消息均未命中；这是针对已识别后台字段的直接检查，不等于任意自由正文的全面隐私认证。

| 实际环节 | 输入token | 输出token | 结束 | 质量问题 |
| --- | ---: | ---: | --- | --- |
| C3 首轮分析 | 5761 | 3707 | stop | 1项成员引用覆盖不足 |
| Deep 深入分析 | 6114 | 746 | stop | 无已记录诊断；正文未全面验收 |
| C6 最终综合 | 8678 | 4263 | stop | 云环境、钓鱼两个不适用领域缺限制说明 |

合计29269 tokens，费用未知。C3内容继续进入Deep/C6，C6的两项质量问题没有中断保存；原领域判断、空限制列表及原最终结论保持。原始请求/响应见[calls.json](real-02/calls.json)，新旧身份映射见[source-mapping.json](real-02/source-mapping.json)，完整保存见[snapshot.json](real-02/snapshot.json)。正文仍待复核，不将 accepted 当作结论已证实。

本次C3/C6均有身份、云环境、钓鱼、内部风险四个领域的审阅记录。C6对云环境与钓鱼写了不适用原因，但限制说明数组为空，因此分别登记问题；身份领域关注账号权限/越权，内部风险领域关注账号滥用或配置错误。领域审阅来自同一次模型分析，不是四次独立专家查询。

[最终只读补验](real-02-readback-03/result.json)通过：50次GET均200，含47份工件正文，与同一次PG保存逐值一致；原答摘要、完整报告、核心报告、结果及质量问题一致，GET前后19张相关表的摘要不变，运行槽为0。使用当前HTTP应用的进程内ASGITransport，未验证21 TCP、浏览器或新增HTTP写操作。补验0模型调用、0业务写入。

原材料来自[此前真实批次冻结快照](../streaming-fullflow-20261116-01/final-pg.json)，文件SHA256为 `e4c3bdd0bd21d1c7fd730ad484623224242be2dbee4c6d5d88d05ab8193bcdc5`；只复制原始告警/材料到新身份，未复制旧结果、重派旧Run或重新投Kafka/A/I。UEBA/知识/图等未接来源按实际未查询记录，不宣称已验证外部服务。

## 保留的验证失败

- [real-01](real-01/result.json)：准备夹具时把SQL NULL写成JSON null，触发对象字段约束；0模型调用、0Case/Run。租户/账号已在独立事务写入，不能说全库无写入。修正夹具保留SQL NULL后另开real-02，未改业务表或原件。
- [real-02原驱动](real-02/result.json)：真实链已经完成；验证脚本把核心 `report_json` 当成含 `delivery` 的完整报告，KeyError。完整报告实际为 `source_snapshot/type=delivery_report`，未改存储合同。
- [只读补验01](real-02-readback/result.json)：错误地将模型A1等别名与程序恢复的UUID整对象比较；[补验02](real-02-readback-02/result.json)：误以为HTTP质量诊断在顶层，实际位于 `delivery.detail.citation_review`。均为验证假设问题，原失败和测时脚本保留；最终按既有合同补验同Run，没有重复生成。第二次已完成的3次GET另存，不混入最终50次。

本机已将原快照按既有 `update_processing_audit.py` 导入[静态运行记录](../../../../deliverables/investigation-validation-20261106/processing-audit/index.html)，新增1条、合计44条，保留已有记录。该本机静态更新不等于当前21的4177服务已更新；统一接入在后续D6验证。

D3–D6的截断单元恢复、网络异常继续、I终结后推动Case及页面兜底仍须逐步实施；本步不核销整个change或历史拒收结果，不部署、不提交推送。
