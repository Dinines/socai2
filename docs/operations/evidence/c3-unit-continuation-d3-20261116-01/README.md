# D3：C3截断条目保留与一次补答后继续

2026-11-16。对应[OpenSpec §10](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-output-continuation-design-20261116.md#10-d3c3单元恢复阶段回执与c6继续)。D3核心实施、直接验证、唯一一批本机PG/Redis→HTTP联验和独立复核均已通过。未部署21、未提交/推送；不把本步通过写成D4–D6或整个change已完成。

## 实际行为

当前C3普通答复和截断答复使用同一单元接收器。完整JSON即使finish_reason=length仍接收并记录截断；不完整答复只保留闭合且通过身份/范围/结构检查的summary、数组项和显式空数组。未知主体、重复定义、非法binding隔离；超过5条发现时第6条及以后明确无效并使交付partial，前5条合法项保留。质量问题继续按D2记录，不因缺限制说明或引用问题改写正文结论。

每个实际保留单元记录原模型值、原正文Unicode区间、UTF-8 SHA256和冻结来源。原别名/原对象保持，UUID恢复和程序生成的观察正文进入单独analysis。新`source_snapshot / socai2.stage-delivery.v1`记录执行、解析、交付、缺口和用途；通过现有完整工件目录发现，不改公开告警DTO。既有Chat Completions与Responses正文定位由原协议适配提供，不伪造第二份原答。

补答上限配置0或1，默认1；使用冻结材料，只补缺失项。禁用、预算未发出、空白、无效或再次截断均不清空初答。C4只执行依赖齐备的完整计划，跳过的计划保留原下标。C6从当前`$.analysis`读取已保留内容及必要缺口说明；不再执行旧`section_completion.retained_analysis`后备路线，缺字段不补空答案。

## 真实母本与受控验证的界限

母本为[D2 real-02](../quality-continuation-d2-20261116-01/real-02/)已完成的真实C3/C6答复；D2当批实际调用真实模型3次。本D3没有新模型生成，使用其完整原答的独立截断变体。独立母本与期望见[测试准备清单](../test-c3-continuation-d3-20261116-01/fixtures-01/manifest.json)：7,516字符、22单元，固定seed=20261116的3个随机切点1724/1753/5207。

本机PG批次复制D2材料到新租户/Case身份，显式映射成员/对象别名与相同角色/主体/字段路径的来源编号；原正文不作语义改写，未能定位的来源保持不可用。[calls.json](pg-http-01/calls.json)保存母本摘要、完整派生答复、截断位置、映射、实际请求和实际返回。计数器与返回usage为明确测试替身，不能当作本批真实模型消耗、准确率或新的真实模型质量验收。

## 直接与独立验证

- D3a最初[33项直接保护](d3a-direct.txt)通过；[独立26项](../test-c3-continuation-d3-20261116-01/attempt-01/execution.json)通过，覆盖21个冻结变体和5项严格来源/回执保护。
- D3b[14项流程控制测试](d3b-attempt-02.txt)通过；补答0/1、原项不覆盖、缺依赖计划保留但不派发、C6真实业务输入均有断言。[联合88项](d3b-direct-02.txt)通过；增加既有协议正文路径保护后的[最终受影响96项](final-direct.txt)通过，数字有重叠，不累加为独立样本。
- 测试模块[D3b独立34项](../test-c3-continuation-d3-20261116-01/d3b-attempt-03/execution.json)通过，含D3a受影响26项；使用当前profile新构造输入，D2母本不改。同批D3c的[59项只读核对](../test-c3-continuation-d3-20261116-01/d3c-readonly-03/review.json)及HTTP模块[23组复核](http-readback-review-01.json)通过，复核保存的同一包，没有重复业务/网络请求。
- 失败保留：[d3b-direct.txt](d3b-direct.txt)的51通过/1失败发现真实边界：显式findings=[]误入领域依赖集合；修正为只纳入Finding对象，不更改原测试的“仅缺followups”预期。[d3b-attempt-01.txt](d3b-attempt-01.txt)是测试fixture导入被lint清理导致的收集失败，修正测试导入后继续；均非业务重派。D3a开始前曾遗漏PYTHONPATH，随后读取JSON空工件未守卫，均为离线测试夹具准备问题，工具回执保留，未连接PG/模型。

## 唯一PG/Redis任务与HTTP读回

[pg-http-01/result.json](pg-http-01/result.json)通过。Case `1576d3fa-a518-5db2-9781-33347eec1fa2`，Task `19f82f9f-34b3-43c5-b3e4-6c09ce1d840c`，Run `1dd4d4dc-b303-4bf8-abb1-8347208a4e17`，Result `4566b95e-6bb7-4e29-9647-42de51d9f457`。一个任务、一次attempt、一个Run，16步骤、44工件，Redis运行槽已释放。

实际通过Case创建受理和当前调度器执行C1–C6：C3返回F1闭合/F2半项的length正文；唯一补答返回空白；C3封存summary+4成员+F1共6单元，交付partial，后续部分仍记缺失，followups没有被伪造为[]。实际C6请求包含F1及prior_analysis角色，不含F2或虚构补查计划；C4零派发。C6完整受控答复落库，保留原结论和2项限制说明诊断，Result为accepted/uncertain/partial，不表示正文真值已验证。

HTTP使用现行适配器与ASGITransport，真实数据来自上述隔离PG。先读任务返回的run_url，再读Run返回的steps_url/artifacts_url；4页步骤、9页工件发现完整16/44，再逐个访问content_url。共60 GET全部200，逐值核原件/派生结果及新回执`47cba86d-339a-4594-8399-c5769bb3ee5a`，四份初/补答请求和原答均可定位，span/SHA可复算。HTTP前后表摘要相同。[HTTP回执](pg-http-01/http.json)、[保存快照](pg-http-01/database.json)、[唯一驱动](validate.py)、[执行时源码](pg-http-01/validate-source.py)、[源码摘要](pg-http-01/source-manifest.json)可追溯。没有通过PG已知UUID手拼工件GET冒充目录发现。

协调方已完成[本机静态记录导入](static-verification.json)：新增1条，原44条逐值保留，合计45条。仅静态文件更新，未部署或浏览器核验；D6的21/4177实际页面验收仍待。[来源复核](source-verification.json)确认本批161项代码/配置与执行时一致；清单不独立覆盖HTTP源码，不据此声称完整部署包已核。[OpenSpec strict](openspec-final.txt)、受影响Ruff和Git空白检查通过。

## 未验边界

本步只实现C3恢复及必要下游接线。A/I恢复留D4；Deep/C6自身截断、超时/连接中断、usage未知及本地收尾/槽释放的跨步骤处理留D5。D3中的“补答失败”实测为空白、结构无效、再次截断、预算未发出和配置关闭，不等同于网络故障已通过。没有重投Kafka、重派D2旧Run或改写历史拒收记录；21仍为原processing r3正式基线，未发布本批新代码。
