# 数据准备、评估与调查：main整合审计及协作交接

2026-10-24。用户要求先合并最新版且不影响双方原开发设计，再做总审计，给两个分支分别提出意见并统一数据湖等交叉工作。本页是双方同步main后的统一续接入口，保存实际进度、发现和协作分工；只做源码/回执审查与断网测试，不替任一分支实现或修改原业务设计。

## 1. 已合并基线与审计范围

| 对象 | 已纳入main的来源 | 合并结果 |
| --- | --- | --- |
| main原基线 | `09de7d05` | 旧迁移限定核销及归档保留 |
| 数据评估 | `cec5ea98`，原工作区基线`65645a55` | 已提交19文件，包含原E0/E1工具、测试、回执及[本轮数据审计](data-evaluation-audit-20261024.md) |
| 调查 | 用户指定的最新`469e94679211d071e39d9c9e73bd316307a2695f` | 包含`74d4d904`独立v2内核及后续跨机器交接 |
| 数据合并 | `c41db518` | 保留数据评估现状及待处理问题 |
| 调查合并 | `5c1202b5` | 两条分支均在main历史中；新版未启用，旧业务入口保持 |

调查27份新增Python源码/测试和2份包README与`469e9467`逐字一致；数据新增8份Python工具/测试保持`cec5ea98`版本。没有把合并当业务改造，也未修下文已知问题。旧services运行源码、依赖和入口不变；新HTTP路径尚未注册，合并不会切换旧调查。

原调查分支在旧restore change中追加的六份记录和22条新Requirement，已完整转入[独立v2 change](../../openspec/changes/continue-isolated-investigation-v2/proposal.md)。调查合并未更改原迁移archive；数据E0的历史追加另保留。历史5/15、当时不提交/不推送等只描述原批次，不覆盖main已归档事实或用户本轮同步授权。该调整只解决当前/历史归属，不改双方业务设计。

主工作区另有20展示及暂停规划的34份未提交文件，全部保留；5份共享文件保留原本地插入，另29份字节hash一致，没有混入上述提交。私密.local材料和其他机器本机适配不入Git。审计结论只覆盖两个模块的集成、已交付范围和协作接缝，不是全产品/全部标书或新版完整流程验收。

## 2. 对齐后的真实进度

| 工作线 | 目前实际成果 | 尚未完成/不能外推 |
| --- | --- | --- |
| 数据E0 | 72条/36对四分类语料、输入/答案隔离、原评分器离线复用、旧probe轨迹核对 | 有A1/A2遗漏；离线导入不能证明真实模型质量 |
| 数据E1 | 原Replay/分诊SDK有界运行器、外部上下文排除、实际请求正文离线预检 | 0真实模型；AWS-01输入截断，尚无本轮模型成绩 |
| 数据E2—E4 | 原数据分支仍未交付这些完整阶段 | 调查分支已补部分网络数据前提，不能继续写成全仓没有入湖/查询工具，也不能直接勾E2/E3完整完成 |
| 调查D1—D3 | 既有回执：3条合成网络事件入ClickHouse、1告警入PG，来源UUID/租户/实体/窗口关联 | 非全量采集、非告警自动入湖；不判连接成功、恶意或授权 |
| 调查M1—M3 | 范围/问题、首个网络记录查询、原子留存及共享额度有限通过 | 旧位置真实HTTP/PG回执不等于隔离后新v2 HTTP已验 |
| 调查M4 | network_observation.v1/Q1,Q2,Q5的8例原文/采用/可读有限通过，选定23484tokens | 开发02共18回复52185tokens、5失败保留；非完整恶意/授权或全调查通过 |
| 调查M5及后续 | M5.1纯合同通过；M5.2仅部分observer准备 | 模型步骤/Deep整环、M6—M9、同版发布和正式入口未完成；v4告警/Case分层仍待讨论定案 |

入口：[数据原设计](data-evaluation-design-20261023.md)、[数据回执](data-evaluation-execution-20261023.md)、[调查进度与问题](../investigation/README.md)、[调查主设计](../architecture/investigation-planning-design.md)、[逐步回执](unified-investigation-implementation.md)。双方继续各自E/M编号，不把它们重新合成一棵开发任务树。

## 3. 需要处理的问题与承接方

以下均为未修或尚未交付，不因合main解除。P2为继续相关评测/使用前处理的正确性问题，P3为平台测试问题；设计待议和实现缺口另标，避免把所有未完成事项都叫代码bug。

| 编号/性质 | 事实与影响 | 后续承接 |
| --- | --- | --- |
| A1 / P2 | 原MCC排除非法预测；构造36正确+36非法输出，accuracy=0.5、MCC=1.0。新离线桥继承该问题，单项分数可误导 | 数据评估：修完整分母或暂时停报MCC，补反例；详见[数据审计](data-evaluation-audit-20261024.md) |
| A2 / P2 | verdict_live只接受两对四条，一对方案不可执行；换成原语料四个不同对并重算manifest仍被接受，单条原件锁定不等于整批选择冻结 | 数据评估：按有界批次支持完整对、冻结选择及anchor/参数，运行器仍不读答案 |
| A3 / 已知输入阻塞 | 旧分诊raw_event最多10行，AWS-01缺来源IP/归属及审批字段；发送前已阻断 | 旧分诊/数据评估共同讨论其输入合同；不把它写成v2 EvidenceView缺陷，不顺带改新版视图 |
| C1 / P2 | investigation_fixture.py:155直接调用Path.is_junction，Python3.11没有该方法；两服务pyproject仍允许^3.11，工具未另声明最低3.12，故按3.11运行的夹具读取路径会失败 | 共享工具维护方（数据线主责、调查线复核）兼容运行时或明确工具下限；保留原junction拒绝语义，不借兼容关闭校验 |
| C2 / P3 | test_investigation_fixture.py:101把IPv4映射IPv6写死为十六进制字符串。本机Python3.12.14返回点分文本，3事件的地址对象/字节相同但断言失败 | 共享工具维护方下批按地址值/packed比较；本轮保留原测试与失败 |
| I1 / 实现缺口 | v2 caller预留/api/v2/investigation/query，而旧应用未注册；历史真实回执对应原位置 | 调查线继续M5独立受控v2接缝与后续M8；数据线不得回挂旧v1或绕过scope来制造通过 |
| I2 / 设计待议 | v4 profile、Case全成员继承、自动关联/启动是设计目标，M5整环和M6—M9尚未交付 | 调查线按主设计12.7原顺序续接；不因数据评估需求提前重构/切换旧版 |
| X1 / 评估接缝 | 四分类评分和旧probe四类文件核对不能直接读取/评价v2 PG工件、有限网络事实及程序采用 | 数据线做小型只读适配和期望断言；调查线提供已有scope/query/committed refs与原文/采用/交付输出，不另造运行账本 |
| X2 / 场景用途 | 当前网络fixture的告警raw_event.telemetry包含匹配事件正文，适合来源关联/查询范围验证，不能据此证明“模型必须查工具才知道事实”或工具增益盲测 | E3由双方另定初始告警不含待查决定性材料的对照；保留原fixture和旧判据，不把原D1测试改题追认 |

C1依据[Python 3.12官方Path.is_junction说明](https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.is_junction)（该方法新增于3.12）与当前源码。此项为静态兼容性结论，未安装/运行新3.11环境；C2为本机直接复现。A1/A2复现步骤与数值在原数据审计中，均非真实模型成绩。

## 4. 统一复用与分工：数据湖不是再开发两套

以现有代码为共同起点，不移动或重写模块、不更换双方算法/编排，也不新增常驻数据服务或评测数据库。

| 能力/现有落点 | 后续主责 | 另一方交接/复用 |
| --- | --- | --- |
| [调查网络fixture](../../tools/testdata/investigation_fixture.py) | 数据准备线维护可复用场景、确定性ID/时间/expected及离线校验 | 调查线定义来源字段、可查询问题和不能判断的业务边界 |
| [单批写湖与独立读回](../../tools/testdata/lake_fixture_probe.py) | 数据准备线维护有界投放工具，复用原Fusion LakeWriter | 调查线声明查询所需字段/索引与来源含义；不再另造写湖器或在模型工具中自动写数据 |
| alert_scenarios/alert_kafka/observe_results | 数据准备线维护生成、正式告警wire、投放及结果观察 | 调查线复用既有Alert/Run关联；告警raw_event里的telemetry不自动变成湖记录 |
| [v2 API records](../../services/api/app/investigation_v2/records.py)及[受限caller](../../services/agents/app/investigation_v2/activity_records.py) | 调查线维护查询/身份、绝对窗口、原文界限和结果合同 | 数据线按真实查询合同准备目标/干扰/边界资料，不以expected替代查询返回 |
| scope/evidence_view/analysis_adoption/execution_* | 调查线维护范围、来源版本、引用、程序采用及共享额度/持久留存 | 数据线只读实际已提交工件和回执，不修改业务状态、预算或伪装新调用 |
| verdict_eval/live/context、verify_tool_handoff及后续v2读取适配 | 数据评估线维护盲测、覆盖、错误/弃答/unknown、真实输入核对和比较 | 调查线提供实际可观察对象/字段，保原文、采用、交付三层；不为测试通过修改答案或返回 |

其中fixture和lake_probe是调查分支已经贡献到tools/testdata的共享资产；上述是后续维护/对接分工，不改写贡献或宣称数据分支原先已经实现。现有数据E2计划先做process_activity，应对齐为优先复用已完成的网络fixture与activity_records；进程/认证扩展需实际来源字段就绪后另做。此处是避免重复的续接建议，不改调查现有network_observation设计。

### 4.1 写湖与查询的实际边界

- E0/E1给定材料评测不需要写湖。网络E2复用现有三事件目标/不同目标/窗外对照；新增场景确需资料时才有界写入，不开启常驻全量写入。
- 原lake_probe以独立writer/reader、一次flush、既有47列及raw/OCSF原文字节hash核对写入，再用真实谓词核唯一匹配、排除干扰。不能把写入返回、exact-ID读回或模型说查到单独当整个查询闭环。
- 真实查询属于调查工具；数据准备工具不接管scope或拼一条更宽SQL替代业务查询。新v2 HTTP未就绪时可做离线适配/合同验证，不能把原M2路径当新版已可运行。
- unknown写入/调用不自动重试，派生夹具/已有工件回放明确标离线复用。默认不清旧资料、释放旧unknown或重跑旧输入。

### 4.2 共同交接字段，不另造身份或hash含义

后续交接可用一份普通文件映射现有字段；不要求本轮改API/DB schema。

| 共同信息 | 现有来源/含义 |
| --- | --- |
| 场景和原件版本 | fixture_kind、generator version、fixture_manifest_sha256及语料hash；二者分开 |
| 测试批次 | fixture manifest.run_id是批次字符串；不得当业务Run UUID |
| 身份和关联 | tenant UUID、输入alert_id、PG canonical Alert、各event UUID、source_event_ids逐项映射；Fusion追加的来源Alert引用与湖事件UUID分别说明 |
| 实际调查身份 | 真实Run UUID、scope_revision/hash、policy_ref、question/member/subtask；沿调查合同，不复用E1 opaque finding_id冒充Run |
| 绝对窗口和实体 | UTC start-inclusive/end-exclusive、实际hostname/source/dest/port/protocol及字段出处；不把相对hours或语料写作日期当事件时间 |
| 原文hash | raw_payload/ocsf_json各自原始UTF-8字节hash、完整/保留字节数、截断说明 |
| 来源版本与视图 | API完整projection content_hash、EvidenceView source version和snapshot_ref分别保留；不能把原文hash或manifest hash互换成这些版本 |
| 独立预期 | expected文件/答案hash仅评估方读取；运行器、模型和来源正文不带期望结论/工具答案 |
| 实际观察 | 查询status/available/空/截断、实际参数、committed事件/工件refs、模型请求/原回复、程序采用、最终交付及usage unknown |
| 执行模式 | offline_import、offline_http_stub、已有真实回执复用、new query、real model分别标识，不能混成同一个分母 |

raw/OCSF字节hash与API完整投影hash是不同对象；EvidenceView中的事件版本校核后绑定该来源内容，snapshot_ref还包含本次证据视图。相同来源重复获取不是独立印证；同身份异文、未交付版本、空或缺源保留为冲突/缺口。

### 4.3 评分保持两条线

1. 旧分诊四分类继续按原72条语料与模型实际可见输入评价；先处理A1/A2/A3，分别记原模型、程序采用及错误/弃答/缺失。
2. 新v2先按有限网络合同核Q1来源观察、Q2精确关联、Q5查询覆盖；连接成功、行为恶意、业务授权无来源时保持unknown/unresolved，不能硬转TP/BTP/FP标签。
3. 后续E3补查询选择、参数准入、真实结果进入下一请求、模型引用、程序采用和最终交付逐层断言；旧verify_tool_handoff仍只核旧probe文件，v2适配读取已有M3工件引用，不把进入请求当语义答对。

## 5. 两个分支各自下一步

### 数据准备/评估分支

1. 同步main后先读[原审计A1/A2/A3](data-evaluation-audit-20261024.md)及本页。先解决评分和批次冻结，补失败反例；先把离线工具正确性做实，不默认跑72条真实模型。
2. 共享工具先处理C1运行兼容/C2地址值断言；补本机/目标Python环境的直接验证，避免双方各自适配。
3. 复用原network fixture/probe，增加普通身份映射与只读v2工件→expected比较。优先读取现有公开/授权材料，标清历史、离线和新执行。
4. E1仅在实际输入完整的批次做有限首次模型评测；E2/E3新真实闭环等待调查独立v2受控接缝及共同预期就绪，再扩场景和E4回归。

### 调查分支

1. 同步main后继续原v4讨论与第12.7节顺序；现有源码/政策不因本审计改成旧四分类评测架构。
2. 先确认profile合同，再逐小步补M5.2模型步骤/Deep循环及独立v2接缝，每块直接测试；正式M8入口、M7同版交付等按原依赖顺序，不能以本次合并放行。
3. 复用tools/testdata共享写湖工具；新增数据源时先提供所需字段、来源语义、查询参数与可判断/未知边界，由数据线补fixture和投放，不在调查工具里承担测试数据生成。
4. 向评估侧提供已提交query/input/raw/adoption/delivery refs、scope/policy/snapshot和unknown状态；Case继承/跨告警/其他领域按原规划推进，不让测试替身替代新入口验证。

### 第一项协作交付

先共同确认“现有网络观察夹具→现有v2查询合同→已提交材料→有限期望断言”这一小段映射文件及一例预期；离线与历史回执可立即用于适配。真实新版调用必须等其受控入口就绪，不重放旧unknown，不为共享而重写两个内核。各自修复和后续模型/业务测试在自己的开发分支及适用change中记录。

## 6. 本轮检查与未通过项

| 检查 | 本轮结果 |
| --- | --- |
| 原数据工具套件 | root断网96 passed、39 subtests passed；3既有UTC弃用warning |
| 新调查Agents合同 | 未参与实现者独立断网85 passed |
| 新调查API合同 | 同一审阅者独立断网8 passed；未运行opt-in真实PG |
| 合并后整套tools/testdata/tests | root断网输出：112 passed、58 subtests passed、3 failed（同一测试内3个事件subTest，均C2 IPv6文本断言）、3既有warning；退出1，不能报全绿 |
| 合并结构与设计保持 | 数据/调查源文件对照、旧入口未改、归档保持、22条v2要求完整、Git无冲突；独立候选窄审限定ACCEPT/0合并必须修 |
| OpenSpec/文档 | 独立v2 change strict通过，候选607个本地文档链接无缺失；最终新增审计入口另窄核 |
| 真实业务/模型/环境 | 0新增模型、PG/CH业务请求、Kafka发送、湖仓写入或部署；历史回执只读复用，不重新验收生产 |

断网工具命令：`PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 <项目Conda>/bin/python -m pytest -q -p no:cacheprovider -p pytest_asyncio.plugin --basetemp=/private/tmp/socai2-integration-tools-tests tools/testdata/tests`。各测试套件有不同用途，不叠加成产品通过率。已知问题按用户要求原样保留供两分支接续。

本页由root作总审计与协调记录；结束独立文档复核结论另记[本轮audit](../../openspec/changes/continue-isolated-investigation-v2/audit.md)。该复核只检查事实、分工和设计保持，不等于修复A1/A2/C1/C2或放行新版业务。

## 7. 其他开发分支如何同步

本页随main正常提交同步。各机器先保存自己尚未提交的开发工作，再在自己的分支正常合入main：

```sh
git fetch origin
git switch codex/data-evaluation  # 调查开发则使用 codex/investigation-working
git merge origin/main
```

如main本身可快进，可使用`git switch main`后`git pull --ff-only origin main`。后续意见从本页及各自主设计读取，不复制其他机器.local目录，不要求切换个人模型/数据库配置，不自动启动服务或历史测试。源分支此后若又有新提交，按新版本另行比较；本轮调查范围固定到用户指定469e9467。
