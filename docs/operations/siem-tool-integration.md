# SIEM调查工具：第三方HTTP接口如何接入与测试

2026-10-21。当前没有提供真实SIEM产品、地址或凭据。本文以**假设的第三方HTTP事件查询接口**说明如何准备合同、配置和分层验证；示例均未执行，不代表新适配器已实现、服务已部署或真实模型已调用。调查工具总览见[调查工具说明](investigation-tools.md)。

当前API、Agents中的SIEM查询客户端已迁入，但独立`services/connectors`查询运行服务尚未选入本轮源码迁移/部署，见[功能对照](alert-function-alignment.md#确实尚未迁入的是独立模块不是上述服务内裁剪)。因此不能仅配置一个SIEM地址，就认为调查能够读取它。

厂商已有HTTP接口的适配与“自己设计的Tool怎样验证实际执行”，见[具体设计/四层验证](../architecture/third-party-search-contract.md)。沿原GET/POST接口做转换，不要求厂商新增统一查询API；该设计尚未实施或运行。

## 1. 现有链路与需要准备的东西

```text
Deep调查模型选择 siem_indicator_search(type, value, hours)
  → Agents携带本次tenant调用API /agent-tools/siem-search
  → API从PG connectors表找同租户、已启用、支持联邦查询的实例
  → API解密auth_config
  → connectors服务 /api/v1/connectors/{connector_type}/query
  → 产品适配器转换请求，访问第三方SIEM HTTP接口
  → 适配器返回事件行，API合并/裁剪并标记来源和查询状态
  → 工具结果回到Deep，作为后续模型输入中的证据材料
```

这是调查时的**按需直接查询**，可以读取AISOC没有预先采集的日志。连接器的`fetch_alerts`轮询、规范化、送入告警链是另一条采集流程；接通调查查询不要求同时启用采集，也不改变当前raw处理职责。

| 内容 | 当前合同与用途 |
| --- | --- |
| 上游查询合同 | 产品/API版本、URL与路径、认证、可查询字段、时间格式、分页/限量、成功与错误响应；“提供HTTP接口”还不足以确定这些信息 |
| PG连接器实例 | `tenant_id/name/connector_type/is_enabled/auth_config/connector_config`；由API管理，不让模型传入地址、凭据或tenant |
| `auth_config` | token、API key、密码等凭据；创建/更新时由API凭据库加密保存，查询时解密 |
| `connector_config` | 地址、索引/表、TLS等非秘密选项；作为普通JSON保存。秘密应放入`auth_config` |
| 查询执行服务 | 当前API会转发给`CONNECTORS_SERVICE_URL`，源码默认`http://connectors:8003`；这个地址指适配器服务，**不是上游SIEM地址** |
| API→connectors身份 | `AISOC_CONNECTORS_SERVICE_TOKEN`，未设置则使用`AISOC_SERVICE_TOKEN`，并传`X-AiSOC-Tenant-ID` |
| Agents→API身份 | `AISOC_API_URL`默认`http://api:8000`；`AISOC_API_SERVICE_TOKEN`优先，否则`AISOC_SERVICE_TOKEN`；本次tenant由Run传递 |
| 功能开关 | API的`AISOC_FEATURE_FED_SEARCH`源码默认true；false时SIEM查询入口404、发现接口不提供SIEM后端。开关不会安装服务或补连接器资料 |
| 权限 | 目录、实例列表、工具发现/查询需`connectors:read`；创建、修改、连接测试需`connectors:write`。现有永久七权限只读服务身份不能创建实例 |

当前`GET /api/v1/agent-tools/backends`只按PG实例及开关列出SIEM后端，**不会实际检查connectors服务或远端SIEM是否可查询**。出现于列表，只证明配置满足发现条件。

相关源码：[连接器模型](../../services/api/app/models/connector.py)、[管理API](../../services/api/app/api/v1/endpoints/connectors.py)、[联邦查询代理](../../services/api/app/api/v1/endpoints/federated.py)、[服务间身份](../../services/api/app/core/connectors_auth.py)、[Agents工具](../../services/agents/app/tools/customer_tools.py)。

## 2. 原版已有的四种适配器

当前联邦SIEM路径的类型允许集只有`splunk`、`microsoft_sentinel`、`elastic`、`qradar`。原版四个适配器均有实际HTTP查询实现；其他连接器即使在目录中声明`query_logs`，也不能据此认为已经进入这条路径。未实现联邦查询的连接器在原版运行服务中返回501。

下面列出构造参数的准确名称。凭据/非凭据的分组是推荐存放方式；执行服务会合并两个字典再构造适配器，字段必须与适配器参数匹配。

| 类型 | 必填/认证条件 | 可选项及查询范围 |
| --- | --- | --- |
| `splunk` | `connector_config.base_url`为管理API地址，通常8089；`auth_config.token`需能执行搜索，不能仅凭目录中“HEC/API Token”标签认为所有HEC写入token均可用 | `saved_search="AiSOC_Alerts"`、`page_size=500`、`ssl_verify=true`。采集可使用saved search；当前直接`query`默认搜索`notable` |
| `elastic` | `connector_config.base_url`为Elasticsearch集群地址；`auth_config.api_key`或同时提供`username/password` | `index="logs-*"`、`ssl_verify=true`；请求`/_query`，要求上游具备所用ES\|QL能力，不能把Kibana地址或任意OpenSearch接口视为等价 |
| `microsoft_sentinel` | `auth_config.tenant_id/client_id/client_secret`；`connector_config.subscription_id/resource_group/workspace` | Azure的`tenant_id`是认证目录ID，与本次AISOC租户ID不同。当前KQL固定查询`CommonSecurityLog`；另有下述静态缺口 |
| `qradar` | `connector_config.console_url`；`auth_config.sec_token` | `verify_tls=true`；Ariel API执行AQL，查询`events` |

精确目录可从`GET /api/v1/connectors/catalog`读取，其`source/degraded/reason`区分运行服务返回与API内置目录回退。**内置目录可以展示配置表单，不能代替查询运行服务。** 字段来源见[内置目录](../../services/api/app/data/connector_catalog_fallback.json)，类型筛选见[federated.py](../../services/api/app/api/v1/endpoints/federated.py)。

一个现有类型的脱敏请求模板如下；这里只展示合同，当前未执行创建，也未证明运行服务可达：

```http
POST /api/v1/connectors
Authorization: Bearer <具有connectors:write的操作身份>
Content-Type: application/json

{
  "name": "示例Elastic查询源",
  "connector_type": "elastic",
  "auth_config": {"api_key": "<只读搜索凭据>"},
  "connector_config": {
    "base_url": "https://elastic.example.invalid:9200",
    "index": "logs-*",
    "ssl_verify": true
  }
}
```

创建默认启用；后续通过`PATCH /api/v1/connectors/{id}`设置`is_enabled`。预保存连接测试为`POST /api/v1/connectors/test`，保存后测试为`POST /api/v1/connectors/{id}/test`，均依赖实际connectors服务。连接测试成功也不自动证明指定字段、索引和查询权限正确，仍需执行一次代表查询。

配置使用上的两个边界：

- `allowed_capabilities`有独立管理接口，但当前SIEM筛选/查询路径没有读取该列；不能仅设置`allowed_capabilities=[]`就宣称此SIEM查询已经禁用。该路径实际读取`is_enabled`和联邦查询开关。
- 代码中每种指标到SIEM字段的映射是固定表，不能靠在`connector_config`里随意添加一个`field_map`就使其生效。实际日志字段不同，需要修改相应适配/映射。

固定原版静态核查还发现：Splunk的`saved_search`以`index=`开头时，会与SPL translator再次拼接的`index=`冲突；Sentinel认证及workspace共用问题见[下文调用分析](#sentinel-static-flow)。不能承诺仅填目录字段即可正确工作，选用相应产品时再做必要接缝修正/实查。此处未执行或修复；其余问题继续沿[现有问题登记](upstream-issues.md)处理。

### 2.1 模型参数到统一查询：谁负责写查询语言

**当前模型不需要写SQL、ES\|QL或KQL。** 模型调用的仍是`siem_indicator_search`，提供指标类型、值与小时数；API选择固定字段，产品translator才生成查询文本。Elasticsearch适配器最终通过HTTP传ES\|QL，Sentinel适配器最终通过HTTP传KQL，两者不是向AISOC数据库执行普通SQL。

以下逐步例子全部是**按固定源码静态推导**，未运行translator、未连接产品、未执行HTTP或模型。原版参考目录为`/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors`；当前迁入API/Agents的对应合同也已核对。查询文本逐行保留源码生成形式，不代表所选产品版本、索引或表已验证兼容。

假设模型提出查主机最近24小时，实际工具参数如下。模型schema没有`limit`，因此这条路径采用API默认40；第4节手工API样例的`limit=20`是调用者另行指定的值。

```json
{"indicator_type":"hostname","value":"TEST-WIN-01","hours":24}
```

| 经过哪层 | 真实对象/处理 | 本例交接内容 |
| --- | --- | --- |
| Agents工具 | `customer_tools.siem_indicator_search`把`hours`改为`since_hours`，tenant/凭据来自Run和服务配置 | POST `/api/v1/agent-tools/siem-search`，body为`{"indicator_type":"hostname","value":"TEST-WIN-01","since_hours":24}` |
| API请求校验 | `SiemSearchRequest`；`validate_value`验证指标形状，`fields_for`按连接器类型取硬编码字段 | 取最近86400秒、最多40行；hostname值不会被当作查询片段 |
| API构造查询 | `siem_search.search_indicator`直接构造`free_text/indicators/since_seconds/limit`字典，每个后端字段各一份 | Elastic一份`host.name`；Sentinel两份`SrcHostname`和`DstHostname`，不是AND成一份 |
| API代理 | `_query_one_backend`给字典附上解密后的`auth_config`及`connector_config` | POST connectors服务`/api/v1/connectors/elastic/query`或`/microsoft_sentinel/query` |
| connectors接收 | 外层Pydantic类名为`FederatedQueryRequest`，其`query`仍是字典；`parse_unified_query`解析它 | 内层真实类名为`UnifiedQuery`，每条条件为`Indicator(field, operator, value)` |
| 产品执行 | `connector.query(unified)`→`to_esql`或`to_kql`→产品HTTP请求 | 返回产品事件行，之后由API合并/投影；模型只收到工具结果 |

API送给Elastic运行服务的完整payload形状如下，敏感值仅为占位符；Sentinel只需替换实例配置与`indicators[].field`：

```json
{
  "auth_config": {"api_key": "<解密后的只读API key>"},
  "connector_config": {"base_url": "https://elastic.example.invalid:9200", "index": "logs-*", "ssl_verify": true},
  "query": {
    "free_text": "",
    "indicators": [{"field": "host.name", "operator": "eq", "value": "TEST-WIN-01"}],
    "since_seconds": 86400,
    "limit": 40
  }
}
```

约束具体由两层承担：API的typed工具只允许既有指标类型、固定字段映射及`eq`，`free_text`始终为空；connectors中的`Indicator`再次校验字段标识符、操作符和值，`UnifiedQuery`限制正时间窗不超过7天、行数不超过1000并拒绝无条件查询。工具路径另有前述更小的40行上限。

两个translator均把字符串值加双引号，并转义反斜杠和双引号；bool/数值则按相应字面量输出。字段标识符不走字符串转义，先由`Indicator`的标识符格式校验，再直接拼接。typed路径还用固定表决定字段，模型不能指定字段。Elastic索引来自操作配置，Sentinel表在适配器中写死，不是模型选择的内容。

这些约束不能推广成“所有查询入口都只接受typed指标”：另一个人工`/api/v1/federated/search`入口允许`free_text`和字段条件；ES\|QL translator的`free_text`分支也不同于typed路径。本文例子只分析调查工具这条固定`free_text=""`、`operator="eq"`路径，不以它证明其他入口的任意查询能力或安全性。

源码：[API构造字典](../../services/api/app/services/agent_tools/siem_search.py)、[API字段/值校验](../../services/api/app/services/agent_tools/indicators.py)、[原版请求解析](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors/app/federated/query.py:94)、[原版HTTP入口](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors/app/api/router.py:509)。

### 2.2 Elasticsearch：生成ES|QL并调用`/_query`

本例的`hostname`在Elastic字段表中只对应`host.name`，所以一次模型工具调用生成一条Elastic后端查询。`ElasticConnector.query`调用`to_esql(unified, index=self._index)`；假设配置`index="logs-*"`，源码生成文本为：

```text
FROM logs-*
| WHERE @timestamp > NOW() - 86400 seconds
| WHERE host.name == "TEST-WIN-01"
| LIMIT 40
```

时间条件使用上游执行查询时的`NOW()`减86400秒，只生成时间下界，没有额外生成`@timestamp <= NOW()`；不是告警发生时间前后各24小时。索引可通过当前实例的`connector_config.index`修改；主机字段`host.name`不能通过添加任意配置字段自动更换。

适配器对配置中的Elasticsearch集群发出以下请求。换行在JSON字符串中编码为`\n`；这就是“最终向后端传查询文本”的位置，而不是让模型传一整段查询：

```http
POST https://elastic.example.invalid:9200/_query
Authorization: ApiKey <该实例解密后的API key>
Content-Type: application/json

{"query":"FROM logs-*\n| WHERE @timestamp > NOW() - 86400 seconds\n| WHERE host.name == \"TEST-WIN-01\"\n| LIMIT 40"}
```

没有API key但配置了用户名/密码时，原适配器改用`Authorization: Basic base64(username:password)`；没有任一认证组合则构造失败。TLS校验由`ssl_verify`控制。适配器HTTP timeout为60秒，但从typed工具调用时API到connectors还有12秒请求上限，不能据适配器的60秒宣称工具会等待60秒。

假设上游按ES\|QL合同返回：

```json
{
  "columns": [{"name":"@timestamp","type":"date"},{"name":"host.name","type":"keyword"},{"name":"process.name","type":"keyword"}],
  "values": [["2026-10-21T08:30:00Z","TEST-WIN-01","powershell.exe"]]
}
```

`_rows_from_esql`提取`columns[].name`，逐行与`values[]`按位置`zip`，得到：

```json
[{"@timestamp":"2026-10-21T08:30:00Z","host.name":"TEST-WIN-01","process.name":"powershell.exe"}]
```

适配器不调用告警`normalize/fetch_alerts`，这些行直接回API；API增加来源再按白名单保留字段，工具行会带`_source="elastic"`。原`_rows_from_esql`使用`get(..., [])`和非严格zip，缺少`columns/values`可能变成空结果、长度不齐可能丢字段；这不是严格响应合同校验。本次仅说明该静态限制，第三方adapter的缺字段处理应沿第3节明确报错，不照搬成“缺结构即零命中”。

源码：[原版Elastic适配器](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors/app/connectors/elastic.py:150)、[ES\|QL translator](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors/app/federated/translators/esql.py:66)。

<a id="sentinel-static-flow"></a>

### 2.3 Sentinel：生成KQL并调用Log Analytics

同一`hostname=TEST-WIN-01`在当前Sentinel映射中有两个字段：`SrcHostname`、`DstHostname`。原统一查询中的多条件默认AND，所以API分别发两份查询、再合并结果，以表达“源主机或目的主机匹配”。不是模型自行编写OR，也不是一次工具必然对应一次厂商HTTP请求。

`MicrosoftSentinelConnector.query`固定调用`to_kql(unified, table="CommonSecurityLog")`。本例按源码分别生成：

```text
CommonSecurityLog
| where TimeGenerated > ago(86400s)
| where SrcHostname == "TEST-WIN-01"
| take 40
```

```text
CommonSecurityLog
| where TimeGenerated > ago(86400s)
| where DstHostname == "TEST-WIN-01"
| take 40
```

时间仍以查询时刻为基准、只给下界。当前适配器没有通过`connector_config`开放表选择；translator虽然有`table`参数和针对`SecurityIncident/SigninLogs`的部分字段别名，当前`query`固定传`CommonSecurityLog`，因此不能仅改JSON配置就查`SigninLogs`。指标表中的`SrcHostname/DstHostname`等列也需与实际工作区表核对；写有映射不证明部署中确实存在这些列或数据。IP同样按`SrcIpAddr/DstIpAddr`拆成两次查询再合并，不能把字段表的ASIM注释当成当前固定表的schema证明；实际表不存在相应列时可能查询报错，应核对/修改映射，不能记成零命中。

执行顺序为先取token，再发KQL。按当前源码，token请求形状是：

```http
POST https://login.microsoftonline.com/<Azure-tenant-id>/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id=<client-id>&client_secret=<secret>&scope=https%3A%2F%2Fmanagement.azure.com%2F.default&grant_type=client_credentials
```

取到`access_token`后，本例第一份查询请求形状是：

```http
POST https://api.loganalytics.io/v1/workspaces/<配置中的workspace>/query
Authorization: Bearer <上一步access_token>
Content-Type: application/json

{"query":"CommonSecurityLog\n| where TimeGenerated > ago(86400s)\n| where SrcHostname == \"TEST-WIN-01\"\n| take 40"}
```

第二份只把查询字段换成`DstHostname`。原运行服务每次请求都构造新的connector实例；实例的`_access_token`初始为空，所以本例两份字段查询按此实现各自先认证，没有从源码证据得出跨请求token复用。这里是调用数量的静态推导，未测量真实请求次数。

假设成功返回Log Analytics表格：

```json
{
  "tables": [{
    "name": "PrimaryResult",
    "columns": [{"name":"TimeGenerated","type":"datetime"},{"name":"SrcHostname","type":"string"},{"name":"Process","type":"string"}],
    "rows": [["2026-10-21T08:30:00Z","TEST-WIN-01","powershell.exe"]]
  }]
}
```

适配器只取第一张表，将`columns[].name`与`rows[]`按位置zip为`{"TimeGenerated":...,"SrcHostname":...,"Process":...}`；随后API投影保留这些已识别字段、附`_source="microsoft_sentinel"`并合并两份结果。无`tables`时当前实现返回空列表；长度不齐同样使用非严格zip，不能当成已做严格合同校验。

必须保留两个静态接入缺口：

- **token用途未分开。** `_authenticate`只请求`https://management.azure.com/.default`，随后该token被用于`api.loganalytics.io`。源码注释声称单独scope，但执行代码没有实现；不能把management认证成功当成日志查询权限/认证成功。选用此适配时需按实际查询API拆分相应认证合同。
- **workspace名称/ID未分开。** 同一`workspace`既填入ARM采集路径中的工作区名称位置，又填入Log Analytics查询URL的`workspace_id`位置。当前配置没有独立`workspace_id`参数；不能假定两种标识相同。只做查询可暂不启采集，但仍需明确查询端要用的标识。

这两点是固定源码事实与静态兼容风险，本次没有请求Azure、验证厂商权限或修改适配器。查询还取决于实际表、字段及认证授权，不能描述成现环境仅差开关。

源码：[原版认证](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors/app/connectors/microsoft_sentinel.py:71)、[原版Sentinel查询](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors/app/connectors/microsoft_sentinel.py:122)、[KQL translator](/Users/lychee/Documents/project/SOCAI/opensource/AiSOC/services/connectors/app/federated/translators/kql.py:94)。

### 2.4 自研第三方检索可以复用什么

可以复用模型的typed工具、API租户实例与加密凭据、`UnifiedQuery/Indicator`、有界行数/时间、来源与缺口回传。自研后端若接收JSON过滤条件，adapter可直接把统一条件翻成JSON，**完全不必生成SQL、ES\|QL或KQL**；若后端确实要求某种查询文本，则由固定translator生成，不能把任意查询文本参数交给模型替代合同。

对当前“只做查询”的需求，业务实现只需接注册/schema/`supports_federated_search`/`query`及API允许集、指标字段映射；不需要为了调查补查启用或实现实际采集轮询/`fetch_alerts`业务。框架要求保留的基类方法可以维持明确的未启用/不支持状态，不将其声明成采集已完成。第三方HTTP合同、脱敏配置和适配伪代码沿用下一节，不另建一套调查工具。

## 3. 假设第三方只提供开放HTTP接口

### 3.1 先约定一个最小上游合同

以下API完全是假设，域名、路径、字段均用于说明，**不是现有项目接口，也不是已经接通的厂商能力**：

```http
POST https://siem.example.invalid/openapi/v1/events/search
Authorization: Bearer <第三方只读token>
Content-Type: application/json

{
  "filter": {"field": "device_name", "operator": "eq", "value": "TEST-WIN-01"},
  "start_time": "2026-10-20T09:00:00Z",
  "end_time": "2026-10-21T09:00:00Z",
  "page_size": 20
}
```

假设成功返回：

```json
{
  "request_id": "example-query-001",
  "data": {
    "events": [{
      "event_id": "example-event-001",
      "occurred_at": "2026-10-21T08:30:00Z",
      "device_name": "TEST-WIN-01",
      "account_name": "test.user",
      "source_ip": "192.0.2.17",
      "destination_ip": "198.51.100.8",
      "process_image": "powershell.exe",
      "rule_name": "Example rule",
      "action": "observed"
    }],
    "has_more": false
  }
}
```

最低限度需要向接口提供方确认：支持哪些实体字段及精确/模糊语义；时间字段与时区；查询凭据；分页/上限；空结果结构；401/403及业务错误的结构。若上游用异步查询任务，则适配器还要处理提交、读取状态及结果，不能套用上面的一次请求假设。

当前Agents工具表达“最近N小时”，时间以查询时刻为基准；原内部`UnifiedQuery`传`since_seconds`。它没有接收任意事件发生时间窗的参数。假设适配器将查询时刻减去该值生成UTC起止时间，不能描述成自动按告警发生时间补查。

### 3.2 需要接的源码位置

对于未支持的产品，先接入小范围的查询适配器，再配置实例。沿原设计至少需要：

1. 在实际查询运行服务中注册产品类型、配置schema及`query(UnifiedQuery)`实现，声明`supports_federated_search=True`；只实现本轮所需只读查询，不要求启动采集轮询。
2. 将新类型加入API的`FEDERATED_CAPABLE_TYPES`，使租户实例可以被查询路径发现；同步可用目录，避免创建实例时类型校验拒绝。
3. 在API的`INDICATOR_TYPES`中为该类型补受支持指标的字段映射；只提供确实可查的类型。原指标集合为IP、域名、URL、MD5/SHA1/SHA256、主机名、用户名、进程名，不必更改模型工具schema。
4. 将上游请求/响应转换成原查询合同，返回现有投影可识别的字段；再配置服务地址、身份及租户连接器实例。

假设新类型取名`third_party_siem`，未来配置可能如下。**当前类型尚未注册，此JSON不能直接提交并期待生效；它只说明完成适配之后应保存什么。**

```json
{
  "name": "第三方SIEM示例",
  "connector_type": "third_party_siem",
  "auth_config": {"api_token": "<第三方只读token>"},
  "connector_config": {
    "base_url": "https://siem.example.invalid",
    "search_path": "/openapi/v1/events/search",
    "ssl_verify": true
  }
}
```

`api_token/search_path`也是本假设适配器拟定的参数，当前没有通用机制读取它们。不能把第三方类型伪装成`elastic/splunk`以绕过类型筛选，除非它实际兼容相应产品的请求和响应合同。

### 3.3 请求与返回怎样适配

例如模型提出`hostname=TEST-WIN-01, hours=24`：API指标表将其解析为新后端的`device_name`；原`siem_search`生成下列内部查询，再经API代理送入connectors服务：

```json
{
  "free_text": "",
  "indicators": [{"field": "device_name", "operator": "eq", "value": "TEST-WIN-01"}],
  "since_seconds": 86400,
  "limit": 20
}
```

适配逻辑示意如下，**只是伪代码，未新增或执行实现**：

```text
query(unified):
  校验仅接受已支持的field/operator，并采用既有时间/行数边界
  end = 查询时刻UTC；start = end - unified.since_seconds
  用固定search_path、已配置认证及字段映射组装第三方请求
  上游HTTP失败或业务失败 → 抛查询错误，不返回[]
  上游响应缺少约定的data.events或行结构错误 → 报合同错误
  events=[]且结构正确 → 返回[]
  事件行 → 转换成原API投影认可的字段，再返回rows
```

上述假设行可转换为：

```json
{
  "@timestamp": "2026-10-21T08:30:00Z",
  "host.name": "TEST-WIN-01",
  "user.name": "test.user",
  "source.ip": "192.0.2.17",
  "destination.ip": "198.51.100.8",
  "process.name": "powershell.exe",
  "rule.name": "Example rule",
  "event.action": "observed"
}
```

运行服务对API返回`{"connector_id":"third_party_siem","row_count":1,"rows":[...]}`；API附来源、合并和裁剪后，Agents才把结果交给模型。当前投影白名单不会自动保留上游`request_id/event_id`；如要求模型引用原事件ID，应补明确的投影合同。测试回执可以单独记录脱敏查询ID，不能声称它已经随原工具持久化。

IP通常需要查源IP、目的IP两个字段，原工具会分成两次后端查询再合并。这不是模型调用了两次工具。适配器必须保留对应字段的精确语义，不能只查源IP后描述成“整个SIEM都没出现该IP”。

## 4. 当前工具怎样请求与读结果

当前已存在的API请求合同如下，**例子不执行**。`API_BASE/READ_TOKEN/TENANT_ID`需由相应测试环境提供；只读服务身份必须同时传租户头。

```bash
# 只检查配置发现，不证明真实SIEM查询成功。
curl -sS "$API_BASE/api/v1/agent-tools/backends" \
  -H "Authorization: Bearer $READ_TOKEN" \
  -H "X-AiSOC-Tenant-ID: $TENANT_ID"

# 需先有受支持类型及实际可用的查询运行服务。
curl -sS -X POST "$API_BASE/api/v1/agent-tools/siem-search" \
  -H "Authorization: Bearer $READ_TOKEN" \
  -H "X-AiSOC-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  --data '{"indicator_type":"hostname","value":"TEST-WIN-01","since_hours":24,"limit":20}'
```

正常匹配的响应结构示意：

```json
{
  "outcome": "ok",
  "indicator_type": "hostname",
  "value": "TEST-WIN-01",
  "since_hours": 24,
  "row_count": 1,
  "rows": [{"host.name": "TEST-WIN-01", "_source": "third_party_siem"}],
  "sources": [{
    "source": "third_party_siem",
    "name": "第三方SIEM示例",
    "status": "ok",
    "rows": 1,
    "fields_searched": ["device_name"]
  }],
  "truncated_rows": false,
  "truncated_bytes": false
}
```

`third_party_siem`仅在前述适配完成后才可能实际返回。当前API限制：`since_hours=1..168`，默认24；`limit=1..40`，默认40；合并结果另按`len(repr(rows)) > 24000`继续裁剪。该常量虽名为`MAX_RESULT_BYTES`，当前实现不是精确UTF-8字节计数。模型工具参数名是`hours`，由Agents转换成API的`since_hours`。模型不能直接提供`query/free_text/field/URL/凭据/tenant`。

| 状态/情况 | 应如何解释 |
| --- | --- |
| `outcome=ok`且来源`status=ok`、零行 | 该来源在已查询字段与窗口内没有匹配；不能推断未接来源、其他字段或窗外均无活动 |
| `no_backend` | 没有可查询实例，实际没有查第三方SIEM |
| `could_not_check` | 没有来源成功回答；连接失败、无字段映射或不支持都不能当作未命中 |
| `partial` | 有来源回答，也有`error`来源；保留失败范围 |
| 来源`no_field_mapping/unsupported` | 相应来源/指标未成功查询。当前顶层`partial`只统计`error`，所以仍须逐项检查`sources`，不能只读顶层`ok` |
| 422 | 请求参数、指标类型或指标值不合法，未获得有效查询结果 |
| 截断标记true | 返回的是有界样本，行数不能当成命中总量 |
| 上游缺字段 | 约定必需的响应结构缺失应报合同错误；可选实体字段缺失保留未知，不补推断值或伪造空查询 |

源码：[请求/响应](../../services/api/app/api/v1/endpoints/agent_tools.py)、[固定字段映射](../../services/api/app/services/agent_tools/indicators.py)、[查询及投影](../../services/api/app/services/agent_tools/siem_search.py)。

## 5. 最少测试顺序：先接口，最后再接模型

当前只有假设接口，可以先使用本地HTTP测试服务返回固定合成样本；它只用于验证协议，不代表连接真实SIEM。以下是后续实施步骤，本次未创建测试服务、未写测试代码、未访问基础设施、未调用模型。

| 层次 | 最少做什么 | 保留什么证据/能证明什么 |
| --- | --- | --- |
| 1. 上游HTTP | 对约定接口发送一条固定主机查询，观察已知命中、明确空结果和明确错误响应；无SIEM时由本地HTTP替身返回这些fixture | 脱敏请求的字段/时间窗、HTTP状态、响应结构。替身只能证明约定可表达，真实HTTP连上产品后才证明上游查询接通 |
| 2. 产品adapter | 把同一查询交给适配器，核实际出站URL/请求体及返回行；补一个缺少必需响应结构的样本，确认不会变成空结果 | 字段映射、时间/limit、认证是否放到正确位置、错误与零行区别。HTTP mock通过是适配合同通过，不是厂商连通 |
| 3. API工具接缝 | 在隔离测试tenant配置已注册的实例和查询运行服务，先GET backends，再POST siem-search；同一已知样本贯穿到rows/sources | 证明租户实例选择、解密/代理、字段映射、结果投影实际相接。若上游仍为替身，应明确记“API全链＋合成源”，不能写真实SIEM通过 |
| 4. Deep实际消费 | 前三层完成后，先可用确定性模型替身产生一次`siem_indicator_search`调用检查工具交接；如需真实模型行为，再单独开展一次有界的新调查 | 核模型收到的工具schema→实际tool_calls→出站请求→工具返回→后续ToolMessage/可见结论。替身证明接线；真实模型也可能不选此工具，不能用“已提供工具”代替“已查询” |

第一层假设接口的手工请求模板如下，当前不执行；没有服务时不应向示例域名发请求：

```bash
curl -sS -X POST "$UPSTREAM_BASE/openapi/v1/events/search" \
  -H "Authorization: Bearer $UPSTREAM_READ_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"filter":{"field":"device_name","operator":"eq","value":"TEST-WIN-01"},"start_time":"2026-10-20T09:00:00Z","end_time":"2026-10-21T09:00:00Z","page_size":20}'
```

每层只补本次接线需要的代表样本，复用已有测试，不把长稳、故障恢复或全部产品组合列为前置。没有真实上游时，先完成至替身验证并标明边界；不需要为了证明工具存在而提前发模型调用。

交付记录至少写清：使用的源码/adapter版本、合成源还是真实产品、测试tenant、输入指标与窗口、成功/空/失败状态、是否实际执行HTTP、是否实际调用模型及工具返回是否进入后续输入。保留脱敏样本和可核对的来源，避免保存token、完整原始日志或模型隐藏推理。

Deep的发现/执行位置见[customer_tools.py](../../services/agents/app/tools/customer_tools.py)与[deep_investigation.py](../../services/agents/app/investigator/deep_investigation.py)。默认Case四节点和Router专业分支不会因为连接器配置出现，就自动获得Deep的模型工具循环；原graph另有按`connector_id`解析的[Splunk固定取证](../../services/agents/app/investigator/splunk_evidence.py)，需与本文通用SIEM工具区分。
