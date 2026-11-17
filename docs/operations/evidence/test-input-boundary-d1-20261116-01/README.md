# D1 五阶段输入边界独立验证

2026-11-16。**D1独立离线复验15/15通过；第一轮镜像字段漏项已在同一步修正，历史失败保留。** 本批使用当前源码与指定正式policy，重建A/I/C3/Deep/C6新请求；旧r3快照只提供冻结材料，不以扫描旧16份请求代替新实现测试。运行属于离线真实构造器验证，0网络、0真实模型、0业务写入、0部署，不证明21当前运行版已修复。

依据：[调查设计§2.1/§7 D1](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#21-输入过滤)、[TC-N02](../../../../openspec/changes/schedule-streaming-investigation-updates/functional-test-cases-20261115.md#d1实施交接后的独立验证准备)。独立脚本：[test_socai2_d1_input_boundary_independent.py](../../../../services/api/tests/test_socai2_d1_input_boundary_independent.py)。

覆盖五阶段 × r3材料/结构化同名字段对照/序列化OCSF对照，共15个变体。显式policy为`deploy/aisoc21/streaming-release-20261116-02/analysis/investigation-policy.toml`，输入profile从当前源码加载。Case只在新离线派生上下文选择新profile，不修改原C1记录。测试禁止socket连接。

第一轮[JUnit](attempt-01/junit.xml)为15失败：I/C3/Deep/C6共12项真实新wire仍存在`$.raw_json.raw_event.ocsf_event.tenant_uid`；3项A在测试检查中误取该模型source_map并不定义的alert_ids而KeyError，属于测试脚本问题。它们不能合并声称15个业务缺陷。具体[逐文件回执与定位](attempt-01/review.json)保留；12份检查中后台原租户/告警/OCSF字段、原件hash、来源ref/owner及正向业务字段保持均通过。

实现方随后仅在A/I两份profile补齐`$.raw_json.raw_event.ocsf_event.tenant_uid`，Case沿I的business profile复用；序列化变体发现的也是同一镜像路径，未证明独立序列化漏洞，不作泛化删键。测试侧按A的单告警来源合同修正检查，未修改业务代码/profile。

[attempt-02测试输出](attempt-02/pytest.txt)、[JUnit](attempt-02/junit.xml)为15/15通过，224条直接断言成立。17份[代码/配置/数据摘要](attempt-02/source-manifest.json)运行前后无变化；[当前构造器源码归档](attempt-02/tested-sources.zip)保存16份已测源码/配置，r3原快照按原路径/hash引用。每个`stage-variant.json`保存新wire、profile指纹、原后台tenant_id/alert_id/OCSF值、source map、单项判据和结果。

两处后台租户字段未进入新模型wire；业务同名tenant_uid/source/id、原文、未知0/false/[]保持，原材料和来源归属保持。本结论是离线当前构造器的独立复核，不证明当前21已加载修正，也不替代实际PG/HTTP/真实模型链。

[结果汇总](result.json)保留第一轮缺陷、测试脚本问题和第二轮通过；[文档/静态校验](validation.json)单列，不混计功能测试。D2–D6及模型输出恢复/质量处理未由本步执行。
