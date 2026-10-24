**main评审来源（实施前快照）：** 本分支从main `541511c`建立，采纳依据见[意见复核与计划](review-response-20261024.md)。该报告是当时评估阶段，最新实施状态以下方本轮结果及实施记录为准；旧调查469e9467已合main，仍作历史来源。

**2026-10-24 main统一审计：** 已整合调查469e9467与数据评估；[双方建议、数据湖协作及续接顺序](../operations/data-investigation-integration-audit-20261024.md)继续作为分工依据。保原设计/源码，v2未启用；共享工具兼容、评测口径与接缝问题未修。

# 调查新版：开发、进度与评审入口

**本轮最新结果：** 前置M1纯绑定、I1正文局部降级、I2完整messages预算分别通过后，本块先补规格/预期/strict，再完成[共享网络场景卡](scenarios/network-observation.v1.json)、独立v2查询应用及36项直接合同。02批新Run的真实HTTP→CH→PG接缝通过：1条命中、两对照排除、3事件/6工件独立读回，模型0；临时进程已停、新身份NOLOGIN并撤权。01批PG字段假设失败原样保留，映射修正后采用新批次，未重放。见[接缝回执](../operations/investigation-v2-query-seam-20261024.json)及[实施记录](../operations/unified-investigation-implementation.md)；未参与实现者复跑36项并只读核PG/清理后限定ACCEPT、0必须修。下一单项为M6固定查询/有限事实路径，先合同/预期；M5按需能力另验。正式M8入口、Deep整环、同版交付和Case继承仍待做，tasks2.2/2.3未勾，change不归档。

更新：2026-10-24。活动分支：`codex/investigation-review-20261024`，基于main `541511c`；原调查`codex/investigation-working`已合main作为来源。普通项目目录逐阶段开发、提交并推送；旧.local工作树已移除。其他机器拉取当前分支即可阅读本页及全部相对链接，无需原机器`.local`。

## 从哪里开始看

| 要看什么 | 仓库中的位置 |
| --- | --- |
| 完整业务设计 | [主设计](../architecture/investigation-planning-design.md)：第1节业务分层，第1.10节旧版/新版隔离，第12.7节下一步顺序 |
| 相对开源改了什么 | 主设计第16节：开源、当前实际、目标三方对照，原因、具体细节及两个例子 |
| 当前进度和逐步过程 | [逐模块实施记录](../operations/unified-investigation-implementation.md)，先看顶部最新状态；[项目进度](../../PROGRESS.md) |
| 规范、任务、独立审阅 | [设计](../../openspec/changes/continue-isolated-investigation-v2/design.md)、[规格](../../openspec/changes/continue-isolated-investigation-v2/specs/investigation-v2/spec.md)、[任务](../../openspec/changes/continue-isolated-investigation-v2/tasks.md)、[审计](../../openspec/changes/continue-isolated-investigation-v2/audit.md) |
| 新版代码 | [Agents v2](../../services/agents/app/investigation_v2/README.md)、[API v2](../../services/api/app/investigation_v2/README.md) |
| 数据/执行/模型的可共享回执 | [ClickHouse](../operations/unified-investigation-clickhouse-20261023.json)、[M3](../operations/unified-investigation-m3-20261023.json)、[M4最终](../operations/unified-investigation-m4-20261024.json)、[版本隔离](../operations/investigation-v2-isolation-20261024.json) |
| 本轮前置三块回执 | [M1纯绑定](../operations/investigation-profile-contract-20261024.json)、[I1正文降级](../operations/investigation-optional-excerpt-20261024.json)、[I2完整请求预算](../operations/investigation-request-budget-20261024.json) |
| 新版真实查询接缝 | [共同场景卡](scenarios/network-observation.v1.json)、[公开回执与失败/清理](../operations/investigation-v2-query-seam-20261024.json)、[可共享受控探针](../../openspec/changes/continue-isolated-investigation-v2/probes/v2_query_seam.py) |
| 首批模型失败及历史问题 | [M4首批失败回执](../operations/unified-investigation-m4-20261023.json)、实施记录的M4调试表、[历史问题总登记](../operations/upstream-issues.md) |

## 当前做到哪里

| 模块 | 实际状态 | 不能扩大成的结论 |
| --- | --- | --- |
| D1—D3数据前提 | 3条合成历史事件入CH，1条告警落PG，来源UUID/租户/实体/窗口关联已验 | 不是全量采集或告警自动入湖；不证明恶意/授权 |
| M1/M2 | 冻结范围/问题合同及网络逐条查询已验；本块新v2独立HTTP/CH接缝1次通过 | 当前仅有限explicit_set/网络观察，不是Case入口已接 |
| M1业务profile增量 | 纯绑定11新＋原scope8项及独审通过，保完整/所选/遗漏成员与交付归属 | 不等于已认证Case、实际解析/继承/启动或接执行器 |
| M3 | 新v2一次工具调用的预留/完成已提交；新Run3事件/6工件独立读回，profile作为已核输入留存 | 未开放多writer/通用恢复，不改旧预算/unknown，不等于完整业务profile执行器 |
| M4 | Q1/Q2/Q5限定8例原文/采用/交付通过；选定23484tokens | 不是完整恶意/授权或全调查质量通过 |
| I1/I2材料消费接缝 | 可选正文局部缺口保留；三处共用完整消息12KiB计量并明确超限结果，直接合同和独审通过 | 未重验真实模型质量；没有自动分组或让10条超限材料被消费 |
| M5 | M5.1问题/查询纯合同通过；M5.2仅部分准备，完整模型步骤/循环未完成 | 新版Deep整环未完成，不能称调查v2已运行 |
| 隔离迁移 | 新包隔离合同保留；本块只新增独立v2应用，旧应用未注册新路径 | 新路径证据取本块02批，不沿用历史HTTP冒充 |
| v2 HTTP、M6—M9 | 独立loopback查询应用已实测并停止；M6策略/M7同版结果/正式M8入口/Case衔接仍待做 | 没有切换旧服务、部署新版、自动建Case或启动Case调查 |

代码隔离的保存提交为`74d4d90`；后续文档/入口整理有独立提交，以分支`git log`为准。`v4`是设计修订号，`v2`是新执行器代际。旧调查版本继续保留，需变化的旧函数复制所需部分到新版修改，不能直接改旧函数/注册。

## 仍有哪些问题和边界

| 问题 | 原因与已有处理 | 后续处理 |
| --- | --- | --- |
| 正式v2业务入口尚未交付 | 新路径已在独立受控应用实测；API负责tenant及全局bounds，Run/问题scope仍由可信caller与M3负责 | M8另验持久启动授权/显式新入口；不回挂旧v1，不把本次查询测试当正式发布 |
| M5.2/循环未完成 | 已有基础模块不代表模型选择→工具→下一轮回答已走通 | 按主设计12.7先profile合同，再逐小步补齐并测试 |
| 数据只能支持有限网络事实 | 当前来源outcome为unknown，缺认证/进程/业务批准资料 | 保性质unresolved、授权unknown；需要其他判断时先补实际来源/字段 |
| 模型结构/语义会失败 | 首批7回复候选全拒绝；后续02批18回复中5个失败保留，含枚举、依赖遗漏、对象称谓、query冒充source等 | 提示/引用限制已在选定样例修订通过；保持严格采用，不做全模型可靠性承诺 |
| 安全降级不等于答对 | 拒绝错误候选能保护交付，但未必产生有用判断 | 原文、程序采用、最终交付分开评价；不能全partial就放行 |
| Case整体/继承尚未实施 | 旧Case投影最近3条，不足以代表全成员 | 新版启动时冻结全成员，至少4成员/早期反证/同源去重场景先验 |
| 统一结果版本未交付 | 旧Run状态与调查完整度不同，多个最新字段可能不同版 | M7同版manifest/MD/读通知；旧结果保持原格式 |
| 旧失败、unknown和unpriced保留 | 当前新包不能追认旧质量、释放未知预留或推断费用为0 | 不重放旧Run、不清账，后续按独立授权处理 |
| IOC OpenSearch尚未推进 | 当前首场景先验证ClickHouse事实来源 | 继续后置，未来只作有来源的IOC佐证 |

M4的完整计数、失败trial/原因、修订和采用边界在已提交的回执及实施记录中；原分支旧任务5/15属于当时历史，main旧迁移已归档；不能以本页或Git推送当新版完整模块验收。历史模型/工具原始捕获、私密配置和冻结原件属于本机证据保留，不是阅读设计/进度/问题的前提，也不会作为开发工作树分享；提交的摘要包含结论、失败、版本hash及限制。

## 正常Git协作

已有仓库的其他机器可使用：

```sh
git fetch origin
git switch codex/investigation-review-20261024
git pull --ff-only
```

直接在该项目目录开发；调查代码、设计、测试、进展和问题按阶段提交/推送远程调查分支。密码密钥、个人环境和本机适配只放被忽略的`.local`，不在其下创建活动分支/工作树。

后续评审通过后，按普通Git流程合并到`main`或其他目标分支；不依赖worktree专用路径，不需要复制本机目录，也不夹带Windows适配分支。本轮用户已要求将`469e9467`合入`main`供各开发分支同步；合并不代表部署或完整新版验收。

跨机器测试使用对应平台的[Agents依赖](../../services/agents/pyproject.toml)/[API依赖](../../services/api/pyproject.toml)与自己的虚拟环境；本机`.venv`不入Git。纯合同测试可按实施记录的明确文件执行；真实PG/CH/模型步骤另需该机器的私密配置与隔离身份，不自动重放历史试验。
