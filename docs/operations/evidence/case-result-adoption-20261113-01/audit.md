# 固定结果人工采用核心：限定独立审计

2026-11-13。审计者未参与本轮实现或执行。结论：**本轮核心实现及本机隔离PG保存读取的限定审计通过，未发现实际功能阻断。** 该结论不包含HTTP适配、真实调查模型效果、生产部署或主change完成。

依据[采用设计](../../../../openspec/changes/complete-socai2-investigation-chain/result-adoption.md)及新增规格，只读审查`case_adoption.py`、内部合同、CaseService接线、直接验收脚本和已保存回执；必要时追踪既有Case锁、活动回执、新鲜度及自动采用规则。没有运行测试、重放、模型、网络、HTTP或数据库操作，仅新增本文件。并行HTTP及其他未提交修改不属于本轮实现。

1. **资格及覆盖没有因人工选择放宽。** 候选限定本案baseline Result和completed/whole_case来源Run，要求accepted、非空model结论、当前scope_revision及相同冻结成员，并重新读取完整input_freshness。当前成员、交付成员和有效结论覆盖须完整相等；缺失、额外、not_analyzed/excluded覆盖不能被提升为全案判断。uncertain/partial仅在其余条件满足时允许采用，原待核及限制保留。已结案必须另行重开；本轮没有修改结案或自动采用原有partial口径。

2. **预览、事务及幂等接线成立。** 提交在Case锁内重算预览摘要，再校资格和未完工作知晓标志；任务修订、相关运行状态及当前判断等预览内容变化会使旧摘要失效。新判断、来源、真实覆盖、当前指针和带操作者/理由的活动回执在同一事务保存，采用本身不修改任务、Run或Case处理状态。幂等检查先于新预览重验：相同操作返回原回执，不再次更新指针；同键改变意图拒绝。请求摘要包括目标、操作者及完整请求。人工操作者和原model结论origin分开保存，没有把人工选择写成人工生成或质量通过。

3. **实际流程及失败边界准确。** pg-01在连接阶段失败，未进入业务；pg-02已完成采用和幂等检查，随后因测试误断处理状态应为`open`停止，实际状态为`new`且应保持预览值。pg-03使用同一Case及已保存操作继续余段，没有重新建Case或重启旧Run。最终快照为1Case、4Run、4份程序提供的Result、3份判断、1任务/2修订和8个C1工件。程序只走C1冻结及显式Publication，没有A/I/C2–C6模型执行。pg-02失败保留，不能改称整段通过；完成余段的证据是[pg-03回执](pg-03/verification.json)。

4. **保存与读取可相互核对。** [预览](pg-02/adoption-preview.json)的token可由保存JSON重算并与[提交参数](pg-02/adoption-request.json)匹配；实际有1个未完任务、1个running及1个pending Run，活动回执记录了明确知晓和这些工作。人工采用生成第2版判断`a1a7c627-6abe-45b3-9730-8fd3b43860df`，仅有1条`case_result_adopted`活动。来源Result、结论、采用人、理由、成员覆盖及[采用回执](pg-03/adoption-receipt.json)与SQL快照一致；[Result读回](pg-03/result-readback.json)、[判断历史](pg-03/history-after-adoption.json)仅有UTC时间`Z`与`+00:00`的等价表示差异。pg-02原2Result、2判断及其来源/覆盖、原14条活动和目标在pg-03逐值保留。Case处理状态一直为`new`。

5. **人工与自动采用的时序未冲突。** 人工采用使用数据库时钟记录`adopted_at`，沿用既有自动采用的Run开始时间比较。[实际回执](pg-03/automatic-order.json)显示：早已启动的Run完成后返回`newer_assessment`，未覆盖人工第2版；后来显式启动的Run正常自动采用为第3版。后续有效H反馈使第3版成为`stale/human_feedback_changed`，指针仍保持第3版且没有自动新Run。旧人工操作重试返回原第2版回执，但不把当前指针回滚；[最终Case](pg-03/final-case.json)与保存快照支持该结论。

6. **源码与执行版本可追溯。** CaseService相对本批修改前快照只有12行、三个核心方法的接线增量。两份新增业务文件没有路由、模型或迁移接线。[source-replay.json](source-replay.json)中的补丁摘要匹配；`first-attempt-source`与pg-02的11份源摘要、`after-source`与pg-03的11份源摘要均相符，pg-03摘要也与本次审阅对应源码一致。业务实现两阶段未变，改变的是验收状态断言及同批续验入口。两份数据库快照均与各自manifest摘要匹配。

7. **静态导入与旧证据保持。** [workbench-import.json](workbench-import.json)记录仅导入pg-03快照，本机记录84→85；其详情文件存在，详情及索引摘要匹配，索引包含本批记录。本审计没有验证TCP入口可达性，回执也明确在线4177未同步。09、Deep知识及C6知识三批manifest分别列出的54、26、30份文件共110份，逐一摘要相同；此次核对没有改写旧原件。

[README](README.md)及[validation.json](validation.json)正确区分程序构造结果、真实隔离PG及真实模型未验。当前HTTP采用接口仍待单独适配，本轮不构成HTTP/生产采用验收，其他线程的HTTP操作总数或发布不计入本项。已结案、其他材料版本及成员变化的分支只做静态检查，没有追加并发或拒绝矩阵。主调查31/41及既有模型正文/知识质量NOT_PASSED保持，不据此归档或前移流式更新。
