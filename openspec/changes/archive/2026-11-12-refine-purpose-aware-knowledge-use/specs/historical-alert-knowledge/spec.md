## ADDED Requirements

### Requirement: Explicit historical import follows saved judgments and preserves current version selection
历史告警知识 SHALL 沿现有显式入库及索引入口，在材料、事件时间和至少一份可用且对应所选材料的分诊／人工反馈保存成功后选入。仅有失败原答、没有判断或只有不对应材料的判断不得成为当前可用案例。系统 MUST 保留原文和对应状态，不把人工陈述、已关闭案件、模型 verdict 或未执行建议自动提升为已核实经验；本 change 不自动监听告警接入或启用入库调度。

#### Scenario: A source has just arrived or a usable judgment has been saved
- **WHEN** 告警刚接入而无可用判断，或已经保存可用分诊／人工反馈并被显式指定
- **THEN** 前者只保留业务原件并返回未入库原因，后者保存有源版本的参考卡并显式索引；索引成功与判断可信性分别表达，模型判断仍标为未独立核实

#### Scenario: Feedback or material changes after a card was indexed
- **WHEN** 所选材料或有效分诊／人工版本变化，后续显式导入该告警
- **THEN** 新源内容产生新快照，相同内容保持同一身份，旧卡和旧 Run 保留；新检索只采用与当前源指针和内容对应的可用快照，新卡尚未索引时不回退采用已过时卡
