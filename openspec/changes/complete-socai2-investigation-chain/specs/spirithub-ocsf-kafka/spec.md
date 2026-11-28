## ADDED Requirements

### Requirement: Delivery execution read limits preserve frozen selection bindings

The native lake delivery runtime SHALL accept an optional complete `read_limits` object in its delivery configuration. Its fields SHALL be `max_records`, `max_result_bytes`, `query_timeout_seconds`, `connect_timeout_seconds`, and `send_receive_timeout_seconds`, each a positive integer. When absent, the runtime SHALL use the existing selection read limits without changing prior behavior. The runtime SHALL preserve the original selection and receive policies, source scope, identity, immutable-version rules, and existing delivery binding digest.

#### Scenario: Existing delivery configuration omits execution limits

- **WHEN** the delivery configuration has no `read_limits`
- **THEN** both the scanner and ClickHouse client use the original selection read limits, and the existing binding remains unchanged.

#### Scenario: Explicit delivery limits cover the native source scope

- **WHEN** the delivery configuration supplies complete valid execution read limits
- **THEN** those limits control the bounded native scan and client timeouts without modifying either bound policy or rewriting existing ledger rows.
- **AND** the scanner retains the same source predicate, version deduplication, over-limit rejection, and complete-read verification.

#### Scenario: Invalid or insufficient execution limits

- **WHEN** execution limits are incomplete, contain unknown fields, or include boolean, non-integer or non-positive values
- **THEN** the configuration is rejected before receipt processing.
- **WHEN** the native scope still exceeds valid configured limits or cannot be read completely
- **THEN** delivery stops before processing that scan, without filtering test identities, truncating records, or changing model budgets.

### Requirement: SpiritHub 清洗日志进入 socai2 Kafka

系统 MUST 接收 SpiritHub 直接发送到我方明确指定 Apache Kafka Topic 的清洗日志。当前跨集群转发作为过渡路径保留，其 Key 和 OCSF 正文保持原样，源消费组进度依据目的端投递确认推进。正式直写切换必须明确稳定事件身份及切换范围，不能把过渡转发与正式直写同时输入的重复记录当作独立事件。

#### Scenario: 从 Kafka UI 核对已转发清洗日志

- **WHEN** SpiritHub 的清洗输出 Topic 中有有效 OCSF 记录且转发服务在线
- **THEN** socai2 Kafka 专用 Topic 中可读到相同的 Key 和 OCSF 正文，Kafka UI 在 socai2 集群的消息页可查看该记录及目的分区和 offset

#### Scenario: 转发服务沿已保存游标恢复

- **WHEN** 转发服务使用同一源消费组重启
- **THEN** 服务从该组已提交的游标继续读取，首启以配置指定的源 Topic 保留起点为准，重启时未完成确认的记录仍可再次处理

#### Scenario: 将完整归档的清洗结果交给测试方

- **WHEN** 使用独立批次回放已指定的六份设备归档
- **THEN** 逐条保留来源文件、行号和 Key，正常及未分类的 OCSF 结果可在 socai2 Kafka 测试主题读回，转换失败逐条记录并与输入总数对账

#### Scenario: 将归档测试 Topic 复制到搜索服务

- **WHEN** 用户明确请求将已交付的归档测试 Topic 复制到 OpenSearch
- **THEN** 使用明确来源的整批 dump 和稳定文档 ID 写入独立索引，保留 Kafka 坐标和 OCSF，核对保存结果，并提供只查询该索引的查看入口

#### Scenario: Discover 可读取含长整数和控制字符的归档

- **WHEN** 归档查询在同一响应中返回需要保留精度的长整数以及含控制字符的字符串
- **THEN** Dashboards 的长数字搜索响应可由严格 JSON 解析器读取，并保持查询结果中的整数精度和字符串原值


### Requirement: 指定 Topic 全量落湖与独立告警选择

系统 MUST 负责将指定接入 Topic 的所有类别日志持久保存到 ClickHouse，接入 profile 默认开启消费及落湖。原件、来源、事件时间及 Kafka 坐标必须可追溯；未完成持久化或执行未知的记录不得以成功提交位点方式跳过。已有告警的选择 MUST 与全量落湖分开，不能按 class 白名单丢弃上下文日志。

#### Scenario: 非告警与未分类日志保留

- **WHEN** 指定 Topic 收到普通活动、已有告警或 partial/class 0 的日志
- **THEN** 所有记录先具有可追溯的完整保存或明确失败去向，仅满足已确认分类合同的已有告警进入告警分诊，原字段及来源关联保持

#### Scenario: 湖写入失败

- **WHEN** 一批日志尚未获得 ClickHouse 持久化确认
- **THEN** 消费位点不得跨过该批并标记成功，失败或未知状态保留，读回验证区分消息消费、完整原件保存及调查可检索

#### Scenario: 分区持久确认与低流量

- **WHEN** 裸输入接入profile启用，某分区收到不足批量上限的消息
- **THEN** 按配置最长等待完成实际保存，仅在本批全部保存回执确认后提交该分区最后处理位置加一；不等待下一条消息，不以客户端已拉取位置代替已保存位置

#### Scenario: 写入结果未知或消费被取消

- **WHEN** INSERT回执未知、运行被取消或处理期间分区被撤销
- **THEN** 保留未提交输入范围，等待已开始的驱动调用结束后按稳定身份核对未知保存，不自动重写或用后续成功跨过该范围；停止接入并使就绪状态反映停止，原未知状态不改成成功

### Requirement: 统一事件表保留完整内容与明确的列语义

系统 MUST 在同一日志湖事件表内保存各类别记录，以有类型的公共列承载身份、来源、类别、时间、设备和网络端点等查询信息，以完整JSON保留OCSF及未知扩展字段。页面展示预览不得替换后台完整内容；旧记录新增字段必须保持未知语义。新增列和读写路径 MUST 以增量方式交付，保留既有数据及冻结告警材料关联。

#### Scenario: 长正文与未建列的扩展字段保存

- **WHEN** 指定输入含超过旧应用预览阈值的正文或未映射为独立列的有效OCSF扩展字段
- **THEN** 完整内容可从湖内读回，公共查询列仍可使用，不因页面长度限制裁掉后台内容，也不为每个类别或未知字段单独建表加列

#### Scenario: 升级后读取旧记录

- **WHEN** 既有表按定稿列合同完成增量迁移
- **THEN** 原记录及关联仍可读，未知来源和告警标记不被伪造成SpiritHub或false，新旧映射按明确版本和兼容规则使用

### Requirement: 事件版本身份与输入位置分别保留

系统 MUST 保留原始来源事件ID，并在租户及来源范围内生成稳定的湖事件版本身份。发送或消费重试不得成为新的业务事件；真实内容更新必须保留与原事件的关联及版本区别。Kafka坐标用于输入追溯，不能替代已存在的业务身份；查询不得依赖后台合并已经完成才去除重复。

#### Scenario: 非UUID来源事件的重读与更新

- **WHEN** 带稳定非UUID来源ID的同一事件版本重复读取，或随后收到按来源合同识别的真实更新
- **THEN** 重读使用相同湖身份，更新使用可关联的新版本；原来源ID原样保留，告警及材料既有ID不被湖ID直接替换

#### Scenario: 来源身份缺失

- **WHEN** 输入未提供可靠来源事件ID
- **THEN** 以明确集群和Kafka坐标生成同记录重读稳定身份，标记来源身份限制；没有原位置或来源映射时不承诺跨Topic业务去重，不仅凭正文相同合并独立事件

#### Scenario: 数值写法影响投影时保持身份一致性

- **WHEN** 同来源ID的两条输入仅在整数与小数/指数写法上不同，且严格整数投影会产生不同时间或class排序键
- **THEN** 内容版本和湖身份必须区分这两条输入，不能让同一湖身份对应不同排序键；同类小数的等值精确表示仍按合同规范化，完整原文分别保留

### Requirement: 按实际对象角色和可靠时间检索

系统 MUST 区分device、源端点和目的端点的字段角色，在租户及允许来源范围内提供适用的host或IP检索，并将结果关联到完整OCSF。原事件时间和替代时间必须可以区分，缺失/失败不能被改写为正常查空。保留期起算方式及适用范围 MUST 在迁移前明确，不能用修改原发生时间规避历史记录过期。

#### Scenario: 设备与网络源不相同

- **WHEN** 一条记录的device.hostname与src_endpoint.hostname分别代表观察设备和连接源
- **THEN** 两种角色分别投影和查询，不将设备名无条件写成连接源；只有IP的适用记录可按IP查询，结果可读取完整正文

#### Scenario: 新湖行的设备显示名称和主机名不同

- **WHEN** 新OCSF湖映射的同一记录分别提供device.name和device.hostname
- **THEN** 取证行投影分别保留显示名称和主机名及各自原路径；不同值不构成两者之间的字段冲突，无效显示名称也不能使有效主机名被记为冲突
- **AND** 原文主机名和device_hostname查询列真正不一致时仍保留两个值和冲突标记；旧冻结投影及对外告警字段合同保持

#### Scenario: 原事件时间不可用

- **WHEN** 输入缺失或无法解析原发生时间
- **THEN** 保留原字段及时间质量状态，兼容字段采用已定义的稳定替代规则；该值不被当作可靠发生时间参加业务窗口，但记录仍可按入湖时间和输入身份追溯

#### Scenario: 同一缺时记录在另一投递位置重试

- **WHEN** 同一来源记录及完整内容再次投递但Kafka记录时间或offset不同
- **THEN** 新接入的event_time仍使用固定缺时哨兵，可靠性标记保持，排序键不随投递时间改变；Kafka时间单列保存，不能用它伪造原发生时间或破坏记录级去重

#### Scenario: 只有设备IP

- **WHEN** 日志有device.ip但没有device.hostname，也没有明确源端点
- **THEN** 设备IP保存在独立可空设备列并可按其角色查询，源端点列不被设备地址填充，完整原字段保留

#### Scenario: 角色和来源限定的基本查询

- **WHEN** 调用方在显式配置的tenant/source/mapping范围内按device、source或destination的host/IP及时间查询
- **THEN** 核对对应角色列，先去除同版本重复再过滤/分页；新映射发生时间只使用可靠OCSF时间，缺时材料可按入湖时间读取，查询不得串入其他来源或把设备名当作源端点

#### Scenario: 中文主机名贯通查询及取证目录

- **WHEN** 已入湖的device/source/destination主机名含中文等Unicode字母、数字或组合标记，且只混合原允许的下划线、点、连字符，长度为1–253字符
- **THEN** 基本查询HTTP和C4目录共同接受该主机名；新查询和C4 v2仅忽略ASCII字母大小写，其余字符原样比较，Python结果校验与ClickHouse条件一致，不改变原存储值、对象角色、来源或时间约束
- **AND** 空白、控制字符、格式控制符和超长输入仍被拒绝；既有v1冻结原值及精确比较不追改，新增v1目录也能接受符合上述规则的中文主机名

#### Scenario: 已存中文主机名查询后完整读回

- **WHEN** 使用已存5001的中文主机名、类别、可靠事件时间窗及配置来源调用搜索，再使用返回的材料引用读取原文
- **THEN** 原名及仅ASCII大小写不同的查询均返回原source_event_id，完整OCSF/raw_payload与对应实存版本一致，不能只用UID查询代替主机名验收
- **AND** 取证目录保留现有工具各自的固定类别，不能将5001查询命中冒称进程、网络或认证工具已取得证据

#### Scenario: 从查询结果读取完整材料

- **WHEN** 调用方使用搜索返回的稳定版本引用请求材料
- **THEN** 在同一租户和来源范围内精确核身份、版本、时间及类别，返回完整OCSF和raw_payload及编码说明；原件不存在、查询失败和结果未知分别表示，旧预览或完整性不明不能标作完整新原件

#### Scenario: 旧冻结工具和旧行兼容

- **WHEN** 读取原C4 v1绑定，或通过显式旧映射范围检索历史行
- **THEN** 原合同及原答保留，旧混合主机列和时间可靠性明确标为legacy，不静默套用新来源、设备角色或OCSF可靠时间；新C4 v2和候选外部查询共享来源/角色/时间语义

#### Scenario: Records without an indexed object remain retrievable
- **WHEN** a caller searches an explicitly configured tenant/source/mapping and a bounded ingestion-time window without an object selector
- **THEN** the service returns deduplicated, paginated event references, including records lacking indexed hostname or IP
- **AND** each reference reads back its stored full material and quality state; C4 model tools still require frozen object bindings

### Requirement: 共用配置映射与事实描述

系统 MUST 对查询得到的日志使用共用解析与描述执行器，按显式OCSF版本、class_uid及适用来源配置选择字段路径、角色、类型、单位、枚举和描述模板。输出 MUST 同时保留结构化事实与有事实依据的自然语言表达，后台保存原路径、配置版本及完整原文引用；不能仅把原JSON改写为文字后丢弃结构化事实，也不能为每个类别复制独立解析流程。

#### Scenario: 同一执行器解释不同类别

- **WHEN** 网络审计、认证、合规或其他已配置类别的记录进入共用解析器
- **THEN** 根据各自配置提取角色正确的事实，并用对应条件模板表达动作、结果或观察；新增受支持结构的类别通过配置扩展，不要求为该类复制查询、解析和描述实现
- **AND** 告警、事件及Case按各自任务选取这些事实，不将所有类别正文无差别透传到模型

#### Scenario: 缺失与未知不能由模板补造

- **WHEN** 必要事实缺失、枚举未知、别名冲突或partial材料不完整
- **THEN** 保留可用事实及其来源，模板省略不成立的语句或明确未知，不生成未经记录的成功、拒绝、操作人或完整类别判断；合法0、false及有意义的空列表不被当作缺失
- **AND** 同一证据数组元素内的字段保持关联，原有说明和原件不被模板语义改写或覆盖

#### Scenario: 描述与统计共享事实

- **WHEN** 一个工具需要同时输出单条说明和多条记录的适用汇总
- **THEN** 描述和确定性汇总使用同一结构化事实，程序不从生成的自然语言反推计数/时间/对象，描述不能直接认定异常或自动生成告警
- **AND** 只有已具备查询对象、目录接线及保存读回验证的配置能力才声明为可用工具；旧冻结调用和告警交接字段保持兼容

### Requirement: 新接入按每次入湖保留400天

系统 MUST 对显式配置范围内的新接入映射按本次ClickHouse实际INSERT的ingest_time起算400天，重试写入刷新保留期。原OCSF主时间保持，旧映射记录的既有事件时间及租户保留策略保持。表TTL与应用清理的计数/删除条件 MUST 使用一致的新接入口径；该配置不得隐式扩展至其他存储或全部历史记录。

#### Scenario: 历史输入刚入湖

- **WHEN** 新接入保存一条原事件时间早于现有400天上限的历史记录
- **THEN** 在新接入范围内按实际入湖时间计算到期，业务原时间不被改成当前时间，租户清理不会按旧事件时间分支提前删除它

#### Scenario: 重试刷新与旧行兼容

- **WHEN** 新接入的相同事件版本被再次实际写入，且表内同时存在旧映射记录
- **THEN** 新接入版本的保留期限按最新实际入湖时间刷新，旧映射继续原规则；清理预览和实际删除使用同一选择条件，不因新增列默认值把旧行判为新接入

### Requirement: 固定范围以聚合结果验证落湖

系统 MUST 支持直接读取既有Kafka固定分区范围进行受控落湖验收，用实际读取数、逻辑版本身份及从湖内实存内容重算的分组摘要核对完整性，并明确重复、失败和未完成的去向。验收不要求人工逐条比对正文，也不要求额外原件归档或复制Kafka Topic；真实统计留在受控环境。

#### Scenario: 输入数与物理行数不相等

- **WHEN** 固定范围包含重复投递、事件更新或尚未合并的ClickHouse行
- **THEN** 按已定义身份对照新版本、重复及未持久化状态，保存聚合验证结果；不以offset跨度代替消息数，不以物理行数代替逻辑版本数，不以输入侧摘要直接充当湖侧内容验证

#### Scenario: 固定范围结束后出现新消息

- **WHEN** 验收开始后Kafka继续收到新的记录
- **THEN** 仅保存和确认冻结结束位点之前的实际消息，范围外预取不参与保存、提交或聚合；有offset空洞时分别记录扫描终点和最后实际保存后的提交点

#### Scenario: 实存正文损坏或未完成扫描

- **WHEN** 湖内完整正文重算结果不匹配输入逻辑版本，或扫描超时/范围失效/持久结果未知
- **THEN** 验收判未通过并保留当前范围及未完成状态；不以已消费数量、输入摘要或进程正常退出替代完整保存证明，不自动重派该批次

### Requirement: 按冻结范围只读盘点当前事件类型

系统 MUST 提供显式配置的只读盘点工具，分别冻结每个输入 Topic 的分区起止范围，统计实际事件类别、告警标记、partial 状态及调查所需字段覆盖。程序不得加入生产消费组、提交位点或触发下游业务；统计报告属于受控数据，保留在原环境。

#### Scenario: 完整读取与保存报告

- **WHEN** 只读程序完成配置 Topic 的冻结范围扫描
- **THEN** 按 Topic 分别保存类别和固定字段的结构统计及扫描边界，非法/空消息单列；报告可在原环境读取且不包含正文、主机、账号等样例，不以程序完成宣称日志已落湖

#### Scenario: 读取未完成

- **WHEN** 扫描超时、位点范围失效或读取失败
- **THEN** 保存已读取范围及未完成状态，不把部分统计描述为完整类型分布，不改变既有消费者进度



### Requirement: Existing alert selection follows the confirmed immutable global identity

系统 MUST 将已有告警选择与全量落湖分开，以显式profile读取is_alert、类别活动语义及来源身份；已存材料可以只读判定并保存可读回的私有报告。当前来源合同使用metadata.uid作为全局唯一、没有更新的告警身份，不要求额外产品/设备范围。租户与来源仍限定存储及读取归属。判定不得调用通用高严重度promotion，不得将候选、来源语义确认和实际A/I交付混为一体。

#### Scenario: Finding lifecycle differs from network activity
- **WHEN** 已配置发现类带Update或Close，或已配置网络活动带Close且is_alert=true
- **THEN** 当前没有更新的来源合同下前者进入review并保留原文，后者仍按网络信号判定；不得创建更新/关闭业务分支或覆盖人工处理状态

#### Scenario: Partial classification and conflicting flags
- **WHEN** 根class0的partial材料保留完整目标分类和明确is_alert，或根/partial关键字段发生冲突
- **THEN** 在根字段缺失且允许回填时按目标语义产生候选但保留原class及质量；显式null/无效值不被回填掩盖，冲突/未配置告警类别标为review，所有材料仍可检索

#### Scenario: Stable delivery uses the global record ID
- **WHEN** 相同metadata.uid和相同正文重读，或不同metadata.uid带相同finding_info.uid
- **THEN** 前者为同一告警重发，后者为不同告警；来源告警身份仅由metadata.uid稳定生成，不因租户、产品或设备的显示值改变，湖版本身份和既有告警ID算法保持各自用途。缺少metadata.uid或未确认身份时保持hold，不使用内容指纹或Kafka坐标补造主体ID

#### Scenario: An immutable source ID has conflicting content
- **WHEN** 相同metadata.uid对应不同OCSF正文版本，或已存主体无法证明其正文版本
- **THEN** 前者保留湖中全部材料并标为合同冲突，后者保持待核；不得追加告警材料或覆盖原告警。同一次只读扫描已发现冲突时整组候选进入review，不因行顺序不同而选取一版作为首次告警

#### Scenario: Read-only candidate verification
- **WHEN** 对既有入湖批次执行固定profile的告警选择验收
- **THEN** 仅只读已配置来源并在受控环境保存与读回判定报告，不生成A/I任务、不提交Kafka位点、不发送业务数据或统计到Codex/GPT；执行通过不代表来源语义或业务分类准确率已经验证

#### Scenario: Immutable alerts have an explicitly configured initial activity
- **WHEN** 不可变来源的发现类处于显式配置的initial_activity_ids，包含Unknown/Other但不包含Update/Close，且原类型一致、is_alert=true、metadata.uid有效、状态及版本无冲突
- **THEN** 可以生成首次接收候选，保留原activity_id，不伪造Create；false或缺标记不得因此提升为告警；旧profile未指定initial_activity_ids时仍沿create_activity_ids

### Requirement: Selected immutable alerts are durably received with full lake provenance

系统 MUST 将确认可接收的湖候选适配为现有RawAlert/source-v1，按全局来源身份建立内部持久回执，并与告警、完整材料、来源关联、事件成员和首次分析任务在同一PG事务提交；提交成功后才报告已接收。新增内部回执不得改变冻结告警HTTP字段，持续派发与初诊模型执行是后续独立步骤。

#### Scenario: First receipt and exact replay
- **WHEN** 可接收候选首次到达，之后同一metadata.uid和同一正文重发
- **THEN** 首次通过现有Fusion和接收逻辑保存完整材料、湖版本引用并登记初诊；重发读取首次接收结果，不新增材料版本、初诊任务或修改人工字段。冲突的正文或存取归属必须hold，不跨租户读取内容

#### Scenario: Full material exceeds the old one MiB limit
- **WHEN** 可接收正文或首次结果快照超过旧1MiB但未超过显式配置预算
- **THEN** 接收、快照生成/恢复及PG保存/HTTP读回均保存完整材料，湖引用精确关联原文；超出配置预算时明确拒绝接收且不留下成功回执，不截断或预览代替完整保存

#### Scenario: Durable state and first tasks are read back
- **WHEN** 用已存湖批次在独立验证数据库接收并通过业务HTTP读取
- **THEN** 程序核对告警/材料/来源回执/初诊任务关系及完整原文，保留全部未选中、hold、失败和unknown的去向；只有登记而未运行的初诊仍为accepted，不能报告模型已通过或整条调查已完成

### Requirement: Durable lake delivery confirms only committed alert receipts

系统 MUST 将完整有界湖扫描的选择结果及精确原文引用持久登记，再按来源顺序调用告警接收器；只有证明对应告警事务及交付确认事务提交成功，才报告已交付。重复扫描不得重建交付项，失败/hold/未知不得被后项成功覆盖。内部交付状态不改变公开告警合同或初诊执行含义。

#### Scenario: Process resumes after durable registration
- **WHEN** 候选登记提交后进程结束，新worker读取同一来源
- **THEN** 从持久待处理项继续；重复扫描、同文重发复用既有交付/接收身份，不重复创建告警、材料或初诊任务；扫描超限或不完整不推进，不用事件时间游标跳过迟到日志

#### Scenario: Receipt is lost after alert commit
- **WHEN** 告警事务可能已提交但交付得到unknown，或进程留下receiving尝试
- **THEN** 保留该项和原尝试并停止后项；恢复时先只读核130回执及材料，证明已提交才能另记恢复确认。无可证明回执时继续unknown，不盲目重执行Fusion

#### Scenario: Receive or confirmation fails
- **WHEN** 接收明确失败，或持久交付确认失败/结果未知
- **THEN** 未取得持久证明前不得报告该项delivered，后项不执行；下一次运行先核同项的数据库状态，旧失败/unknown尝试保留。确认delivered必须关联已提交的来源版本、告警和材料，不能依赖内存返回值；确认事务结果未知时不得以本地unknown覆盖数据库可能已提交的确认
