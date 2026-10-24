# 外部HTTP数据接口：Tool接入与执行验证设计

2026-10-21。**仅设计，未实现、未连接厂商、未发HTTP或模型、未运行功能测试。** 用户重点是接入厂商已经开放的HTTP数据接口，并验证自己设计的Tool实际执行正确。我们在内部保留统一查询，由adapter转换厂商请求；不要求厂商新增接口、改字段或接收UnifiedQuery，也不预先要求厂商支持全部算子。

现有实现见[SIEM接入说明](../operations/siem-tool-integration.md)、[工具目录](investigation-tool-catalog.md)及[执行/配置/测试指南](../operations/investigation-tools.md)。本设计沿[当前OpenSpec change](../../openspec/changes/archive/2026-10-24-restore-alert-investigation-integrity/design.md)2.1/4.1记录，不改变当前业务/模型schema/配置；未来实施前补必要规格和任务，原5/15保持。

## 1. 接什么：外部HTTP接口保持原样

```mermaid
flowchart LR
    A[Deep提出结构化tool_call] --> B[已注册Tool包装器]
    B --> C[可信API按tenant选择凭据和后端]
    C --> D[厂商adapter转换请求]
    D --> E[厂商已有GET或POST接口]
    E --> F[adapter校验并转换事件行]
    F --> G[API来源/合并/有界结果]
    G --> H[匹配call id的ToolMessage]
    H --> I[下一轮模型]
```

同属SIEM事件补查时优先复用当前`siem_indicator_search(indicator_type,value,hours)`，在厂商query adapter及必要的类型/服务接线处扩展，不必每个厂商再造模型工具。资产详情、信誉查询等不能用指标事件查询表达的业务，可以增加一个明确命名、限定参数的Tool；其HTTP包装与验证方式相同。

当前固定16工具中没有任意URL请求工具。仅写一份schema、填connector URL或把工具名字放进prompt，都不会让模型实际执行HTTP。独立connectors查询运行服务尚未迁入，支持的SIEM类型仍只有四种原产品；这些缺口要在未来接入时处理，本设计不声称现已可用。

## 2. 每个接口需要确定的最小合同

| 项目 | 从厂商说明确认什么 | adapter负责什么 |
| --- | --- | --- |
| 能力 | 查主机事件、账号活动、IP记录还是资产详情 | 只声明实际支持的实体/条件，不能把主机接口说成全能检索 |
| 请求 | method、固定base URL/path、URL参数或JSON body | 将内部条件放到厂商要求的位置；URL和路径由配置确定，不让模型任意指定 |
| 认证 | API key/Bearer/Basic/OAuth或签名 | 从该tenant实例的加密auth_config取凭据；按原合同设置header/token，不把凭据交模型 |
| 条件 | 哪些字段、精确还是模糊、支持哪些操作符 | 固定字段/算子映射；不能把eq悄悄变成全文模糊检索 |
| 时间 | 参数名、UTC/本地时区、ISO8601/Unix秒/毫秒、端点包含规则 | 转换实际查询窗口并记录采用范围；没有时间条件时明确覆盖限制 |
| 响应 | 数组在顶层、events[]还是data.items[]，业务成功码 | 明确路径提取/校验，不猜响应、不把缺结构当空列表 |
| 分页 | page/offset/cursor，是否has_more/next_cursor | 只取本次有界样本；不知完整性时标未知，不把第一页当全部 |
| 输出字段 | time/device/account/src_ip等各自含义 | 映射到内部可识别的扁平标准键；不从字段名猜业务含义 |

简单同步GET/POST可以用固定adapter或有限模板实现；本轮不设计通用模板语言。所谓method/path/request_map/response_map目前只是配置设计概念，**当前connector_config没有能自动解释任意HTTP映射的执行器**。异步查询任务、轮询、特殊签名、复杂分页或多接口合并通常要写该厂商adapter，仍无须厂商改API。

## 3. 完整例子：厂商只开放GET主机事件

### 3.1 厂商既有接口（假设）

以下接口和数据完全是假设，所有示例未执行。

```http
GET https://vendor.example.invalid/v1/events?host=TEST-WIN-01&from=2026-10-20T09:00:00Z&to=2026-10-21T09:00:00Z&limit=40
Authorization: Bearer <vendor-read-token>
```

假设接口合同规定：host为精确主机名，from/to是UTC事件时间，区间为[from,to)，正常响应总含events和has_more：

```json
{
  "code": 0,
  "events": [
    {
      "id": "vendor-event-001",
      "time": "2026-10-21T08:30:00Z",
      "device": "TEST-WIN-01",
      "account": "demo.user",
      "process": "powershell.exe",
      "summary": "HTTP-TOOL-SAMPLE-001"
    }
  ],
  "has_more": false
}
```

这不是要求真实厂商采用此合同。如果厂商只支持模糊host、时间采用毫秒或成功码不是0，就按真实说明调整，不照搬示例。

### 3.2 内部Tool到UnifiedQuery

当前SIEM工具模型参数为：

```json
{"indicator_type":"hostname","value":"TEST-WIN-01","hours":24}
```

新类型若采用标准字段，API侧固定hostname→host.name，形成现有统一对象：

```json
{
  "free_text": "",
  "indicators": [{"field":"host.name","operator":"eq","value":"TEST-WIN-01"}],
  "since_seconds": 86400,
  "limit": 40
}
```

厂商不接收这份对象；adapter执行以下转换。假设当前时刻为2026-10-21T09:00:00Z：

| 内部输入 | 出站HTTP |
| --- | --- |
| host.name eq TEST-WIN-01 | query参数host=TEST-WIN-01，使用HTTP客户端参数编码 |
| since_seconds=86400 | to=本次UTC时刻；from=to-86400秒；按厂商要求格式化 |
| limit=40 | query参数limit=40 |
| 当前tenant实例的token | Authorization header；不传模型提供的tenant或凭据 |

query(unified)在此源只支持`host.name/eq`。若收到username/IP/hash、非空free_text、其他算子或多条件，而厂商无法精确表达，则返回明确不支持，不忽略条件后继续查。原统一协议虽定义10种算子，这不表示每个HTTP源必须实现它们；当前Deep实际也只生成eq。

### 3.3 返回字段转换

| 厂商字段 | 内部标准字段 | 规则 |
| --- | --- | --- |
| time | @timestamp | 验证/转换为UTC事件时间，不能用查询时刻替代 |
| device | host.name | 保留源主机值；不自动把短名当FQDN |
| account | user.name | 保留源账号；不自动补域/推断身份 |
| process | process.name | 原进程名称，不因出现PowerShell就标恶意 |
| summary | _raw_summary | 有界原文摘录，裁剪须可辨；不是模型生成的事实 |
| id | event.id（拟议） | 当前API投影会丢此键；后续若需精确引用须显式加白名单，不能声称已透传 |

adapter先得到标准事件行：

```json
{
  "@timestamp": "2026-10-21T08:30:00Z",
  "host.name": "TEST-WIN-01",
  "user.name": "demo.user",
  "process.name": "powershell.exe",
  "_raw_summary": "HTTP-TOOL-SAMPLE-001"
}
```

采用扁平键`host.name`，不期待现有API自动展开嵌套ECS。原query运行服务沿`{connector_id,row_count,rows}`返回给API，再由API添加可信实例来源和裁剪；厂商不能用_source或_aisoc_source覆盖tenant/实例归属。

HTTP200、code=0、正确events=[]才是本次成功无匹配。HTTP401/403/5xx、业务码失败、events缺失/类型错误或时间格式错误，都不能转换成成功空列表。没有某条可选字段时保留未知；整个接口不提供某类查询能力时明确不支持。

## 4. 若厂商是POST、IP或其他业务接口

若厂商已经采用POST请求，也无需统一它的URL和字段：

```http
POST https://vendor.example.invalid/openapi/search
X-API-Key: <vendor-key>
Content-Type: application/json

{"filter":{"field":"src_ip","op":"equals","value":"192.0.2.17"},"start_ms":1792486800000,"end_ms":1792573200000,"page_size":20}
```

上例时间意指与第3节相同的UTC范围；只是静态请求形状，接入时需核实际时区/单位和时间换算。source.ip/eq可映射成src_ip/equals；从data.items等约定路径取行；毫秒转UTC标准时间。若另有dst_ip条件，目的IP查询另发一份，沿当前合并流程处理。**把源/目的两个条件同时放在UnifiedQuery.indicators里是AND，不是OR。**

IP源不支持目的IP时应标覆盖缺口；只支持账号详情的API也不能假装返回账号登录事件。资产/信誉等业务可用独立typed Tool直接表达目的，无须硬转成事件搜索或SQL。

分页遇next_cursor可按厂商合同继续取，直到达到本次limit或结果耗尽；分页中断不能报告完整查询成功。若达到limit但has_more=true，只能称有界样本。当前query→list和API只读rows的接缝不会自动传has_more/total/cursor，上游截断需要后续最小元数据透传；未接前标“上游完整性未知”，不能凭API截断=false声称上游完整。

## 5. 自己设计一个Tool，具体怎样接入

以下`vendor_host_events`仅为新Tool命名示例，**当前源码没有这个工具**。若业务就是前述SIEM补查，优先复用siem_indicator_search；新Tool适用于独立业务，或先在隔离测试中验证包装器。

拟议的最小模型合同：

```json
{
  "type": "function",
  "function": {
    "name": "vendor_host_events",
    "description": "Read events for an exact hostname from the configured vendor source. Returns bounded observations or an explicit query error.",
    "parameters": {
      "type": "object",
      "properties": {
        "hostname": {"type":"string","minLength":1},
        "hours": {"type":"integer","minimum":1,"maximum":168,"default":24}
      },
      "required": ["hostname"],
      "additionalProperties": false
    }
  }
}
```

接入包含四个实质位置：

1. **Tool定义和执行函数：** schema的name/parameters与真正fn签名一致。fn/后端显式验证hostname、hours；现有ToolRegistry不提供通用JSON Schema运行时校验，不能只写schema便认为非法参数一定被拦下。
2. **真实HTTP包装：** 可信后端选择tenant实例及凭据，adapter按第3节发送请求并转换响应。不把HTTP改成返回一份固定成功字典就算接通。
3. **注册进实际调用路径：** 新Tool放进本次Deep使用的registry/bind_tools清单，按实际后端能力条件开放。只在别的文件定义函数无效；Case默认四节点和Router没有Deep自主工具循环，不能用那两个入口验证模型选Tool。
4. **结果交接：** fn真实返回结构送进ToolMessage，下一轮模型可见。仅日志打印结果、没有返回给loop，也不算模型已收到。

复用现有SIEM工具时，改动在新vendor adapter、query服务注册/运行、API支持类型及指标映射；独立Tool还需要schema/包装器和相应受控API能力接缝。具体未来API路由随实施规格确定，本文不把假设路由说成现已可用。

## 6. 验证方式：从固定调用到模型选择，四层就够

### 6.1 先固定一次HTTP请求，确认数据合同

用厂商测试环境或本地HTTP替身准备唯一样本TEST-WIN-01＋HTTP-TOOL-SAMPLE-001，固定窗口和参数。手工HTTP客户端读取，核状态、业务码、数组位置及字段。这一步不需要模型。

- 命中：确实返回预置标记及预期主机/时间。
- 正常空：对另一不存在的主机返回正确空数组。
- 明确错误：如无效参数或上游失败，包装器不能伪装成0条。

本地替身只证明约定格式可处理，不能冒称真实厂商已连通。接真实接口后替换相同数据合同的目标再核一次，不扩复杂故障矩阵。

### 6.2 直接执行注册Tool，证明它确实发出了HTTP

测试设计：用本tenant的registry直接执行`execute("vendor_host_events", {"hostname":"TEST-WIN-01","hours":24})`，截获最末端的出站HTTP请求，并保留脱敏原响应。

必须断言：实际method/path、host参数、from/to及单位、limit、认证位置正确；厂商接口调用次数符合预期；返回的标准行含真实fixture标记。固定时间样本测试应固定测试时钟，或使用本次窗口内的新样本，避免时间漂移造成假空。此时LLM不参与，证明Tool执行函数和HTTP数据适配接通，不能写“模型自主调用通过”。若前面经API，需核API之后的厂商出站请求，不能只看Agents调用本地API成功。

### 6.3 用脚本模型强制一条tool_call，证明循环交接

模型替身第1轮明确返回：

```json
{
  "tool_calls": [{
    "name": "vendor_host_events",
    "args": {"hostname":"TEST-WIN-01","hours":24},
    "id": "call-http-demo-001"
  }]
}
```

第2轮检查收到的messages，核存在`ToolMessage.tool_call_id == "call-http-demo-001"`，且正文包含HTTP-TOOL-SAMPLE-001及正确主机/时间；同时使用第6.2节HTTP观察断言。随后返回一条简短完成文本即可。

```text
脚本模型发结构化调用
  → 原run_with_tools调用registry.execute
  → 真包装器请求本地HTTP替身/授权厂商测试环境
  → 行映射后回到ToolMessage
  → 截获下一轮messages核call id与数据标记
```

这一步验证的是协议交接，不是让假模型自行挑工具。复用[test_tool_calling.py](../../services/agents/tests/test_tool_calling.py)的脚本模型方式，显式增加next messages捕获才可断言call id；原测试本身不能被描述成已核全部证据。[test_tool_result_channel.py](../../services/agents/tests/test_tool_result_channel.py)主要核唯一渲染/4000字符边界，不代替此循环断言。本文没有新增或运行测试。

### 6.4 最后才用一次真实模型验证会不会选用

需要验证真实选择时，使用新输入，例如“请查询TEST-WIN-01最近24小时在已配置厂商中的事件，并说明查询范围”。确认入口确实是Deep、模型请求中带此schema、回包真正有对应tool_calls，再读HTTP执行与下一轮ToolMessage。

真实模型可能不选该Tool；这时不能把“提供了工具”写成“工具已执行”。也不为凑答案连续重调。先看schema/description、策略和入口是否合适，再决定后续修改。模型正文写“已查询”不作为执行证据；返回一句正确答案也可能来自原prompt，须沿下表核实。

## 7. 怎样判定“正确执行”，各证据证明什么

| 证据 | 通过判据 | 还不能证明什么 |
| --- | --- | --- |
| 注册清单 | 本次bind_tools实际含精确工具名和schema | 不证明模型请求过 |
| 模型结构回复 | tool_calls.name/args/id与目标一致 | 不证明fn或HTTP成功 |
| 执行记录 | 原loop实际进入对应fn，参数一致 | 不证明最末端厂商接口已被调用 |
| 出站HTTP及响应 | method/path/条件/时间/tenant实例正确；返回原样本标记或明确错误 | HTTP200本身不证明业务成功，也不证明全部历史已查 |
| 标准结果 | 原返回字段按合同映射，空/失败分开 | 不证明下一轮模型收到 |
| 下一轮模型输入 | 匹配call id的ToolMessage含标记和范围/缺口 | 不证明模型正确解释或最终引用 |
| 最终结果/Run工件 | 能定位实际使用记录及结论依据，未超证据陈述 | 不证明未接数据源、全量覆盖或服务可用性 |

本轮建议最小功能验收为：一条已知命中贯穿HTTP→fn→ToolMessage、一条正常空、一条明确失败；涉及tenant接线时复用原越权断言。第6.3层先用脚本模型，真实模型选择需要时只补一个代表案例。服务重启、压力、恢复、复杂分页矩阵均后置，不作为当前合同设计前置。

当前tool_trace/ledger一般保存tool、args和约200字符result_preview；ToolMessage通常还会约4000字符裁剪，不默认持久保存全部原HTTP行。协议内call id已经存在，但现有registry.execute只接name/args，**call id不会自动贯穿到厂商HTTP header**。

未来若需一眼串联生产执行，最小补充是由可信编排上下文记录run_id/tool_call_id/http_trace_id及脱敏参数、状态/结果标记；不让模型指定凭据或以model args注入租户。未实现该接缝前，本地测试观察器可截获模型消息、fn入参及出站请求逐项比对，不能声称已有全链关联日志。厂商不支持回显request id也不影响我们记录自己的出站调用。

## 8. 未来实施位置与当前限制

- SIEM HTTP源：按[SIEM说明](../operations/siem-tool-integration.md)接新query adapter、受支持类型和指标映射，复用原工具与原编排；只做查询，不顺带迁采集。
- 新业务Tool：沿[ToolRegistry](../../services/agents/app/tools/registry.py)、[条件customer组装](../../services/agents/app/tools/customer_tools.py)及[Deep组装](../../services/agents/app/investigator/deep_investigation.py)接入；不能新增文件后便宣称bind成功。
- 结果证据：现有API投影不保留event.id、部分hash字段或顶层窗口/截断元数据；需要精确引用时最小补传，不能靠第三方多返回几个字段自动生效。[当前投影/合并](../../services/api/app/services/agent_tools/siem_search.py)还可能按投影内容合并不同事件/同类型实例，因此sources.rows不是上游命中总数。
- 相对时间：UnifiedQuery目前只有since_seconds、最多7天；当前Deep API为1–168小时/最多40行。绝对告警时间窗口、分页和自由SQL不因本设计而已支持。

本轮只交付设计与最少验证方法，尚未确定实际厂商API、实现adapter/Tool、接线配置或运行任何样例。来源为当前API/Agents及固定原版[统一查询](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors/app/federated/query.py:94)，不把设计目标当现有功能。
