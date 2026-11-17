# 交互验收脚本：材料、分段执行与已存状态

统一设计任务3a提供`convert`离线转换与`inspect`校验/列计划；3b增加离线`prepare`和显式`run`首段执行；3c.1增加离线`status`读已存状态及下一候选段；3c.2提供显式`append`追加下一段。`run/append`连接Kafka、数据库及业务HTTP，并经现有业务服务触发模型。3c.3提供`session`交互菜单和`report`全会话报告；3d提供[专用Docker入口](../../deploy/investigation-test/acceptance-docker.md)。材料检查的`passed`只表示材料通过，不表示业务执行或模型质量通过。示例不是自动环境选择，使用前必须核对实际目标与凭据文件。

## 使用方式

在仓库根目录使用现有Python环境（需要Pydantic 2）。材料、环境profile、结果目录明确分开；转换输出必须是原材料目录之外的新目录，检查报告也必须写在材料目录之外，已有输出不覆盖。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/acceptance.py convert \
  --source docs/operations/evidence/model-blind-data-20261116-01/revision-02/clean-data-01 \
  --recipe tools/testdata/acceptance-examples/streaming-conversion.json \
  --profile tools/testdata/acceptance-examples/profile.json \
  --output /tmp/acceptance-materials-one

.local/conda-envs/socai2/bin/python tools/testdata/acceptance.py inspect \
  --materials /tmp/acceptance-materials-one \
  --profile tools/testdata/acceptance-examples/profile.json \
  --report /tmp/acceptance-inspection-one.json
```

`convert`先校验全部记录和关系，再写编号JSON、来源追踪`conversion.json`与`plan.json`，重新读取核对。`inspect`只读取材料，报告包含每段数量/文件顺序、来源关联、Case创建/后续检查计划、未覆盖分支和配置身份。默认选part1，其他段不会自动选；没有part1时`selection_required=true`，可用`--part part2`明确选择。这里的“选择”只影响计划，不会发送。

## 统一目录和必需材料

```text
材料目录/
  scenario.json
  part1/alerts/001.json
  part1/context/001.json
  part2/alerts/001.json
  expected.json                 # 可选；程序旁路，当前未执行核对
```

- `scenario.json`必需；结构见[场景Schema](acceptance-schemas/scenario.schema.json)及转换示例的`scenario`。有序parts指定`check_level`（alert/incident/case）和`context_required`。每段至少一条告警；文件按数字排序，1/01重复报错。不能用未来Case/task/Run ID配置材料关系。
- 告警沿现有RawAlert/source-v1，明确id、tenant_id、source、title、severity、带时区event_time/created_at、source_event_ids数组及raw_event。身份封装仅可补identity_version/source_alert_id，正文、未知业务字段、0/false/[]保留。后台tenant和来源关联保留，实际模型视图仍由业务服务过滤。
- 独立上下文沿现有v1信封，明确tenant_id、可解析event_id/id/metadata.uid、ocsf_event及time/class_uid；OCSF时间可用数值或带时区字符串。opaque来源ID受支持，已声明内外身份不能冲突。context_required=true时须有当前或前段的独立上下文，来源引用可解析；多余context不要求全部被告警引用。不要求独立上下文时，未提供来源记not_provided、查询分支not_covered，不能记查空。内嵌telemetry不生成独立湖记录。
- Case可同时按事件与固定选定告警建案，参考[双Case示例](acceptance-examples/streaming-conversion.json)。`alert_refs`是材料路径，`create_after_part`声明创建段，`check_after_parts`仅可列更晚段；`cases: []`明确不建案。
- [profile](acceptance-examples/profile.json)必需，包含目标身份、tenant、连接配置文件路径、每段数量上限及间隔/时限；[Schema](acceptance-schemas/profile.schema.json)。`convert/inspect/prepare/status/report`及交互查看不读取连接文件；显式`run/append`读取并核目标。示例值可修改，程序没有固定3+12/1+1或环境回落。
- expected、资产/账号/知识/人工材料可选；本步只列旁路文件、未导入/未执行状态，不将它们直接拼入业务消息或宣称已接入。已知作者答案与批次控制字段（含JSON字符串内嵌字段）会拒绝；这是结构边界检查，不是任意正文秘密识别或语义清洗。

## 支持的旧数据转换

[转换recipe Schema](acceptance-schemas/conversion.schema.json)固定来源类型、目标scenario及每段alerts/context相对路径。

| 来源 | 操作与边界 |
| --- | --- |
| streaming_fixture v2的S01/S04 JSONL | 用streaming-conversion示例拆为part1/part2，逐文件核旧manifest输入SHA，逐条保留业务值/来源关系。旧源码SHA及candidate无需匹配当前源码/环境 |
| alert_scenarios v2的payloads | 先用已有生成器显式选择少量模板并生成中性告警；再用templates-conversion选择payload。5条内嵌telemetry仍只是2条告警的原材料，不造5条context。原始55模板/旧答案文件不直接作为转换输入 |
| 其他格式 | 明确拒绝；须先添加有完整映射的转换器，不能猜字段或假造上下文 |

转换保留旧身份和事件时间，因此材料计划标`requires_new_execution_identity`。**这些文件是材料模板，不能重派旧批次。** `prepare`生成全包跨part一致的新身份；本版只支持`time_policy=preserve`，不自动平移时间。旧expected/actions/ACK/Case/Run/模型原答留在原目录，不作为新结果导入。

## 准备与执行首段

先选择目标租户一致、适用于当前时间窗的新材料。单改UUID不会隔离事件归并或同主机历史查询；首段执行会检查目标实体历史，遇到已有归并/上下文要求另选材料，不能靠清空数据通过。来源connector须已在目标租户登记；程序不改租户、不注册来源、不改模型预算。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/acceptance.py prepare \
  --materials /path/to/materials --profile /path/to/profile.json \
  --execution /path/to/execution.json --output /path/to/new-execution

.local/conda-envs/socai2/bin/python tools/testdata/acceptance.py run \
  --prepared /path/to/new-execution --part part1
```

[execution示例](acceptance-examples/execution.json)明确唯一`execution_id`。`prepare`不连接网络；冻结源文件SHA、全包wire、告警规范ID/事件ID映射和逐字段变更。仅改已识别身份路径（包含OCSF及其嵌套raw_data身份），保留租户、来源、时间和业务原文；任意正文中同值文本不替换。重复输出目录拒绝覆盖。

实际连接文件分别参考[HTTP](acceptance-examples/http.json)、[Kafka](acceptance-examples/kafka.json)、[PostgreSQL](acceptance-examples/postgres.json)、[湖](acceptance-examples/lake.json)及同名Schema。HTTP明确服务/就绪地址、租户、分页及超时；Kafka明确生产者环境文件、目标地址/协议、两Topic及发送时限；PG明确DSN文件、库/角色/schema/TLS；湖明确地址、端口、库/表、只读账号、密码文件、TLS及超时。凭据放受控挂载文件，不写入材料、报告或Git。运行依赖列在测试服务`drivers`可选依赖中；本步使用现有环境，不等于3d镜像已交付。

`run`只支持声明的第一段，其他段保持`not_executed`。顺序为：

1. 校验冻结文件、显式目标、来源登记、身份和实体隔离。
2. 上下文逐条取得Kafka ACK，再按真实湖记录核身份、时间及原值。
3. 每条告警取得ACK，核PG材料及来源关联，并等自动分诊任务结束，再发下一条。
4. 等事件首次任务结束，再提交一次显式`check`；`no_changes`不增加Run或模型。
5. 按计划POST建Case，等待实际`allocations[].initial_task`，不追加旧start调用。
6. 保存本段PG快照，沿公开HTTP任务、Run、完整步骤/工件分页及原件核对；Case冻结成员与已保存结果一并核对。

`runs/<part>/state.json`持续保留进度和真实ID；旁边保存发送回执、上下文读回、HTTP请求/响应、PG快照与`readback.json`。HTTP写操作先存intent，结果未知不盲重试。已存在本段执行目录即拒绝再次执行，应先查看原回执。终态失败/局部模型质量问题保留并继续合法后续；ACK未知、身份/保存/读回不一致则记录未完成，不能伪造通过。CLI退出码：0流程完成、3流程走完但存在执行/原件问题、2未完成或配置/材料错误；模型质量始终单列，不能从0推断正文准确。

首段原验证与未覆盖边界见[单段记录](../../docs/operations/evidence/acceptance-singlepart-20261117-01/README.md)。完成后不会自动发送下一段；显式追加与只读汇总见下文。中断恢复及正式Docker命令不由本入口提供。

## 读取已存状态和下一候选段（3c.1）

```sh
.local/conda-envs/socai2/bin/python tools/testdata/acceptance.py status \
  --prepared /path/to/new-execution --report /path/to/new-status.json
```

命令只检查冻结session/wire及`runs/<part>`保存回执，不读取连接配置、不查询远端，也不发送任何数据。报告必须是prepared和原材料目录之外的新文件；独占写入并重新读回，已有报告不覆盖。再次查看时选另一个新报告路径。它是保存时事实的派生报告，不是实时任务列表、运行锁或允许立即投递的凭证；`append`会重新核对实际状态。

| 状态 | 含义与下一步 |
| --- | --- |
| `ready` | 首段无执行目录，可显式使用已有`run`执行声明的首段 |
| `selection_required` | 没有默认part1，或默认part1不是声明首段；需用`run --part <first_part>`显式指定声明首段 |
| `waiting_append` | 已存前段均结束且保存/读回匹配，`next_part`为下一未发送候选；可显式调用`append --part`，命令另做实时核对 |
| `recorded_in_progress` | 本地记录仍是running，不能推断远端此刻仍在运行；无追加候选，先核对原件 |
| `needs_review` | 未完成、回执缺失/不符、投递或写入未知、任务未结束或段顺序冲突；报告列阻断代码和原件路径，不重发 |
| `all_parts_completed` | 所有声明段的本地执行均已闭环；不等于模型正文或所有任务成功 |

报告按scenario声明顺序列计划数量、记录中的发送数、实际A/I/Case身份、task/attempt/Run/Result的各自状态和执行问题。实际身份只来自已保存快照，prepare预测ID不算落库。`completed_with_issues`保留失败/无Result，已结束尝试对应的unknown Run仍为unknown；质量保留未全面评估，不因已有质量问题扣住合法下一候选，也不将候选视为前段成功。只有state终态、绑定、保存快照、读回和已确认发送/HTTP写回执一致才给下一候选。原模型及HTTP内容不复制到状态摘要，沿报告原件路径查看。

`status`退出码：0成功观察且无阻断（仍可能需显式选择、存在历史失败或质量问题）；3报告已保存但需要核对；2材料/配置或报告写入错误，未产生可信新状态。CLI打印摘要，完整状态和来源SHA位于指定报告。[真实01/02离线复验](../../docs/operations/evidence/acceptance-session-status-20261117-01/README.md)只核保存回执，未重新执行这些历史批次。

## 显式追加下一段（3c.2）

```sh
.local/conda-envs/socai2/bin/python tools/testdata/acceptance.py append \
  --prepared /path/to/new-execution --part part2
```

`--part`必须填写，且只能是`status`中已存前段闭环后的紧邻未执行段。命令保留同一冻结session、全包身份映射和已有Case，不重建旧Case，不使用`rerun`；每次仅执行所选一段。发送前重新连接原profile核对前段主体、任务终态、原件和成员关系；四份连接JSON摘要必须与前段实际preflight一致，同一路径修改目标、Topic或库表配置也会被拒绝。本段及未来段身份必须仍未入库，前段上下文必须可读且原值一致。核对不符时保存`incomplete`、明确原因和真实发送数，禁止自动重派。

通过后先发送并读回本段上下文，再逐条发送告警并等待分诊，检查受影响事件，最后对`check_after_parts`声明的原Case提交`check`。已有自动后轮任务先等结束；显式检查返回`no_changes`时沿真实任务/Run关联读取，不为了制造后轮而强制重跑。整事件Case成员跟随实际事件变化；固定告警Case成员不扩充，但是否需要后轮由业务增量检查决定。

`runs/<part>/before-records.json`记录追加前真实快照；`append-readback.json`列各Case当前成员、新Run和新Result。旧Run按其冻结`run_members`核对C1，不拿当前Case扩充后的成员误判首轮；后轮的`previous_run_id`、`comparison_result_id`和HTTP比较上下文逐项核对。旧Run、Result、工件及旧段回执保持原值。成员已变化但没有覆盖新范围的后轮、或新Run无Result，均单独记录为`passed_with_issues`并传到段状态，不能借首轮Result声称成功。模型正文质量保留待核/原诊断，不阻断合法流程；发送未知或保存关系不一致不能冒充完成。退出码沿`run`口径。

设计与验收边界见[统一设计§12.8](../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#128-任务3整体实施顺序与3a材料入口2026-11-17)及§12.11。本机直接检查命令：

```sh
.local/conda-envs/socai2/bin/python -m pytest tools/testdata/tests/test_acceptance_materials.py -q
```

## 只读会话汇总（3c.3）

```sh
.local/conda-envs/socai2/bin/python tools/testdata/acceptance.py report \
  --prepared /path/to/new-execution --output /path/to/new-report
```

输入是已经 `prepare` 冻结的完整会话目录；原材料先走 `convert/inspect/prepare`。命令不读取连接配置、不访问网络、不派任务。输出必须是 prepared 和原材料目录之外的新目录，已有目录或指回原件的符号链接拒绝使用。

- `report.md`：中文段计划、已存发送数、阶段结果、实际主体与轮次、模型用量、质量问题和未验边界。
- `report.json`：程序按各类真实 ID 去重的统计、逐段新增/累计记录、同 Case 的冻结成员、前轮与比较 Result 关联。
- `models/<request_artifact_id>/messages.json`、`schema.json`、`output.txt`：筛选后的可见模型输入与原答；字符串和原答空白保留，不导出 HTTP 认证或隐藏推理。缺失/损坏内容单独记录，独立有效原件仍可查。
- `manifest.json`：导出文件的 SHA 与读回结果；来源 prepared 相对路径、JSON pointer、原件 SHA 单独保留。筛选导出不冒称完整原始回执。

后段快照包含首段时只按 ID 计一次；模型计数是已保存请求数，不自动认定是本次新调用。已开始但缺快照的段标统计不完整，总量为未知，保留可读小计；未发送段仍为未开始。缺失 usage 或费用不记零，已知 Token 小计与未知请求数分别显示。质量诊断按阶段列出，步骤跳过/错误另列；接收、待复核和部分交付不混成“全部成功”。

退出码 0 表示报告已生成且无执行/原件阻断；3 表示报告已生成但需核对执行或原件问题；2 表示材料或输出错误。0 不表示所有段已执行或模型正文正确。生成报告不会关闭会话或改写旧原件，后续仍可按 `status` 再显式选择下一段。

## 按段交互操作（3c.3）

```sh
.local/conda-envs/socai2/bin/python tools/testdata/acceptance.py session \
  --prepared /path/to/new-execution --output /path/to/new-console-records
```

启动先显示显式环境、每段材料计划和已存状态。输入以下命令，每次只做所选操作：

| 命令 | 实际动作 |
| --- | --- |
| `view` / `1` / 空输入 | 重新查看保存状态，不发送 |
| `report` / `2` | 在本次 output 的新子目录生成只读报告 |
| `run part1` | 明确选择当前显示的声明首段；无默认part1时填写实际首段ID |
| `append part2` | 明确选择当前显示的紧邻未发段；沿同一会话与Case追加 |
| `finish` | 生成报告后退出本次操作，未发段仍未发 |
| `quit` / `q` / `exit` | 退出查看，仅保存结束观察；EOF同样处理 |

执行前重读候选、会话和来源SHA；有变化要求重新选择，不把原命令挪到下一段。动作意图先保存，再调用现有run/append一次；返回后显示保存状态，等待下一条命令。无效命令和自由文本不落操作日志。未完成/未知状态不自动恢复或重派；本次执行结果未知的段另记unconfirmed，不混入未发送数。

output 中 `start.json` 保存初始观察，编号 `intent/result` 保存执行选择与结果，`reports/` 保存各次报告，`end.json` 保存退出原因、已存执行状态、未发/阻断/结果未知段、最近报告及操作次数。Ctrl-C尽力保存中断观察并退出130；执行器仍沿原规则留存incomplete/unknown，不宣称远端取消。其他退出码0为正常离开且无原件/执行阻断，3为需核对，2为配置/输出错误；正常退出不表示全流程完成。

退出和finish均不永久关闭prepared；下次使用另一个新output即可继续查看或明确追加，旧段仍禁止重派。同一入口已封装为[专用Docker镜像](../../deploy/investigation-test/acceptance-docker.md)，八个子命令沿相同实现。材料与配置只读，prepared和每次新output写宿主持久目录；默认帮助/查看不发送。容器使用者无需宿主Python或源码挂载；没有新增网页执行按钮、常驻会话服务或第二套队列。

本步[完整记录及测试模块独审](../../docs/operations/evidence/acceptance-session-console-20261117-01/README.md)区分真实历史原件只读验证、受控执行回调和真实业务执行。3c.3本身不重复调用模型；真正两段Kafka/HTTP/Case执行沿3c.2原证据。
