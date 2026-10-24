> 2026-10-24追加：最新代码审查见[分支审计](data-evaluation-audit-20261024.md)。96测试/39子项复跑通过，但新增发现MCC非法分类边界、完整配对/批次冻结问题；连同已知输入截断均未修。原限定ACCEPT仅为当批范围，本次按用户授权保存并合main不追认完整闭环。

# 数据与评估模块分步执行回执

最新：E0已完成；E1运行器与离线预检完成，真实模型评测尚未执行。预检发现分诊raw_event的10行上限截掉AWS-01关键材料，已按用户要求停在输入设计讨论点。21起初SSH超时，用户告知恢复后只读SSH确认成功，不能继续以网络为当前停点。详见本页E1记录及[设计第9节](data-evaluation-design-20261023.md#9-e1预检发现与待讨论的小改动)。

2026-10-23。用户要求评估设计并继续推进，按[设计](data-evaluation-design-20261023.md)先实现可独立工作的离线数据/评分/轨迹核对；登录合同及调查设计修改另讨论。工作在`codex/data-evaluation`隔离工作区，主工作区原有文档/页面工作未复制或覆盖。

## 实际交付

- `tools/testdata/verdict_eval.py catalog/prepare/score`：固定原72条/36对四分类语料；五字段可见输入及opaque ID，答案/配对单独保存，hash及原件一致性核对，0600及拒覆盖。复用现有分类映射与API vendored Replay评分器，不修改业务源码或另写评分公式。
- 分类评分是`offline_import`，不证明模型实际调用或输入已可见；缺失/错误/弃答/未知分类分开，部分批次不报headline，未知usage不填0；实际prompt未核时不报幻觉率。自动关闭阈值显式传入，四分类命中指标不冒充实际关闭安全率。
- `tools/testdata/verify_tool_handoff.py`：同tenant/Run/Alert内核模型tool_calls→执行→原返回/渲染→后续真实请求的ToolMessage。缺原生执行call_id时使用完整顺序及参数签名，歧义未核，不凭名字或工具数量判通过。报告只有hash/身份/状态/引用，无原始正文。

## 分步测试与结果

1. 先完成语料与答案隔离，6项直接测试通过，再加入评分接入。
2. 首次评分接入出现10失败/6通过：导入`agents`包触发运行时依赖而失败；只修工具加载方式，直接读取纯分类模块，未改业务/依赖。之后16项通过，补离线无网络/不改模型环境检查后17项通过。
3. 轨迹核对器17项直接测试通过，包含同Run防串、重复参数、无后续请求、返回/渲染不一致、失败仍进入下一请求等。
4. 实际CLI离线准备72条成功。人为“全部TP”的评分器对照得到普通准确率0.5、平衡准确率0.25；无观察对照为missing72、metrics=null，没有补成100%弃答。此为评分程序自检，0模型调用，不是本系统研判质量成绩。
5. 复用上批原始trace：8个执行回执，6 unavailable/2 error；8份返回与已记录的后续请求正文内ToolMessage一致。模型提议共10个tool_calls，其中2个无执行回执，明确列未配对，不计执行。model-request来自发送前hook，通用核对器不保证提供方成功接收或模型语义采用；没有成功有效补证评分，也没有根据此记录确定底层湖查询失败根因。
6. 结束独审发现部分费用缺失时原评分器仅累加已知项，可能将不完整总费用显示为0。本工具现对measured/estimated费用分别计未知数量，任一缺失则总值null，完整显式0仍为0；新增直接回归测试，评分原实现保持。修后数据/评分18项、轨迹17项通过。
7. 最终整套`tools/testdata/tests`：79 passed、39 subtests passed，3项既有pydantic UTC弃用warning，无跳过。该数包含既有44项，不能全部称本批新增。测试汇总及静态核验记录保存在本批verification目录。
8. 4份使用/设计文档的19个本地链接与围栏通过；24个生成文件均被Git忽略且为0600，业务及部署目录无改动。OpenSpec strict、git diff --check通过，任务仍5/15。

离线CLI和净化轨迹报告保存于隔离工作区`.local/verification/data-evaluation-20261023/`，全部生成材料保持Git忽略。费用修正后追加`score-all-tp-v2.json`和`score-no-run-v2.json`，首版保留。此前8工具结果的原始调用及失败证据仍在主工作区的原批目录，未重调/改写。

## 范围与后续

E0离线工具已完成；E1给定证据模型实测、E2真实工具成功查询、E3模型选择及语义采用、E4回归比较尚未实施。已核登录工具缺主机/认证类型/结果筛选及必要返回字段，湖schema已有部分基础字段；需要讨论后改工具合同，不能靠造成功返回通过。

本批0新模型、0业务/生产查询、0湖仓写入、0业务源码/配置/部署修改、0Git提交/push；原restore仍5/15。最初普通文件命令写worktree被沙箱拒绝，文件未改变；随后用apply_patch完成，OpenSpec strict在设计记录落盘后通过。

未参与实现者`eval_increment_audit`结束独审限定ACCEPT、0剩余必须修项；费用unknown发现及修复保留在本回执。最终测试、静态核验见本批verification目录，14份选定源码/文档及hash manifest保留于`.local/versions/data-evaluation-20261023/`；该结论仅覆盖E0，不代表模型研判或调查质量通过。

## E1：工具接入与离线输入预检

用户在指标说明后要求继续，按预先固定的VRD-AWS-01/03两对共4条推进。新增`verdict_live.py`和`verdict_context.py`；前者复用原Replay/worker/Shadow，后者只隔离外部上下文来源。业务源码、角色pin、temperature0/512/JSON合同保持；runtime不读答案文件，只核固定hash的72条可见材料及所选4条。独立进程清空业务DB/Kafka/Redis配置，其他连接拒绝；预检模式全部禁网。

逐步检查：

1. 上下文adapter 3项独立进程测试通过，原接口/返回类型、snapshot行为、外部来源disabled/not queried及不联网已核。
2. runner最初5通过/4失败，原因是工具将raw-HTTP补/v1逻辑误用于SDK原路径；只修工具预期路径后9项通过。未联网，旧失败保留。
3. 独审指出usage=null会丢最终回执、重算manifest可伪装改过的输入、原未知分类可被业务默认TP后三项。工具分别补unknown容错、可见原件固定hash/逐行对照、原输出有效性与程序采用分列；未修改原parser。补原请求叶字段可见性、缺材料真实发送阻断及预检明确替身标识。
4. 新工具17项直接测试通过；最终整套96 passed、39 subtests passed，3项既有pydantic UTC弃用warning。其中79项为已有E0/迁移工具测试，不算本批新增。HTTP替身检查原worker实际路径，包括503、畸形JSON、usage缺失/null、未知原分类及业务无写。
5. CLI准备4条，并完整预检4份原SDK待发送正文。预检使用HTTP替身，不是模型答复；`source_mode=offline_http_stub/new_model_requests=0/ready_for_live=false`。首版保留，v2补单例transport标识与源码hash。程序采用观察存`preflight-observations.json`，不作为模型成绩。

| 案例 | 可见叶字段 | 缺失字段 | 真实评测状态 |
| --- | --- | --- | --- |
| AWS-01-B，有审批的管理员角色使用 | 9/12 | sourceIPAddress、sourceIpOwner、ticketState | 未运行；完整材料未进入模型输入 |
| AWS-01-M，疑似恶意管理员角色使用 | 9/11 | sourceIPAddress、sourceIpOwner | 未运行；完整材料未进入模型输入 |
| AWS-03，两条C2对照 | 9/9及8/8 | 无 | 输入预检通过，尚未调用真实模型 |

原`format_extra_fields_for_llm`对raw_event使用10行摘要；有序数组标题也占行。不能按完整答案把截断导致的缺材料计成模型错误，更不能把HTTP替身分类当真实模型成绩。建议只给分诊raw_event单独40行/4000字符上限并标注省略，或保持现状只测完整C2对；已向用户提交选项，业务修改尚未实施。

原始材料保存于`.local/verification/data-evaluation-e1-20261023/`：prepared、preflight、preflight-v2及stdout/stderr。21恢复仅确认SSH，不查询业务或发模型；未开隧道/临时worker，不涉及清理线上身份。0新增真实模型、0业务查询/写入、0业务源码/配置/部署更改、0Git提交/push；原5/15、E0及旧失败保持。E1完整实测、E2—E4仍待推进，不能称评估模块全部完成。
