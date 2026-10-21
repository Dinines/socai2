# C03-02：Fusion关联及PG额外表边界补充

2026-10-21，冻结之后、任何本批业务写/额度安装/真实模型之前补充。[原执行卡](c03-triage-quality-plan.md)与已保存的`scope-before.md`保持原字节；不增加输入、模型、发送或交付上限。

固定源码`fusion/app/services/correlator.py`在Redis中保存incident及告警成员。四条新告警允许正常创建最多4个新Redis incident、增加最多4个告警成员关联；按实际首次Fusion快照的incident_id与新告警对应取证，不重建旧关联，不把Redis缓存当长期持久历史证明。

实际schema只读核对：`public.incidents`不存在；`public.aisoc_cases`有3条旧行，`public.alert_source_links`为0行，逐行hash基线已单独保存。Fusion PG sink只向alerts及有厂商映射的alert_source_links写入，本批中性connector-54没有厂商写回映射；因此Case新增0、source link新增0，不新增PG incidents表、不执行DDL，也不授权泛化的PG incident/link新增。

十四张原材料表按原卡检查旧行及指定增量；上述额外表的存在性和逐行hash分别保持。范围声明不外推全部PG/Redis对象绝对不变，也不把自然TTL变化当作持久历史可恢复保证。独立审计不额外读取broker记录。
