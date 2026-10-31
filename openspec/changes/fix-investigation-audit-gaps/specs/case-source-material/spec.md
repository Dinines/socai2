## ADDED Requirements

### Requirement: Tool provenance and exact member source matches remain explicit
程序 SHALL 为Tool模型视图及新报告生成来源说明：区分historical_reuse与current_tool_result，并仅在reused_from.run_id与历史材料Run一致时标明already_in_history。事件湖行 SHALL 按event_id与可读选定告警source_event_ids的精确相等生成row_alert_refs，不以同主机或标题猜测对应。报告query_sources及Markdown显示这些确定信息，不将它们当作模型语义正确的证明。

#### Scenario: A followup reuses a previous result
- **WHEN** Tool返回来自H1对应Run的缓存结果
- **THEN** 模型与报告显示历史复用、原Run及该历史已持有同一结果；原始行、H1摘要和旧报告保持，不描述为独立的新查询证据

#### Scenario: Only two of three rows match selected alert source IDs
- **WHEN** 前两行event_id分别对应A1/A2，第三行不在所选告警source_event_ids中
- **THEN** 对应列表为A1、A2和空项；空项只表示未匹配，不证明无关。模型裁剪行时同步裁剪对应列表，完整报告仍按已保存行生成

### Requirement: Network conclusion fields and readable member coverage are checked
新的Case结论 SHALL 对每个可读选定成员提供且只提供一条引用自身A材料的判断。当存在network_connections证据时，摘要、发现、成员说明及关系依据中未出现在可用网络行protocol字段的HTTPS/TLS/SSL名称 SHALL 仅用于明确的不确定表述，例如“HTTPS尚未确认”或“TCP/443不直接证明HTTPS”；无依据的肯定或否定断言仍拒绝。实现只识别有限中文句式，不是通用语义判定；gaps/open_questions可保留待核问题。本规则不证明其他语义正确，不改写旧Run。

#### Scenario: The model omits a readable selected member
- **WHEN** 结论缺少可读成员判断或引用不合法
- **THEN** 沿原一次纠错与预算限制处理；纠错未成功则failed/partial，不能以completed接受遗漏；不可读成员仍为source_unavailable

#### Scenario: TCP port 443 is described as HTTPS
- **WHEN** 网络行仅提供TCP/443，但结论字段肯定或否定未观察到的HTTPS、TLS或SSL
- **THEN** 拒绝该结论并使用原纠错路径，不把端口当作应用协议证据，也不自动重写为已核实事实

#### Scenario: Explicit uncertainty is followed by an unsupported assertion
- **WHEN** 结论写“HTTPS尚未确认”或“无法确认是否使用HTTPS/TLS”，并可能另有“已证实SSL”等断言
- **THEN** 只允许明确不确定部分；若仍有无依据的断言则整份结论继续被拒，不能因一句不确定表述而放行其他协议声明

### Requirement: New Case runs retain bounded original source material
新 Case Run SHALL 按 case.source-material.v1 固定本次 Case.description 及选定 Alert.description/raw_event 的来源路径、状态、截断前指纹/长度、保留文本/字节和省略原因。MUST 使用 design 中单字段/单 Run 上限，明确 JSON 指纹为 canonical JSON 数据指纹；不编造未读来源，不用旧 AI 摘要替代正文。

#### Scenario: Office source fields already exist
- **WHEN** 已有 Office 告警的 description 包含父子 PID，raw_event 包含 full_log/approval_status，且均在上限内
- **THEN** 新 A 证据保存这些来源字段并可经 Run 读回，明确它们是来源陈述而非已独立证实的结论

#### Scenario: Original source exceeds retention limits
- **WHEN** 字段或全 Run 新增正文超过冻结上限
- **THEN** 按确定顺序和 UTF-8 边界保留，记录完整字段 hash/字节数及实际保留量/原因，不将 hash 或当前链接当作历史全文已保存

### Requirement: Model source views remain bounded and explain omissions
模型视图 SHALL 与冻结正文分离，按 design 的 8 KiB 新增正文上限及成员分配规则取材，记录 model_retained_bytes/model_truncated/model_omission_reason；MUST 继续遵守原整体输入、调用数、输出及时间预算，不修改已保存原件或将材料指令当执行指令。

#### Scenario: The model receives a shorter view than stored evidence
- **WHEN** 冻结材料超过模型视图配额
- **THEN** 模型输入明确其省略量与原因，读回仍返回实际冻结正文，来源省略与旧 saved_analysis 截断分开表达

#### Scenario: A follow-up combines source material and correction
- **WHEN** 新取材规则与已有 H1 精简、required_tools 和一次结论纠错共同使用
- **THEN** 以实际组合请求核原预算，不拿旧离线重建数字作为通过依据，不提限额、不静默丢弃来源；额度不足时沿原停止合同返回

#### Scenario: A source field violates the existing model input contract
- **WHEN** 完整来源字段含禁止直接发送的原始OCSF/log或secret形状
- **THEN** 在嵌套/裁剪前按现有合同检查，模型字段省略并注明llm_input_contract，冻结上限内的原文仍可读，不关闭guard或通过转义编码绕过

#### Scenario: The fixed Office correction input includes original sources
- **WHEN** Office冻结追加材料和原错误响应/6982 usage进入当前执行器
- **THEN** 保留新增描述和raw材料，显式省略H1模型报告的结构化细节及A旧摘要，原H1/报告不变，纠错请求在剩余17018内派发并可保存替身结论；不能以input_or_token_limit关闭这个回归场景

### Requirement: Source fingerprints and history respect material versions
新 source_hash/material_hash SHALL 纳入来源 schema 和完整字段指纹/状态/长度，正文或 raw_event 变化 MUST 阻止不适用的历史查询复用。旧 Run 缺新 schema 时仍可读取和作为 H1，但不得冒充已具备新材料；旧 operation_key 的 intent 及仅读行为保持。

#### Scenario: Only an omitted tail of raw data changes
- **WHEN** 新 Run 读取的 raw_event 仅在冻结/模型裁剪尾部发生变化
- **THEN** 完整字段指纹及材料 hash 仍变化，旧查询不因可见前缀相同而被复用

#### Scenario: A new question follows a legacy run
- **WHEN** 新 key 指向缺少新材料 schema 的已完成同范围旧 Run
- **THEN** H1 保留旧判断和原链接，新 Run 读取并冻结当前材料，不把旧材料当作新版本复用依据

#### Scenario: An existing operation is read again
- **WHEN** 调用者使用同 key 同 intent 重复请求旧 Run
- **THEN** 只返回原结果，不升级材料、不查询来源、不重写旧 Markdown 或结果工件
