# 标准 Swagger 作为唯一主入口

Swagger根路径按接口主体归类：Case及H归调查，告警接口归告警，事件接口归事件，subject为alerts/incidents的三项公共读取同时归两组。接口实现状态从现有实现说明取值，代码已实现与生产开关未知分开。

每个接口保留标准Parameters、Request body、Responses、Schema及示例；说明区只写用途、输入摘要、输出类型、实际结果和必要规则。输出动态结构放在Response说明，固定字段语义仍放Schema，不再嵌入整套产品功能表或页面进度。旧/handoff/index.html仅转入Swagger，接入指南简化为HTTP说明。

已审计字段补充继续作为字段说明来源，历史125项功能清单不删除、不借本轮改动提升实现结论。暂存构建、限定独审后一次发布同包；仅读取文档和架构。不同架构继续使用原固定镜像。
