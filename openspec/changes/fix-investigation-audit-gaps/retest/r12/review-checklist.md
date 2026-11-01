# r12候选与报告核对表

P1本地准备已完成；这是下一批的执行材料，不是部署或真实验收结果。候选标签为`20261101-r12`，源码取自当前工作区快照，尚无新Git提交。以[候选清单](../../../../../docs/operations/evidence/investigation-r12-preparation-20261101/candidate-manifest.json)的文件hash和[包记录](../../../../../docs/operations/evidence/investigation-r12-preparation-20261101/candidate.json)固定内容；后续源码变化须更新候选，不能沿用旧包声称包含新修复。

## 固定调用范围

完整租户、接口、operation_key、预计Run ID、正文及客户端实际序列化hash见[plan.json](plan.json)。本批至多3个新Run，不新建Case/Alert/湖数据，不刷新事件概况。已有凭据仅在远端通过环境变量传递，材料中不保存Bearer。

| 场景 | 材料 | 派发条件 |
| --- | --- | --- |
| A 正向 | [A-positive.body.json](A-positive.body.json)；r11已有Case、原两成员/窗口；强制真实进程和网络补查 | 核对当前Case/来源与基线差异，预计Run不存在；一次POST |
| B 空查询范围 | [B-empty-scope.body.json](B-empty-scope.body.json)；r10已有Case、原两成员/窗口；同样真实补查 | 不依赖A；当前返回是否为空按实际判断，一次POST |
| C 追加 | [C-followup.template.json](C-followup.template.json)；A同成员/窗口，允许既有查询复用，不强制Tool | A的返回Run ID须与计划一致，状态completed且报告来源/语义核对合格后，才替换`<A_ACCEPTED_RUN_ID>`并重新校验/保存正文hash |

C模板保留非法UUID占位，因此不能直接作为合法调查请求；本地只在内存中替换预计A Run验证其余字段，未保存可直接派发的C正文。A/B不是旧请求重放，operation_key及预计Run ID均不同于旧批次。若POST结果不明，只按预计Run ID读取，不自动再次POST。

## 样本来源与判断边界

[source-baselines.json](source-baselines.json)保存旧冻结上下文的文件hash、Case说明、逐告警来源指纹及身份。它证明旧批次曾读取的材料，执行前仍须读取当前来源；不据此宣称线上内容未变。

| 事项 | 已有材料支持什么 | 不支持什么 |
| --- | --- | --- |
| A的测试标记 | Case说明标明功能测试；A1/A2 raw各有`synthetic=true`和fixture_ref | 标记来自同一测试样本，不能当多份独立证据；本次不验收真实生产攻击检测能力 |
| A进程 | A1原文陈述WINWORD PID4100启动PowerShell PID4200，账号fixture.reader；历史进程Tool有对应event_id的1行活动 | Tool没有PID/父链/命令全文，不能说Tool独立证实了父子链、脚本内容或审批情况 |
| A网络 | A2原文陈述PID4200向198.51.100.80建立TCP/443、8192出站字节；历史网络Tool有对应event_id的1行连接 | Tool不提供PID和出站字节；documentation address不是“文档服务器”的用途证明；TCP/端口不证明应用协议、C2、外传或授权情况 |
| A关系 | 可区分共同主机/时间与A原文的相同PID陈述，并说明各自来源 | 不能仅凭共同主机/时间宣称攻击链；来源事件ID匹配不等于所有raw字段都被Tool独立核实 |
| B原文与处置 | 两条raw陈述Office/PowerShell及TCP/443；既有disposition分别为true_positive和needs_review，T为历史分诊判断 | 当前调查不能把旧处置/分诊当新独立观测；审批未提供不等于非法，缺威胁情报判定不等于安全 |
| B历史空查询 | r10在该范围实际查询成功且进程/网络均0行 | 不能据0行反证原文、判安全或推测采样/阻断/丢日志。若新查询非空，记录变化，空查询场景保持未覆盖，不改数据制造0行 |
| C历史引用 | H属于A的新Run，保留来源归属、未决问题和缺口；实际复用时明确原Run/原查询 | 不能把历史判断或历史复用说成本次新查、独立印证；未调用Tool不伪造Tool证据；未复用不补跑追求覆盖 |

## 验收与停止

按[后续计划](../../report-followup-plan-20261101.md)的报告要求检查完整输出：成员覆盖、引用、来源/关系强度、未知事项、完整中文及控制文本泄漏。`completed/partial`可以合格；`failed`且正确拒收坏报告只说明保护行为，不计报告交付成功。Schema通过不能替代这次内容核对。

每Run原4模型/4Tool/24000tokens/120秒循环及一次纠错保持；最多3Run、12模型、72000tokens。A/B仅各一次；A不合格则C不派发；首份报告合格不人为制造纠错。未知usage和未定价费用如实记录，不记作零。

部署前仍需读取21当前调查镜像ID并与r11已核实镜像`sha256:59d9fe097588dad6c019797a9ba635f5f2126ae66ffddbdc3e466447ebc3ffcb`比对；有变化则先说明差异，不盲用旧状态。沿现有installer的`--upgrade-from`更新独立API，保持环境文件和其他服务不变。当前只执行过installer无`--execute`分支，未构建镜像或访问Docker/SSH。

旧r11执行脚本会新建Case，不用于本批。后续逐条通过现有`scripts/investigation_client.py`读取/提交固定请求并保存原件；本轮不新增自动批次框架。
