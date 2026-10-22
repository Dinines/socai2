# 调查工具目录与当前实现边界

本文按 **2026-10-21 当前工作树**核对 Deep 实际注册表，供二次开发选择和调用工具。运行入口、配置步骤、调用过程及分层测试办法见[调查工具使用指南](../operations/investigation-tools.md)；逐模型输入输出见[预处理、模型与工具说明](investigation-preprocessing-tools.md)。本次仅补文档，没有修改业务源码、启用配置、运行测试、调用模型或访问基础设施；当前工作树实现不等于21已部署版本。

## 1. 先区分四类能力

| 类别 | 怎样进入调查 | 本目录口径 |
| --- | --- | --- |
| 5个基础工具 | `default_registry(runTenant)` 固定注册 | 提取、映射、资料和信誉/沙箱查询；包含 `lookup_file_hash`，旧的“4个基础工具”描述已不完整 |
| 11个typed调查工具 | `investigation_tools(runTenant)` 固定注册 | 7个有湖仓查询实现，4个显式占位；不是11个都能返回调查数据 |
| 最多6个customer工具 | 先固定读取租户后端清单，只注册可用能力 | 面向客户SIEM、EDR、身份、云审计；工具目录存在不等于该租户拥有这些后端 |
| 租户MCP工具 | 读取租户已启用服务器，发现并审核白名单工具 | 数量、名字和参数随租户配置/服务器发现结果变化，不计入固定16项 |

注册入口是 [Deep组装](../../services/agents/app/investigator/deep_investigation.py)中的 `default_registry`、`investigation_tools`、`scoped_customer_tools` 和 `build_mcp_toolset`。**固定16项表示源码提供了16份schema，不表示16项都有数据、都执行过、都通过真实场景测试。** 模型获得schema后是否请求、请求是否执行、返回是否可用、是否进入下一轮，分别以实际调用回执为准。

以下 `string`/`integer` 指模型看到的JSON Schema类型；“必填”是schema的 `required`。通用registry不执行完整JSON Schema校验，实际约束由注册名、Python参数绑定、各工具实现和API权限/参数处理共同形成，不应将“typed”理解为所有参数已严格验证。固定16项及customer工具的schema不包含 `tenant_id`，平台租户由本Run闭包和认证上下文交接；外部MCP参数以服务器发现的schema为准，平台选择哪个租户的服务器仍取本Run身份。

## 2. 5个基础工具

参数与注册以 [registry.py](../../services/agents/app/tools/registry.py) 为准。

| 精确name | 必填参数 | 可选参数 | 实际后端/处理 | 主要输出 | 时间与上限 | 当前实现 |
| --- | --- | --- | --- | --- | --- | --- |
| `lookup_file_hash` | `sha256: string` | 无 | Agents调用API `POST /api/v1/sandbox/lookup`，由沙箱provider注册表查询已有分析；工具自身检查64位十六进制SHA-256 | `available/outcome/sha256/provider`；已知时附 `report/detail`，失败附 `reason` | 无事件回看窗；单次HTTP截止15秒；不会上传文件 | 已实现已有分析查询；未知hash不等于良性，pending不等于已分析 |
| `extract_iocs` | `text: string` | 无 | 本地原规则提取IPv4、域名、HTTP(S) URL、64位SHA-256；不查数据库、不调用模型 | `[{type,value}, ...]` | 无时间窗；没有工具级条数/文本长度参数，仍受实际模型输入/结果长度限制 | 已实现启发式提取；不是完整IOC解析器，例如可把`.exe`形式当作域名 |
| `map_to_mitre` | `text: string` | 无 | 本地小型关键词→技术ID映射，非模型打分、非完整ATT&CK分类 | 技术ID列表，例如 `["T1059"]` | 无时间窗、无回看配置 | 已实现关键词映射；命中不证明该技术在事件中实际执行 |
| `lookup_technique` | `technique_id: string` | 无 | `app.tools.mitre`本地内存中的常见技术子集；不是所有MITRE数据/向量知识库的统一入口 | 已知时 `id/name/tactic_id/tactic_name/mitigations`；未知时 `id/name=Unknown/tactic=Unknown` | 无时间窗；无网络调用 | 已实现子集查询，未知ID不会触发在线补查 |
| `enrich_ioc` | `ioc_value: string`；`ioc_type: string`，枚举 `ip/domain/hash/url` | 无 | `POST {ENRICHMENT_SERVICE_URL}/enrich`，正文 `{value,ioc_type}`；将增强服务JSON返回 | 成功透传服务结果，可含信誉分/置信度/来源等；异常 `{error,ioc}` | 无模型可选时间窗；单次HTTP截止10秒，缓存新鲜度/来源由增强服务负责 | 已实现HTTP接线；没有来源或没有命中不等于已判安全 |

实现参考：[通用调查工具包装器](../../services/agents/app/investigator/tools.py)、[本地MITRE资料](../../services/agents/app/tools/mitre.py)、[hash查询工具](../../services/agents/app/tools/sandbox.py)。`lookup_file_hash`只调用lookup；文件上传、URL提交、上传同意配置等API能力没有因此成为Deep的可调用工具。

基础工具中的 `fetch_case`、`fetch_related_alerts`、图邻居等其他Python函数即使存在于代码库，也不能据此加入这5项名单；只有实际进入 `ToolRegistry` 的name才会通过这一注册表交给模型。

## 3. 11个typed调查工具

### 3.1 共同请求和返回

模型选择name和args后，Agents向 `POST /api/v1/graph/investigate/query` 发送 `{tool,args}`，带服务Bearer身份和本Run的 `X-AiSOC-Tenant-ID`。API要求 `lake:query`，以认证身份确定租户；dispatch会丢弃模型args中的 `tenant_id`。模型不提供SQL、列名或运算符。

前7项都查询ClickHouse `aisoc.raw_events`，使用固定参数化SQL和租户条件。公共返回为：

```json
{
  "tool": "process_activity",
  "available": true,
  "row_count": 0,
  "rows": [],
  "query": "processes on HOST-A in the last 24h"
}
```

`available:false`配 `reason` 表示没有查成、参数不满足或该数据类未实现；成功零行只表示指定查询/数据范围内无匹配，不证明数据充分入湖或实体安全。达到本次行数限制时可有 `truncated:true/note`。后端默认50行、最大200行；**这11份模型schema没有 `limit` 参数**，API函数另有这个参数，二者不能混为模型已获得的能力。

所有查询窗为 **`now() - lookback`**，不是告警 `event_time` 前后窗。hours上限2160小时、days上限90天。显式非正hours会归默认24；days按各函数默认及1–90天处理。因此要知道本次实际查哪个时间范围，必须看模型args及工具返回的query说明。

schema和HTTP实现见 [Agents investigation.py](../../services/agents/app/tools/investigation.py)；API入口见 [graph.py](../../services/api/app/api/v1/endpoints/graph.py)；SQL、缺源与dispatch见 [API investigation_tools.py](../../services/api/app/services/investigation_tools.py)。`GET /api/v1/graph/investigate/tools`可列出 `tools/backed_by_data/not_ingested`，它是工具能力清单接口，不是模型工具之一。

### 3.2 逐项合同

下表的后端行数限制统一为默认50、上限200；“未给参数的实际默认”与schema描述分别列明。

| 精确name | 必填参数 | 可选参数及实际默认 | 真实查询与主要rows字段 | 时间上限 | 当前实现/限制 |
| --- | --- | --- | --- | --- | --- |
| `process_activity` | `hostname: string` | `hours: integer = 24` | `src_hostname`精确匹配、`process_name`非空，时间倒序；`event_time/process_name/file_path/hash_sha256/user_name/connector_type` | 2160小时 | 已实现进程事件查询，不提供父子谱系 |
| `historical_execution` | schema无必填；后端要求 `process_name` 或 `sha256` 至少一个 | `process_name: string`；`sha256: string`；`days: integer = 30` | 同时给名称和hash时优先hash；按主机/用户聚合，返回 `src_hostname/user_name/first_seen/last_seen/executions` | 90天 | 已实现湖仓历史执行聚合，不等于完整厂商EDR历史 |
| `network_connections` | schema无必填；后端要求 `hostname` 或 `source_ip` 至少一个 | `hostname: string`；`source_ip: string`；`hours: integer = 24` | 同时提供时优先hostname；目标IP非空，按目标IP/主机/端口/协议聚合；`dest_ip/dst_hostname/dst_port/protocol/connections/last_seen` | 2160小时 | 已实现连接聚合；没有按上一个进程ID关联的参数 |
| `authentication_events` | `user_name: string` | `hours: integer = 168`（后端） | 用户名匹配、source_ip不是IPv6零值，时间倒序；`event_time/source_ip/src_hostname/connector_type/severity_id` | 2160小时 | 已实现查询，但SQL没有按认证事件类别过滤，也没有直接计算不可能旅行；共享hours schema文案写24，实际省略时168 |
| `fleet_ioc_hunt` | `indicator: string` | `days: integer = 30` | 在source_ip、dest_ip、dst_hostname、hash_sha256、iocs匹配；按主机/用户/连接器聚合；`src_hostname/user_name/connector_type/first_seen/last_seen/hits` | 90天 | 已实现全湖指标检索；不是自动调用客户SIEM/EDR的工具 |
| `entity_timeline` | schema无必填；后端要求 `hostname` 或 `user_name` 至少一个 | `hostname: string`；`user_name: string`；`hours: integer = 24` | 同时提供时优先hostname；事件正序；`event_time/connector_type/user_name/src_hostname/process_name/source_ip/dest_ip/severity_id/mitre_techniques` | 2160小时 | 已实现原事件时间线；受行数和入湖范围限制 |
| `technique_activity` | `technique_id: string` | `days: integer = 7` | 按mitre_techniques数组匹配，主机/用户/连接器聚合；`src_hostname/user_name/connector_type/events/last_seen` | 90天 | 已实现同技术事件聚合，技术标签本身不是攻击成功证据 |
| `process_tree` | `hostname: string` | `pid: integer` | 无查询；返回 `available:false`，reason说明缺父进程/进程GUID等谱系数据 | 不适用 | **占位，当前函数无条件unavailable** |
| `mailbox_activity` | `user_name: string` | 无 | 无查询；返回邮箱审计未接入说明 | 不适用 | **占位，当前函数无条件unavailable** |
| `oauth_grants` | `user_name: string` | 无 | 无查询；返回OAuth授权数据未接入说明 | 不适用 | **占位，当前函数无条件unavailable** |
| `persistence_mechanisms` | `hostname: string` | 无 | 无查询；返回run keys、计划任务、launch agents、cron等持久化数据未接入说明 | 不适用 | **占位，当前函数无条件unavailable** |

最后4项故意保留在模型工具列表中，使模型可以收到明确的资料缺口。源码reason虽提示可连接EDR、M365、Entra等，**仅配置连接器不会使当前4个函数自动可用**：仍需补数据合同、采集/存储和具体查询接线。当前阶段只记录该设计，不新建缺失后端。

## 4. 6个customer工具及动态注册

customer目录定义于 [customer_tools.py](../../services/agents/app/tools/customer_tools.py)，真实可提供列表由 `scoped_customer_tools(runTenant)`决定。先固定GET `/api/v1/agent-tools/backends`：

- `siem_search.enabled=true` 且 `backends`非空，才注册 `siem_indicator_search`。
- `vendor_reads`包含对应capability，才注册对应vendor工具；API依租户已配置且启用的连接器、允许能力及Actions只读能力注册表确定它。
- 后端发现失败时不把整个目录盲目注册，返回无工具及coverage说明；“发现不到”不能写为“租户没有这个系统”。

customer模型schema不接受原始查询语句或租户。`*`为必填；无星号为可选。`hours`是integer，其余下表参数是string。

| 精确name与schema | 真实后端/调用 | 主要输出 | 时间/上限与实现边界 |
| --- | --- | --- | --- |
| `siem_indicator_search(indicator_type*, value*, hours=24)` | `POST /api/v1/agent-tools/siem-search`，API按指标类型为该租户各SIEM选固定字段并做联邦检索 | `available/outcome/indicator/window_hours/sightings/rows/sources`；partial附失败源，截断附说明 | 24小时默认；API允许1–168小时；最多40行，按`len(repr(rows))`的24000阈值裁剪，并非严格UTF-8字节限额，之后仍受ToolMessage限制 |
| `edr_host_details(hostname*)` | vendor-read capability=`get_host`；经API/Actions调用租户EDR | `available/outcome/vendor/summary/data`，data为厂商投影的主机状态、平台、最后在线等 | 无模型时间参数；真实字段依厂商，不能统一承诺所有字段都有 |
| `edr_host_detections(hostname*)` | capability=`get_detections` | 同一vendor返回包，data为厂商检测记录 | 无模型时间参数；具体历史范围依实现，不能写成查了全部EDR历史 |
| `identity_user_activity(user*, hours)` | capability=`get_user_activity` | 身份系统只读投影，具体状态/活动/风险字段依厂商 | schema说明24小时默认、上限720小时；Entra/Google有活动窗口，当前Okta执行器主要读取账号当前status，未使用hours，不能统一承诺登录历史 |
| `cloud_audit_lookup(principal*, hours, attribute_key)` | capability=`lookup_cloud_audit` | 云控制面活动投影；vendor包同上 | schema说明hours默认24、上限720；`attribute_key`枚举 `Username/EventName/ResourceName/AccessKeyId`，默认Username |
| `endpoint_telemetry_sightings(indicator*, template*, hours)` | capability=`lookup_endpoint_telemetry` | 终端hunting模板查询结果投影；vendor包同上 | schema说明hours默认24、上限720；template枚举 `file_hash_sightings/process_sightings/network_sightings/logon_sightings`，不接受任意hunting query |

`indicator_type`闭集为 `domain/hostname/ip/md5/process_name/sha1/sha256/url/username`。vendor API还限制允许参数、将hours夹在1–720，并限定limit不超过50；vendor工具schema本身没有limit，实际记录范围仍以厂商返回为准。源码参考：[API agent-tools入口](../../services/api/app/api/v1/endpoints/agent_tools.py)、[SIEM查询](../../services/api/app/services/agent_tools/siem_search.py)、[vendor读治理](../../services/api/app/services/agent_tools/vendor_reads.py)、[当前厂商执行器](../../services/actions/app/live_actions/investigation_reads.py)。

vendor读只有收到 `executed=true` 才返回成功数据；`simulated/dry_run/no_integration/unsupported/blocked/failed`等均转换为 `available:false/outcome:could_not_check`。这是“只读查询真正触达厂商”的边界，不代表该数据本身已证明告警结论。工具默认HTTP截止30秒；本目录不据源码目录推定任何租户已完成厂商联调。

## 5. 租户MCP工具

MCP不属于固定16项，也没有一份跨租户固定参数表。配置和schema经过以下来源交接：

| 配置/资料 | 当前来源与作用 |
| --- | --- |
| 哪些服务器进入调查 | API `GET /api/v1/mcp-servers/resolved?tenant_id=<本Run租户>` 返回该租户启用的服务器和已解密连接资料；凭据不由模型输入 |
| 服务连接参数 | `name/transport/url`，或stdio的 `command/args`；`auth`为完整header映射，不由客户端猜Bearer前缀 |
| 工具范围 | 租户服务器配置中的 `tool_allowlist`，默认空即不提供工具；不是把服务器所有工具自动给模型 |
| 工具描述与参数 | 服务器 `list_tools` 返回的name、description、inputSchema及annotations，经本地审核/清理后成为Tool的description/parameters |
| 模型看到的name | `mcp__<server>__<tool>`，各段转义，最终函数名须满足provider字符及64字符长度要求；不是旧的点分名字 |
| 每次调用界限 | server `timeout_seconds`默认20、夹在1–120秒；`max_response_bytes`默认65536、夹在1024–1048576字节；实际ToolMessage仍最多4000字符 |

服务器允许 `streamable_http` 或受控stdio。stdio默认关闭，需 `AISOC_MCP_STDIO_ENABLED` 和 `AISOC_MCP_STDIO_ALLOWED_COMMANDS`同时满足，参数也检查不允许的shell字符；网络连接另走现有地址/SSRF保护。工具须在白名单内，拒绝 `destructiveHint=true` 或 `readOnlyHint=false`，并拒绝描述/schema中发现的指令注入；未标注的工具并非天然安全，当前源码是在操作人白名单授权且其他检查通过后接入。

每次dispatch会重新审核该工具，不只在发现时检查。返回作为不可信第三方资料附来源和nonce边界；失败返回 `available:false`及原因。**当前Deep MCP不开放状态修改工具**；不能从项目其他MCP API支持审批，反推此工具循环能执行写操作。

来源：[MCP注册表客户端](../../services/agents/app/mcp/registry_client.py)、[配置解析](../../services/agents/app/mcp/config.py)、[发现/执行](../../services/agents/app/mcp/tools.py)、[准入及命名](../../services/agents/app/mcp/policy.py)。MCP工具的具体参数表必须看本Run实际发现/绑定的schema，不能用别的租户或旧Run名单代替。

## 6. 配置分别由谁决定

| 配置类别 | 主要位置/当前值 | 对工具使用的作用 |
| --- | --- | --- |
| 是否走Deep与循环界限 | `AISOC_DEEP_INVESTIGATION`默认true；`AISOC_DEEP_INVESTIGATION_MAX_ITERS`默认6；`AISOC_DEEP_INVESTIGATION_BUDGET_SECONDS`默认120；`AISOC_DEEP_INVESTIGATION_MAX_TOKENS`默认60000；外层Graph还有自己的预算 | 只有调用路径实际进入Deep才使用本目录；这些设置不代表每条Case调查都采用Deep，不代表模型一定调用6次工具 |
| 固定16项工具范围 | `default_registry`和`investigation_tools`源码 | 当前没有针对每一个固定工具的统一租户开关；schema字段和后端能力是开发合同，不能靠提示词把占位变实现 |
| 本Run查询参数 | 模型 `tool_calls.args`中的实体、hours/days等 | 决定本次查谁/查多长；受具体工具约束，不是operator给所有工具共用的一份固定查询 |
| 增强服务地址 | `ENRICHMENT_SERVICE_URL`，默认 `http://enrichment:8080` | 基础enrich_ioc直接调用此服务；其缓存/Feed/供应商配置由增强服务负责 |
| typed/customer/sandbox API地址及身份 | `AISOC_API_URL`默认 `http://api:8000`；`AISOC_API_SERVICE_TOKEN`优先，回退 `AISOC_SERVICE_TOKEN`；另带本Run `X-AiSOC-Tenant-ID` | API分别校验权限：typed为lake:query；customer后端发现/SIEM为connectors:read，vendor读为actions:read；hash查询为threat_intel:read |
| 客户SIEM/厂商可用性 | API `AISOC_FEATURE_FED_SEARCH`源码默认true；租户连接器启用、能力许可、凭据和Actions只读实现 | SIEM需开关与实际后端，厂商需对应连接器/能力；源码默认开不等于部署已接通 |
| 沙箱provider | API的provider注册配置；例如 `AISOC_CAPEV2_URL/TOKEN`、`AISOC_MALWAREANALYZER_ENABLED`及现有隔离策略 | lookup能否得到真实报告取决于provider；无真实provider时原mock不产生真实厂商分析证据，lookup工具不开放上传 |
| MCP配置读取身份 | `AISOC_AGENTS_SERVICE_TOKEN`优先，回退 `AISOC_SERVICE_TOKEN`；以 `X-AiSOC-Service-Token`访问resolved路由；`AISOC_MCP_REGISTRY_TIMEOUT_S`默认5秒 | 这与前一行API Bearer reader用途不同；仅设置 `AISOC_API_SERVICE_TOKEN`不能据此推定MCP registry已获访问身份 |
| MCP租户和进程配置 | 租户服务器启用/连接/白名单/单服务上限；stdio两个环境设置见上节 | 决定本Run额外工具；未启用、空白名单或发现失败不等于服务器数据为空 |
| Case默认流程/Router开关 | `AISOC_INVESTIGATE_USE_ROUTER` | 在两种Case编排间选择，本身不把Deep的16个工具绑定给Router或默认四节点模型 |

这些是当前源码中的配置名和默认值，没有读取部署凭据，也没有宣称当前20/21的实际配置与源码默认相同。具体本地调用准备和最少测试见[使用指南](../operations/investigation-tools.md)，无需为查看目录先发起模型或修改运行设置。

## 7. 图、链、UEBA、KB为什么不另加进这16项

| 能力 | 当前如何交接 | 与模型工具目录的关系 |
| --- | --- | --- |
| Attack Chain/Case Attack Path/Alert图 | 准备阶段按显式Case/Alert查询；Bundle保存完整快照及有界 `model_summary`，后者送模型 | 本轮是固定预取接线，没有增加 `get_attack_chain/get_attack_path` 等Deep tool schema；工具代码存在不等于被本registry注册 |
| 通用图邻居/影响范围、机构记忆、事件上下文 | ContextBundle按当前输入并行预取并标明来源/失败 | 成为输入摘要，不是Deep每轮自行决定调用这些Python函数 |
| UEBA | Bundle查询已有基线/偏离结果 | 模型不通过固定16项启动基线学习或重新计算UEBA；输入有结果与实际结果可用是两回事 |
| KB | 默认四节点通过原知识预取/`knowledge_prompt_append`交接本Run资料和引用边界；其他路径是否看到资料须核实际消息，不能因state存有资料便追认Deep已消费 | 不是把整个知识库给模型，也没有因此注册一个通用任意知识检索工具 |
| 默认四节点的IOC增强 | Recon解析后，代码固定遍历IOC调用enrich_ioc并缓存 | 复用同一Python函数，不等于Recon模型已发 `tool_calls`；模型选择工具循环是Deep路径的行为 |

见[ContextBundle](../../services/agents/app/context/bundle.py)、[链图适配](../../services/agents/app/context/attack_context.py)、[Deep首轮投影](../../services/agents/app/investigator/deep_investigation.py)、[默认Recon](../../services/agents/app/investigator/recon_agent.py)。完整快照留在state/工件，不代表所有原字段都送入模型；例如原Forensic/Report增强摘要可只呈现 `dict(15 keys)`，不能声称模型已看到这些字段的值。

## 8. 既有证据与测试入口索引

### 8.1 已有实际证据可以证明什么

[2026-10-21本地调查回执第5节](../operations/investigation-functional-20261021.md#5-deep模型怎样决定用工具)保留一条Deep旧Run：模型获16份schema，6轮真实回复，7个工具实际执行，21,540 tokens；认证查询当时失败，3次湖仓查询成功但零行，3类占位均返回不可用；最后 `network_connections`虽被请求，预算触发后**未执行**。`narrative`为空且 `truncated=true`，不能写成完整调查/报告成功，也不能把这条证据扩大为全部16工具逐项真实通过。

该回执中工具call-id和下一轮ToolMessage已核对。后续认证IPv6合同最小修正、单IOC `ioc_type`请求修正及对应实际接缝验证仍以原回执为准；旧失败不改写。默认四节点的两个真实单IOC200只证明该HTTP查询返回，若来源为空、引擎及置信度为0，不证明指标安全，更不证明Deep模型选择并使用过该工具。

customer与MCP的单元/受控传输测试不能代替本项目租户真实SIEM、EDR、身份系统或MCP部署接入证据。当前目录按实现和使用合同记录，不为填满测试状态重跑旧Run、完整工具矩阵或复杂可用性专项。

### 8.2 现有测试文件及用途（本轮未执行）

下表是按需选择入口，不是一份要求每次全部执行的清单。“现有”仅表示源码有该测试；是否已运行及结果须看对应原回执，不能从本表追认通过。

| 文件 | 核对目的/适用改动 |
| --- | --- |
| [Agents test_tool_calling.py](../../services/agents/tests/test_tool_calling.py) | 基础registry的OpenAI schema、真实本地规则函数、未知工具、模型替身选择→执行→下一轮、轮数上限 |
| [Agents test_socai2_tool_failure.py](../../services/agents/tests/test_socai2_tool_failure.py) | 单IOC HTTP的 `{value,ioc_type}`合同；直接/缓存失败不在审计中记成功 |
| [Agents test_sandbox_tool.py](../../services/agents/tests/test_sandbox_tool.py) | hash lookup schema、已知/未见/pending/错误语义，不执行上传 |
| [API test_sandbox_providers.py](../../services/api/tests/test_sandbox_providers.py)、[test_sandbox_upload_policy.py](../../services/api/tests/test_sandbox_upload_policy.py)、[test_sandbox_settings_reach_the_api.py](../../services/api/tests/test_sandbox_settings_reach_the_api.py) | provider响应、hash先查、缺源/隔离/上传同意边界及配置能否到API；不据此声称Deep拥有上传工具 |
| [API test_investigation_tools.py](../../services/api/tests/test_investigation_tools.py) | typed工具租户SQL、参数/行数/时间范围、IPv6列类型、占位与湖仓异常；主要使用查询替身，不代表真实入湖覆盖 |
| [Agents test_deep_investigation.py](../../services/agents/tests/test_deep_investigation.py) | 策略选择、首轮投影、缺源/失败、工具深度统计及结果文字；不是每个工具后端联调 |
| [Agents test_tool_result_channel.py](../../services/agents/tests/test_tool_result_channel.py) | ToolMessage唯一渲染入口、静态工具名目录一致性、伪造工具结果识别；不是后端数据质量评测 |
| [Agents test_customer_tools.py](../../services/agents/tests/test_customer_tools.py) | 6项schema无任意query、枚举/模板、HTTP参数、租户后端筛选、空/部分/失败返回边界 |
| [API test_agent_tools.py](../../services/api/tests/test_agent_tools.py) | SIEM指标类型、参数白名单/上限、只读能力治理、来源与结果投影、客户端路由前缀 |
| [Agents test_deep_investigation_customer_tools.py](../../services/agents/tests/test_deep_investigation_customer_tools.py) | customer工具可装入Deep及受控调用/失败/覆盖缺口交接；不等于接到真实客户产品 |
| [Agents test_mcp_registry_client.py](../../services/agents/tests/test_mcp_registry_client.py) | resolved路由前缀、服务身份和租户交接、注册表失败不当作空列表 |
| [Agents test_mcp_client.py](../../services/agents/tests/test_mcp_client.py) | MCP白名单、只读/破坏注解、dispatch复查、注入描述/结果、截止与响应大小边界 |
| [Agents test_mcp_real_transport.py](../../services/agents/tests/test_mcp_real_transport.py) | 受控本地MCP传输及实际provider可接受的函数名字；名称“real”不等于项目真实租户已部署 |
| [Agents test_mcp_investigation.py](../../services/agents/tests/test_mcp_investigation.py) | MCP工具接入Deep、工具/拒绝审计、Run/tenant及账本序号交接 |
| [API test_mcp_registry.py](../../services/api/tests/test_mcp_registry.py) | 服务器租户配置、启用状态、凭据处理、resolved内部服务身份、URL/参数边界 |
| [Agents test_attack_context.py](../../services/agents/tests/test_attack_context.py)、[test_attack_context_orchestration.py](../../services/agents/tests/test_attack_context_orchestration.py)、[API test_investigation_attack_context.py](../../services/api/tests/test_investigation_attack_context.py) | 固定链图准备/读取、读写身份、摘要可见及Run工件；证明预取接线，不增加或验证16项模型工具 |

只有当前改动触及的直接功能才选对应测试，优先复用已有有效回执；发现的非阻塞问题沿[现有问题登记](../operations/upstream-issues.md)后续评估。当前功能目录不另设逐工具可用性、重启/恢复或多模型全矩阵作为继续开发前置。
