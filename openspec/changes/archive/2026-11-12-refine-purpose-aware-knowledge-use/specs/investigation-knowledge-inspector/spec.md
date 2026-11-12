## ADDED Requirements

### Requirement: Knowledge selection and omission remain inspectable
4177 SHALL 在既有知识与模型节点，用本 Run 的回执展示候选、适用筛选、去重关系及每次请求实际选择／省略的知识和原因。页面 MUST 保持查询状态、模型可见、结构化引用与质量结论分离，不触发新检索或自动判定合理使用。

#### Scenario: Retrieved knowledge is not sent to a particular model step
- **WHEN** 候选因不适用、旧版本、重复、与当前问题无关或可选容量限制未进入该步请求
- **THEN** 展示保存的具体原因及对应原件，不把候选命中显示为已使用，也不把未进入模型显示为查询失败

#### Scenario: A deduplicated source is referenced downstream
- **WHEN** 模型实际请求包含一份去重后的知识并在原答中产生可解析结构化引用
- **THEN** 能定位唯一知识正文、全部原查询出处和输出引用位置；分角色引用与校验／质量限制保持，不据此自动宣称知识正确采用
