# 设计

采用规则以调查模块的[result-adoption.md](../../complete-socai2-investigation-chain/result-adoption.md)及已通过核心审计为依据。仅发布采用核心两文件及CaseService三个包装方法，加独立HTTP适配；并行模型修改不进入本次运行包。

1. GET `/api/v1/socai2/cases/{case_id}/results/{result_id}/adoption-preview`：返回当前判断、候选完整结果、来源Run、成员覆盖、依据新鲜度、未完任务/Run、能否采用及原因。返回review_token代表此次预览。
2. POST原E21路径：提交operation_key、expected_review_token、非空reason及可选acknowledge_pending_work。核心事务重验并追加判断/来源/覆盖及活动，返回六字段回执。发生未完工作必须显式确认，但任务、Run及处理状态保持。预览变化或资格不足409；不存在404；格式422。
3. GET `/cases/{case_id}/assessments`：limit默认20、1–100，offset默认0且非负；版本倒序、total和next_offset。保留模型结论来源、实际采用人、原因及原结果，不把人工选择当人工生成。

HTTP只依赖CaseOperations及共享DTO；适配器连接CaseService，内部调查继续直调核心，无HTTP回调、自调用。现有E19/E20继续501。

验收：新合成Case和程序构造结果（不调用模型），真实HTTP预览→未完确认→采用→重放→详情/历史/活动及独立SQL读回，直接检查旧预览冲突和不合格结果拒绝。复用核心已验证的自动采用时序；不重做全仓或质量测试。发布后读回版本、运行文件和本批数据。独立审计收口后归档。

分工经负责人明确确认：调查聊天完成核心/路由及本机验证，本聊天维护Swagger/交接、统一发布和Git；不重复实现。采用HTTP新增方法归入现有external_routes/cases.py。
