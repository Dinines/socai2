# D4c 当前真实模型任务链

状态：唯一批次 `real-01` 的真实任务链及当前ASGI HTTP读回已通过，同包测试9组/414项独立保存断言与HTTP22组合同核对通过。正文质量保留未通过结论；D4c在本机限定范围收口，不等于整个change完成。设计见 [§11.6](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#116-d4c当前真实模型任务链执行前设计2026-11-16)。

本批使用本机隔离 PostgreSQL 租户、独立 Redis namespace、当前真实模型及真实 tokenizer。四条告警原材料复制到新身份；不复制旧分析/Run/Result，不重投 Kafka。A1/I1/I2 从本次真实原答分别注入 rationale 前缀、首成员前缀、零长度前缀；全部 Case 调用使用本次真实模型返回。原答、实际交付片段、切点和实际 usage 分开保存，人工注入不记为模型自然截断。

唯一执行驱动为 [validate.py](validate.py)，私密 profile 在 `.local/ai-case-chain-d4c-20261116-01/verification.json`。预算、4/6小时、7天配置保持；仅 scanner 显式使用实际 next_check_at 的受控检查时钟，不改调度器执行时间。日志查询依赖明确未配置，UEBA/knowledge/graph 沿本机禁用设置；本步不能证明这些外部服务已验。

实际顺序：A1→I1，I1运行时正式建案先保存4成员和initial task；I1 partial→真实Case R1；无变化check；另一A2首次分诊→I2新输入/none→真实Case R2；再次无变化check；完整HTTP分页/正文/Result/源I读回。各断言均达到，本批没有为通过重派或追加采样。没有修改核心、HTTP合同、公共DTO或生产配置。

| 实际验证 | 结果 |
| --- | --- |
| 真实调用 | 9次：A×2、I×2、C3×2、Deep×1、C6×2，均实际stop；实际reported总量69015 tokens，0缺失usage。注入3条返回另存，不重复计调用/usage |
| 持久化与调度 | 8 task、6 Run、46步骤、134工件、2个Case Result；两个check均skipped/no_changes、无Run或额外调用；最终active/待写回执/Redis运行槽均0 |
| A1不可用时I继续 | 真实原答截至rationale的239字符前缀，保留verdict/confidence/rationale而缺evidence_ids；failed/partial、无伪造分诊。I1真实执行继续 |
| I1部分分析→Case R1 | I1 782字符前缀保留首成员；I实际选4条、保留1成员分析，Case完整4条。R1实际C3/Deep/C6结束并保存Result |
| 更新顺序 | R1完成且无变化检查结束后才受理A2首次分诊。A2完成后、I2受理前Case周期检查submitted=0；I周期检查submitted=1，新I输入摘要实际改变。未在I2运行期间另调用checker，运行/重试门控复用D4b直接证据 |
| I2空答→Case R2 | I2当前真实响应零长度前缀保存none。Case周期检查submitted=1，R2当前C1选I2，不回退旧I1；真实C3/C6保存第二个Result，按实际没有Deep派发 |
| 上一轮比较 | R2 previous_run_id为R1，comparison_result_id为R1实际Result，资格eligible。不是当前采用结果或其他Case的Run |
| 完整读取 | 196次ASGI GET均200；6 Run全分页目录发现46步骤/134工件，逐条content_url同PG；C1跨Run源I各5份来源核对，25表读取前后摘要相同 |
| 质量保留 | 两轮均accepted/uncertain/partial。共4项独立模型质量诊断：两轮C3各1项支持/反证同源，R1 C6影响范围缺依据，R2 C6支持/反证同源。两轮C6原结论均未改写；正文质量未全面验收 |
| 另行正文复核 | 两轮C6均把05:50:12的A4网络活动说成早于05:46:12的A2进程启动；实际晚4分钟。这个事实错误被第二轮沿用，原结论保留并登记，不能以eligible/accepted或接口成功算内容正确。此为只读复核发现，不混称自动校验已识别 |

Case为`eeba7c9b-502c-56a7-b7dc-db247a3e99f6`，实际身份见[本批结果](real-01/result.json)；Run R1为`4b69d125-c1d0-49f1-9980-f57a7fd78459`、R2为`7e0d7394-da06-485d-bdf2-01376f4c63e1`。各阶段数据先提交后调用，周期检查只使用明确的受控scan clock，不称已经历真实六小时。

证据：[调用及质量摘要](model-and-quality-summary.json)、[完整结果](real-01/result.json)、[原请求/实际响应/派生](real-01/calls.json)、[任务](real-01/tasks.json)、[周期检查](real-01/scans.json)、[PG终态](real-01/database.json)、[全部HTTP读取](real-01/http.json)、[读回核对](real-01/http-validation.json)、[原件清单](real-01-manifest.json)。注入前完整响应另作为同Run/模型step的验证source_snapshot，从HTTP目录可读取；业务strict receipt只定位程序实际收到的片段。所有程序/profile冻结文件运行前后相同；[专用转发已关闭](forward-cleanup.json)，未改共享服务。测试和HTTP模块只复核同包，不重复业务或模型调用；根进展和静态导入由协调模块维护。

便捷查阅：[9次模型输入/输出索引](model-io/index.json)、[首轮C6原文](model-io/05-C6/real-output.txt)、[后轮C6原文](model-io/09-C6/real-output.txt)、[时间判断问题及两轮来源](prose-time-order-review.json)。这些是固定原件的只读导出或复核，没有新调用；三份注入后的内容与真实完整原文分别列出。[本机静态导入](static-verification.json)已保留46条并新增本批至47条，6页/22本地链接核对通过；真实4177及浏览器仍未更新或验收。

测试模块另在I1完整原答的第二成员发现“登录8分钟后启动进程”，实际05:40:12→05:46:12为6分钟；该单元未交付下游（I1只收到首成员前缀），不能将其描述为本次Case实际输入。详见[独立复核最终记录](../test-ai-case-chain-d4c-20261116-01/saved-review-05.json)。两轮C6时间倒置为下游实际输出中的错误，两类问题分别保留；没有为质量再发模型请求。

[测试独立复核](../test-ai-case-chain-d4c-20261116-01/saved-review-05.json)414项通过，[HTTP同包复核](http-readback-review-01.json)22组通过，双方新增业务/模型/PG/HTTP调用均0。复核01启动错误、04脚本字段错误和02/03中间记录保留，不重写成通过、不累加重复检查数。HTTP澄清：Result.source_answer是对话回答来源，两baseline结果为null正确；C6原答通过同Run的C6 model step及Result.delivery追溯，不新增字段或路径。实际分页采用显式5/5测试额度；本步是核心服务受理+ASGI GET，未验外部POST/TCP。

本步不部署、不提交推送；超时/断连及Deep/C6自身恢复留D5，实际21/4177页面留D6。历史失败和质量问题保持，完整change未完成。

[协调模块最终交接核对](root-handoff-validation.json)已通过：复核414项断言/22组HTTP合同、227文件、9次真实响应及3次前缀注入、静态47条与旧46条保留、34份模型IO导出。根进展/交接/任务/问题清单已同步至下一步D5；该回执不替代正文质量通过或整个change结束审计。
