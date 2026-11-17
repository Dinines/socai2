# 当前模型预算调整与S04续验

**结果：预算配置、I完整生成、整事件Case自动第二轮、保存及比较身份/HTTP链接通过；模型质量仍NOT_PASSED。** [机器汇总](outcome-summary.json)分别记录配置、程序链、引用与正文未验边界。主31/41、流式2/11保持，未正式发布或提交推送。

2026-11-16，负责人要求事件输出8192并提高整体预算及输入输出容量；随后提供43参数：max-model-len=65536、max-num-seqs=1、RTX4090/24GB、gpu-memory-utilization=0.92、max-num-batched-tokens=2048。实际模型目录与tokenizer[再次读回65536](remote-capacity-02.json)。本批只调整21候选调查policy，不修改43服务窗口或调度配置。

## 配置子步

[本地检查](local-validation.json)记录38项直接检查通过，包含输入+输出窗口边界及Case两次完整C6预留；[应用回执](apply-01.json)确认旧调度已停止、0在途，保存原policy后只修改10项容量值，同版镜像实际loader通过。两份当前policy字节相同，新SHA为`9ef4129c88b94be7cecfe3b0ad89ba545919554cf93b5ddb8c923f853ef90a8c`；在该配置子步原8份运行配置仅policy变化，其余7份及镜像保持；后续输入保护接线另见下文。

| 预算 | 当前值 |
| --- | --- |
| 服务上下文 | 65536，输入+包络+安全余量+输出共用 |
| A/I单Run累计 | 各131072，最多2次生成 |
| Case单Run累计 | 393216，最多6次生成 |
| A/I/Deep单次输出 | 8192，计量消息+包络最多56320，另留1024余量 |
| C3/C6单次输出 | 16384，计量消息+包络最多48128，另留1024余量 |
| 输入准备容量 | 1048576 bytes；不替代真实token计量，不整包透传原件 |
| C6输入及总预留 | 输入48128/次；2次完整窗口共131072，仍在Case总预算内 |

工具次数、模型次数、时限、最多5发现、一次补答、生命周期和HTTP/数据库合同保持。A/I总预算扩展释放了输入空间；固定64K下，C3/C6输出增加会占用输入空间，不能把1 MiB字节准备额度称为token输入扩大。原policy[副本1](policy-before-01.toml)/[副本2](policy-before-02.toml)和原S04失败、首轮10项引用问题保持。

## 实际执行与读回

按[当前change安排](../../../../openspec/changes/schedule-streaming-investigation-updates/stage11-candidate-design-20261115.md#s04事件输出额度修正与继续验证2026-11-16)，新operation_key经当前18424[受理一次I rerun](submit-02.json)，原失败task/Run未重派。唯一候选调度完成新I后，自然触发整事件Case的periodic/check；6条后续检查因no_changes跳过、无attempt/Run，无重试、A重分析、Kafka重投或新建Case。

| 生成 | 实际输出上限 | 输入tokens | 输出tokens | finish_reason |
| --- | ---: | ---: | ---: | --- |
| I | 8192 | 6499 | 4518 | stop |
| Case C3 | 16384 | 13277 | 3939 | stop |
| Case Deep | 8192 | 13176 | 982 | stop |
| Case C6 | 16384 | 13882 | 4177 | stop |

[实际调用](model-usage.json)共4次、60450tokens，费用未知。新I覆盖原事件4成员并保存诊断；整事件Case从3扩到4成员、scope_revision=2，完成第二轮并采用新结果，当前判断freshness=current。比较冻结到本案首轮Run/Result，未串到单告警案。单A01案仍1成员/1Run，无新task，其旧判断因incident_context_changed为stale；固定范围对照通过，不把stale称为新分析成功。

全部终态且0在途后[正常停止](stop-01.json)exit0，随后一次[PG保存快照](analysis-pg-01.json)完成[119项检查](saved-validation.json)：新增8task、2attempt/Run、19步骤、53工件、1诊断/1Case结果；旧失败、首轮及原件逐行保持。[48次真实HTTP GET](http-validation.json)全200，24份必要正文及上一轮Run/Result两条链接与同一快照一致。C2真实查询知识和资产；C4只有1次Deep分析，没有新增湖查询，不把推断当实际取证。

[查阅追加](audit-export.json)仅使用保存快照，经update_processing_audit.py新增整事件后轮卡，原40卡/85历史Case文件保持，现41卡；0新查询/生成，实际4177未切换。

## 质量与未验边界

[本轮质量摘要](quality-summary.json)区分C3结构/来源校验与C6引用：C3有`observed_original_fields_exceed_statement_contract`、`unknown_domain_finding`两项诊断，按既有规则保留原答及独立有效部分；C6保留`comparison_needs_selected_baseline_and_current_sources`和`delivery_source_coverage_missing`两项问题。最终仍accepted/uncertain/partial，模型给出的change_kind=withdrawn原样保留，不确认其正文判断正确。比较身份和链接通过，不等于比较正文通过；I/Deep没有引用诊断也不等于正文已全面验收。原两案首轮10项引用问题和原3000/length失败均保留，不反复采样。

W4/W5、完整change结束审计、正式发布及正文质量专项保持各自未完成范围。没有真实长上下文压力测试；窗口边界为离线计量替身检查，4次真实调用仅证明本批实际输入可完成。

## 输入保护额度接线

收口复用输入检查时[发现候选env缺少字符额度](input-guard-before.json)，供应端保护默认60000字符；上述4次生成在该保护下完成。仅提高policy不足以放开较大输入，本步已同步候选analysis.json、deployment.json及受控私密env的`AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS=1048576`。常规本地/生产启动器已从policy派生该值，复用[生产profile检查](input-guard-profile-test.log)通过。

原两项测试中的3000字符/小metadata必省略假设已改为按所选配置构造超字节额度材料，保留值、路径、整字段省略及原件不变检查；[最终2项通过](stage-input-capacity-after-03.log)。先前相对policy路径错误、原断言失败及未设置完整保护环境的中间失败日志保留，没有改原历史失败。业务代码与保护规则未改。

[最终21加载回执](input-guard-finish-01.json)确认同镜像、同资源/挂载/执行命令，其他环境值一致；无网络探针成功接收131043字符的合成业务文本，超限、原件形态及模拟秘密仍拒绝。[本机同探针](input-guard-local.json)一致。字符保护与1 MiB字节准备是两道上限，实际派发仍须通过65536 token窗口和累计预算。

当前同名调度容器ID为`fafe844947104f0edaaac94cc262c30d359216aef6fbbaae941e53ef12e34c0d`，状态created、未启动；原实际执行容器`7928bec2…`已改名`socai2-streaming-dispatch-20261115-before-budget-20261116`并保持exited。未来只使用当前同名入口，不启动保留容器。8份运行文件最终仅policy和deployment.json变化；私密env只新增上述键。最初严格克隆比较因Docker create/run的OomKillDisable null/false及stdout/stderr attach默认差异停止，已[只读核对](input-guard-created-review.json)并限定等价项继续核验；保留失败回执，未重复创建或启动调度、未新增模型调用。

## 已知执行限制

先前SSH中转握手超时，第一次包装探针另被本机沙箱拒绝（[stderr](remote-capacity-01.stderr.txt)），未触及远端。网络恢复后只读探针通过；`/server_info`返回HTTPError，但`/v1/models`和`/tokenize`均明确65536。第一次HTTP提交连接127.0.0.1被拒绝，未发送请求；核对实际绑定192.168.1.21及旧任务后，仍使用同一operation_key完成唯一受理，失败记录保持。没有把理论262144作为实际运行容量。未正式发布、提交推送或改写原批次。

[最终文件核对](final-file-verification-02.json)通过：两份policy字节一致，policy及deployment与21回执摘要一致，PG快照未变；OpenSpec strict、Ruff和本轮路径diff检查通过，44条当前证据链接存在。首次链接核对发现一处空格，修正后复验通过，原失败回执保留；这不替代完整change的独立结束审计。两份只读探针的原执行文本另存`.executed.txt`，当前`.py`仅整理import格式，未重复发请求。
