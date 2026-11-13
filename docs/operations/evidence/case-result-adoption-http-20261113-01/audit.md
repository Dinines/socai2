# 人工采用HTTP接线：本机限定独立审计

2026-11-13。审计者未参与本轮实现或执行。结论：**三个HTTP接口的本地接线及本机保存读回限定通过，未发现业务功能阻断。** 审计发现的一处请求汇总记录缺陷已保留、说明并完成驱动的静态修复复阅；修后驱动未重新执行。此结论不覆盖生产发布、已发布基底与七文件的组合、Swagger交接或整个change收口。

只读审查本轮HTTP合同、端口和路由增量、既有测试更新及保存证据；采用核心沿用[前批独审](../case-result-adoption-20261113-01/audit.md)，本轮三份核心文件逐字未变。审计没有运行测试、重放、模型、网络、HTTP或数据库操作，仅新增本文件，未修改业务、旧证据、并行HTTP文件或交付change。

1. **接口直接复用核心，合同变化范围明确。** E21从`case_ai`的501占位移至Case路由，调用`CaseOperations.adopt_result`；预览和判断历史分别调用原核心读取方法，没有在路由中复制采用事务或启动调查。GET沿用读连接及`cases:read`，POST沿用写连接及`cases:write`；tenant和actor来自认证上下文，采用仍拒绝服务身份代替用户。旧占位请求明确422；新的理由、review_token和未完工作确认由既有内部合同及核心校验。历史分页约束、未知查询参数拒绝及StoreError到HTTP状态的转换保持直接接线。E19/E20仍为501，原Run/Result历史接口未改义。

2. **公开合同保留数字可核对。** 对比[修改前OpenAPI](before-openapi.json)和[实际候选HTTP OpenAPI](http-01/openapi.json)：原62项业务操作中除E21外的61项逐值相同；新增两个GET后为64项。125个原有Schema逐值保持，移除公开占位`AdoptCaseAIResult`，新增5个采用DTO。`candidate-openapi.json`与实际HTTP工件仅`info.version`不同，实际版本为`case-result-adoption-20261113-candidate`。这只是本批候选合同核对，不代表已发布文档已同步。

3. **实际HTTP证据与数据库一致。** [20次请求汇总](http-01/responses.json)包含15次200、3次预期409、1次旧占位请求422及1次未知Result404。实际路径涵盖预览、旧摘要拒绝、未确认未完工作拒绝、采用、同键重试、改理由冲突及Case/Result/两页判断历史/任务/Run/活动读回。只新建1个合成Case、1条告警和1份程序提供的uncertain/partial Result，另保留1项未完任务及1个显式pending Run；没有模型或外部工具调用。采用返回第2版判断`45987a86-c3c8-433d-85bb-96d1c93dd367`，同请求重试回执相同，最终仅1条人工采用活动。

4. **原件、指针和覆盖保存正确。** [采用前SQL](http-01/sql-before-adoption.json)与[采用后SQL](http-01/database.json)中的Result/成员、任务/修订、Run/成员及工件逐值保持；旧自动判断保留，Case处理状态不变。新判断的原结论、model origin、操作者、理由、Result来源及覆盖与HTTP读回和活动回执一致，Case当前指针指向该判断。判断历史分页返回总数2、第一页next_offset为1，第二页返回旧判断且next_offset为null；原判断与采用前预览一致。SQL与HTTP的时间值仅有UTC等价表示差异。数据库文件与[manifest](http-01/manifest.json)摘要匹配。

5. **已发现的日志缺陷不得掩盖。** 执行时驱动把可变body对象直接放入汇总，随后更新review_token，使`responses.json`第6条的输入token被回改为第7次预览的新值。逐项核对20份请求前意图，只有这一字段不同；[06-intent.json](http-01/06-intent.json)保留实际发送的旧token，并与第3次预览对应，服务器409原响应也保持。因此旧预览拒绝仍有证据，但不能把该条汇总input当作实际请求原值。[差异说明](request-reconciliation.json)及README/validation已明确这一边界；原汇总与意图没有被修写或重派。执行脚本、配置和当前修后脚本摘要匹配记录；修后仅deepcopy冻结请求/响应并发送已冻结input，静态上消除了该共享对象问题，没有新增HTTP执行来追认本批。

6. **验证和源码范围未扩大。** [JUnit](direct-tests.xml)记录4项既有测试、12个子检查通过，无错误或失败；汇总16不是16个独立测试函数，本审计未重跑。七份业务源码的当前文件、`after-source`快照及[source-files](source-files.json)摘要一致，补丁摘要匹配；三份采用核心与前批快照相同。HTTP后`case_ai.py`的尾部空行清理与驱动记录修复分别在[source-replay](source-replay.json)留明，不作为新业务验证。前批核心manifest列出的74份文件摘要均保持，旧Run自动采用顺序及H后stale证据按原范围复用，没有重复执行四Run流程。

7. **本机静态材料与发布边界分开。** [4177导入回执](workbench-import.json)记录追加本批1份快照，85→86；详情及索引摘要匹配，索引包含本批记录。没有验证本机4177 TCP可达性，也未同步在线4177。本机18027候选使用完整工作树；七文件冻结可供交接，但本批没有证明它们叠加已发布基底后的兼容性。正式Swagger、统一发布、Git及`adopt-investigation-results`整体验收由负责交接会话收口，本审计不预报其结果。

本地HTTP功能通过不代表程序构造的Result获得模型质量证明。既有模型正文/知识质量NOT_PASSED及主调查31/41保持，流式和自动反馈重算不在本次通过范围。
