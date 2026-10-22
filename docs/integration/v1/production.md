# v1.0.0 生产接入与已发布结果

[返回总指引](README.md)。2026-10-22 已在21发布 API `5a1e1fd8`、Agents `49643b84`，两服务标签均为 `v1.0.0`；模型沿用现有配置，Fusion及共享基础设施保持原配置。[完整发布回执及回退步骤](../../operations/service-v1-release-20261022.md)

## 1. 上游必须使用的参数

| 项目 | 正式值 |
| --- | --- |
| 租户名称 / slug | `stingAISOC Production` / `stingaisoc-prod` |
| `tenant_id` | `f6a5c700-69b8-44fc-8238-609362fb1a9f` |
| Kafka bootstrap / transport | `192.168.1.21:19093` / `SSL`，使用发放的CA；不是SASL或客户端证书认证 |
| 告警输入 | `socai2.alerts.raw`，UTF-8 JSON，`identity_version=source-v1` |
| 上游必须提供 | 固定 `source`、每条独立告警稳定 `source_alert_id`、租户及告警事实；重投保留同一来源ID |
| Fusion输出 | `socai2.alerts.fused`，包含 canonical Alert ID；不代表调查已经完成 |
| Agents专用生产组 | `socai2-agents-v1-prod-20261022`，后端订阅者应另建自己的group |
| 正式告警HTTP入口 | 不使用；HTTP告警接收仅测试辅助 |

新组在 `2026-10-22 16:39:54 +08:00` 显式提交起点：fused partition0=`30`、1=`32`、2=`39`。只处理其后的新消息，不回放旧测试积压。原 `socai2-agents-triage` 和旧租户/unknown 保留。共享正式topic后续只投本生产租户；其他租户无本发布预算会hold，测试继续用隔离topic。

[消息完整示例](examples/raw-alert.json)仍用虚构UUID；实际对接必须替换为上表生产租户及真实来源信息。[客户端模板](examples/kafka-client.env.example)已填生产tenant，CA、业务source、API token仍需在受控环境配置。

## 2. 结果读取与凭据

API在21主机为 `http://127.0.0.1:18000`，同Docker网络服务为 `http://api:8000`。18000绑定loopback，不是外部公开API；远端后端通过获授权网络代理/SSH隧道或部署在同网络访问。不要把 `127.0.0.1` 原样当成远端21地址。

生产只读key与单独投影writer仅存于21 `/opt/sting-aisoc-socai2/private/release-v1-20261022/`，文件0600、UID10001、只读挂载。`context-readers.json` 是生产tenant到reader的映射，`writers.json` 为内部 `alerts:write` 投影身份。对接方由运维受控发放reader；不复制整个私有目录或把writer交给查询调用方。两key到期时间为 `2026-11-21 16:34:33 +08:00`，到期前轮换。

查询使用 `Authorization: Bearer <发放的生产reader>` 及 `X-AiSOC-Tenant-ID: f6a5c700-69b8-44fc-8238-609362fb1a9f`。reader权限为 alerts/cases/connectors/graph/knowledge_base/settings 的read及 lake:query，不含告警/Case写。人工创建Case、手动调查需要另外发放已授权的 `cases:write`，本reader不提供该权限。

自动分诊会保存首次结论；未关闭且允许升级时，同Run继续调查，无需再次点击。前端/后端应同时读取首次 `triage_verdict` 和 `graph_result.completion`，并用实际 `report_md` 工件ID读取Markdown。`Run.status=completed`不能替代调查完整性判断。[每一步输入输出](README.md#2-每一步的输入点与输出点)、[事件/工件API](investigation.md)

## 3. 本次真实发布验证记录

下面均为**单条合成告警**的真实处理结果，不是生产攻击或结论准确率证明；记录保留在生产tenant中，标记 `release-validation` / `synthetic`，查询展示时可以排除。

| 阶段 | 实际坐标 / 输出 |
| --- | --- |
| raw Kafka发送确认 | `socai2.alerts.raw` partition0 offset37 |
| 上游source_alert_id | `7b9fd642-97be-52f1-8b04-4f9f5c98acb2` |
| canonical Alert | `00a6434c-eaf1-563d-93dc-70946e46e1d1` |
| Fusion Incident | `bbb6055f-5efc-40d8-93a2-d270185839d9`，不是Case |
| 自动Run | `39dd7fba-5f42-5b4e-9653-ae7de5fce32c` |
| 首次分诊 | `true_positive / 0.85`；告警保持 `triaged`，未关闭；此为模型结果，非确认攻击 |
| 调查前投影 | `success`，同Alert邻域5节点；attack_path=`not_linked`，没有人工Case |
| 自动调查 | graph三节点已记事件；Deep六轮、7条工具调用记录；`graph_result.completion=partial`，候选结论 `needs_review` |
| 用量 | 首次分诊2048 + graph26168 = 28216 tokens；7个可见模型回复；无已知美元定价 |
| Markdown工件 | `f0f36fcf-d491-4802-b238-7b8b4d59fb4a`，6468字节UTF-8 |
| 提交确认 | 新组 committed=`{0:30,1:33,2:39}`，与观察时end一致；原组未改 |
| 查询检查 | Alert、Run、events、artifacts、Markdown工件正文GET均200；API/Agents readyz200，Agents有fused订阅 |

使用本reader读取示例Run的工件正文：

```bash
curl --fail --silent --show-error \
  -H "Authorization: Bearer $STINGAISOC_API_TOKEN" \
  -H "X-AiSOC-Tenant-ID: $STINGAISOC_TENANT_ID" \
  "$STINGAISOC_API_BASE_URL/api/v1/investigations/39dd7fba-5f42-5b4e-9653-ae7de5fce32c/artifacts/f0f36fcf-d491-4802-b238-7b8b4d59fb4a"
```

响应是JSON，Markdown位于 `content`。告警ID、Run ID、工件ID各有用途，不能互换。

本Run的模型/工具顺序如下。Deep每轮请求由固定调查提示、告警/当时上下文、已有对话及工具说明组成，模型回复后代码执行 `tool_calls` 并回填ToolMessage；表内是本次实际记录，不表示所有调查都要查这些工具。完整查询合同见[工具说明](../../architecture/investigation-tool-catalog.md)。

| 调用 | 本轮新增输入 / 目的 | 可见回复 / 代码随后采用 |
| --- | --- | --- |
| 首次分诊 | fused告警、五类资料读取状态及已采用上下文，分类是否可关闭/升级 | JSON `true_positive/0.85/rationale`；持久triage_verdict、告警triaged，未关闭并自动升级 |
| Deep 1 | 当前调查state，选择首个取证方向 | `process_activity(hostname=v1-validation-host,hours=24)`；API工具返回available=true、0行 |
| Deep 2 | 前轮零行结果，继续查进程父子关系 | `process_tree(hostname=v1-validation-host)`；返回not_ingested，不证明没有父子关系 |
| Deep 3 | 已知process_tree不可用，按技术标签补查 | `technique_activity(days=7,technique_id=T1059.004)`；返回available=true、0行 |
| Deep 4 | 该技术查询零行，按主机补时间线 | `entity_timeline(hostname=v1-validation-host,hours=24)`；available=true、0行 |
| Deep 5 | 主机时间线零行，改查告警用户认证 | `authentication_events(user_name=v1-validation-user,hours=24)`；available=true、0行 |
| Deep 6 | 认证零行，继续查用户邮箱/授权 | `mailbox_activity`及`oauth_grants`，均传上述user_name；两项not_ingested；达到6轮，未得到最终narrative |

七个回复全文可回查；首次分诊及Deep第3—6轮的**持久prompt副本**被8000字符记录上限截断，不能据此复原完整实际请求，也不能说发往模型的请求本身被截断。各轮独立token数未留在这些交换记录，本版只给账本已观测的分诊/graph聚合用量，不编造均摊。末轮工具返回JSON被原流程放入narrative，属于已登记问题，不是模型最终结论。

## 4. 容量与结果边界

当前为单并发，滚动24小时普通分诊最多10次、200000预留tokens、1个未结算调用；本例已使用1次预留，实际首次回复2048 tokens。调查仍使用原独立限制，不包含在普通分诊预留上限内；预算到限/unknown会hold，不能清账绕过。

本例自动链已走通，但调查因原六轮及软token预算停止，26168高于20000检查点，保存partial。报告仍出现“无恶意命中→良性prior”、Unknown攻击阶段、状态running/Run completed差异；TI归因401、UEBA及部分处理上下文读取失败、未接入数据源等也已保留。不能把建议、知识映射、空查询或可达候选当确认攻击/影响。旧C2质量问题继续后置评估，未以此宣布质量通过。

自动关闭沿用已测试原规则；审批/真实响应、SIEM写回、告警playbook触发、记忆写回与抑制关闭。完整迁移任务仍5/15，本发布是当前告警/调查服务可接入版本，不认定整个平台或标书全部完成。
