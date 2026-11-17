# 设计

## 事实基线与范围

Fusion对象索引提取host/user/ip/domain/url/hash；normalized_value当前保收到的值。related_alerts按namespace/type/key匹配，没有时间筛选/匹配依据。C5读取冻结材料，hash/process/other保记录内身份。本项新增只读候选，不改上述逻辑；关联只是线索，不确认同一实体或攻击因果。

## 输入和时间

Case路径；可选alert_id或object_id（互斥），都不传使用本案当前成员。指定起点必须是同租户、与Case.source_namespace一致的真实告警及最新材料对象，允许案外起点以逐层探索；旧材料对象409。不接收前端伪造的对象值或图节点名称。调用方将图节点来源映射至真实对象ID，历史图节点先回查当前材料，不能直接把图的内部节点ID当object_id。

time_from/time_to必须同时给，带时区，[from,to)。默认指定告警使用它的event_time前后配置窗口；指定对象使用所属告警event_time；未指定使用本案已知告警时间min/max前后窗口。配置默认24小时，无已知时间须显式给范围（422）。空案件未指定起点且无对象时200空结果，窗口可null；用户窗口始终原样使用。未知时间候选不进入时间筛选。limit1–100默认20；cursor下一页，未知/重复参数422。

## 对象匹配

同租户、Case告警source_namespace、对象namespace均须一致。host/user/ip/domain/url只按对象类型和normalized_value完全相同匹配（无大小写、DNS、IP格式别名或跨来源归并），basis为same_source_value。保留原object_key/原值/source_path/material_id作回查；不称统一资产身份识别。

hash仅MD5/SHA1/SHA256/SHA512，明确algorithm（忽略大小写及连字符/下划线）并校验16进制值长度；值比较忽略十六进制大小写；算法不同不匹配。未给/未知算法或无效值排除并在起点排除说明中给出；不能从长度猜算法。basis为same_hash_algorithm_and_value，仍只表示记录的指纹一致，不跨图合并文件实体。

file/process/email/application/cloud_resource/technique/other本批不查询。指定此对象422；整案或告警起点中不支持对象列入排除说明。重复字段/多个起点引用同对象只计一个共享对象，但返回各匹配原件；不同IP、域名、URL不会在程序中猜成同一对象。

## 查询、排序与读回

排除作为起点的告警，其余当前成员可返回且标记already_in_case。按shared_object_count DESC、距实际匹配起点已知event_time的最短秒数ASC NULLS LAST、alert.id ASC排序；不返回合成威胁分数。matches只含匹配对象；展开候选全部对象需沿E30 objects读取。每项返回原AlertFacts、共享对象数、最短时间差、是否已在本案、事件/Case ID及每对起点/候选对象引用。按身份去重，保留来源路径。

整请求REPEATABLE READ/READ ONLY；SQL先条件匹配/分组/排序再分页。游标绑定租户/案件/查询/实际窗口/起点对象及成员范围版本；过滤或起点变化409，格式无效422。跨页候选数据变化可能改变排序，刷新读取，不承诺跨请求冻结全库。

## 接入与边界

独立core服务不导入HTTP包；external_routes仅依赖contracts/ports/dependencies。现有E08负责明确加入，查询/预览不保存、不启动Run；返回详情后调用者读取最新scope_revision再明确关联。不维护画布、不查询资产库存、不用模型、无新表。旧告警事实DTO/旧related_alerts/C5完全保持。

本机一批合成数据覆盖匹配→分页→依据和材料GET→明确加入E08→Case成员GET，SQL核查询只读。模型0；21仅已有数据GET。直验及独立结束审计后一次发布本机/21与Swagger，再读回；并行模型文件不打包。
