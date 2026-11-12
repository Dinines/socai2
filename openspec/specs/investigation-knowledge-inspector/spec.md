# investigation-knowledge-inspector Specification

## Purpose

让 4177 按同一 Run 展示 C2 各目的的实际输入、检索结果和失败，并将模型输入可见、原答引用与校验/质量分开，便于前后端交接和追溯。

## Requirements

### Requirement: The C2 knowledge node displays purpose-specific inputs and outputs

4177 SHALL 在 C2 知识节点按检索目标展示实际来源材料、查询文本、过滤/限制、嵌入模型/维度、命中片段/来源和状态/错误，保留原始工件入口。展示 MUST 基于本 Run 保存记录，不触发新的查询或模型调用，不暴露凭据或隐藏推理。

#### Scenario: A user opens the C2 knowledge node
- **WHEN** 当前 Run 保存了技术解释和取证指导检索回执
- **THEN** 右侧分别展示各目标输入与输出，能定位文档块和来源；相关度标为相关度，不标为可信度或案件置信度

#### Scenario: Retrieval is skipped, empty, failed, or absent from historical records
- **WHEN** 某目标未执行、完成查空、失败，或历史批次未记录目标详情
- **THEN** 分别显示未查询及原因、无匹配、实际失败原因或未记录，不因 C2 父阶段完成统一显示知识成功

### Requirement: Knowledge retrieval, model input and model citation are displayed separately

4177 SHALL 保留 C3/Deep/C6 实际提示词、Schema、输入输出、校验和错误，并依据 source_map/原始请求/原答或装配引用关联知识。系统 MUST 分别表达已检索到、已进入模型输入及存在可解析输出引用，不能从其中一项推断另一项或自动宣称合理采用。

#### Scenario: A retrieved chunk enters a model request without an output citation
- **WHEN** 片段已检索且进入实际 model_request，但该次输出没有可定位引用
- **THEN** 显示已检索/已进入输入/未见引用，保留原答，不显示为已被模型采用或质量通过

#### Scenario: A model cites knowledge or returns an invalid response
- **WHEN** 实际输出存在知识引用，或本次输出被校验拒收
- **THEN** 可解析引用能定位对应片段与输出位置，拒收/未解析引用保持原状态和原因；引用存在不替代业务质量判断

### Requirement: Historical cards and nested citations remain inspectable
4177 SHALL 在本 Run 知识节点展示历史目的的范围、过滤、历史告警/材料/判断身份、原观察/分诊/人工反馈与版本状态，并关联模型的卡片及子字段引用。页面 MUST 使用已保存回执，不重新检索，不将相似度或历史人工判断显示为本案可信度或授权。

#### Scenario: A model cites historical human feedback
- **WHEN** 本轮原答引用已进入输入的历史卡片人工反馈字段
- **THEN** 面板定位具体历史卡片、人工来源路径和输出位置，输入可见/原答引用/校验状态分别显示

#### Scenario: Historical knowledge was not retrieved
- **WHEN** 缺少时间范围、未执行、有效查空或失败
- **THEN** 显示已记录原因及真实状态，不因 C2 父阶段完成显示为知识已成功使用
