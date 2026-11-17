# D4 A/I恢复独立测试准备

当前D4a本机范围已独立通过：接收/内存保存27项及受影响D3a 26项，合计[53/53](receiver-attempt-02/execution.json)；唯一真实/受控保存包的[92项只读复核](saved-review-02/review.json)通过。**D4b/c终结门控与Case链尚未独立验证，不将D4a核销为完整D4或21发布。** 测试模块未改核心、未重复派发业务任务。本目录所属现有change的[D4设计§5/§7/§11](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md)及[功能用例](../../../../openspec/changes/schedule-streaming-investigation-updates/functional-test-cases-20261115.md)。

调查模块转达负责人最新要求：D4需包含真实模型验证，由调查模块统一负责有限的新A/I真实调用、唯一隔离PG/Redis任务和HTTP读回，测试模块只读复核同一批。真实调用与受控截断分开记录；本目录本次准备为0模型/数据库/网络调用，不把旧原答或模拟输出称为新生成。

## 冻结来源

两份母本来自r3已保存[final-pg.json](../streaming-fullflow-20261116-01/final-pg.json)，文件SHA256为`e4c3bdd0bd21d1c7fd730ad484623224242be2dbee4c6d5d88d05ab8193bcdc5`。每阶段保留同Run的冻结输入、请求、模型响应、独立原件和步骤，原正文路径均为`$.raw.choices[0].message.content`。

| 阶段 | 原Run / 原件 | 内容与候选粒度 |
| --- | --- | --- |
| A | Run `7e2f68f4-393f-5dde-ab74-36ac0f866e65`；原件 `0886e909-d5eb-40f3-bd23-ca9397498b7c` | 685字符；verdict/confidence/rationale/evidence_ids和2条建议，共6个单元；四核心完整且符合依赖才形成有效分诊 |
| I | Run `015358ab-c7f4-576e-b67d-9c57b7cfb07e`；原件 `1a62ee86-d1ed-49e2-b397-d11cf1782079` | 2,998字符；3个成员、1个发现、2个待核问题、diagnosis下summary/conclusion/limitations/source_ids，共10个候选单元 |

母本有真实质量问题，保持原文，不将其当作业务真值。历史请求含当时配置和输入；新测试须显式选当前r3引用的policy及最新A/I profile，重新构造当前输入并记录派生身份/映射。当前配置路径及摘要见各阶段manifest，不能从旧冻结请求推断当前服务配置已加载。若profile在D4实施中发生变化，后续新构造另记实际hash，不改历史母本。

## 独立预期与准备验证

[prepare.py](prepare.py)只用标准库解码完整母本并定位全部值，不导入被测接收器，也不解码截断片段来生成预期。`value_span`为Unicode字符左闭右开，SHA256按原区间UTF-8计算；数值/null/布尔值必须在片段中看到后续合法分隔符，不能凭完整母本猜测半个token。原字符串、字段顺序和数组序号保持。

每阶段10个变体：空正文、完整stop、完整length、根闭合前、3个关键业务切点、3个固定随机点。A覆盖仅verdict、rationale闭合、建议1闭合/建议2半项；I覆盖成员1闭合/成员2半项、发现闭合/问题半项、diagnosis.summary闭合/conclusion半项。seed=20261116，A随机点217/221/654，I随机点863/878/2606。

[fixtures-01](fixtures-01/manifest.json)保留设计定稿前的词法准备记录；[当前fixtures-02](fixtures-02/manifest.json)按调查§11.1加入独立业务预期，原片段和切点相同。A必须有完整四核心字段，I必须有完整diagnosis四字段及全部冻结成员覆盖才有有效核心结果；实际闭合单元仍可作为有限材料，来源/类型/范围校验由后续实际接收测试核对。只有verdict不能成为有效分诊；I只有首成员时不能把其余两个alias标为已分析；空正文不能产生模型结论；半条建议不能成为动作。两阶段dispatch_paths均为空，不产生Case采用/比较资格。

[prepare_boundaries.py](prepare_boundaries.py)当前生成[7个明确结构变体](boundaries-02/manifest.json)：A仅理由、前置/末尾重复verdict、显式空建议；I未知成员、重复成员冲突双方隔离、首问题范围非法但次问题保持原Q2序号。它们是受控改造原答，原文保持，变更字段及必须保留/隔离的路径显式给出；不把它们称为新真实模型结果。[原6变体](boundaries-01/manifest.json)及其中前置重复键后继续读取的错误预期保留供追溯。

[早期词法准备验证](preparation-validation.json)、[原26例业务预期准备验证](preparation-validation-02.json)与[当前27例准备验证](preparation-validation-03.json)分别保存。当前49份前缀文件及15份结构变体文件，共64份在第二个独立目录重建后逐字节相同；A 21个、I 99个完整母本原值的span/value/SHA共120项核对通过。原快照hash保持；准备结果与下面的产品接收测试分别记录。

## D4a独立接收与内存保存

[独立测试文件](../../../../services/api/tests/test_socai2_d4_units_independent.py)显式选择当前正式policy，A/I输出均8192；当前builder从冻结原材料重建prepared。当前过滤后source_map可变化，但母本实际引用过的每个source_id均须仍对应完全相同的字段、角色和成员，I成员别名也须一致；不将旧别名盲绑定到当前不同来源。历史请求和原答不改写。

27个样本经过实际`ai_delivery_store.receive_payload`的协议/usage/预算校验及`ai_stage_delivery.receive`，再调用实际`ai_delivery_store.save`配内存存储，核对插入的alert_id/incident_id、Run、step、严格回执及原件范围。结果与预先冻结原值/span/SHA、有效核心条件、实际成员覆盖及Q2原序号相符。A仅理由不补verdict/confidence；I缺完整核心/成员时不生成全事件诊断，合法闭合内容保持；质量仍not_checked，零派发/采用/比较资格。调用/usage是受控原响应变体，不计新真实模型或真实耗费。

[首轮](receiver-attempt-01/execution.json)45通过/7失败保持：6项是测试将内部quality.path_mapping手工塞入严格回执；改为调用实际save验证正确投影，未放宽合同。另1项为前置重复键后仍要求保留尚未读取字段的测试预期错误。协调及调查模块确认沿D3规则：遇语法/重复键即停止读取，剔除冲突分支，仅保留此前已闭合的独立单元。当前前置重复verdict为none，末尾重复verdict保留此前理由/建议，均无有效分诊。实际核心代码未为测试修改。

[第二轮](receiver-attempt-02/execution.json)53/53通过（D4a 27+D3a 26），33份源码配置在执行期间未变。实际回执及派生结果逐例保存在该目录cases。测试侧0网络/数据库/模型请求；内存保存与下面真实PG/HTTP证据分别记录。

## D4a真实调用、保存与HTTP独立复核

调查唯一新批[real-01](../ai-unit-continuation-d4-20261116-01/real-01/tasks.json)实际调用A、I各一次，均stop并形成complete；A输入1348/输出348/共1696 tokens，I输入3678/输出3101/共6779 tokens。其后3次受控响应明确使用本批真实原答派生：I首成员闭合的partial、I空答none、另一告警的A截断partial。受控usage复制不计真实生成或真实费用；本批正文质量仍not_checked，issues=0不代表事实正确。

三次受控Run均failed且无可用核心；I partial只保留members[0]，4成员输入不被改写成4成员已分析。A partial实际保留verdict/confidence/rationale三字段，缺evidence_ids，不是“仅理由”，该告警没有新有效分诊指针。两次失败I保留原有效诊断指针。真实I输入只有1份可用A，仍以4份原告警继续分析；此证据不替代D4b/c当前I终结推动Case的未完接线。

首次业务批的8项业务检查已完成，HTTP验证因缺RunRecordLimits profile失败，原[result](../ai-unit-continuation-d4-20261116-01/real-01/result.json)保持。调查补配置后[readback-01](../ai-unit-continuation-d4-20261116-01/readback-01/result.json)仅对同批读取，0新增业务/模型：5任务/Run、16步骤、45工件、5份严格阶段回执，77次GET；13表读取前后摘要一致，槽0。运输为本机ASGI/真实隔离PG，不是21 TCP或4177。

[独立只读脚本](review_saved.py)按本次task返回run_url、Run/trace目录链接、游标及content_url核对；A/I正文使用metadata封套。92项通过，21个实际保留单元的原value/span/SHA及source_map角色/成员逐项一致，原请求/原答、实际覆盖、有效结果、旧指针、45份HTTP正文与PG均同源；源包未变。5份实际请求的[profile摘要](saved-review-02/current-profiles.json)与本轮已测当前profile相同，预算A/I 8192及Run131072保持。

[首次独立只读失败](saved-review-01/review.json)是脚本自行拼目录路径漏API前缀，未发任何请求；改为沿实际trace返回链接后92项通过，原失败不改写。测试模块全程0新增网络/PG/HTTP/模型/业务写入；D4a证据仅用于本步收口。

HTTP模块对同一保存包的[15组独立复核](../ai-unit-continuation-d4-20261116-01/http-readback-review-01.json)也已通过，未重复执行。实际阶段的input指针为空，阶段回执input_artifact_id正确指向同Run input_snapshot；本步不将前者写成已填充。失败Run/none原件仍可读，旧有效I不冒充本次失败Run；D4b/c因果触发仍未验证。

## 后续直接验收

D4a接收/保存读取已验，下一步按调查D4b稳定交接测I终结材料信号，再由调查统一驱动D4c、测试只读复核。功能判据包括：A不可用时I仍读取真实原告警；I部分或none只在当前输入本地终结且完整回执落库后推动合格活跃Case；running/待合法重试不提前触发；同输入同业务内容重复终结不重复派发，新输入不可用与旧输入不可用不同；同输入旧可用不被后续失败覆盖；实际选入、实际保留成员、完整事件分配范围分别核对。新模型质量单列，旧失败/原答不改写。

HTTP入口：task.attempts[].run_url→A/I分析详情→该Run的trace→steps_url/artifacts_url完整分页→content_url，已在本批77次读取记录中核对。A/I正文封套为metadata，Case为artifact；availability和正文delivery/quality分别核。完整性失败可为200加content_integrity_mismatch及null正文，不能当读取成功；本批未另外制造完整性失败。无合格诊断时仍读当前Run/回执，不借旧current替代；新stage_delivery不会自动进入旧partial_analysis展示。回执必须保存真实alert_id/incident_id、Run和step关联；目录无kind/type/schema过滤，step_id不递归。

D5网络/其他阶段恢复、D6页面和整个change审计不在本步；未部署21、未更新4177、未提交推送。
