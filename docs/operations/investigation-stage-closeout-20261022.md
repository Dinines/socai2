# 调查阶段收口与候选发布差异

2026-10-22。用户确认继续[模块评估后的推进路线](../architecture/attack-chain-path.md#module-assessment)，本轮沿既有restore B5→B6完成任务责任对照及具体候选差异整理。已有能力证据复用[阶段交接](investigation-stage-handoff-20261022.md)，不再创建一套产品任务树。

**本轮实际产物：10项未勾责任逐项映射；19个拟选运行文件的本地审查副本；Deep仅接入链图摘要的独立补丁；7个旧C2/文案差异明确排除。** 原工作区业务源码不改，未构建镜像、部署、访问21运行态或启worker。这个审查副本不是可部署包，也不表示整个change完成。

## 1. 已完成部分与剩余责任

原15项中，1.1—1.4及2.4已勾选，其余10项仍保留未勾；这是跨批整项责任，不是业务完成比例。下表不新增验收门或要求重跑全部模型。

| 原任务 | 已有覆盖证据 | 当前仍需明确的责任 |
| --- | --- | --- |
| 2.1 功能/入口清单 | [18组功能对照](alert-function-alignment.md)、Fusion/分诊/调查/工具/知识/链图说明已累计整理 | 核实际选定范围中的发布、本地、禁用、未验和声明未实现状态；不是重新盘点上游 |
| 2.2 归属与所需入口 | [B2/B3](integrity-b2b3.md)及[人工R01](integrity-investigation-r01.md)有Case/Run归属解耦、错误Case/跨租户拒读与冷读证据 | 实际选入差异涉及哪些入口/权限，对应原代表证据是否仍适用；不扩大到全部历史入口矩阵 |
| 2.3 正常graph结果/用量 | I2原子追加/正常完成用量修复已部署；[C2实际Run](integrity-autonomy-r01.md)总22568＝首次2117＋graph20451，工件/PG/API可核 | 核普通完成/首次分诊可读的原责任；与后续未终审C2预算/内容质量修改分开，不重发模型 |
| 3.1 工具/来源 | 七权限reader、缺源与empty区分、full基本来源、链图实际消费已有证据 | 两处工具合同、链图与Kafka入口仍本地；本次选入改动对应包/权限/来源边界须明确 |
| 3.2 知识路径消费 | PG全文同Run读取、同块入四prompt，candidate04引用parser接线已有记录 | 以当前选用PG路径核材料/来源/标记；向量未消费、引用质量未全过保留，不强制新增向量验证 |
| 3.3 自动关闭/调查 | C1原worker实际关闭；C2正式告警入口无需再点就执行graph/deep，报告/工件可读 | 主链技术接通成立，旧partial、cap/超预算与质量失败不追认通过；常驻保持OFF |
| 3.4 人工/自动交付 | 默认四节点R01、本地Router/Deep、自动C1/C2、链图工件及Markdown各有记录 | 按各自范围核实际状态/材料/usage；不能拼成一次新的端到端实测，也不重调旧失败 |
| 4.1 来源/交付记录 | 架构、逐调用记录、回执、选定版本和阶段交接已具备 | 本轮以具体文件/差异对应来源、验证、发布状态和剩余责任 |
| 4.2 结束独审 | 各局部批次均有相应限定独审 | 真正选定组合还需相应整包审查；本次审查副本及结束复核不自动批准构建/发布 |
| 4.3 归档 | 完整change尚未结束 | 实际责任完成后再核归档/规格同步；本轮不勾选、不归档 |

本地两处合同、链图和Kafka准备已有直接/真实接缝证据，不要求为上表再跑一轮全模型矩阵。旧质量、unknown、积压和未发输入原样保留。任务定义见[原tasks](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/tasks.md)。

## 2. 比较基线与本地能够证明的范围

最近full发布回执记录：API为`1be37c38`，Agents为`aec3c54f`，Fusion为`c52b9aac`；Agents在candidate05上只替换过`app/context/bundle.py`以接UEBA。完整镜像ID在本轮机器摘要及原[full回执](full-support-migration.md)中保留。本轮没有新查21，不把它们称为此刻运行健康/无漂移证明。

candidate05已有773项运行来源manifest及本地可读副本，可用于比较其余文件；**Git HEAD不是发布基线，candidate05也不是full之后整个Agents基线**。本地现有full记录没有保存纯bundle文件/hash，因此不能把当前bundle相对candidate05的所有差异都说成未发布内容，UEBA部分已经发布。

只读比较当前运行源码与candidate05记录，共有26个不同文件：API 7、Agents 19。其中19个构成本次拟选接线集合；另外7个旧C2/文案差异先不选。这个数量是源码比较结果，不是新增26项功能或实测。

## 3. 19个具体候选文件

本地审查目录：`.local/review/investigation-stage-closeout-20261022/`。`manifest.json`记录来源、工作区与副本hash、排除项、镜像记录及限制；`files/`只含下列运行文件，不含凭据、业务HTTP观察、完整依赖环境或构建配方。

| API文件 | 本轮选入意图 |
| --- | --- |
| `services/api/app/api/v1/endpoints/attack_chain.py` | Alert薄链入口，复用原算法 |
| `services/api/app/api/v1/endpoints/cases.py` | 人工Case调查入口准备图及回执 |
| `services/api/app/api/v1/endpoints/graph.py` | 受权限保护的context GET/POST及来源边界 |
| `services/api/app/api/v1/router.py` | 注册Alert薄链路由 |
| `services/api/app/services/graph_service.py` | 已报告关系投影及现有图读取适配 |
| `services/api/app/services/investigation_attack_context.py` | 可信PG锚点、定向投影、PG链/Case路径/Alert图读取；显式Alert只投当前告警 |
| `services/api/app/services/investigation_tools.py` | authentication_events的IPv6空值过滤合同修正 |

| Agents文件 | 本轮选入意图 |
| --- | --- |
| `services/agents/app/agents/attack_path_agent.py` | 采用本Run的Case路径或Alert图，保来源/适用范围 |
| `services/agents/app/context/attack_context.py` | 独立writer prepare、reader GET、有界摘要及工件 |
| `services/agents/app/context/bundle.py` | 保留已发布UEBA接线，加入链图读取及可信入口回执 |
| `services/agents/app/investigator/bundle_prompt.py` | 向原模型输入追加有界材料 |
| `services/agents/app/investigator/deep_investigation.py` | **单独构造的candidate05＋链图摘要变体**，不是复制当前混有C2的整文件 |
| `services/agents/app/investigator/ledger.py` | 原事务结果内保存三类链图工件 |
| `services/agents/app/investigator/orchestrator.py` | 默认调查预取及本Run工件交接 |
| `services/agents/app/investigator/tools.py` | 单IOC请求`type → ioc_type`字段修正 |
| `services/agents/app/orchestrator/report.py` | Router模板报告呈现上下文 |
| `services/agents/app/orchestrator/router.py` | Router领域调用及Run工件采用 |
| `services/agents/app/tools/graph.py` | 原图工具reader身份及tenant头适配 |
| `services/agents/app/workers/fused_alert_consumer.py` | Kafka分诊前准备、可信回执、显式Case/Alert锚点；当前差异不包含关闭原因文案 |

除Deep变体外，其他18个文件均逐字匹配各自最新保存的功能批次来源：先functional，再链图，最后Kafka增量覆盖其中4文件。链图旧副本中的3个文件被Kafka版本后继覆盖是预期现象，不修改原manifest假装旧副本也是最新。

## 4. Deep混合文件已拆出可审差异

当前工作区Deep还含旧C2的摘要、tracker/governor、预算、循环及nullable usage改动。本轮保留工作区，在审查副本中以已匹配candidate05来源manifest的Deep原件为底，只在`_summarise_alert`返回前追加：

```python
from app.investigator.bundle_prompt import format_bundle_prompt_append

context = format_bundle_prompt_append(getattr(state, "context_bundle", None))
if context:
    parts.append(context)
```

完整可审补丁为该目录的`deep-chain-only.patch`。本地核对“移除这段新增摘要后，副本与candidate05原件完全一致”；这不回退工作区、不删除旧C2，也不采用其未终审行为。

新增变体有实际差异，因此仅复用一个必要的既有用例：`test_attack_context.py::test_bundle_summary_reaches_manual_append_and_deep_user_without_extra_call`。独立进程明确装载**审查副本中的Deep**，禁用socket连接及OTEL发送，没有模型/HTTP/数据库，结果为**1 passed**。报告与执行器分别保存在`deep-summary-contract.json`、`verify_deep_summary.py`；pytest已有导入重写警告与可选OTEL exporter提示保留，不为它们扩依赖安装。

该用例只证明摘要确实到达变体的模型材料，不证明19文件组合、Deep预算/分类、真实模型质量或发布包通过。19份候选Python语法解析通过，也只属于静态检查。

## 5. 明确后置的7个工作区差异

下列文件没有复制到候选目录，原件仍在工作区。旧C2失败、157项直接测试及未终审事实继续由[原回执](integrity-graph-correctness.md)维护，不重调输入或重做其质量专项。

```text
services/agents/app/agents/auto_triage_agent.py
services/agents/app/agents/investigation_agent.py
services/agents/app/agents/triage_agent.py
services/agents/app/confidence/scoring.py
services/agents/app/core/cost_governor.py
services/agents/app/graph/runner.py
services/agents/app/llm/tool_loop.py
```

第一项是未关闭原因文案，其余六项为旧C2；Deep中相应C2差异也没有纳入本次变体。已部署I2普通结果/用量保护来自candidate05父版本，保留为基线，不能将排除后续C2误说成排除了I2。

## 6. 配置、依赖与下一步剩余工作

拟选差异仍沿既有合同：API/Agents的`AISOC_ATTACK_CONTEXT_ENABLED`、Agents的API地址、reader及独立`AISOC_INVESTIGATION_PREPARE_KEYS_FILE`，映射只读挂载且权限0600或更严，writer需`alerts:write`；reader仍为原只读身份。review-only/shadow、预算/unknown与原worker保护保持。人工Case入口和原PG/Neo4j/APOC复用，不新增PG迁移。

API/Agents的pyproject/lock仍匹配既有保存来源；本地Conda统一环境里的SQLAlchemy覆盖不属于服务镜像依赖变化。Fusion、UEBA、enrichment、TI、Actions不在这19文件内，不用本轮候选覆盖其已发布功能或现有full/infra overlay。

真正准备构建时，还须以记录的API/full Agents父镜像确定实际构建输入，核保留full bundle/配置；旧`Dockerfile.integrity-complete-agents`会COPY大量C2差异，不能直接从当前工作区套用。现有本地材料缺full纯bundle的字节证明，也没有新查21运行态；这些是构建/发布准备时需处理的明确事项，不新增全量冻结或模型矩阵。

下一步的具体工作已经缩小为：**对这个19文件组合及Deep选择做必要审查和组合核验，再形成真正的构建配方与阶段发布包。** 本轮审查副本未构建、未部署，不批准常驻启用或追认旧质量。机器摘要见[本轮清单](../handoff/investigation-stage-closeout-20261022.json)。

## 7. 本轮结束独审

未参与实现的stage_closeout_audit只读对照源码、candidate05/各批manifest、机器摘要与原任务，限定**ACCEPT，0项本轮阻塞**。确认26项差异（24修改＋2新增）正好对应19候选＋7排除；18份原样复制、Deep仅追加摘要，工作区hash保持，15任务/5勾一致。独审所查420条本地文件链接0缺失。

审查发现导入副本生成了一个未列清单的pyc缓存：root仅移除本轮生成的该缓存，并在runner导入前设sys.dont_write_bytecode=True；审查后只读确认files恰好19份.py，运行源码hash未变，没有为缓存修正重跑业务用例。原测试1 passed及警告保留。

本结论只覆盖责任收口及可审源码，不批准真实组合/构建/发布、旧C2、常驻或整体质量；原5/15保持，下一步按第6节处理实际组合与构建范围。

## 8. 后续组合与构建准备

同日用户继续后，已另补[候选组合与构建回执](investigation-candidate-build-20261022.md)：定向核父镜像与full bundle、UEBA保持，隔离19文件组合100项直接合同及router登记通过，最小context/配方已准备。前文缺full字节/未组合为本轮收口当时事实，不回写原审查manifest。实际镜像尚未构建或部署，原C2/质量及5/15保持。
