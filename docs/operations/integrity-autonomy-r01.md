# 完整性迁移：自治 R01 受控结果

2026-10-21。本批 **case01 的限定分类、理由与自动关闭通过；case02 的实际调用、持久材料和核账通过，完整调查及报告质量失败，已受控停止**。整体迁移和常驻自治准入未完成。两例均使用 candidate04 的 `c311a94b…`，常驻 worker 保持 OFF。

[机器回执](integrity-autonomy-r01.json)保存完整 SHA 与分项状态；[candidate04 来源](../handoff/integrity-candidate04-source-manifest.json)绑定本批实际产品代码。[candidate05 来源](../handoff/integrity-candidate05-source-manifest.json)是另行构建的默认调查报告语义修正，不覆盖下述 graph/deep 问题。

| 样本 | 首次实际分诊 | 实际结果 | 模型回复 / tokens | 独立结论 |
| --- | --- | --- | --- | --- |
| case01 | benign_true_positive，0.95 | 首次快照 `auto_closed=true`；PG resolved、关闭时间非空；API resolved/BTP | 1 / 2174 | 分类、理由、实际关闭限定通过 |
| case02 | needs_review，0.85 | 未关闭；实际进入 graph/deep，最终 graph partial、deep truncated | 7 / 22568 | 技术材料通过，完整调查与报告质量失败 |

## 实际链路与判据

两条新 source-v1 输入分别只 POST 一次原 `/api/v1/alert-ingress`，经真实 raw Kafka、Fusion、告警持久化及 fused Kafka，交给原 `FusedAlertTriageWorker.start()`。有限消费者仅限制已经冻结的单条坐标和信封 hash，在交给原循环前暂停后续交付，保留原持久确认和无参数 commit。没有直接调用 triage、重投 fused 或重放旧 unknown。

每例先保存输入、判据、告警初态及水位；case02 的发送另经过 root 对 case01 的显式质量门。消费提交与 Run completed 均不代替业务质量门，原判据未在看到结果后修改。

case01 的可见原回复区分“检测有效”与“提供的活动获批”，理由得到输入中的对应账号、目标、命令与 UTC 授权窗支持，未发现虚构外部核验或广泛无害结论。首次分诊为 LLM、非 shadow，原阈值仍为 env 0.85，groundedness floor 为 0.75。五类专用来源均实际 HTTP 200、no_match、无读取错误；这证明有认证的合法空读取，不证明已有组织知识或知识质量。

关闭事实由首次 `auto_closed=true`、最终 PG `status=resolved`、BTP disposition 和非空 `resolved_at` 联合证明。消费前保存的 API 仅证明 status=new；API 的原响应 schema 不含 `resolved_at` 或 groundedness 字段，缺键不能当作 null。case01 没有消费前 PG 关闭时间快照，不能补称初始 PG null。消费后独立 Alert GET 返回 resolved/BTP/0.95，与其暴露的 PG 字段一致；关闭时间仍由 PG 证明。

case02 有独立的消费前 PG 原件，明确 `status=new`、`resolved_at=null`；最终 PG 为 triaged/needs_review，关闭时间仍 null，独立 API GET 为 triaged/needs_review/0.85。首次理由保留授权与后续活动未知，没有把缺证判为误报或据此关闭。

## case02 的真实调查与失败

原 graph 实际完成 triage、enrichment、investigation 三个节点，deep 实际取得六次模型回复和六条工具调用。`lookup_technique(T1110)` 返回原 ATT&CK 知识，结果以匹配的 tool-call ID 进入第 5、6 次实际 ToolMessage；另有 `extract_iocs` 成功。四个 lake 工具返回 `available=false` 和明确的 lookup failure，未当成“查到零条”；未配置 SIEM/vendor 的可见性明确记为未知，没有伪造外部材料。

本例未达到冻结的完整调查条件：

1. investigation 节点后核得 graph 使用 20451 tokens，触发原 20000 的节点边界预算，持久结果为 `completion=partial`、status=running。预算保护正常标出未完成，不能把 Run completed 解释成 graph 已完成。
2. deep 达到原六步上限，`truncated=true`；最终 narrative 是最后一个 IOC 工具结果，尚无最终模型综合结论。`error=null`、`over_budget=false` 不覆盖该截断事实。
3. 报告虽保留缺源、partial 和升级分析员提示，仍把 ATT&CK 映射写成已观察攻击阶段，声称 single-stage attack 和 confirmed_incident/0.94。缺少授权、后续会话及 lake/vendor 证据时，这些确认及范围收缩不受支持。Markdown 2878 字节、HTML 4133 字节完整可读，材料可交付不等于内容质量通过。

另外，实际 deep Human 消息没有收到 state 中仍存在的账号、23 次失败、事件窗及显式授权/后续活动缺口；上游 `_summarise_alert` 只投影摘要与旧字段名。报告还出现 `confidence 0.85 < threshold 0.85` 的错误升级文案。这些问题单独记录，后续做最小修复，不改本例或补调模型。

“已观察阶段”和确定性 confirmed_incident 来自固定上游已有的调查与评分逻辑；`investigation_agent.py` 本批与固定上游逐字节相同。它们不是本地持久补接改写了首次分诊，但已阻断当前承诺的调查质量。case02 的原首次 NR 快照、原模型回复和来源工件均保持。

## 用量与持久化

| 项目 | case01 | case02 | 两例合计 |
| --- | --- | --- | --- |
| 首次分诊 tokens | 2174 | 2117 | 4291 |
| graph tokens | 0（已关闭，未进入 graph） | 20451 | 20451 |
| Run 实际 tokens | 2174 | 22568 | 24742 |
| 实际模型回复 | 1 | 7（首次 1 + graph 6） | 8 |
| unpriced calls | 1 | 7 | 8 |
| C 预约固定单位 | 20000 | 20000 | 40000 |

case01 的 2174=2039+135；case02 的 22568=2117+20451，与首次快照、graph_usage 事件、Run 和成本表逐项相等。两条 C 预约均 responded/settled，`observed_tokens` 只记录首次分诊，共 4291；40000 是预约单位，不能当 usage。调用均 unpriced，数据库默认数值 0 不表示实际费用为零。

case01 的 7 项、case02 的 11 项工件，其 SHA、UTF-8 size、内容与逐项原 API 读取一致。case01 prompt 原件受 8000 可见边界裁剪，所需授权事实在保留部分中；case02 六个 deep 可见消息记录在本例均未裁剪且 hash 可核。均不外推完整 provider wire、tool-schema payload 或隐藏推理。

## 算子失败与保留

| 原阶段失败 | 实际影响 | 修正与保留 |
| --- | --- | --- |
| prepare 把配置文件路径误当成目录 bind 目标 | 只留下 spec-freeze/STOP，尚无预算文件、env、group 或模型操作 | 核六个文件各有唯一 RO owner、保留 CA；仅对该已审零业务中断沿原 spec/ID/时间续行 |
| baseline 的 `/control/operator.py` 遮蔽 Python 标准库 | 在进入内部阶段前循环导入失败，未连接 PG/Kafka | 仅改控制挂载与导入/hash 路径；原脚本、STOP、host/log 保留，断网冷启动通过 |
| baseline 误用无订阅 Consumer 的空 metadata 缓存 | 只读 broker bootstrap 后停止，无提交或模型 | 原公开 Admin 先确认 topic 存在、读取真实分区，再用原 Consumer 读取水位/commit；原失败与诊断保留 |
| observe 误把 nested alert.id 当 source ID | 一次 ingress 已成功，仅观察既有信封后停止；未启动 worker/模型 | 按固定源码核三处 canonical ID、独立 source_alert_id，观察同一坐标；未重复 POST |

四次失败的原控制器/STOP/host/log、明确恢复批准和独立诊断均保留；另有诊断文件权限及测试替身构造失误，也保留首失败，没有转成业务重试。输入、判据、阈值、原业务结果未重冻或改写。case02 的实际质量失败另行封存 STOP，不再发输入或 consume。

## 收尾状态与后续

旧 A 的 10 条预约及 B 的 4 条预约，含 3 条 unknown/unsettled，内容 hash 与两例前后保持；两个受保护旧 group 的 committed offsets 保持。未退款、重分配或重调旧 unknown。C 两预约均结算，原 A/B reader 及常驻映射保持。

两个业务窗口结束时独立读取确认：常驻仍为同一 c311 容器，worker OFF、review_only、审批/graph/memory 关闭；七个只读 bind、60 秒停止宽限保持，同 spec 活动有限容器为零。

随后 root 仅撤销本批两枚 A/B 操作 key 与 C 的六枚临时 key，八次原实际 HTTP 均为 401。[凭据收尾汇总](../handoff/integrity-final-key-revocation.json)绑定 triage_review 的结束独审：八枚 inactive、旧十枚 reader 保持 active/未过期、其他 key 行 hash 与五类旧映射保持，常驻 service identity 保持；独审没有重复发八次 HTTP。私有原件保留，不公开 key 值。

candidate05 随后另行单次部署为 `4ccf3a6d…`。运行独审逐项核 773 来源与其冻结清单相等，恰两处默认 Forensic/ReportWriter 修改，父层、其余容器、全部 env、七只读挂载、60 秒宽限和 worker OFF 等守卫保持；0 新模型/业务消息。它不改变本批两个样本实际使用 c311 的事实，也不构成新模型质量通过。

后续仅针对本次实际暴露的 deep 材料投影、有限循环收束和报告证据边界规划最小修复。candidate05 的默认 Forensic/ReportWriter 修正不包含这些 graph/deep/评分问题；本次 C2、旧质量失败和旧 R02 不改写，也不因基础设施通了而宣称完整自治或整个迁移完成。
