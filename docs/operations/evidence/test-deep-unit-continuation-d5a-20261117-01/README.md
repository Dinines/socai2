# D5a Deep独立预期与只读复核

当前为**材料准备及接收器10项直接验证通过，保存/HTTP及C6实际保存输入待验**。范围按[调查§13](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#13-d5分步设计与验证安排2026-11-17)与[测试§7.7](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#77-d5a本轮独立验证范围2026-11-17)；不重复调查侧唯一隔离PG执行、不调用模型或业务接口、不改核心/页面。

[配置](fixture-config.json)冻结新02两份Deep原答路径与hash；[prepare.py](prepare.py)只用Python标准库解码完整母本，核请求/响应工件/Run/step一一对应及模型索引内对应文件摘要，不导入应用恢复器。原母本与输入文件保持。[preparation.json](preparation.json)保存两份来源、四字段原始span、10项受控片段及独立预期。

- 主母本R1：855字符，answer值[246,853)；关键截246/309/852/854，完整stop与受控length为855。
- 固定种子20261117，随机切点仅3个：150/25/240，均在answer闭合前，预期无业务answer。
- 两份原答均answer最后。`prepared/answer-first-controlled-mother.txt`只把完整answer前置，字节保持；`answer-first-controls-missing.txt`截622，完整答案保留但无可执行Decision/查询。这是明确受控重排，不是自然模型输出。
- 所有10项query预期均0：母本本来提出answer，不冒称已验证合法query或全部binding保护。缺/未知binding、重复/冲突控制另核实现方最小直接用例。

准备阶段0新模型、0数据库/HTTP/业务请求，Ruff通过；这些不是接收器执行或D5a整体通过证据。接口交接后逐项核原片段来源及实际返回，再只读复核调查侧唯一保存包。正文质量不在本步重采样或追认通过。

[receiver-01.json](receiver-01.json)按已冻结独立预期对当前`case_deep_delivery.receive`核10/10通过：答案/Decision、完整字段、实际片段span/hash/原件路径、非全案采用/比较、length标记及零dispatch_paths。受控接收身份只在内存构造，未写入业务库，不能把它称为原02实际响应工件。6份相关接收代码及两母本文件摘要前后不变，0模型/数据库/HTTP调用。

[check-receiver.py](check-receiver.py)只验证接收函数，不执行查询或自动续写；零dispatch_paths不等于已验证实际工具副作用。提供方直接用例已有合法query、未提供binding、冲突query+answer、重复控制及C6 builder样本；本步独立结果不重复计这些数量。后续只读核唯一PG代表包的每次调用回执、deep_summary、C6实际请求及HTTP来源，不展开第二条业务流程。
