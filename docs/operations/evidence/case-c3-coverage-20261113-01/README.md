# C3业务判断与程序覆盖分工

2026-11-13，对应主调查字段梳理第32节。C3模型只回答五个业务问题，程序根据冻结材料视图、本Case的C2回执和实际保留的分析状态补coverage；保存仍为六问。历史A查询不计作当前Case执行，无C4材料读取回执时如实记unrecorded。模型代写coverage及相应补查均拒收，partial按实际保留片段重算；Deep不继承C3的覆盖来源，C6独立生成。

通过可选`program_output.c3_coverage`启用；旧v2冻结边界没有coverage_facts时继续接收六问，旧v1/无程序观察装配合同保留。不改HTTP字段、表或读取结构，原件和模型原答保持。不是手工压缩，也不因字符减少认定判断质量提高。

- [调整前完整预览](before/C3-model-input.txt)、[调整后完整预览](after/C3-model-input.txt)及对应request-preview包含全部消息和Schema；只读使用09冻结材料、显式离线绑定前后配置，没有派发旧Run。
- [程序核对](preview-summary.json)：105项原材料/引用逐值保持，108份旧文件摘要保持。旧09实际C3六问原答按旧边界仍接受。新coverage事实在[程序记录](after/program-coverage-facts.json)，没有追加到模型正文。
- 五个既有检查函数共7个执行场景通过，含C3/C6装配、旧边界、局部拒收重算及C4来源保存门。首轮因缺PYTHONPATH收集失败；第二轮5项通过、两项旧夹具缺original_value失败；补齐夹具后仅复验两项并通过。原日志/XML保留，没有全仓回归。
- Ruff与OpenSpec严格校验通过。[本轮差异](source.patch)和前后9文件快照区别于仓库已有修改。

随后只执行[10批一个新固定Run](../fixed-investigation-20261113-10/README.md)，真实C3已验证五问请求→程序六问保存，综合结论、H和当前判断实际读回；不以离线预览替代执行。正文质量NOT_PASSED、主31/41及流式后置保持；模型运行服务未发布。最终限定审计另存audit.md。
