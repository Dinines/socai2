# C01：Fusion持久交付与首次结果恢复

2026-10-20。**本change限定验收通过，整个服务端迁移尚未完成。** 对应[审核R1/R3](migration-review-20261020.md)及[原计划](c01-fusion-delivery-plan.md)。最终缓存镜像直接测试107项通过；真实PG/Redis/SSL Kafka及部署后HTTP通过，0真实模型、0厂商动作。来源见[manifest](../handoff/c01-fusion-delivery-source-manifest.json)，完整坐标/计数/审计见[机器回执](c01-fusion-delivery.json)。

## 实际变化

live Fusion先确认PG完整首次结果，再等待fused消息broker确认，最后只提交当前分区的offset+1；处理、发布或commit失败结束该轮消费，防止后一成功项越过失败输入。source-v1从PG或有限TTL/大小的Redis首次快照恢复原告警、incident、完整增强、分数和narrative/session，不重跑关联或评分。已存在PG行却缺完整快照，或尚有dedup痕迹却无法取得首次快照时保持hold/unknown。若PG行不存在且dedup及快照均因TTL/丢失消失，不能与新输入区分；本批未验这种故障恢复，也不保证永久unknown。无新DDL，原134迁移保持；legacy原指纹/UUID及既有归并事实不重建。

## 输入到结果

| 输入/故障 | 实际中间产品 | 最终值/关系 |
| --- | --- | --- |
| A1、A2同分区；A1插入接缝实际执行SELECT1/0 | PostgreSQL返回SQLSTATE22012，sink FAILED；Redis已保留完整首次结果，worker退出 | raw offset保持0，A2未越过；fresh进程复用A1快照，A2正常关联，确认后commit2 |
| 改A1 title/description/event_time/raw_event及候选增强后重投 | 新raw offset2；PG首次快照优先，engine不重入 | commit3；PG首次材料及实际fused完整内容保持，仅persist_outcome为duplicate |
| B1 PG成功后，独立真实SDK producer已stop | PG首次结果存在，send_and_wait实际失败；raw offset0 | 仅删除B1本批delivery key；fresh进程从PG恢复，不重入engine，broker确认后commit1 |
| 新legacy首次/重投 | 原UUID/首次快照保持，只有新来源事件允许追加 | 原夹具漏计canonical raw.id而断言失败；产品已commit2，后续只读恢复，无重发/重提交 |
| dedup已登记却没有完整首次结果 | 实际worker识别不可证明原关联 | gap保持unknown，offset0/end1，不生成PG伪恢复 |
| 坏schema及缺DLQ provider | 缺确认时不提交；恢复provider后真实PG DLQ保存坐标 | 新增1条DLQ后才提交；没有停止共享服务 |
| 升级后的真实HTTP已有告警 | API→项目raw→常驻Fusion→PG/完整快照→实际fused/API回查 | 新增1行，越权401/另一tenant404；材料与snapshot/信封对应 |

以上恢复场景的增强为明确的合成嵌套fixture，验证完整保存恢复；不作真实情报消费成绩。PG故障只在独立探针INSERT接缝，不是全库断开；发送故障是独立SDK真实stop，不是共享broker停机。

HTTP首个探针容器把文件挂到`/operator.py`，遮蔽Python标准库operator，在任何请求前ImportError退出；当时HTTP证据目录只有contract，0次HTTP请求。原`http-first-operator.py`及首次started/exit/log原样保留。后续`run-fixed-startup`先核原hash、raw offset元数据、contract及私有key env保持，改用`/c01_http_probe.py`和`PYTHONPATH=/app`，才完成4次实际HTTP检查。该启动失败与legacy已commit后的夹具断言失败分开记录，均未改写为首次通过。

## 计数、部署与保护

本批显式HTTP共6项：主链验收4项、撤销两枚操作key后的401回查2项。首次HTTP启动失败发生在请求前，不计入实际请求。

实际broker发送尝试17次，物理worker交付/输出回读23次；分raw/fused/失败/审计回读见机器回执。初始12次发布未区分输入输出，执行前保留原件并补充总attempt20；独立审计4次回读及HTTP常驻raw消费漏算，在仅16次物理交付时暂停并预先补充上限24。原限制、两次补充及失败均保留，未通过移除物理读取美化计数。

仅Fusion更新，候选/运行镜像`sha256:a8825d41c00dac30682ea273aa502076845df7f04a25a0167b64aa43330391d4`；56个运行Python文件与最终测试逐项对应。当前23层Compose、20层来源。新增5条告警/1条DLQ，旧14表材料、35其他容器、18卷、134迁移、十枚reader、5预约/三unknown及旧六测试group保持。两枚本批操作key已停用并HTTP401；Agents worker仍禁用。回退定义在受控private/completion-c01，回退不删除新快照、消息或重置group。

最终独立审计及撤key后closeout独立复核均accepted。首次legacy夹具失败/只读恢复，以及HTTP零请求启动失败/受控启动恢复分别保留，未标原探针首次通过；没有重调旧unknown、退款或改写旧回执。完整缓存丢失、旧无snapshot行恢复、分布式恰好一次、真实厂商和研判质量仍未通过。

下一单项为[C02执行卡](c02-triage-material-cache-stop-plan.md)：分诊正文/发生时间投影、普通live禁用跨告警pattern结论缓存并保留同Run PG复用、停止异常清理（R2/R4/R5）；不开启常驻分诊替代这些验收。未提交或推送。
