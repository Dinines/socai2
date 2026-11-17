# D4a：真实 A/I、闭合单元接收与保存

2026-11-16。D4a程序直接验证与同批PG/HTTP读回通过；独立接收53项、保存/读取92项及HTTP侧15组复核全部通过。本步只覆盖告警/事件接收及必要保存，尚未接D4b的事件终结推动Case门控，不代表整个D4完成。范围和顺序见[设计§11](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#11-d4ai接收保存与事件终结材料)。未部署、未提交推送、未重派旧批。

本轮按负责人“使用真实模型”要求，调用当前`aisoc-investigation`各一次告警分诊和事件诊断。模型窗口65536，A/I输出各8192，沿当前配置；专用模型/分词转发只改变本机地址，未修改21配置或服务。实际选择及无生成预检见[preflight.json](preflight.json)。之后使用这两份新真实原答作3次受控返回，真实调用与派生样本分别记录。

## 本步行为

- 正常、length、局部无效、空白正文均进入同一接收路径。复用C3的词法读取，按阶段指定字段及数组项定位原答；不补括号、不填默认判定、不跳扫语法/重复键错误。冲突前闭合的独立单元保留，冲突分支排除。
- A完整verdict/confidence/rationale/evidence_ids才能装配分诊；缺核心字段时保留其余内容但不补needs_review/null。I完整核心与冻结成员覆盖才能装配全事件诊断，单个成员/发现/问题仍可独立保留，F/Q编号沿原序号。引用、范围与正文质量诊断独立，不改写原判断。
- 所有有响应的执行保存`socai2.stage-delivery.v1`，包含本轮输入、原件位置和摘要、实际保留/缺失/无效单元及可用性；保存时重算原值区间及哈希。后台主体、租户、Run和步骤保持，可经现行目录和content_url读取。公共告警五字段/HTTP DTO不变，新回执不塞入旧partial_analysis。
- 共享读取器已复验当前C3。原网络异常/usage未知处理不在此扩展，D5另步；没有新的A/I自动续写或因质量触发的重采样。原件中的后台tenant_uid仍保留，模型请求中无该路由字段。

## 真实调用与受控返回

使用本机隔离PG `127.0.0.1:28413/v12_upgrade_dev`、独立Redis namespace和新租户/告警/事件身份。原告警来源与新身份映射见[source-mapping](real-01/source-mapping.json)；只复制原材料，不复制历史分析或重投Kafka。

| 输入方式 | 环节及Run | 实际结果 |
| --- | --- | --- |
| 真实生成 | A `547af3ba-3f1b-5cde-8b89-35d11f88d212` | stop，输入1348/输出348，completed/complete，保留6个单元 |
| 真实生成 | I `75255ae9-8159-5fa4-ae53-af5927e26523` | stop，输入3678/输出3101，completed/complete，4成员、11个单元 |
| 新I真实原答的前缀 | I `7ef7bceb-7c93-5894-bd0c-b0343334050b` | 截至首个member闭合，length，保留1个成员；failed/partial，无虚构全事件结论 |
| 新I真实原答的空前缀 | I `3d8b5a17-512d-563d-b34e-6250c3f1bf35` | length，none，0单元；failed，无虚构正文 |
| 新A真实原答的前缀 | A `26f3e656-b970-5b94-895f-de2b70b69d71` | 保留verdict/confidence/rationale共3单元，缺evidence_ids；failed/partial，不形成可用分诊 |

便于直接查看的真实原件：[A输入](model-files/A/input.txt) / [A原答](model-files/A/output.txt)、[I输入](model-files/I/input.txt) / [I原答](model-files/I/output.txt)。协调方从实际calls逐字导出，来源见[manifest](model-files/manifest.json)，未重新生成。

真实生成2次，合计8475 tokens，费用未知；受控返回3次，不计新模型生成。受控payload沿母本usage作测试元数据，调用记录明确它不是新增模型费用，不能将五份usage相加当作真实消耗。截断前缀、来源母本摘要、当前及原source map均在[calls.json](real-01/calls.json)。本批没有真正的“仅理由”原答；真正rationale-only由直接单测覆盖。

I真实输入只有1个可用A，其他成员使用原告警；未等待它们的分诊。两个受控失败I均未覆盖原可用诊断指针。单告警新增任务失败未生成分诊指针。全部5个任务/Run各1个attempt，16步骤、45工件、5份严格阶段回执，均已本地结束、Redis占用0。它们不涉及Case自动更新或新Case执行。

本批回执的质量issues为0，仅说明现有检查没有记录问题，正文质量仍`not_checked`，不报告准确率或全面质量通过。正常结果与partial/none执行状态分别保留，不把有回执等同于有有效结论。

## 验证与原失败

- [direct-01](direct-01.txt)：17项A/I接收与保存检查，加23项当前C3，40通过。
- [direct-02](direct-02.txt)：扩大到117项；105通过，12项旧A输入测试因命令缺少显式`SOCAI2_INVESTIGATION_POLICY`失败。选择现有profile后[direct-03](direct-03.txt)原12项全部通过，未改测试预期或产品配置。
- [direct-04](direct-04.txt)：新增协议/工具拒绝/usage预算保护与既有Responses原正文路径12项，A/I当前29项全过。去重后本步129项直接检查通过，未全仓回归。Ruff、相关diff检查及OpenSpec strict通过。
- [独立接收](../test-ai-continuation-d4-20261116-01/receiver-attempt-02/execution.json)：27项新A/I+26项受影响C3a共53通过。独立关键切点/固定seed随机切点、原值span/hash、核心依赖、未知/重复成员、Q2序号和实际save的严格回执均验证；网络/真实PG仍由本批另验。测试初次7项装配/预期失败原样保留，未让产品扫描越过重复键。
- [real-01原回执](real-01/result.json)保持failed：5个业务任务已执行并通过保存断言，HTTP前3次GET成功；随后目录读取因驱动缺少分页profile抛service_unavailable。没有重新发起任何模型/业务任务。
- 配置从新独立文件选择后，[readback-01](readback-01/result.json)仅补读相同5个Run：77次GET全200、availability=available；task.attempts.run_url→本次Run→trace→完整分页steps/artifacts→返回content_url，16步骤45工件逐值及原件摘要相同。13张相关表在GET前后摘要一致。原尝试3次成功GET另计，全批80次成功GET，不冒称原尝试已通过。
- [独立保存复核](../test-ai-continuation-d4-20261116-01/saved-review-02/review.json)92项及[HTTP侧复核](http-readback-review-01.json)15组通过：21个保留单元与10份请求/响应原件、同Run及主体、全目录/正文、失败Run与旧有效I区别均核对。复核不再发HTTP或模型请求。正常阶段output指向结果工件，失败阶段可指阶段回执；回执由目录发现，input_artifact_id指同Run冻结输入，不假设stage输入指针必须非空。
- [164份源码/profile冻结](source-before-real.json)及[实测后核对](source-after-real.json)全部一致。原驱动备份为[validate-source-real01.py](validate-source-real01.py)；当前[validate.py](validate.py)补了显式分页配置，旧批禁止重跑；[readback.py](readback.py)只读、不生成。
- [资源清理](resource-cleanup.json)：本批SSH socket和24014/28014端口已关闭，未重启、清理或关闭共享PG/Redis及其他服务。

协调方已按[静态核对](static-verification.json)导入同5Run/16步骤/45工件，原45个批次逐值保持并新增1批至46；仅为离线静态记录，不代表21或实际4177页面已验。

本步证据既区分真实模型与受控返回，也区分隔离PG、ASGI HTTP与21 TCP/浏览器。最终21整体验收仍从Kafka开始，D4b/D4c、D5、D6以及统一结束审计均不由本批核销。
