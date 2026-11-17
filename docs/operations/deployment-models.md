# 模型网关、调查模型与知识检索配置

2026-11-16。本页说明当前目标文件及其加载方式，不把旧A/AI示例或历史测试方案作为部署入口。当前容量配置已按负责人要求提高，见[本次证据](evidence/streaming-budget-20261116-01/README.md)；**仓库目标不等于21已加载，运行以本次实际读回为准。** 11-15的[脱敏运行清单](evidence/deployment-docs-20261115-01/runtime.json)仍是原时点证据；完整部署以最终candidate profile绑定的地址、私密文件和源码摘要为准。

## 1. 本轮配置入口

| 配置文件 | 负责内容 | 加载与生效 |
| --- | --- | --- |
| [compose.gateway.yml](../../deploy/aisoc21/compose.gateway.yml) | LiteLLM镜像、环境文件、端口、挂载及进程资源 | 部署Compose加载；更改后需针对该服务重建进程，并核实际镜像/挂载/环境摘要 |
| [litellm.config.yaml](../../deploy/aisoc21/litellm.config.yaml) | 五个逻辑模型路由、超时、重试、指标和网关key引用 | LiteLLM启动参数`--config /etc/litellm/config.yaml`加载；不能仅改仓库文件就认定运行更新 |
| [investigation-policy-case-v1.toml](../../deploy/local-investigation/investigation-policy-case-v1.toml) | A/I/Case预算、tokenizer、输出额度、工具说明及输入合同选择 | `SOCAI2_INVESTIGATION_POLICY`必须是进程内绝对文件路径；当前统一工厂用`investigation_policy_file`选择，首次加载后进程缓存；改配置需正常重启对应执行进程 |
| [alert-input-v1.json](../../services/api/app/socai2/alert-input-v1.json)、[incident-input-v1.json](../../services/api/app/socai2/incident-input-v1.json)、[case-input-v1.json](../../services/api/app/socai2/case-input-v1.json) | 按环节选择模型材料、提示词、引用和输出装配合同 | 随源码包冻结；策略仅填包内文件名，不能指向任意外部路径。Run保存策略及输入合同摘要 |
| [compose.embedding.yml](../../deploy/aisoc21/compose.embedding.yml) | Ollama嵌入进程、模型目录和资源 | Compose启动加载；模型文件须预先存在于指定持久目录 |
| [knowledge-profile.json](../../deploy/local-investigation/knowledge-profile.json) | 嵌入客户端、Qdrant集合、三用途检索、适用条件及历史材料 | `SOCAI2_KNOWLEDGE_PROFILE`指定进程可读JSON；prepare/index/query重新读取并比对hash，批次中途变化报错，不能靠热改文件切换本轮材料 |

本轮[候选processing-build.toml](../../deploy/aisoc21/streaming-candidate-20261115-01/processing-build.toml)明确引用上表case-v1策略。知识文件是JSON；仓库没有`deploy/aisoc21/knowledge-profile.toml`，不将口头路径写成可执行入口。

下文“示例”均指这些文件当前声明值，不是第三方组件默认值。配置表的“部署分类”说明部署人员需要做什么，字段能否省略仍由实际loader决定：

| 部署分类 | 如何填写 |
| --- | --- |
| **部署必填** | 按目标环境确认/填写地址、模型身份、资源名、挂载和凭据引用；示例值经核对适用可沿用，不能盲用 |
| **保留默认** | 通常保留当前交付模板值，不要求部署人员逐项调参。**多数是模板默认，不是loader缺省值；strict结构要求存在的键仍不能省略** |
| **启用时必填** | 仅在所述功能/路由启用时必须提供有效值；不启用时按Schema允许的省略/null方式处理，不能随意删其他必填键 |
| **程序生成** | 由发布器、启动器或运行记录生成；确认来源并读回，不手工伪造 |

部署优先确认上游模型URL/ID、网关凭据、tokenizer端点与模型、知识embedding/vector地址、集合及私密挂载；预算、重试、输入合同和释义通常保留当前交付值。改变模型时仍须成套核对context_tokens、输出额度、tokenizer和嵌入维度，不能只换地址。

源码用于核实配置含义，部署人员只需按文件和加载入口操作；无需修改业务代码。Qdrant服务本体、数据库存储及数据湖由部署总入口负责，本页只覆盖模型与知识客户端。

## 2. LiteLLM网关

### 2.1 五条路由及私密环境

`model_list`是对象数组，每个对象的`model_name`为对调用方公开的字符串；`litellm_params`包含`model/api_base/api_key`，三者均为字符串或环境引用。当前全部通过`os.environ/变量名`读取受控环境文件：

| `model_name` | 部署分类 | `litellm_params.model` | 用途 |
| --- | --- | --- | --- |
| `aisoc-triage` | 保留默认（模板） | `AISOC_LLM_MODEL_FAST` | 告警角色路由 |
| `aisoc-recon` | 保留默认（模板） | `AISOC_LLM_MODEL_FAST` | 侦察角色路由 |
| `aisoc-investigation` | 保留默认（模板） | `AISOC_LLM_MODEL_DEEP` | 当前统一调查策略选择的路由 |
| `aisoc-summary` | 保留默认（模板） | `AISOC_LLM_MODEL_FAST` | 汇总角色路由 |
| `aisoc-report` | 保留默认（模板） | `AISOC_LLM_MODEL_DEEP` | 报告角色路由 |

角色名不证明实际执行了哪个环节；本轮A/I/Case实际使用策略的`model.alias`，当前为`aisoc-investigation`。

| 环境项 | 部署分类 | 类型／填写要求 | 用途与核对 |
| --- | --- | --- | --- |
| `AISOC_LLM_MODEL_FAST`、`AISOC_LLM_MODEL_DEEP` | 部署必填 | 非空字符串，必填；provider前缀与上游模型ID，如`openai/<served-model>` | 逻辑角色到实际模型的映射；检查实际网关路由和上游served-model，不能凭响应alias当作权重身份 |
| `AISOC_LLM_API_BASE` | 部署必填 | URL字符串，必填 | 上游OpenAI兼容地址；必须与本批明确上游及网络规则一致 |
| `OPENAI_API_KEY` | 部署必填 | 私密字符串，按上游要求填写 | 网关发给上游的凭据；不同于客户端访问网关的master key，不保存进回执正文 |
| `LITELLM_MASTER_KEY` | 部署必填 | 私密字符串，必填 | `general_settings.master_key`引用，客户端访问网关的Bearer凭据 |
| `AISOC_LITELLM_REQUEST_TIMEOUT` | 保留默认（模板） | 可解析为秒的数值；当前Compose显式`300` | `litellm_settings.request_timeout`引用；Compose的environment覆盖env_file同名值。需同时核实际加载与应用单次/Run时限 |

环境文件路径为Compose中的`/opt/sting-aisoc-socai2/private/gateway-1e.env`，这是私密文件引用，不将其内容复制到文档、Git或查阅API。候选若用独立路径，由最终Compose明确挂载，不能默认复用正式文件。

### 2.2 YAML中的全部行为项

| 配置项 | 部署分类 | 类型／当前值 | 作用与边界 |
| --- | --- | --- | --- |
| `litellm_settings.drop_params` | 保留默认（模板） | bool；true | 丢弃provider不支持的请求参数；业务端仍须验证输出结构，不能据此放宽结果合同 |
| `litellm_settings.callbacks` | 保留默认（模板） | 字符串数组；`[prometheus]` | 注册指标回调；指标不替代Run/请求证据 |
| `litellm_settings.require_auth_for_metrics_endpoint` | 保留默认（模板） | bool；false | 指标端点不要求该鉴权；网关监听和网络范围仍由Compose限定 |
| `litellm_settings.request_timeout` | 保留默认（模板） | 环境引用；当前300秒 | 网关请求超时；不是整个Case的执行期限 |
| `router_settings.num_retries` | 保留默认（模板） | 整数；0 | 禁止网关自身自动重试；与调度器对已知失败最多一次重试、C3缺字段补答分别记录 |
| `router_settings.fallbacks` | 保留默认（模板） | 数组；空 | 不配置备用模型链，不自动切模型补成功 |
| `router_settings.allowed_fails` | 保留默认（模板） | 整数；3 | Router将部署置于冷却前的失败阈值，错误类型规则仍取决于固定LiteLLM版本 |
| `router_settings.cooldown_time` | 保留默认（模板） | 秒；30 | 冷却持续时长；不是业务任务重试间隔 |
| `general_settings.master_key` | 部署必填（凭据引用） | 环境引用 | 只引用`LITELLM_MASTER_KEY`，不在YAML写密钥 |

第三方含义核对自[LiteLLM YAML配置](https://docs.litellm.ai/docs/proxy/configs)及[Router参数](https://docs.litellm.ai/docs/routing)；文档网站可能更新，本项目实际以固定镜像、当前YAML及运行读回为准，不采用网站的新默认替换本批配置。

### 2.3 网关Compose全部配置

| 配置项 | 部署分类 | 类型／当前值 | 用途／生效核对 |
| --- | --- | --- | --- |
| `name` / `services.litellm` | 部署必填（目标绑定） | 字符串；socai2 / litellm | Compose项目与服务身份；候选资源须显式隔离，不能误操作正式同名项目 |
| `image` | 保留默认（模板） | 固定sha256 ID，详见原件 | 锁定已准备镜像；核实际Image ID |
| `pull_policy` | 保留默认（模板） | 字符串；never | 不临时拉取浮动版本，目标宿主必须已有该镜像 |
| `env_file` | 部署必填（目标绑定） | 绝对路径 | 提供上游及网关私密环境；只记录存在/权限/摘要，不打印值 |
| `environment.AISOC_LITELLM_REQUEST_TIMEOUT` | 保留默认（模板） | 字符串；300 | 显式覆盖环境文件同名项 |
| `command` | 保留默认（模板） | 字符串数组；config路径、port4000 | 容器内加载文件与监听端口；核进程参数 |
| `user` | 保留默认（模板） | 字符串；10001:10001 | 容器进程UID:GID；挂载必须可读 |
| `ports` | 部署必填（目标绑定） | 数组；127.0.0.1:14000:4000 | 宿主回环14000映射容器4000；容器内客户端按实际网络使用litellm:4000 |
| `volumes` | 部署必填（目标绑定） | bind数组；源码YAML→/etc/litellm/config.yaml:ro | 只读配置挂载，核宿主源路径及hash |
| `read_only` | 保留默认（模板） | bool；true | 根文件系统只读 |
| `tmpfs` | 保留默认（模板） | 数组；/tmp，rw/nosuid，512m，mode1777 | 临时文件空间；不是证据持久卷 |
| `cap_drop` / `security_opt` | 保留默认（模板） | 数组；ALL / no-new-privileges:true | 去能力及禁止提权，随服务配置生效 |
| `ulimits.nofile.soft/hard` | 保留默认（模板） | 整数；65536/65536 | 进程文件描述符限制，核HostConfig |
| `cpus` / `mem_limit` | 保留默认（模板） | 数值4 / 字符串8g | CPU/内存限额；不据此声称并发能力已验 |
| `restart` | 保留默认（模板） | 字符串；unless-stopped | 容器重启策略，不是模型请求重试 |
| `healthcheck.test` | 保留默认（模板） | 命令数组 | 容器内GET `/health/liveliness`，请求timeout4秒；只证明存活，不产生推理 |
| `healthcheck.interval/timeout/retries` | 保留默认（模板） | 10s / 5s / 12 | 检查周期、单次容器检查超时及失败次数；不证明业务调用成功 |

## 3. 调查进程的路由与预算

### 3.1 调用进程环境

当前执行器从显式进程配置与租户有效配置解析调用目标，并核对目标policy。部署文件必须给出确定值；下列优先顺序用于核对实际结果，不是推荐省略配置。

| 配置项 | 部署分类 | 类型／填写要求 | 加载、优先级与验证 |
| --- | --- | --- | --- |
| `SOCAI2_INVESTIGATION_POLICY` | 部署必填（所选入口） | 必填绝对路径字符串 | 或统一工厂的`investigation_policy_file`指定同一文件；进程缓存。核policy SHA及A/I/Case profile SHA |
| `OPENAI_BASE_URL` / `LLM_BASE_URL` | 部署必填（所选入口） | URL字符串 | 前者非空优先；未显式提供且model为网关alias时才解析LLM_GATEWAY_URL。最终地址须来自本批profile |
| `OPENAI_MODEL` / `LLM_MODEL` / `AISOC_LLM_MODEL` | 部署必填（所选入口） | 字符串 | 依次取首个非空值；当前目标与policy.alias一致。若租户存在启用的model/base_url/凭据覆盖，核最终解析来源，不只看env |
| `LLM_GATEWAY_URL` | 启用时必填（网关路由） | URL字符串 | alias采用的网关base，例如同网络`http://litellm:4000/v1`；具体模型ID不会自动当作alias走此回落 |
| `OPENAI_API_KEY` / `LLM_API_KEY` | 部署必填（所选入口） | 私密字符串 | 显式base路径按前者优先取客户端key；当显式base指向LiteLLM时，这里应配置访问网关的key，不能混成provider key |
| `LITELLM_MASTER_KEY` | 启用时必填（网关路由） | 私密字符串 | 自动采用LLM_GATEWAY_URL的路径优先用此key，再取OPENAI_API_KEY；回执不得返回明文 |
| `SOCAI2_MODEL_PROTOCOL` | 保留默认（模板） | 字符串；目标chat_completions | 必须与policy.model.protocol一致；当前计量执行链只支持此协议，不在目标说明中启用其他历史路径 |
| `SOCAI2_MODEL_SCHEMA_PROFILE` | 保留默认（模板） | 字符串；目标vllm_grammar_v1 | 与policy一致。standard原样传Schema；vllm_grammar_v1省略不支持的uniqueItems及自由正文长度/非空pattern，保留专用格式pattern与枚举；本地字段、非空、长度、引用和重复校验保持 |
| `AISOC_AIRGAPPED` / `AISOC_AIRGAP_ALLOWLIST` | 保留默认；allowlist按环境确认 | bool / 主机列表 | 出站限制；网关、tokenizer、embedding及vector都需符合实际环境规则。列表填主机，不填完整凭据URL |
| `AISOC_AGENTS_LLM_CONTRACT_MAX_CHARS` | 程序生成（启动器） | 当前1048576 | 常规启动器从model.max_prepared_bytes设置字符保护；候选analysis.json的runtime_env显式同步该值。与准备字节及存储原件上限分开；容器env改变需重建，不能只restart旧容器 |
| `SOCAI2_KNOWLEDGE_PROFILE` | 启用时必填（知识来源） | 路径字符串 | 知识客户端配置入口；见第5节；浏览器和测试账本不读取私密连接 |
| `SOCAI2_SOURCE_KNOWLEDGE_ENABLED` | 保留默认（模板） | bool文本；启用用true，未设视为false | 是否连接调查知识来源；profile存在不自动启用，必须与本轮来源配置一起核对 |

路由解析依据[llm_resolver.py](../../services/api/app/services/llm_resolver.py)、[model_aliases.py](../../services/api/app/services/model_aliases.py)和[当前Gateway](../../services/api/app/socai2/baseline_analysis_model.py)。本轮只说明所用路径，不增加其他产品角色、BYOK管理或外部模型切换任务。

11-16正文语法兼容修正已完成本地直接验证，沿原profile且不增加配置项；须随新处理镜像生效，不能认为运行中的旧r2镜像已因同名profile自动修复。[同输入一次重试与边界](evidence/model-output-compatibility-20261116-01/说明.txt)记录1166/stop及原合同校验，正式修正版尚未部署；额度继续保留已确认值，不用加大max_tokens处理空白循环。

### 3.2 TOML必填字段

当前文件的所有字段均显式给出，无预算默认回落；`version=socai2.investigation-policy.v1.2`是身份字符串，最终身份还包括内容hash。**统一目标由输入合同及指纹判断，不由C3额度是否8192判断。** 数值可按已确认预算配置，不能换预算就误认另一合同版本。

| 字段 | 部署分类 | 类型／当前值 | 用途与限制 |
| --- | --- | --- | --- |
| `single_model_timeout_seconds` | 保留默认（模板） | 正整数；300 | 每次实际模型请求上限，还受剩余Run时间限制 |
| `final_reserve_seconds` | 保留默认（模板） | 正整数；300 | 为最终阶段保留时间；需single_model_timeout≤该值<case.deadline_seconds |
| `case.max_model_calls` | 保留默认（模板） | 非负整数；6 | 单Case Run模型次数上限，补答也计入 |
| `case.max_tool_calls` | 保留默认（模板） | 非负整数；4 | 单Run工具额度 |
| `case.max_total_tokens` | 保留默认（模板） | 非负整数；393216 | 单Run累计token预算，6×65536；不是单次上下文长度 |
| `case.max_rows_per_query` | 保留默认（模板） | 非负整数；200 | Run工具行数上限；实际工具可有更小配置，如统一执行器log_query.max_rows_per_query=50 |
| `case.deadline_seconds` | 保留默认（模板） | 正整数；1500 | 单Run期限，不是Case持续更新窗口 |
| `alert_basic.max_model_calls/max_tool_calls/max_total_tokens/max_rows_per_query/deadline_seconds` | 保留默认（模板） | 同上类型；2 / 3 / 131072 / 200 / 300 | A单Run额度与期限，最多2次完整服务窗口；次数/工具/期限保持 |
| `incident_diagnosis.max_model_calls/max_tool_calls/max_total_tokens/max_rows_per_query/deadline_seconds` | 保留默认（模板） | 同上类型；2 / 0 / 131072 / 0 / 300 | I单Run额度；工具与查询行数0表示本环节不派查询 |
| `views.max_graph_bytes` | 保留默认（模板） | 整数且>16384；1048576 | C5派生图视图字节上限，不限制原始工件保存或HTTP读取 |
| `model.alias` | 保留默认（模板） | 非空字符串；aisoc-investigation | 请求模型alias，须与实际Gateway配置一致 |
| `model.protocol` | 保留默认（模板） | 当前只允许chat_completions | 计量与生成协议一致 |
| `model.schema_profile` | 保留默认（模板） | 非空字符串；vllm_grammar_v1 | 实际Gateway还校验standard/vllm_grammar_v1能力；不得只改一侧 |
| `model.context_tokens` | 保留默认（模板） | 正整数；65536 | 单次模型上下文容量，tokenizer返回max_model_len必须相等 |
| `model.max_prepared_bytes` | 保留默认（模板） | 正整数；1048576（1 MiB） | 送模视图准备字节额度；仍按任务筛选，不等于token输入容量，不删除数据库原件 |
| `model.final_reserved_input_tokens` | 保留默认（模板） | 正整数；48128 | C6输入预留；加16384输出及1024 safety恰好65536 |
| `model.final_reserved_calls` | 保留默认（模板） | 正整数；2 | 最终处理预留模型调用次数，仍受单Run总额度 |
| `model.output_tokens.A/I/C3/Deep/C6` | 保留默认（模板） | 每项正整数且<context_tokens；8192/8192/16384/8192/16384 | 各阶段请求max_tokens；计量与真正发出的值必须一致 |
| `model.tokenizer.endpoint` | 部署必填（后端绑定） | http/https URL；示例43:8000/tokenize | 无URL用户名/密码、query或fragment；按候选上游配置，不自动推断 |
| `model.tokenizer.served_model` | 部署必填（后端绑定） | 非空字符串；aisoc-test-investigation | tokenizer后端真实模型名，与alias分开；核同一模型空间 |
| `model.tokenizer.timeout_seconds` | 保留默认（模板） | 正整数；30 | 每个计量HTTP请求超时，还受剩余deadline |
| `model.tokenizer.safety_tokens` | 保留默认（模板） | 正整数；1024 | 在计量输入上增加保守余量，不当作真实usage |
| `model.tokenizer.authentication` | 保留默认（模板） | 当前仅none | 计量器没有其他鉴权实现；不能在此填key并期待生效 |
| `alert_io.profile` / `incident_io.profile` / `case_io.profile` | 保留默认（模板） | 包内JSON文件名；三份*-input-v1.json | 当前统一工厂三者必备，缺合同明确失败。profile文件名及内容须随包同步 |

tokenizer对最终消息和非消息请求包络分别计数，再加安全余量与输出上限；真实响应usage另记，未知费用不能记0。计量请求不生成正文；失败应保留为发送前阻断，不能改成已执行模型成功。加载与边界实现见[runtime_policy.py](../../services/api/app/socai2/runtime_policy.py)及[token_budget.py](../../services/api/app/socai2/token_budget.py)。

当前65536已在11-16由实际后端模型目录/tokenizer再次确认；A/I/Deep的消息+包络最多56320 tokens，C3/C6最多48128，再各加1024安全余量及上述输出上限。A/I单Run总预算提高后，单次有效输入比原24000预算下更大；C3/C6更多输出会占用部分输入空间，不能宣称固定窗口内两者都增大。负责人已确认当前模型为Qwen3.5-9B，与保存的模型目录路径一致；该型号[官方原生最大为262144](https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/config.json)，不代表当前服务已开放。扩大服务窗口须先核实际模型/启动参数及资源，再成套同步context_tokens、C6预留和总预算并读回；不直接拿理论容量替换服务容量。C3七部分、最多5发现和一次补答规则保持。候选曾漏设输入字符保护而沿用60000，现已按[实际加载回执](evidence/streaming-budget-20261116-01/input-guard-finish-01.json)补齐；替代调度容器未启动，4次真实续验生成与无网络容量探针分别记录。

TOML还有两组完整结构配置：

| 结构 | 部署分类 | 字段类型及填写 | 用途与校验 |
| --- | --- | --- | --- |
| `tools.<tool>` | 保留默认（模板） | `<tool>`当前为process_activity/network_connections/authentication_activity/product_host_details；各含purpose、inputs、can_answer、cannot_answer四个非空字符串 | 给模型说明已有工具的目的、冻结输入和解释边界；配置描述不自动实现工具或扩大调用权限。字段集合必须完整，不额外增加执行SQL |
| `labels.version` | 保留默认（模板） | 非空字符串 | 检测标签释义版本 |
| `labels.entries.<id>` | 保留默认（模板） | name、description、source_url、verified_on四个非空字符串；source_url必须https | 标签名称、说明、来源及核对日期；原件当前含TA0009/T1005。检测标签不是本案事实，词典按完整结构随包冻结，不逐字复制到部署文档 |

## 4. 输入profile配置结构

三份JSON是当前合同的一部分，与policy一起冻结和发布。它们修改的是模型业务视图，原始材料仍在后台保存。下列结构表说明每个配置组的用途；字符串词典和提示正文以原件为准，不能在部署文档维护第二份提示词。

### 4.1 A与I共同结构及差异

顶层`version`是固定合同版本字符串；`system_prompt`为非空提示正文；`render`是下面的配置对象；`output_validation.prose_alias_format=namespaced_v1`是当前活动合同要求。A的render.revision当前alert-business-input-v2，I当前incident-business-input-v4；版本与hash同时核对。

| `render`字段／组 | 部署分类 | 类型与用途 |
| --- | --- | --- |
| `revision`、`task`；A的`format_instruction/query_rule`；I的`member_prefix/history_prefix` | 保留默认（模板） | 字符串；视图版本、任务/格式/查询解释边界、A/H等冻结短号前缀 |
| `roles`、`field_labels`；A的`actions/outcomes/queries/query_outcomes/block_labels`；I的`text_field_labels/query_names/query_text_fields/query_row_labels/notices` | 保留默认（模板） | 字符串映射；已知角色/字段/状态的显示名和空态文案，不改原始正文 |
| A的`known_metadata_paths`；I的`metadata_paths/out_of_task_paths/event_roots` | 保留默认（模板） | 路径字符串数组；标记后台字段、任务外字段及原始活动根路径；按路径匹配，不按具体样本值判断 |
| `container_rules.<path>.omit/empty` | 保留默认（模板） | 每个容器路径对应字段数组；omit去掉已识别后台项，empty仅省略配置中无意义空项，不能用真值判断删0/false |
| `raw_alert_envelope.required_fields/backend_fields/empty_optional` | 保留默认（模板） | required_fields为字段→类型名对象；其余为字段数组。先识别已知原告警封装，再去后台字段及配置的空项，未知结构不能整包吞掉 |
| `raw_field_aliases`、`raw_alert_mirrors` | 保留默认（模板） | 路径→字段字符串映射；仅按已定义关系识别重复/镜像，不语义改写正文 |
| `object_paths`、`object_index_keys` | 保留默认（模板） | 对象类别→路径数组；索引字段数组；构造主机/账号/IP等任务相关对象视图 |
| `enrichment_schema`、`backend_enrichment_items` | 保留默认（模板） | schema字符串；kind→后台字段数组；只识别对应融合材料封装 |
| `history_catalog_fields`、`serialized_material_paths` | 保留默认（模板） | 字段/路径数组；历史目录与可识别序列化材料的位置，保留来源角色 |
| I的`field_values.<field>.type/values` | 保留默认（模板） | 类型名字符串与已知值→显示值字典；精确类型/值转换，不翻译任意文本 |
| I的`text_field_order/role_order` | 保留默认（模板） | 字符串数组；稳定展示顺序 |
| I的`program_backend_keys/member_fact_backend_keys` | 保留默认（模板） | 字段数组；程序统计和成员事实视图的后台字段过滤 |
| I的`query_receipt_fields/query_record_backend_fields/query_envelope_backend_fields/query_scope_backend_fields/query_selector_backend_fields` | 保留默认（模板） | 字段数组；明确查询业务记录与后台执行回执的边界，原回执仍保存 |
| I的`incident_only.roles/raw_alert_backend_fields/container_omit` | 保留默认（模板） | 角色映射、字段数组、容器→省略字段数组；I专属材料整理规则，不照搬A输入 |

### 4.2 Case当前数值、选择和输出配置

| 字段 | 部署分类 | 类型／当前值 | 用途与限制 |
| --- | --- | --- | --- |
| `version` / `business_profile` | 保留默认（模板） | 字符串；socai2.case-boundary.v1 / incident-input-v1.json | Case合同及共享业务字段定义文件；实际Case仍按自身任务选择材料 |
| `enrichment.version` | 保留默认（模板） | 固定字符串socai2.case-background-coverage.v1 | 背景补充选择规则身份 |
| `enrichment.reserved_tool_calls` | 保留默认（模板） | 非负整数；2 | 给后续证据查询预留，实际还受工具总额度的一半限制 |
| `enrichment.paired_source_penalty` | 保留默认（模板） | 非负整数；100 | 对已成对覆盖的背景来源降优先级 |
| `enrichment.priorities` | 保留默认（模板） | 六类非负整数；assets100、knowledge90、threat_intel80、ueba70、history60、graph50 | 当前背景选择优先级，不意味着来源已连通 |
| `c3_output.version/max_findings/max_followups/instruction` | 保留默认（模板） | 固定版本；整数5/2；非空模板 | C3发现/后续要求上限；loader容量允许0–24/0–12，模板必须含两个额度占位符；不以存储最大值替换本批配置 |
| `c3_completion.version/max_attempts/instruction/dependencies` | 保留默认（模板） | 固定版本；整数0或1，默认1；含{missing}模板；字段→字段数组 | 0禁用、1最多一次缺字段/未闭合条目补答；已保留条目不覆盖，补答失败仍保留初答。依赖键固定summary/members/findings/questions/domains/conflicts/followups，不新增无限重试。D3本机变更，21仍以实际发布版本为准 |
| `program_output.version/instruction/c3_coverage` | 保留默认（模板） | 当前v2；非空正文；true | 程序恢复统计、关联及实际C3覆盖。活动执行必须v2且c3_coverage=true |
| `followup_routing.version/C3/Deep` | 保留默认（模板） | 固定版本及非空说明字符串 | 后续取证要求与实际工具派发之间的职责说明，建议不当作已执行 |
| `fixed_comparison.version/summary/instruction` | 保留默认（模板） | 固定版本、非空summary≤1200字符、说明 | 本轮固定比较基线展示，不回查后来的“最新”结果替换 |
| `c3_input_selection.omit_unusable_prior_results/prefer_incident_conclusion` | 保留默认（模板） | bool；true/true | 不把不可用旧结论充有效输入；优先使用适用事件结论，仍保留原范围 |
| `followup_input_selection.stages/final_prior_omit/defer_prior_context/graph_directory_relations` | 保留默认（模板） | 数组Deep/C6；数组members/domains；bool true；数组source_reports_object | 控制后续阶段已选材料与图目录重复项，不能丢掉必要事实来源 |
| `knowledge_selection.stage_max_characters.C3/Deep/C6` | 保留默认（模板） | 非负整数；12000/8000/8000 | 各阶段知识视图容量，不等于删除知识原文 |
| `knowledge_selection.stage_purposes` | 保留默认（模板） | 每阶段非空用途数组 | C3/C6三用途；Deep为取证指导和历史参考，详见第5节 |
| `knowledge_selection.deep_question_purposes/final_question_purposes` | 保留默认（模板） | 问题类别→用途数组；authorization为空数组 | 定向限制该问题可用知识用途；空数组是有意义配置，不强补查询 |
| `token_measurement.stage/command_timeout_seconds` | 保留默认（模板） | C3 / 45秒 | 当前profile带有该验证元数据，但生产执行器不读取此组作为运行参数；实际生成及计量使用TOML和Run期限，不能把45秒当模型超时 |

Case其余结构均按原件随包发布：

| 配置组 | 部署分类 | 完整结构及用途 |
| --- | --- | --- |
| `member_prefix/external_member_prefix/object_prefix/incident_prefix`、`task/system_suffix/citation_instruction` | 保留默认（模板） | 字符串；范围内外成员、对象、事件短号及任务/引用说明 |
| `system_replacements` | 保留默认（模板） | `{old,new}`字符串对象数组；已审核的系统提示替换，不用于改写用户材料 |
| `rules.<kind>.omit/empty`、`context_projection.<path>.omit/empty` | 保留默认（模板） | 字段数组；按数据角色或精确容器控制后台字段与可省空项 |
| `hierarchy.<kind>[]` | 保留默认（模板） | 每项path、action、reason，constant动作另有value；JSON Pointer支持`*`，动作omit/empty/constant；记录省略原因及原值hash，未知字段保留 |
| `activity_time_paths/material_optional_paths/material_backend_paths` | 保留默认（模板） | 路径数组；业务活动时间、已知可空及后台材料字段 |
| `empty_enrichment_kinds.<kind>` | 保留默认（模板） | wrapper_keys、payload_keys数组及payload_mode字符串；只省已识别的空或纯后台封装 |
| `material_field_aliases/material_labels/block_labels` | 保留默认（模板） | 字符串字典；已定义字段别名与块名称，原件不受影响 |
| `semantic_rules.<kind>[]` | 保留默认（模板） | path/type/values；精确路径、类型及已知枚举翻译，不推断正文含义 |
| `presentation` | 保留默认（模板） | receipt_shared_fields/tool_shared_fields/equal_fields/repeatable_prior_prose/map_containers/tool_field_order数组；labels字典；member_scope_kind字符串；tool_field_detail含required_business_fields/known_fields数组。控制重复显示与工具业务说明，不能把完整原件截短 |
| `field_meanings[]/question_instructions` | 保留默认（模板） | `{paths:[字符串],meaning:字符串}`数组；问题类别→说明字典；补业务字段含义与问题职责 |
| `followup` | 保留默认（模板） | version；Deep/C6/common非空说明；query_omit/execution_omit/comparison_omit/comparison_source_omit/prior_followup_omit数组；labels字典；parent_dependencies对象数组（suffix/source_kind/label/keep）。按来源路径后缀与context_children/material_fields选择依赖，keep为保留字段数组；定义各后续阶段所需前序材料及后台过滤 |
| `knowledge_selection.content_projection` | 保留默认（模板） | version；profiles数组，每项name、required_fields（字段→类型）、rules（同hierarchy）；labels字典。只对匹配结构的知识正文做字段选择，其他原文按合同保留 |
| `c3_input_selection` | 保留默认（模板） | version；material_field_aliases映射；material_backend_paths/history_catalog_fields/object_index_fields/incident_program_limitations数组；historical_card_schema字符串；hierarchy规则；query_names/labels字典；两项bool见上表。定义C3专属材料，不整包透传上游 |
| `followup_input_selection` | 保留默认（模板） | version；query_backend_fields数组；hierarchy规则；no_tools_text/unavailable_text/graph_unavailable_text字符串；labels字典；其余数值/选择见上表。明确无工具、不可用与合法查空 |
| `comparison_input_selection` | 保留默认（模板） | version；omit含findings/questions/case_impact字段数组；question_states/exclude_questions数组；instruction字符串。只选固定比较所需业务内容 |
| `context_input_selection` | 保留默认（模板） | version；human_feedback/prior_result/current_assessment各含omit/empty数组；labels字典。人工陈述、历史结果、当前采用各保留原角色 |

最低验证是加载三份当前profile、核活动合同要求及hash，并在直接测试中验证引用/范围/预算；仅JSON能解析不代表业务或正文质量通过。真实模型输出可能因格式、超时或引用失败阻断流程，不能把这些程序失败归入“质量后置”。

## 5. Ollama与知识检索

### 5.1 嵌入服务Compose全部配置

| 配置项 | 部署分类 | 类型／当前值 | 用途与核对 |
| --- | --- | --- | --- |
| `name` / `services.ollama-embedding` | 部署必填（目标绑定） | socai2 / ollama-embedding | 项目/服务身份；候选以实际发布清单为准 |
| `image` / `pull_policy` | 保留默认（模板） | 固定sha256 / never | 使用已准备镜像，不拉取新版本 |
| `environment.OLLAMA_HOST` | 保留默认（模板） | 字符串；0.0.0.0:11434 | 容器内监听，宿主暴露由ports决定 |
| `environment.OLLAMA_NUM_PARALLEL` | 保留默认（模板） | 数值字符串；1 | 单模型并行处理设置，不作为压力验收结论 |
| `environment.OLLAMA_MAX_LOADED_MODELS` | 保留默认（模板） | 数值字符串；1 | 同时加载模型数量限制 |
| `environment.CUDA_VISIBLE_DEVICES` | 保留默认（模板） | 字符串；-1 | 本配置不使用CUDA GPU；还需核容器设备挂载及请求num_gpu |
| `ports` | 部署必填（目标绑定） | 127.0.0.1:11435:11434 | 宿主回环访问；同网络客户端用ollama-embedding:11434 |
| `volumes` | 部署必填（目标绑定） | runtime-data/ollama-embedding→/root/.ollama | 模型持久目录；升级保留并核模型清单/hash，不临时自动pull |
| `cap_drop/security_opt/restart` | 保留默认（模板） | ALL / no-new-privileges:true / unless-stopped | 容器能力、提权与重启策略 |
| `cpus/mem_limit/memswap_limit` | 保留默认（模板） | 16 / 32g / 64g | CPU、内存及含swap总限额；实际可用swap取决于宿主 |
| `healthcheck.test` | 保留默认（模板） | CMD ollama show qwen3-embedding:0.6b | 检查指定模型存在，不生成嵌入 |
| `healthcheck.interval/timeout/retries` | 保留默认（模板） | 10s / 5s / 12 | 检查周期、超时及失败次数 |

监听与并行配置含义可核[Ollama配置说明](https://docs.ollama.com/faq)。当前配置值全部显式设置，不依赖网站或新版本默认。

### 5.2 knowledge-profile全部字段

除下文明确两个history默认外，现行结构字段按[knowledge_config.py](../../services/api/app/socai2/knowledge_config.py)显式填写；strict类型及额外字段拒绝。`version`必须为`socai2.case-knowledge.v1`。加载成功记录原JSON SHA；不自动猜后端、模型或集合。

| 字段 | 部署分类 | 类型／当前示例 | 用途、约束和验证 |
| --- | --- | --- | --- |
| `embedding.url` | 部署必填（启用知识时） | HTTP URL；http://ollama-embedding:11434/api/embed | 完整嵌入端点，不是base URL；容器网络须可解析该主机 |
| `embedding.model` | 保留默认（模板） | 非空字符串；qwen3-embedding:0.6b | 响应model必须相同，不能静默换模型 |
| `embedding.dimension` | 保留默认（模板） | 正整数；1024 | 每个向量必须此维度、数值有限且非全0；与Qdrant空间一致 |
| `embedding.timeout_seconds` | 保留默认（模板） | 正整数；90 | 单次嵌入HTTP请求超时 |
| `embedding.options` | 保留默认（模板） | 必填对象；num_gpu=0、num_thread=16、num_ctx=32768 | 传给Ollama的运行选项：GPU使用、线程数及上下文设置。项目loader只校验是对象，不声称验证Ollama所有子项；本批发送原配置 |
| `vector.url` | 部署必填（启用知识时） | HTTP URL；示例http://192.168.1.21:6333 | Qdrant base；候选需绑定其明确目标，不推断正式可写 |
| `vector.collection` | 部署必填（启用知识时） | 字符串，仅字母数字下划线连字符；socai2_knowledge_qwen06b_1024 | 仅知识文档集合；不能复用其他维度/模型的索引 |
| `vector.api_key_file` | 启用时必填（向量鉴权）；键必存 | 字符串或null，字段必填；/run/knowledge/qdrant-key | 客户端读取私密文件为api-key请求头；null表示不发该头，不能用null绕过真实服务要求 |
| `vector.timeout_seconds` | 保留默认（模板） | 正整数；20 | 每个向量API请求超时 |
| `topics.material_paths` | 保留默认（模板） | 非空路径数组 | 从原观察取检索词；当前为进程命令/名称、动作及raw command_line |
| `topics.label_paths` | 保留默认（模板） | 路径数组，可空 | 告警title、检测规则名仅为source_label线索，不提升为事实 |
| `topics.max_value_characters` | 保留默认（模板） | 正整数；512 | 单个检索词字符上限；保留来源与截断记录，不截原件 |
| `topics.max_query_characters` | 保留默认（模板） | 正整数；4096 | 完整查询文本上限，超限明确失败 |
| `topics.max_queries` | 保留默认（模板） | 正整数；12 | 单次知识工具选择器数量上限 |
| `max_index_chunks` | 保留默认（模板） | 正整数；24 | 单次显式索引的文档块数量上限；空集或超限拒绝 |
| `max_chunk_characters` | 保留默认（模板） | 正整数；1600 | 普通知识块正文长度上限；历史卡片使用history.max_card_characters |
| `history` | 启用时必填（历史用途）；当前保留 | 对象或省略/null | 与historical_case_reference必须同时存在或同时缺省；当前已配置三用途 |
| `history.lookback_days` | 保留默认（启用历史时） | 正整数；90 | 以调查窗口起点向前取历史，不含当前及未来观察 |
| `history.max_import_alerts` | 保留默认（启用历史时） | 正整数；8 | 单次历史告警材料导入数量限制 |
| `history.max_card_characters` | 保留默认（启用历史时） | 正整数；16000 | 历史卡片正文上限，超限不静默删改 |
| `history.observation_paths` | 保留默认（启用历史时） | 非空路径数组 | 卡片保留进程、动作、账号、端点、原命令等原观察 |
| `history.sync_after_adopted_triage` | 保留默认（启用历史时） | bool；当前true；loader默认false | 允许已采用分诊后尝试同步历史知识；配置存在不证明后台消费者已部署运行 |
| `history.sync_timeout_seconds` | 启用时必填（同步）；当前120 | 正整数或null；当前120；默认null | 开启同步时必须有正值，限定同步期限 |
| `applicability.tag_prefix/generic_tag` | 保留默认（模板） | 非空字符串；applies: / applicability:generic | 文档适用条件标签与通用材料标签 |
| `applicability.facets.<name>.paths` | 保留默认（模板） | 非空路径数组 | 从材料提取适用条件，不将相似度当作已满足条件 |
| `applicability.facets.<name>.normalization` | 保留默认（模板） | exact/casefold/basename_casefold | 精确值、大小写归一、文件基名加大小写归一 |
| `applicability.facets.<name>.topic` | 保留默认（模板） | bool | 是否提供历史检索所需主题条件；当前process.name/activity.action/class_uid为true，os.name/product.name为false |

请求固定`truncate=false`，超上下文应报错，不悄悄截短；这一参数来自当前客户端，不是另一项可调profile。API含义见[Ollama嵌入接口](https://docs.ollama.com/api/embed)。客户端还核数量、模型名、维度及有限向量，保存输入/向量hash；未知usage不能填0。

### 5.3 三用途的每个配置字段

`purposes`必须含technical_explanation与investigation_guidance，可加historical_case_reference；不接受其他用途。每项完整字段如下：

| 字段 | 部署分类 | 类型与约束 | 当前值／用途 |
| --- | --- | --- | --- |
| `label` | 保留默认（模板） | 字符串 | 技术解释／取证指导／历史案例参考，供界面与材料标注 |
| `template` | 保留默认（模板） | 字符串且恰有一个{topic} | 对各用途拼接查询；正文以原配置为准，不在部署时改写 |
| `doc_kinds` | 保留默认（模板） | 非空字符串数组 | 技术解释wiki/other/runbook；取证指导runbook/playbook/sop/other；历史other |
| `tag` | 保留默认（模板） | 字符串 | 对应knowledge:technical_explanation / knowledge:investigation_guidance / knowledge:historical_case_reference；索引选用途时必须匹配 |
| `candidate_limit` | 保留默认（模板） | 正整数；三者8 | Qdrant召回候选上限，必须≥limit；返回后还要核文档版本/适用条件 |
| `limit` | 保留默认（模板） | 正整数；2/2/1 | 各用途最终选入上限，不把全部候选送模 |
| `score_threshold` | 保留默认（模板） | float，-1到1；三者0.45 | 向量检索阈值，不是事实准确率或恶意置信度 |
| `use` | 保留默认（模板） | 字符串 | 各用途的解释边界；知识不证明本案行为、授权、结果或处置已执行 |

Qdrant集合必须为1024维Cosine空间，并与embedding model/维度匹配。查询限定tenant、model、dimension、purpose和doc_kind；历史再限定时间并排除当前成员。命中后回读PG文档与内容hash并核适用条件，旧/缺正文不能当作新命中。查询路径只检查已有集合；显式索引路径才允许在缺失时创建集合及写向量。索引会调用嵌入并写Qdrant，不能把它包装成只读预检。

### 5.4 程序生成的值不作为人工配置

| 程序生成项 | 生成来源／核对方式 |
| --- | --- |
| policy身份与SHA、A/I/Case输入profile SHA、knowledge profile SHA | 从所选文件原字节计算；部署确认所选文件，运行/发布器生成并保存摘要，不手填摘要去匹配旧包 |
| 构建清单中的镜像/源码摘要、Run中的冻结配置快照 | 构建或执行过程生成；核对目标包与实际运行，不能用手填版本字符串代替 |
| tokenizer计量、真实usage、请求/响应及工具回执 | 来自本次真实执行；未知值保持未知，不作为部署默认值 |

## 6. 部署前与部署后的最小核对

1. 取本轮最终候选包、policy、三份输入profile、knowledge JSON、两份Compose及LiteLLM YAML，记录版本/hash。生成绑定候选实际地址与私密路径的配置，确认secret挂载可读，不打印内容。
2. 离线加载policy并要求当前三个执行合同；加载knowledge JSON校验字段、三用途、维度和限制。核网关alias、运行model、tokenizer served_model/context及输出额度一致；缺项不能退到旧示例。
3. 获准部署的步骤中分别启动指定依赖/服务，核实际镜像、命令、端口、配置挂载摘要、存活状态，以及Ollama模型清单/Qdrant集合元数据。存活检查不算真实模型或检索通过。
4. 按测试计划先单模块再相邻链，使用新批真实生成/嵌入/查询，保存请求、原答、工具回执、预算、解析、落库及HTTP读回；格式/连接/保存失败保留失败，正文质量单列。
5. 最终Kafka整链与4177 HTTP取数按各自交付进度完成；本文配置解释、离线校验或已有历史回执均不能核销尚未执行的验收。

本次[离线核对回执](evidence/deployment-docs-20261115-01/model-config-docs-01.json)记录实际policy/knowledge/test-service loader通过、目标配置摘要前后不变，以及10份相关文档194个本地链接存在。输入profile顶层及render配置组均有说明；该检查只证明配置与文档对齐，不证明21加载或真实模型通过。没有更改上述运行配置、模型提示正文、服务、数据或旧批次。测试账本自身配置另见[测试服务部署入口](../../deploy/investigation-test/README.md)。
