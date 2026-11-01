> 阅读说明（2026-11-01）：以下为原r3本地交付的独立结束审阅，审阅结论和范围保持；不是r11复审或报告语义验收。最新问题见[当前审阅指南](../../../docs/investigation/review-guide-20261101.md)，真实批次见[r11回执](../../../docs/operations/investigation-r11-positive-fixture-20261101.json)。本轮仅维护文档，没有再次独立审阅或业务测试。

# 结束审阅：fix-investigation-audit-gaps

日期：2026-10-31。审阅者：`investigation_end_review` 独立子代理，未参与本 change 的实现、测试编写或交付打包。审阅对象是基于 `5b9513860c566ea9c7f17917ddb71cc199a1988e` 的审阅开始时尚未提交的工作区及 r3 候选包；后续提交绑定见第 6 节。本文件是任务 5.2 的结束审阅记录，不是部署或真实业务验收。

**限定结论：本次范围内未发现需修复的缺陷，必须修项 0；接受本地实现及已有直接验证证据的限定结论。** 未发现需要最小复现的具体问题，因此没有新增或重跑业务测试，不把作者已有的 31 项通过写成独立重跑通过。4.2 的新提交、4.3/4.4 的实际更新与同批真实回执、5.3 的完整归档前条件仍须按实际进展处理，不因本次审阅自动完成。

## 1. 实际范围与方法

- 读取根目录 `AGENTS.md` 最新执行边界、本 change 的 proposal/design/tasks/validation/execution-validation、三项 capability 规格、[实施记录](../../../docs/investigation/audit-fixes-implementation-20261031.md)及[机器回执](../../../docs/operations/investigation-audit-fixes-20261031.json)。
- 对基线读取四份已跟踪业务文件的完整 diff，并直接读取新增 `case_source_material.py`；检查改变的 Case/Incident 测试及其替身设置。依赖核对涵盖原模型调用/输入 guard、Case API 权限、概况 worker、related 来源视图复制、tenant session 事务收尾和仓库 ClickHouse 表字段。
- 独立只读计算 5 份业务源码、6 份列入回执的测试源码、476 份候选文件、归档各项、7 份测试日志和 6 份 Office 冻件的 SHA256；从 tar 内直接读内容比较，没有解压或改写原件。
- 阅读各阶段日志、原 B2 两个失败 subtest 和最终复核日志，按测试方法去重；核对 Office 测试使用实际执行器、MockTransport 的两次调用、原错误答复/6982 usage、结果保存断言和当前预检公式。原 Case 冻件的 description 确为 null，与 Office 用例中的输入一致。
- 运行范围内 `git diff --check`，退出 0；仅有既有 LF/CRLF 提示。静态检查使用本地 `.venv/Scripts/python.exe -B` 及 Git `safe.directory` 参数，无业务模块运行、模型/数据库/事件湖连接或网络访问。

本次只写本 `audit.md`。不修改源码、测试、原日志、规格或任务勾选，不对其他工作区文件作处置。

## 2. 功能与合同核对

下表行号对应本次已核 SHA256 的工作区文件；均位于仓库相对路径下。每项结论仅覆盖所述代码与证据，不表示模型语义或生产运行已经通过。

| 范围与位置 | 实际核对 | 结论及证据边界 |
| --- | --- | --- |
| A01：`services/api/app/investigation_v2/case_analysis_tools.py:45`、`:61`、`:84`、`:89`、`:95` | 进程 SQL 保持 tenant、主机、半开窗口及 limit+1，增加 `class_uid=1007` 和非空进程名；保存 class/activity/action/outcome。模型视图只省略原始编号并明确说明，以语义类别及原 action/outcome 表达，未把终止/未知活动解释为启动成功。 | 符合规格。`services/api/tests/test_case_analysis_api.py:261` 将实际 SELECT 的绑定/时间函数适配到 SQLite，在混合类别中验证谓词及网络对照；不能替代真实 CH。仓库表定义已有四个新增返回字段。 |
| 进程复用：同文件 `:89`；`services/api/app/investigation_v2/case_analysis.py:423` | 原 available、Tool 名、参数和范围/材料检查外，进程还要求精确 `case.process_activity.v2`；产品快照仍不复用，旧证据读取不补标版本。 | `services/api/tests/test_case_analysis_api.py:299` 的缺版本旧结果不复用、当前结果可复用和旧 key 读回断言对应实现；没有为兼容放宽旧合同。 |
| A02：`services/api/app/investigation_v2/incident_api.py:51`、`:65`；`incident_summary.py:136`、`:175`、`:183` | 请求 Case 权限及锁内非空旧 Case 正文的回退权限均先于模型/last_attempt。锁定 record 直接传入生成函数；没有模型后的回退权限拒绝。基础和 related 是不同视图，各保 source_updated_at；成功按新 source_refs、失败按旧正文模式返回，原尝试/usage/可写成本沿事务提交。 | 符合条件式收紧合同。`services/api/tests/test_investigation_incident_summary.py:162`、`:200` 核双向失败、GET stale、已知 usage 和前置 403/纯基础对照；是 ASGI/DB 替身，非真实 PG 锁或 JWT/RBAC 验收。worker 的 initial/last_attempt 跳过规则保持。 |
| D01 冻结：`services/api/app/investigation_v2/case_source_material.py:19`、`:38`；`case_analysis.py:160`、`:486` | 描述按原文、raw_event 按排序紧凑非 ASCII 转义 JSON 编码；完整字段先算指纹/长度，按 UTF-8 边界及字段/Run 上限保留。顺序沿 Case 后已排序 Alert 的 description/raw。Case 材料写入最终结果，Alert 材料随 A 证据，超限保 hash 而不冒充全文保存。 | 符合 4/4/16 KiB 字段与 128 KiB Run 合同。`services/api/tests/test_case_analysis_api.py:407` 的 Office 原件、读回和多成员 UTF-8 超限断言覆盖直接目标；未新建原件下载接口或改变授权范围。 |
| D01 模型视图：`case_source_material.py:48`、`:59`；`case_analysis.py:309` | 新字典保存模型状态/text/省略信息，冻结字典不改写；Case 最多 1 KiB，剩余按可读成员均分，description/raw 分别最多 1/2 KiB，总新增正文不超过 8 KiB。完整来源在嵌套/裁剪前调用既有 classifier，命中后省略模型正文并保留冻结文本；最终调用仍经过原 validate_messages。 | `services/api/tests/test_case_analysis_api.py:448` 的原始 OCSF 字段阻断符合合同；guard 源码与开关未修改。8 KiB 不是完整模型请求上限，也不表示所有来源形态已获安全或语义验证。 |
| 指纹与历史：`case_analysis.py:507`、`:526`、`:543`、`:557` | 同 key 的 intent/只读分支先于当前来源读取；新 source/material hash 包含新 schema 及完整来源 hash/状态/字节。只有精确新材料版本才可能复用；缺版本旧 Run 仍作为 H1 读入原报告，旧 Markdown 不重写。 | `services/api/tests/test_case_analysis_api.py:460` 覆盖尾部变更、正文变更、旧材料、H1、原 key 和报告读回，源前缀相同也会失效复用。未发现旧 Run 被隐式升级。 |
| H1、预算与纠错：`case_analysis.py:43`、`:297`、`:332` | H1 模型报告省略的字段逐项列明，完整 report/gaps 留账；未再删除与已省略明细对应的 gaps。有 H1 时 A 旧摘要省略与缓存可用性无关。仅三份成员列表完全相同才省两份，scope 原件不改。原 4 模型/4 Tool/24000 tokens/3000 输出/120 秒及一次纠错限制保持。 | `services/api/tests/test_case_analysis_api.py:323`、`:372`、`:529` 和最终 6 项复核相互对应。Office 当前 16929≤17018，余 89，是固定来源和原 usage 下的实际执行器＋模型 HTTP 替身结果，不是新真实模型结果或一般输入保证。 |

## 3. 独立完整性核对结果

业务源码实际 SHA256 与机器回执一致：

| 文件（`services/api/app/investigation_v2/`） | SHA256 |
| --- | --- |
| case_analysis.py | `4160df36bec7ff3a46e012473fc7d00e0f73ed0d236f0fac15f3172af9f0e437` |
| case_analysis_tools.py | `9a404e6845749a5b6d916e40e118151933fee0da4ffb86e317544ae7fa6f74c2` |
| case_source_material.py | `f9d78fa0a947aa9d8c7e0cd8df246453e4e7cc391a81b6e4b8efcc944ed2732d` |
| incident_api.py | `9e7366d0d59619d346d445e05b5ade7faf1767ef946a707953fe58fbe7b500f8` |
| incident_summary.py | `8611e026208590d6e0eac3f8a8c6598620996adc65d9acda5fc92a76ddbdfca1` |

- [source-manifest.json](../../../docs/operations/evidence/investigation-audit-fixes-20261031/source-manifest.json) SHA256 为 `8da5555ceb9dc211143ac70d098a981db26f5335630615dd025f6edc3a1342f8`，与回执相同；全部 476 个路径的工作区内容逐项匹配，无不一致。
- [r3 归档](../../../docs/operations/evidence/investigation-audit-fixes-20261031/investigation-api-20261031-r3.tar.gz) 实际 1,653,951 字节，SHA256 为 `21bebe063a482201577b61cc146804dd2cc2d2e76a0ea67039720cae534c677a`。477 项正好为 476 个 manifest 文件及 `SOURCE-MANIFEST.json`；重复、缺失、多余项均为 0。每项内容 hash 与 manifest 匹配，内嵌 manifest 与独立文件字节相同。
- 机器回执列出的 6 份测试源码 hash 全部相同；7 份日志的 hash/字节数全部相同；6 份 Office 原始输入 hash 全部相同。未改写失败日志和冻件。
- 部署文件相对基线只调整 r2→r3 标签，候选未构建、没有 image digest；源码包一致性不能代替远端当前镜像确认或服务更新回执。冻结 manifest 的 `new_commit=null` 保留打包时点状态，后续提交绑定见第 6 节。

## 4. 测试事实与发现

**可操作缺陷：0（P0/P1/P2/P3 均无新增项）；必须修复：无。** 上面的文件行号是审阅范围索引，不是缺陷列表。

已有证据为 Case API/synthesis/product/navigation 合计 26 个不同方法、Incident 5 个不同方法，合计 31。H1 gaps 修正后仅复核 6 个受影响方法，均为这 31 项内的重跑；本次从日志和回执去重均得到 31，没有把阶段运行数相加。

`b2-direct.txt` 原双向模式用例有两个时间格式断言失败，原文显示 Z 与 +00:00 差异；最终 `b2-mode-recheck.txt` 原方法通过。`case-final.txt`/`b4-combined.txt` 的 Office 16486/532 是较早阶段；当前 `followup-gaps-recheck.txt` 明确为 16929/89，与完整 gaps 保留后的实现一致。B1 首轮 guard 拒绝未留独立完整控制台文件的证据限制，实施记录已经明确；本次不重建或伪称该原失败已独立重放。

没有发现具体错误需要离线复现。本次业务测试执行数 0、额外通过数 0；不新增测试框架、恢复/压力/故障注入或权限专项，也不要求为独审重跑既有已通过且未变化部分。

## 5. 保留范围与交付判断

本审阅仅接受已核版本的本地实现、合同对应关系及现有直接替身证据。真实 PG 锁/提交、实际 ClickHouse 字段与查询、真实模型原生 Tool/纠错行为及报告语义、JWT/RBAC、厂商调用、部署后服务版本和 worker 行为均未在本次验证。不得据此宣称 r3 已部署或原 r1 失败全部关闭。

Office 的 89 字节保守预检余量很窄，但固定回归已在现有记录中通过；本次不提高预算、不据此要求额外压力测试。后续真实输入/输出可能不同，按已拟定的一批定向真实复验记录实际结果，不循环重试到内容满意。

一次未参与实现者的结束审阅已实际完成，任务 5.2 可引用本文件。主代理可同步对应状态；归档、主规格同步、旧 `fix-case-followup-gaps` 真实任务、旧 2.2/2.3、F5、自动 Case、提交/推送/合并不由本结论核销或授权。

## 6. 审阅后提交绑定补充

同日源码已保存为本地提交 `bb8dbc321dca574ce19b37ec524051f5ed16b421`。已读取 [source-commit-attestation.json](../../../docs/operations/evidence/investigation-audit-fixes-20261031/source-commit-attestation.json)；其记录原候选 476 份文件与提交内容一致，其中 36 份逐字节相同、440 份仅 CRLF/LF 差异。原 tar/manifest 未重写。

审阅者另以 `git show <commit>:<path>` 独立只读取得第 3 节五份业务源码：五份均与原审阅工作区逐字节相同，SHA256 均保持表中值，并与 attestation 的 candidate_sha256 相同，无需依赖换行规范化。本审阅因此绑定到该提交的相同源码快照，必须修项 0 的限定结论不变。未重跑测试或增加真实访问；4.2 可由主代理依据提交及交付材料更新，其他真实复验/归档边界不变。
