# 调查功能基本运行测试（2026-10-28）

后续：[真实PG联调结果及追加模型剩余问题](real-pg-test-20261028.md)。本页保留前一轮测试边界，不代表后续测试仍使用内存账本。

源码基线`e98852a`，加本轮时间绑定和模型提示修复。按用户要求只做必要功能检查，并沿用21之前的模型配置；未开展压力、恢复、权限或可用性专项。

**22项已有直接用例通过；修复后，21既有模型→当前Case工具→真实ClickHouse→结构化报告的单例通过。真实Case读取/PG落库和完整业务入口整链仍未验证。**

## 直接功能用例

| 用例文件 | 通过数 | 主要覆盖 |
|---|---:|---|
| `test_case_synthesis.py` | 4 | 成员覆盖、关联引用、时间线、未决问题 |
| `test_investigation_navigation.py` | 3 | 三种入口到同一Run，证据/步骤/来源行跳转 |
| `test_case_analysis_api.py` | 7 | 预览、调查、报告、追加问题、重查 |
| `test_case_product_tool.py` | 2 | 来源绑定、工具消息、空结果与失败区别 |
| `test_related_investigations.py` | 3 | 告警/事件关联、报告回显和AI概况引用 |
| Actions `test_case_host_http.py` | 3 | 主机HTTP请求/返回映射 |

这些用例使用数据库、模型或厂商HTTP替身。22为不同用例数；时间修复后只重跑受影响Case的7项，提示调整后再核对其中1项完整链路，均通过，不重复计数。

## 真实环境发现与修复

1. **时间绑定失败。** Case工具将`2026-10-23T09:58:00+00:00`交给`toDateTime64`，实际ClickHouse返回Code 6。改为先转UTC，再绑定`2026-10-23 09:58:00.000000`；范围JSON仍保留时区，窗口仍起始包含、结束不包含。既有records读取器已采用这一格式，本轮只修Case工具。
2. **模型首次未实际调用工具。** 返回带代码围栏的报告，声称已查询并引用不存在的E1/E2。现有校验拒绝为`invalid_or_unreferenced_conclusion`。一次180-token上限的最小协议请求返回原生tool_calls，确认接口支持工具调用。随后明确提示：用户要求补查时必须实际调用，收到Tool结果前不能编造E编号/空结果，最终输出纯JSON。保留原引用校验和预算，没有增加重试框架或强制所有Case查询。

## 实际执行例子

沿用21网关角色`aisoc-investigation`，配置上游是43的`openai/aisoc-test-investigation`；没有新部署模型，也未独立核验底层权重版本。只向一次性进程注入既有配置，没有修改常驻API配置。

- 既有合成租户：`53824f24-d1d4-5820-8147-f6cfda8a1247`。
- 主机：`investigation-ch-20261023-01-host`。
- 窗口：`2026-10-23T09:58:00Z`至`10:03:00Z`。湖内已有3条网络记录，无进程记录；未新增湖数据。
- 输入：前两条来源事件构造的2条合成告警及内存Case，要求补查网络和进程、说明关联及缺口。不是从PG读取的真实Case。

| 步骤 | 实际输入/输出 |
|---|---|
| 模型第1轮 | 读取A1/A2、窗口及工具定义，返回两个原生调用 |
| network_connections | 限定主机、limit=50；E1，available=true，3条连接 |
| process_activity | 同主机、limit=50；E2，available=true，0条，未冒充查询失败 |
| 模型第2轮 | 收到带原call_id的Tool消息，输出引用A1/A2/E1/E2的JSON |
| 程序整理 | 2个成员判断、1条shared_context关联、1个未决问题、5项来源时间线；内存收集12个工件 |
| 最终状态 | completed / analysis_complete / partial；缺少发起连接的进程和账号证据 |

实际2次模型调用、2次Tool调用，已知6507 tokens。E1查询ID为`9e012160-df10-4bdd-9e52-0ed1cfeb6ef0`，E2为`14833583-8d51-4d8a-b9e3-80be82bb47df`。

此例证明协议、查询、结构和引用链路能运行，不证明模型每句业务解释都准确。例如报告“同一会话”的措辞不能由这些独立连接记录直接证实。

两个工具的独立实际读取也成功（进程0、网络3）。第一次模型探针在运行后的结果整理中误把上下文evidence数组当作单个Tool证据，导致脚本异常；修正一次性探针后取得上述失败及修复后结果，没有把脚本异常计为业务通过。

## 整链剩余边界

- 当前21常驻API本身没有有效模型配置；本次临时进程复用Agents已有的网关配置。
- 实际PG连通，但缺少`fusion_incident_summaries`和`investigation_case_links`（迁移120/121未安装）。本轮没有执行共享库DDL。
- 选定合成租户下未读到可用Case/Alert；Case成员、账本存储及模型配置查询的数据库结果使用替身。当前API的真实PG写入、重读及JWT/RBAC未验证。
- 产品HTTP仅通过MockTransport验证，未访问真实CrowdStrike；未部署当前入口、启动worker或执行响应动作。

六批计划第6项仍待真实Case/PG与业务入口联调，不能标记完整上线。机器记录：[本轮调用与结果](../operations/investigation-basic-runtime-20261028.json)。修改：[Case查询](../../services/api/app/investigation_v2/case_analysis_tools.py)、[提示](../../services/api/app/investigation_v2/case_analysis.py)、[直接回归](../../services/api/tests/test_case_analysis_api.py)。OpenSpec CLI在当前Shell不可用，未执行CLI严格校验或归档。
