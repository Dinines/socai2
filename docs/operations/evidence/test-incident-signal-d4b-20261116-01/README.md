# D4b独立测试准备与后续证据

2026-11-16。当前状态：**passed_within_D4b_local_component_scope**。D4b共有30个不同直接用例通过；末次归一化修正的13项受影响检查通过。三分支保存包初核106项、最终完整分支补核55项、最终代码对三份实际保存材料的9项核对通过。后两轮包含重核，不相加冒充不同用例数。测试侧0新增模型/PG/HTTP或业务请求，未推进D4c。

当前要求见[设计§5/§11.2](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#5-i结束之后继续case避免失败重复触发)，[总计划§7.5](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#75-d4b当前子步终结门控语义去重及冻结读取)、[B01–B12判据](../../../../openspec/changes/schedule-streaming-investigation-updates/functional-test-cases-20261115.md#d4b终结材料的独立功能判据)和[数据§15.7](../../../../openspec/changes/schedule-streaming-investigation-updates/test-data-design-20261115.md#157-d4b冻结数据及执行噪声对照)。使用当前r3 release显式引用的r2配置；旧模型原答的配置不成为本步默认值。

[freeze.py](freeze.py)仅用标准库读取现有文件，不导入产品门控、接收器或数据库客户端。`preparation-01`包含：

- [manifest.json](preparation-01/manifest.json)：实际来源、当前policy/输入profile/周期/分配配置摘要及准备产物摘要。
- [mothers.json](preparation-01/mothers.json)：D4a真实I complete及受控partial/none的原Run/task/attempt/input/receipt/原件身份、实际保留单元和选入范围。
- [scenarios.json](preparation-01/scenarios.json)：B01–B12独立业务预期及依赖；不是产品执行结果。

三份I母本原始输入摘要相同，均选入4成员；partial只有首成员，none没有保留单元。旧可用诊断指针保持。4总成员/3选入/1保留是另行受控范围对照，不能回写为D4a事实。B05执行身份及别名变化保持真实内容、对象、来源角色和范围；B08真实内容/范围变化必须被识别，防止以删除全部证据引用实现伪去重。

首轮准备脚本误把profile名解析为部署TOML的同目录文件，在读取前报路径不存在，未产生准备清单或业务请求；[原脚本及失败](preparation-failed-01/result.json)保留。按实际runtime_policy加载规则改为当前源码包同目录profile；这只修测试准备脚本，不修改运行配置。

稳定入口已交接，独立测试见[test_socai2_d4b_independent.py](../../../../services/api/tests/test_socai2_d4b_independent.py)。[direct-attempt-01](direct-attempt-01/pytest.txt)21通过/5失败：4处未适配project新增source_map参数，1处错误地给冻结Pydantic对象赋值；均为测试接线错误，原脚本和回执保留。只修测试后，[direct-attempt-02](direct-attempt-02/pytest.txt)27/27通过，[184份核心/profile/独立测试文件](direct-attempt-02/source-manifest.json)运行前后不变，快照保存在tested-sources.zip。

直接验证覆盖freeze实际完整/partial/none、未结束/待重试/原件缺失损坏、Run/input身份及错误噪声去重、结构化alias和旧诊断support身份对照、业务内容/范围/来源角色/源值变化、新输入none、晚到A，以及实际capture消费受控SQL行后构造当前C3 messages。逐单元原文/范围及prior_analysis保持，receipt/hash/attempt台账不进正文，selected_refs保留源I身份。SQL未执行，follow_current的关系服务用明确内存依赖，只证明材料门控调用，不证明实际分配成员。B02/B07的动态选择、B09的4/3/1实际范围及B12保存核对仍待。

在上述27项后增加必要的跨Case范围对照：I发现原4成员、Case仅1成员，C3关联Case1但original_scope保留4，原文不变；[direct-attempt-03](direct-attempt-03/pytest.txt)28/28通过。最终发现上游A建议source_refs仍可能使语义摘要随工件ID变化，调查修正两行投影；保留03旧源码，定向重验11个受影响旧例及2个A建议正反对照，[direct-attempt-04](direct-attempt-04/pytest.txt)13/13通过，185份源码/profile/测试文件运行中不变。实际不同直接用例30，未重跑无关范围。

保存核对先完成[saved-review-03](saved-review-03/review.json)106项，源为complete07/partial02/none01及final-readback-01。前两轮脚本因续验中重复label取最后一轮、未追溯首次有效allocation而报失败，[01](saved-review-01/review.json)及[02](saved-review-02/review.json)保留；只修只读脚本。complete07续验的空分配正常，最初1→4实际回执在同Case的[complete05](../incident-signal-d4b-20261116-01/pg-complete-05/allocation.json)，该批后续失败不抹去也不追认全批成功。

最终只对受末两行修正影响的完整分支补新身份C1存取，未重跑partial/none PG。最终组合为[complete08](../incident-signal-d4b-20261116-01/pg-complete-08/result.json)+final-readback-02/complete、partial02+final-readback-01/partial、none01+final-readback-01/none。[saved-review-04](saved-review-04/review.json)55项定向核对通过；[最终代码freeze汇总](current-freeze-final.json)三分支business_view及完整材料均与实际保存C1一致，来源文件未变。初次partial/none回执把来源I Run字段名写为case_run_id，汇总已按实际身份标source_run_id，原回执保留。

实际PG证明running/待合法重试不提供材料，旧stale不推动分配，合格核心优先于后到空失败，非空partial优先于none；partial为4总成员/3选入/1保留且Case实际全4。3选入是对D4a真实母本的受控依赖派生，原答不重解析，不声称模型真实收到3成员。C1清单、完整Context、5份源I原件、原span/hash/value、业务正文/范围、后到数据后C1不变及终态已核；Case仅C1保存并构造C3 messages，Run明确failed/component_capture_only，无C3/C6模型或完整任务执行。

HTTP侧[初次33组](../incident-signal-d4b-20261116-01/http-c1-source-review-01.json)及[最终完整分支11组](../incident-signal-d4b-20261116-01/http-c1-source-review-02.json)离线来源复核通过，含17表内容摘要复算及读前后相等；0实际HTTP请求，不能称HTTP执行通过。D4c完整模型任务链、D5/D6、21/TCP/4177和正文质量均未覆盖；历史失败不改写。
