# 3b Case 本机续验：执行、保存及 HTTP 读回通过

2026-11-17。在新建本机库 `acceptance_c1_20261117_01` 中，以当前 C1 修正代码、真实联合调度/Redis、真实模型和 21 只读湖查询完成 Case 续验。**成功 Run 有17步骤、50工件和1个Result；168 GET 与保存值一致，26表读前后摘要不变。** 本机功能阻断已打通，测试模块独立复核通过。21 原失败仍是失败，未替换活动服务或发布新4177；3b的21整链恢复、3c/3d/任务4及整个change不据此通过。

[汇总](final-validation.json) · [完整读回](execution-03/validation.json) · [实际保存记录](execution-03/saved-records.json) · [问题记录](quality-register.json) · [本机静态详情](../../../../deliverables/investigation-validation-20261106/processing-audit/cases/8b538db76642fe7aaaba1d0ac8578497aa1d1d5fc89a5f6e3bf8b8b14450415a.html)。

## 这次跑了什么

| 环节 | 实际结果与边界 |
| --- | --- |
| 来源导入 | 21只读取回这一案的必要依赖，16表46行与单段02一致；新库123–129、32表521列。保留原tenant、业务UUID、A/I原答和失败任务，公开tenant/user/connector依赖以相同ID及中性名称补齐，未复制21凭据。没有新Kafka投递或A/I执行。 |
| C1 | 同租户另有一个无关事件；预检查和真实保存C1均只含本案1告警、1原事件、正确I Run及原件，无串读。 |
| C2 | 资产/情报查询完成；历史因工具预算保留跳过，UEBA/知识/图谱来源未接，原因原样保存。完成/查空/未查不混用。 |
| C3 | 真实模型正常结束。模型对身份、云资源、内部人员领域标为适用，钓鱼不适用；完整四领域组件均保存。该标签不代表正文已全面验收。 |
| C4/C5 | 认证查询取回上轮2条上下文，event_id、class_uid及解析OCSF原值一致；网络查询0行。图由保留材料生成，本轮未执行Deep、未宣称外部图谱可用。 |
| C6/保存 | 真实模型正常结束，结果`accepted / uncertain / partial`；Case任务与Run均completed。前轮固定为本地02的unknown Run，comparison_result_id为空，reason为previous_result_unavailable，未伪造比较基线。 |
| HTTP | 1次真实ASGI POST202 +168次GET；任务/尝试、完整分页、步骤、模型原件、SHA、Result及冻结来源一致。是当前真实应用的ASGI调用，未声称21 TCP已验。 |
| 收尾 | 本地N=1，峰值1、最终槽0。专用模型/tokenizer/湖隧道关闭；21三服务容器ID与镜像保持。静态50→51，原50条记录和页面摘要不变；本地库及所有原件保留。 |

## 保留的失败

| 批次/执行 | 终态 | 原因与处理 |
| --- | --- | --- |
| 21 单段02 | 原初始task failed，无Case Run/Result | 嵌套SQL别名遮蔽，SQLSTATE21000；本机同一最小修正继续验证，未修改21历史。 |
| 本地第1次 | task failed、attempt unknown，无Case Run/新模型 | 验证驱动只读轮询误用带锁task读取；改lock=False。原受理/失败及与hash一致的驱动源码保留，未重派原task。见[记录](driver-failure-review.json)。 |
| execution-02 | task failed、attempt/Run unknown，Result0 | C3/C6两次stop已保存，但新库漏配auto_adopt_baseline_result执行权限导致保存回滚；驱动另漏接RunDirectoryBackend。补齐后同Run101 GET读回通过，0新模型；unknown/原答不改。见[失败](execution-02/failure-review.json)、[只读补验](execution-02/readback-validation.json)。 |
| execution-03 | task/Run completed，Result1 | 仅为核实上述保存阻断修正而用新operation_key执行；旧task/attempt/Run/原答逐值保持，不属于追求模型质量的重复采样。 |

最终本地快照为7task、6attempt、4Run、41步骤、116工件、1Result，包含复制的A/I及保留的失败，不能全部计为新成功执行。

## 模型输入输出与质量

成功Run的两次调用如下；上限均为16384，服务窗口保持65536。

| 阶段 | 输入tokens | 输出tokens | 结束 | 原件 |
| --- | ---: | ---: | --- | --- |
| C3 | 4003 | 5210 | `stop` | [输入](execution-03/model-io/1977d41d-9708-4565-932a-1c286c43a122-11-815379fb-4271-4e69-8367-02283fffbdd7/input.txt) · [模型原答](execution-03/model-io/1977d41d-9708-4565-932a-1c286c43a122-11-815379fb-4271-4e69-8367-02283fffbdd7/output.txt) |
| C6 | 7793 | 6533 | `stop` | [输入](execution-03/model-io/1977d41d-9708-4565-932a-1c286c43a122-17-2e68b4a2-86ec-40f7-af30-7a52a37477c3/input.txt) · [模型原答](execution-03/model-io/1977d41d-9708-4565-932a-1c286c43a122-17-2e68b4a2-86ec-40f7-af30-7a52a37477c3/output.txt) |

execution-03新增2次、23539tokens；execution-02新增2次、16059tokens，**本批合计4次、39598tokens**，均stop、reasoning_tokens=0。索引中的旧A/I两次只是复制依赖，不计本批调用或usage。usage无未知，费用未知；[全部输入输出索引](execution-03/model-io/index.json)、[02原答索引](execution-02/model-io/index.json)。已扫描的tenant_uid、租户UUID、来源标签和测试标记均0命中；后台关联不删除。

成功Run C6记录5项程序引用诊断：3处重复引用、1处空引用及1处影响范围引用覆盖缺失。另明确登记1项正文问题：模型把实际跳过的历史查询写成“历史告警查询无结果”。已保留原答、诊断和待复核/部分交付结论，不中断保存/读取，也未追加质量采样；正文质量仍为NOT_PASSED/未全面评估。

## 复核依据

- [初始化](database-initialization.json)、[导入逐值核对](seed-validation.json)、[源快照比较](source-comparison.json)。
- [实际核心修正范围](core-fix-scope.json)、[执行前源码](execution-03/source-before.json)、[执行后源码](execution-03/source-after.json)。
- [并发终态](execution-03/dispatcher-final.json)、[隧道收尾](cleanup.json)、[21服务身份](services-after.json)、[静态读回](static-verification.json)。
- [测试模块独立复核](../test-acceptance-case-continuation-20261117-01/independent-review-01.json)与[HTTP模块合同复核](http-handoff-review.json)通过；[收口回执](audit-completion.json)记录独审完成。`final-validation.json`是独审前冻结汇总，其pending字段仅表示当时阶段，不改写已冻结证据。
