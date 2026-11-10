# Deep/C6 本地接入与同材料比较

2026-11-10。落实用户要求：整理 Deep/C6 输入、补齐 C3 判断与证据交接、由程序补回已知输出字段。**本地接入和隔离数据验证已完成；尚未部署到 21，未新增真实模型调用，不宣称质量或速度改善。**

## 这次改了什么

| 环节 | 原来 | 本地新版 |
| --- | --- | --- |
| Deep 输入 | 旧 JSON 投影，重复读取部分字段，沿用旧来源号的前序判断 | 共享 C3 的冻结业务材料；指定问题、对应 C3 判断/计划、支持和反证、实际补查、当前工具目录。结构化旧引用重新对应本轮来源，正文保持 |
| C6 输入 | C3 摘要与两项计划，没有完整交接具体分析；Deep 主要是答案文字 | 实际有效 C3 的成员、发现、六问、四领域、冲突和计划；Deep 答案及支持/反证；原计划与实际执行逐项对应；当前图和指定历史比较 |
| Deep 输出 | 5 项，含固定问题号 | 4 项：`action / binding_id / reason / answer`；问题号由当前请求恢复 |
| C6 输出 | 6 块，模型写建议编号、真实成员/对象身份和固定首次比较 | 保留业务判断职责；成员/对象用短号，程序恢复真实身份；建议编号由程序生成；首次无历史结果时省去固定 `comparison`，程序补 `initial/null/[]`。其他比较仍需模型判断 |

成员/对象短号是模型表达范围所需，发现编号用于本答复内部关联，不是后台运行身份，继续保留。C6 仍给出完整新判断，未引入默认继承或“只输出变化项”。报告由同一结果在程序中渲染，不增加报告模型。

输入按固定结构配置转换，未针对此 Case 的主机、厂商或具体字段值编写规则。来源角色、跨成员范围、实际查询和历史正文保持；缺引用显式列为不可见，不伪造依据。C3 局部拒收后只接收已保留部分；没有有效 C3 时明确提示，沿现有独立最终分析/系统收尾。

本次核对还修了两个结构问题：

- 旧引用指向整份 I 诊断或材料元数据时，直接补原父对象会重复带入大量后台字段。现在按配置关联已呈现的具体明细，保留父引用及来源角色；不重新总结正文。
- C4 原字段投影仅在材料身份、路径、角色、成员、原值与可见值全部一致且为 identity 转换时合并引用。枚举映射或冲突值继续独立保留。查询字段有同一行编号及“仅查询绑定”限制，C6 必要行为字段不可见时拒绝调用；旧图未覆盖新查询时不当成当前图。历史比较保留原窗口/范围，旧成员/对象不扩展新输出目标。

规则、提示、剔除字段进入 [case-input-v1.json](../../../services/api/app/socai2/case-input-v1.json)；[输入构建](../../../services/api/app/socai2/case_followup_input.py)、[冻结读取](../../../services/api/app/socai2/case_followup_loader.py)、[输出恢复](../../../services/api/app/socai2/case_followup_output.py)分别负责边界工作。原 DDL、GET、存储和读取字段未改。无 `case_io` 的旧 Run 沿旧 JSON/输出；有 profile 的 Run 要求冻结指纹匹配，不能途中换规则。可选 C3.reanalysis 暂时仍是旧装配。

## 修改前后完整输入与输出

比较固定为历史 Run `8d53cdb1-1cba-4df3-8ac2-f2724c062342`，48 份原工件 hash/大小核对。业务材料、历史前序答案及实际查询来自同一保存快照；候选 C1 在内存补入经核对的同 A 回执和来源角色，**不能追认旧 C1 或旧模型已经看过这些内容**。

| 查看内容 | Deep | C6 |
| --- | --- | --- |
| 修改前完整输入 | [旧输入](../../../docs/operations/evidence/case-followup-comparison-20261110-01/deep-before-input.txt) | [旧输入](../../../docs/operations/evidence/case-followup-comparison-20261110-01/c6-before-input.txt) |
| 修改后完整输入 | [新版输入](../../../docs/operations/evidence/case-followup-comparison-20261110-01/deep-after-input.txt) | [新版输入](../../../docs/operations/evidence/case-followup-comparison-20261110-01/c6-after-input.txt) |
| 修改后输出 Schema | [四项输出](../../../docs/operations/evidence/case-followup-comparison-20261110-01/deep-after-schema.json) | [首次调查输出](../../../docs/operations/evidence/case-followup-comparison-20261110-01/c6-after-schema.json) |
| 历史真实模型原答 | [原答](../../../docs/operations/evidence/case-followup-comparison-20261110-01/deep-original-output.txt) | [原答](../../../docs/operations/evidence/case-followup-comparison-20261110-01/c6-original-output.txt) |
| 旧答按新结构机械转换 | [结构示例，非新生成](../../../docs/operations/evidence/case-followup-comparison-20261110-01/deep-output-shape-replay-not-generated.json) | [结构示例，非新生成](../../../docs/operations/evidence/case-followup-comparison-20261110-01/c6-output-shape-replay-not-generated.json) |

机械转换保留原正文及旧引用，仅验证程序恢复后与原答一致。旧编号不因此成为新版请求的合法引用；没有把旧答当成新模型结果。前后请求均另存完整 JSON，来源及逐处映射见同目录 `*-mapping-ledger.json`。

| 指标（UTF-8 字节） | Deep 之前 → 之后 | C6 之前 → 之后 |
| --- | --- | --- |
| 用户材料正文 | 26,244 → 33,481（+27.58%） | 37,860 → 49,413（+30.52%） |
| 全部消息，含指令/工具 | 31,718 → 38,581（+21.64%） | 45,749 → 53,524（+16.99%） |
| 完整请求，含 Schema | 33,678 → 41,105（+22.05%） | 53,286 → 61,561（+15.53%） |
| 旧输出机械转换 | 1,649 → 1,626（−1.39%） | 9,813 → 8,318（−15.23%） |
| 观察条目 / 原始字段位置 | 47 / 25 → 53 / 53 | 47 / 25 → 56 / 56 |

**本轮主要收益是交接完整和职责明确，不是输入缩短。** 重复观察消除了，但补入完整 I 明细、同 A 查询、C3 判断和引用依赖后总体输入增加。C6 的 C3 内容由摘要/两计划扩为 3 成员、3 发现、6 问题、4 领域、1 冲突、2 计划。Deep 的 4/4 处、C6 的 84/84 处前序结构化引用对应到可见来源；84 是引用出现次数，不是独立证据数。

来源可达与往返一致不代表推理正确。此次未计真实 tokens、生成耗时或新模型错误率；没有声称压缩改善质量。这是同保存材料的输入覆盖/格式比较，不是相同可见输入下的受控模型 A/B。[比较回执](../../../docs/operations/evidence/case-followup-comparison-20261110-01/summary.json)。后续查询最小依据和比较范围分支补强后，当前构建器再次生成的两份请求与固定对比逐值一致，另存复核回执，不改原比较。

## 直接验证与实际保存

- 42 项不同纯检查最新通过，包括 17 项 Deep/C6 边界检查、原 C3/查询回归和打包检查；覆盖引用/反证、跨成员依赖、历史范围、缺失/guard、0/false、查询四态、输出恢复、一次纠正与局部保留。最后对新增边界及 Case 打包重验 18 项通过。[最终定向日志](../../../docs/operations/evidence/case-followup-integration-20261110-01/pytest-final.txt)。首批两项旧检查缺少显式 policy 环境，补正确配置后通过，不称首轮全过。
- `v12_upgrade_dev` 独立 PG 中，`pg-04` 的四条路径通过：正常 C3→Deep 查询→回答→C6；无效局部引用；空引用纠正一次；C3 拒收后的 C6 独立收尾。模型和湖均为替身，**0 真实模型调用**。请求、原答、有效输出、报告、结果和采用信息走实际存储；同次 finalize 重放不重复调用。[PG 回执](../../../docs/operations/evidence/case-followup-integration-20261110-01/pg-04/summary.json)。随后历史比较范围/后台标识分支的补强以专门纯检查验证，未冒称该分支也做了 PG 实测。
- 原 Case/Run/历史服务方法 12 次读取成功，非新 HTTP GET 实测；采集说明与业务原值保持。数据库前后仍为 **29 表、462 列**，无 DDL/正式库操作。三个正常/纠正/无 C3 的合成结果校验 accepted；局部错误结果 validation=rejected、delivery=partial，不采用该整体结论。四个 Run 实际都是 completed/partial，不能把执行完成写成完整交付或语义通过。
- `pg-01` 至 `pg-03` 原失败保留：先后为测试只读事务误用 FOR UPDATE、报告层级/Run 状态断言、结果关联字段应为 source_run_id；另有随机选到认证工具但替身未给用户字段，C6 正确拒绝缺少最小依据。修正测试选择与断言，没有为通过而放宽业务校验。13 份实际 Case 快照（含早期失败测试产生的实际记录）均已追加到本机静态工作台，登记总数 **47**；未发布到 21 或声称本机 4177 在线可访问。[本机目录](../../../deliverables/investigation-validation-20261106/processing-audit/index.html)。初次误用严格 `--folder` 导入失败后，按既有联合测试导出用法改为 `--batch`；原导出未改。

早期离线比较曾暴露父诊断整块回填超出输入 guard；已用上述父级引用明细映射解决。比较脚本最初括号错误与 Ruff 导入格式错误也已修；未产生模型请求或修改历史材料。全部失败/改正过程在本批报告和原回执保留。

## 部署来源与下一步

[候选策略](../../../deploy/local-investigation/investigation-policy-case-v1.toml)、[打包配置](../../../deploy/aisoc21/processing-build-case-v1.toml)及部署说明已同步；候选名为 `processing-case-20261110-c2`，三个新模块与规则均逐字随包核验。没有切换正式 A/I profile，没有重启或恢复消费者，没有提交推送。

下一步按新批固定实际模型请求，验证补齐前序后是否正确使用支持/反证，以及新增输入对 tokens、耗时和判断的影响；不能沿用已结束 C3 两次授权或重派旧批。之后再决定 Case 发布和逐项显式复核/减少重复输出。任务 3.30、Case 整体语义质量和 1.2 整体 NOT_PASSED 保持。
