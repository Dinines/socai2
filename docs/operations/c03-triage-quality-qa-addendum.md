# C03-02：原自动关闭QA附属记录边界

2026-10-21，任何本批业务写或模型之前补充；原执行卡及前一补充的冻结字节保持，不增加模型、输入或发送/交付上限。

原`run_auto_triage`在关闭策略允许高置信benign/BTP/FP时会调用`ClosureQaSampler.record`，早于worker的shadow写入选择。本批保持该原策略，不能通过关闭采样提高测试成绩。实际PG基线中`aisoc_closure_policies`和`aisoc_closure_qa_samples`均为0行，逐行hash另存。

允许该原分支为四条新输入最多增加4条pending QA回执；原QA/关闭policy与其他租户行不改，不设置reviewer、评分或reviewed状态。预检固定needs_review且无采样写；只读verify也不得写QA。实际新增数量、tenant、记录ID及对应本批Fusion incident/Alert/Run分别报告，不将待审QA当作已有人审质量或本批独立评分。

已核固定源码的身份边界：`_sample_for_qa`把`state.incident_id`写入名为`alert_id`的字段，普通fused state的该值来自Fusion incident；迁移079未为该字段建立Alert外键。因而不能宣称QA已经正确关联canonical Alert，或按canonical Alert hash抽样。本批不改该上游附属路径；实际记录若采用本批Fusion incident只按原事实标注，核心Run/Alert/工件仍须按canonical Alert严格核对。准备开放QA读取/评分前须单独修验，入口矩阵列未交付并阻止使用；不以本批理由质量复验替QA路径背书。
