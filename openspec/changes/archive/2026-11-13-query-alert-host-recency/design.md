# 同主机最近告警

## 用途与输入
原设计的告警详情→概况→相关告警，F08-01。E71只接受路径alert_id（UUID），不接受查询参数。读取当前告警最新材料中的host对象；多个主机取并集。没有材料或有效主机时返回空items和source_hosts，起点不存在404。

## 范围与匹配
同租户、同告警source_namespace，主机对象namespace和normalized_value完全相同；起点与候选均只取latest_material_id下对象，排除当前告警。空白主机值不作为匹配依据，不从IP、资产ID或文本推断主机。不要求战术一致，不自动识别别名，不把关联解释成攻击因果。

“最近7条”是查询时数据库已保存、真实event_time已知的最近记录，并非7天或当前告警之前的历史窗口；不按起点event_time截断，也不自行添加时间下界。候选event_time未知排除，不用入库时间替代；起点时间未知仍可查。按event_time倒序、alert_id倒序，先匹配去重计数再取7条。已关闭或已判误报仍返回原状态。display_limit由alert-host-query.json配置，当前7；不开放分页参数，total为完整匹配数，limit为本次实际数量上限。

## 输出与边界
新AlertHostPage包含items、total、limit、source_alert_id、source_material_id、source_namespace、source_hosts、observed_at。items各含原AlertFacts和matches，每对match含seed/candidate原ExplorationObject；主机算法字段为null。双方材料ID、对象ID、字段路径和原值供E31回查；标题点击以alert.id调用E28。空页只代表未找到，不证明主机安全。
单次REPEATABLE READ READ ONLY事务；查询不改判定、状态、成员、Run或模型。独立alert_hosts核心不依赖HTTP；external_routes通过port调用，不改变E30/E66/E70规则。保留原70操作/150运行schema。

## 直接验收与发布
独立本机合成批验证超过7条排序/去重、多主机/重复来源、不同战术仍匹配、只有IP不匹配、错namespace/source/旧材料排除、候选未知时间排除/起点未知时间可查、包含起点之后记录、原状态及来源回查、404/422、相关数据查询前后保持。复用既有HTTP边界测试，不重跑全仓或模型。完成文档和独立审计后统一更新本机/21独立API及Swagger；21只读既有记录，如无匹配如实记录。当前指令不提交或推送Git。
