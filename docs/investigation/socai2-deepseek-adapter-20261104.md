# 独立新服务接入 DeepSeek

用户于 2026-11-04 指定使用 `deepseek-flash`，凭据从本机指定文件读取，并要求原配置保持。n7 已部署到独立 `socai2-next-api`；原四个业务容器和 LiteLLM 网关不替换、不重启。

## 实际路由及配置边界

| 对象 | 当前处理 |
| --- | --- |
| 原服务、原 LiteLLM | 保留原路由及模型；容器状态、网关环境和配置文件指纹已核对 |
| 新服务原 `api.env` | 文件字节保持；不覆盖原模型配置 |
| 新服务 DeepSeek 配置 | 新增机上私有 `model.deepseek.env`，权限 0600；Compose 单独叠加，只作用于新 API |
| 新服务调用链 | 新 API → `https://api.deepseek.com/responses` → `deepseek-flash`，本批不经过原 LiteLLM |
| 网络策略 | 保留原策略，仅为新服务增加官方域名白名单，不关闭全局 guard |
| 凭据 | 通过 SSH 标准输入传入私有文件，不在命令参数、候选包、Git 或验收工件中保存；用户本机文件已加入精确忽略规则 |

原来新服务使用 `aisoc-investigation`，经共享 LiteLLM 到自报 Qwen3.5-9B 的后端。此次只改变独立新服务。默认协议仍为原 `chat_completions`；只有显式 `SOCAI2_MODEL_PROTOCOL=deepseek_responses` 且地址、模型匹配才使用新适配。

## 为什么需要一个小适配

[官方 Chat Completions 文档](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)仅声明普通文本和 JSON 模式；[Responses 文档](https://api-docs.deepseek.com/zh-cn/api/create-response/)声明 JSON Schema 输出。为了保留当前字段合同，使用后者，没有自动回退到仅 JSON 模式。

A、I、C3、Deep、再分析和 C6 在记录请求及预留额度前转换为实际发送的 Responses body。输入成员、来源和值、Schema、3000 输出 tokens 上限保持；完整 body 仍计入原保守预算。模型原始 response 原样保存，只在解析时建立兼容视图，读取真实 input/output/cache/reasoning token 字段；缺失或不一致用量不补造，费用仍记未定价。

显式使用 `reasoning.effort=none`，不依赖供应商默认开启思考的行为，避免改变本批输出额度含义；`temperature=0`、`stream=false`、`store=false` 均在实际请求工件里。没有请求供应商搜索或其他隐式工具。依据[官方思考模式说明](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/)，“none”关闭思考，不代表取消本系统的 Deep、多领域分析或 Tool 流程。

响应必须是已完成的一条 assistant 文本消息；拒答、多消息、供应商工具调用及未完成状态不作为成功调查结果。原引用归属、角色、交叉字段与交付校验继续执行。没有新增重试、增加额度或提高运行时限。

## 验证范围

- 18 项协议/结构检查最新通过：初次 17 过、1 个测试尝试修改冻结配置对象失败，改为创建新配置对象后定向通过；业务断言未放宽。
- 6 项部署/批次驱动离线检查通过，确认原配置文件保持、新 profile 单独写入、旧批次禁止派发、首轮失败不得进入 H/第二 C。
- 4 个受影响 PG 方法通过：A 同次结果、I 成员诊断、C3 工件与用量、完整自适应 C3→Deep→C6；使用既有独立合成库，模型及湖返回为替身，受限角色和隧道已清理。
- 本机及新容器官方 `/models` 均 HTTP 200，确认指定模型可用；这些探测没有执行推理。
- n7 镜像 `1abe67cf1b17…`，546 个应用文件与候选一致；[部署核对](../operations/evidence/socai2-next-service-20261104/20261104T073915-start/receipt.json)确认原配置和容器保持。

r4 使用原两条合成告警及两条湖事件、新操作和 Case，保持原预算。模型接入和服务 ready 不代表语义验收完成；具体结果另列，旧 r13/5.3 以及 Q 暂缓范围不因此核销。
