# 既有迁移代码完整性评估

2026-10-21。对象：固定上游 `34ca18c57dd4175539e5c6dd3d04a72dc057306b` 与本项目当前四服务。依据用户最新口径，完整迁移告警/调查及其自治功能；playbook、反馈可随整体原样保留，不额外改测；启动/退出/恢复专项后置。本轮不实施产品修复、不访问21、不调用真实模型或发送业务消息。

## 结论

**没有发现原件被删漏、原路由声明被删除或锁文件被替换；但当前功能并不完整等价于原版。** 部分能力被有意临时关闭，另有本地保护与上游业务链的组合缺陷。不能将所有差异称作“源码损坏”，也不能凭文件齐全声称功能完整。

| 服务 | 迁入基线原件 | 原样 | 修改（含测试） | 缺失 | 原/现路由声明 |
| --- | ---: | ---: | ---: | ---: | ---: |
| API | 872 | 852 | 20 | 0 | 634 / 636 |
| Fusion | 115 | 102 | 13 | 0 | 14 / 14 |
| Agents | 426 | 392 | 34 | 0 | 46 / 46 |
| Actions | 165 | 164 | 1 | 0 | 16 / 16 |
| 合计 | 1578 | 1510 | 68 | 0 | 710 / 712 |

68个修改原件中50个运行文件、18个测试；四服务另新增21文件。12个原构建输入（四服务各Dockerfile/pyproject/poetry.lock）与固定上游字节一致。当前770运行Py、prompt lock及28Compose与R01来源清单零差异，770文件可静态编译；未新增可识别的缺失 `app.*` 模块引用。API/Fusion两份告警schema当前字节一致。

这只是文件、路由声明和静态引用完整性；没有完整动态导入/外部依赖或全仓回归证明。静态扫描仍见上游自带的可选模块引用，不能将“无新增缺失”写成所有依赖已接通。

## 问题与归属

### I1 临时入口裁剪与人审profile限制完整功能

本地新增 [scoped_baseline.py](../../../services/agents/app/core/scoped_baseline.py) 只放默认人工调查、查询及MD/HTML；router triage、agent-runs、PDF、WS等源码存在但被阻止。API仍有PDF代理，转发会到被挡入口。这是1G有意缩小开放面，不是文件删除。

当前review_only配置使 [auto_triage_agent.py](../../../services/agents/app/agents/auto_triage_agent.py) 在566行附近、closure/QA之前返回；worker1248行附近禁止graph，ledger575/600行附近不写canonical Alert。它们符合旧R01限定合同，但不满足用户最新完整自动关闭/调查目标。

**恢复不能只关总开关**：[investigate.py](../../../services/agents/app/api/investigate.py) 378—390行新增Case所属tenant检查与baseline开关耦合；直接关闭会同时撤掉必要归属校验。WS原尾读Run也未绑定Run tenant。规划先解耦身份检查，再恢复完整告警/调查入口和效果边界；playbook/反馈/厂商动作不随解除限制自动打开。

### I2 分诊首次结果保护与自动调查共享Run不兼容

[worker](../../../services/agents/app/workers/fused_alert_consumer.py) 894/902行在warm pending保存或cold结果复用后直接return，绕过1248行自动升级。首次保存失败后仅恢复保存成功，可能不再推进本应执行的调查。

原 [graph runner](../../../services/agents/app/graph/runner.py) 176—183行调用complete_run时不传usage；[ledger](../../../services/agents/app/investigator/ledger.py) 347—352/379—384行默认0并覆盖Run总tokens/counts。这个总量覆盖行为继承上游；新增 [triage_delivery](../../../services/agents/app/workers/triage_delivery.py) 151—154行又要求triage首次快照usage等于Run总量，于是完成graph后可能拒绝读取原分诊结果。

未改写的生产函数AST加内存替身已复现：warm和cold复用均未进入escalate；graph完成使旧tokens18→0、unpriced_calls1→0，随后首次结果投影报 `recovery usage differs from completed run`。这是本地恢复保护与原graph的组合缺陷，不是21现场故障；当前graph关闭。探针首次缺注入time的NameError为探针错误，修正后才取得上述结果，见probes。

应最小区分分诊阶段与调查阶段的完成状态、身份和usage，既不重新调用分诊模型，也不覆盖首次结果；避免只移除review_only就上线自动升级。当前只验证正常升级的业务结果与必要方法接缝，不展开停止/重启故障矩阵。

### I3 HTTP与Kafka融合入口的完整处理合同分叉

原 [/process](../../../services/fusion/app/api/router.py) 118行直接engine.process，仍被 [tools/fusion.py](../../../services/agents/app/tools/fusion.py) 76行调用；它写共享dedup却绕过live canonical ID、首次快照、PG和消息交付。C01保护遇到同输入已有dedup却无快照时会hold，故不能声称两入口业务等价。

路由本身继承上游，分叉影响与本地持久合同组合；principal未绑定body tenant也是上游缺口。现有Fusion认证503限制不能当已发生越权或已完整开放。规划保持FusedAlert响应，统一两入口关键处理与身份合同，核同输入跨入口结果一致；不以回退C01解决。

### I4 默认调查缺源与真实空结果混淆

原 [bundle_prompt.py](../../../services/agents/app/investigator/bundle_prompt.py) 51行构造builder未传api_token；通用图工具在关闭/缺身份时返回error/available=false，但 [bundle.py](../../../services/agents/app/context/bundle.py) 617—629行仍生成“0 neighbors”。该摘要会进入实际模型prompt。生产方法加不可用工具替身已复现。

此问题继承上游，不是本地删代码。完整调查须补所需工具身份，并将不可用、失败、无匹配、成功分开。五类分诊reader不替代通用调查工具。向量空间/embedding/集合尚未对齐及知识实际消费仍是未完成接入，不属于原件丢失。

## 应保留的修改

source-v1独立告警身份、风险缺失null与显式0区分、正文/发生时间投影、租户Bearer/细分scope、持久交付确认、首次结果不重调模型及预算/SDK上限均有明确合同或故障依据。不应为追求字节回到原版而撤销。旧float-only消费者须按schema版本处理，不用补0伪装兼容。当前没有schema漂移证据，不为潜在漂移先建共享包。

## 暂缓与完成口径

启动顺序、正常/异常退出、重启恢复、cold/warm故障矩阵、ack丢失注入、长稳/压力等列专项后置；R02不作为功能修复前置，原0/17及五文件hash保留。现有保护不删除，旧unknown/积压不清空或重放。

playbook及反馈一体源码保留，不额外改业务或做专项测试；调查所需的已有处置/记忆读取保留，暂缓的是额外闭环工作。真实厂商响应不因完整迁移自动开启。源码已迁入、功能已接通、业务已验证、运行已启用分别记录；旧自治质量失败及旧回执原样保持。

按design/tasks的最小顺序规划修复，当前仅评估/规划完成，产品修复尚未实施。

## 后续原则补充（2026-10-21）

用户进一步要求功能完整、结果正确优先；所有一体模块可整体原样迁入，不额外修改或测试，冗余设计与服务可用性相关测试/修复登记后置。上述源码和探针事实保持；I2正常graph用量覆盖仍列业务修复，仅故障重投/恢复后调查接续先登记暂缓，不为后者先加通用阶段账本/恢复框架。修复设计与待办已据此收敛，本评估不是要求重跑恢复专项。
