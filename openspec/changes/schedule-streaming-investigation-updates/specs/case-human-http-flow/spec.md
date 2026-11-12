## MODIFIED Requirements

### Requirement: Human feedback remains an explicit versioned input to the next investigation
系统 SHALL 沿用 Case/H 版本保存及身份/范围合同。调度关闭时保持显式 prepare/start；启用时，适用已完成反馈的提交、实质修订或撤回 SHALL 合并登记 Case 待办，草稿/纯管理编辑不得触发。仅反馈变化选择综合复核，已有完整调查原因时合并到 full；领取时冻结适用版本。人工正文 MUST 保留 human_statement 角色，不自动代表业务授权、采用判断或 Case 已解决；Case H MUST NOT 冒充告警级 human_feedback。

#### Scenario: A user completes and revises feedback before starting the next run
- **WHEN** 调度关闭，用户保存并修订反馈后显式准备和启动下一轮
- **THEN** 后轮冻结领取时选中的适用版本，保留原文/范围和旧结果，仍从原 Result 路径读取

#### Scenario: Valid feedback is submitted while scheduling is enabled
- **WHEN** 用户完成或实质修订适用 H，Case 材料未变化
- **THEN** 合并一份综合复核待办；有运行中调查则等其结束，不因每次保存重复启动

#### Scenario: A submitted fact is withdrawn or only metadata changes
- **WHEN** 用户撤回原适用已完成反馈，或只编辑负责人/标题
- **THEN** 前者触发综合复核并保留撤回来源，后者不启动模型；范围不适用/空正文保存仍保留原件和原因

## ADDED Requirements

### Requirement: Feedback review reruns synthesis without collecting new evidence
仅反馈变化的 Case Run SHALL 冻结原调查必要证据、前序结果状态、适用反馈及相关原知识，并只执行 C6/保存读取；MUST NOT 重跑 C2/C3/C4/Deep、重新检索或把旧取证算作本轮新执行。来源重新映射须保留实际原 Run/版本，不能只用一段旧结论替代必要证据。复核 SHALL 说明维持/改变的判断及待核事项；不足以回答的新调查方向只能记待查。无可用调查材料时保留反馈并提示首轮调查需要，不自动升级为深查。

#### Scenario: Human feedback narrows the interpretation of existing observations
- **WHEN** 反馈说明只有某主机指定时段属于维护，原调查材料可复核
- **THEN** C6 只在该范围重新综合，保留其他成员待核；原记录/来源和新反馈共同可追踪，无新工具/Deep 调用

#### Scenario: Feedback requests an unsupported new investigation direction
- **WHEN** 用户要求查终端而已保存材料只有网络记录
- **THEN** 复核指出终端证据缺失并保留待查事项，不生成终端取证成功或正常/恶意的假结论
