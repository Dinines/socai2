# C6指定历史比较的业务内容与存取闭环

2026-11-13，沿主调查[第27节](../../../../openspec/changes/complete-socai2-investigation-chain/model-input-field-review-20261112.md#27-c6指定比较基线的必要判断内容)实施。C6要比较本轮判断与指定旧结果，原输入却只给旧结论摘要，将已保存的发现、未决问题和影响边界全部过滤。本批修正这一实际选择缺口，不改写历史判断，也不把历史材料当本轮新证据。主调查31/41、正文与知识合理使用NOT_PASSED保持，流式后置。

## 模型实际需要什么

只有C6明确指定且可比的Result及同一结果的冻结副本，补充以下内容；其他历史和C3/Deep沿用原规则：

| 比较目的 | 程序选入 | 留在原件 |
| --- | --- | --- |
| 判断内容及其边界是否变化 | 原发现陈述、状态、成员/时间范围、限制与替代解释 | 发现内部编号、原始引用UUID和引用外壳 |
| 原待核问题是否得到回应 | 未决业务问题的原回答、范围、限制及所需材料 | coverage执行统计、已回答问题的重复条目 |
| 影响判断是否变化 | 原影响摘要、支持的变化、不能推广的边界及原范围 | 旧建议动作，不自动转为本轮建议 |

这些正文逐字保留；未知业务扩展、0、false及有效空列表保留。原范围不缩成当前成员，历史成员/对象也不进入本轮可执行目标枚举。指定Result与同身份副本仍各自保存原引用，同内容共享显示。历史正文中的旧短号不作本次引用；模型仍须引用当前指定基线短号与本轮依据，不能从摘要长度或条目数断言证据更充分。不可用基线继续原规则，未加载旧Run全文或另查历史日志。

## 完整输入

冻结09真实材料的离线前后重建，来源时点、原答与失败保持，**新预览没有派发模型**：

- [整理前C6完整输入](before/C6-model-input.txt)：13,526字符，与09实际请求逐字一致。
- [整理后C6完整输入](after/C6-model-input.txt)：16,799字符；[指定基线完整段落](after/C6-selected-comparison.txt)。新增3条原发现、5个未决业务问题及影响边界，增加的是任务所需内容。
- [完整请求预览及Schema](after/C6-request-preview.json)、[原Result](before/selected-result.json)、[原最终响应](before/C6-original-final-response.json)、[选择与映射](after/C6-selection.json)。只有N5_S93指定结果的视图变化，其余104条材料、105条原引用和52个依赖保持；55份09原件摘要不变。[离线核对](verification.json)。

下面是另一条新合成Case中**实际保存、交给替身的请求**，不是上述09预览，不与09作压缩率或模型效果比较：

| 环节 | 已保存正文 | 字符数 |
| --- | --- | ---: |
| C3 | [完整输入](inputs/C3-model-input.txt) | 3,779 |
| Deep查询前 | [完整输入](inputs/Deep-01-model-input.txt) | 3,556 |
| Deep查询后 | [完整输入](inputs/Deep-02-model-input.txt) | 4,590 |
| C6 | [完整输入](inputs/C6-model-input.txt) | 6,846 |

完整请求/Schema随同目录保存，[逐请求摘要](inputs/summary.json)对应真实保存的工件ID。C6指定旧结果的[实际保存视图](outputs/saved-comparison-basis.json)可与原件及请求互查。

## 保存与读取

复用一个既有H后固定调查场景，实际连接本机`127.0.0.1:28412/v12_upgrade_dev`，角色`v12_developer`。一个新合成Case `18f669f8-0825-4618-bbcc-ac78ff21a50f`，先有一轮结果，保存H两版，再显式开始指定首轮结果比较的新调查。新增2个Case Run及3个A/I替身Run；全部模型、Token计量和外部查询为替身。没有真实生成、TCP服务验收、生产写入或清理旧数据。

流程一次通过，见[原检查及读回](pg-01/checks.json)、[数据库快照](pg-01/database.json)、[存取核对](persistence-verification.json)：

- H第2版原文、附件原引用、原计划及指定旧结果进入C3/Deep/C6；保存H没有自动启动Run。旧Result及两版H保持。
- C6新结果为accepted / uncertain / partial，比较为unchanged；[结果读回](outputs/result-readback.json)、[完整交付报告](outputs/delivery-report.json)的结论、比较和影响一致，[当前判断读回](outputs/current-assessment-readback.json)采用同一结论。其[H及比较来源](outputs/H-revisions-readback.json)可追溯。
- 已保存模型请求与实际替身接收的请求逐值一致。原结果、原始依据和模型原答未因输入选择被修改；当前判断的新鲜度current，首轮在H后为stale。

这里的accepted仅代表程序接收，替身回答没有模型质量证明。正文M01/F02等继续NOT_PASSED，没有为已登记质量问题增加真实采样。

本合成PG旧Result的findings为空，非空发现的选择由09冻结重建及1项定向检查覆盖，不补跑一个场景。该旧测试场景只给Case关联两条告警，独立I是替身种子记录，未显式关联Case；本批不作为新增完整A/I→Case验收，09已有实际关联证据沿原范围复用。

原`pg-01`导出同时含独立I，4177范围校验[拒绝导入](workbench-import-01-error.json)，原件保持。随后使用既有`capture_processing_case`按真实Case范围只读导出；首次保存因相对路径被拒绝，[原错误](case-capture-01-error.json)及执行脚本保留，修正绝对路径后一次补读成功，未写库或重派调查。新快照仅含Case、两个告警及对应4个Run，239行均与原快照相同，不补造Case/事件关系。[导入回执](workbench-import.json)记录追加1份至本机静态包，当时共88份；[本批4177静态详情](../../../../deliverables/investigation-validation-20261106/processing-audit/cases/7858ca4e26a49860d16b4a4c2817b9d1f93b8844b84b2ecb967070775675039c.html)。在线4177未同步，也未验证TCP可达性。

## 验证、重放与边界

只扩充并执行1项已有比较边界检查：[通过JUnit](direct-tests-02.xml)。初次命令漏PYTHONPATH，收集阶段失败且未执行测试，[原错误JUnit](direct-tests-01.xml)保留；修正运行路径后该项一次通过。Ruff发现新增PG断言的未定义变量，在PG执行前修正并通过。离线汇总脚本首次读错当前判断封套，留下[原错误](offline-summary-01-error.txt)，随后只读现有快照完成导出，没有第二次数据库流程。

[rebuild.py](rebuild.py)重建冻结09材料；[run_persistence.py](run_persistence.py)复用已有场景，要求显式数据库/环境文件和新输出目录；[extract_inputs.py](extract_inputs.py)及[summarize.py](summarize.py)只读已保存快照。[config.json](config.json)保存目标与选项，凭据仅在受控忽略提交文件中。`pg-01`已结束，不覆盖或重派；旧批原答和失败不重写。业务4文件及2个既有测试文件的本轮增量见[source.patch](source.patch)，修改前后文件和[源码摘要](source-files.json)可重放。

HTTP接口、告警交接字段和数据库表不变，没有发布、提交、推送或消费者变更。采用接口与Swagger沿用另一交付change；本批不修改其交接或部署文件。[限定审计](audit.md)已通过，验证汇总见[validation.json](validation.json)，原件及回执按[文件摘要](files.sha256.json)封存；主调查未整体验收，不归档、不转入流式。
