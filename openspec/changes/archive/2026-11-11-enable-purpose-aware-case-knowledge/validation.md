# C2 目的检索与 4177 直接验收

2026-11-11；仓库 `socai2`、分支 `V1.1`，开始基线 `f95331d76984cc8aac4b3a2861597ceed68dc40c`。先补 proposal/design/specs/tasks 并严格校验，再实施。发布前代码/配置以本批冻结 hash 为证；本页不将模型失败改写为通过。

## 本地实际链路

[批次](../../../../docs/operations/evidence/case-knowledge-20261111-01/local-flow/execution.json)：Case `c171f011-ec81-5020-914f-0e83eb9fab0f`，Run `e1229e23-3fce-43ea-951a-aa8d74c48bbb`。原 HTTP 导入两份 MITRE ATT&CK 已有资料（T1087.001 技术描述、AN0846 检测方法）→4 个 PG 块→真实本地嵌入/向量索引→建案/start→C2→C3→两项 Deep→C6 一次有界纠正→结果保存/GET。8 次业务 HTTP 均成功，6 项结果字段与落库一致，3 份原材料未改写。

实际组件：本机 PostgreSQL `v12_upgrade_dev`、独立本机 Qdrant 集合；既有 21 本地 qwen3-embedding:0.6b/1024 维经 SSH 转发；真实分析模型由既有 SSH 网关传输。仅本机认证主体和分析模型传输适配，业务路由、执行器、DB、嵌入和向量查询没有 mock。本机通用 API 用已有 developer 连接完成必要 KB INSERT；不同于生产 aisoc_app。演练告警沿 C02 原件复制新身份，未增加业务授权事实。

首次只读模型预检因驱动缺 `timeout_seconds` 参数终止，未写业务/调用模型；[原回执](../../../../docs/operations/evidence/case-knowledge-20261111-01/preflight-missing-timeout/model-preflight.json)保留。补齐驱动后才执行唯一实际 Run，不重派结束批次。

## C2 与后续输入输出

- 3 个成员分别生成技术解释/取证指导，6 条实际查询。一次批量嵌入、6 次向量检索；5 条非空、1 条有效查空，共 8 条命中、4 个唯一块，不是 8 个独立来源。原文身份/hash经 PG 回读检查，按行冻结。
- C2 知识步骤 completed，C2 汇总保存模型空间、目标回执和各调用；查询参数/rows 保持原 tool_exchange 顶层合同。资产有效查空，历史/情报/UEBA 因现有预算预留跳过，图未接入。
- 实际 5 份模型请求 source_map 均包含 8 个可定位知识引用。C3 在 behavior_nature 回答中引用两类资料，说明 T1087.001 可能解释；两个 Deep 的原答无知识引用，分别 handoff/answer，均保留未决和未接入能力。C6 两次原答有知识引用，但因 duplicate_source 拒收，Result 为 `partial/rejected/unavailable`、`conclusion=null`，没有当前案件判断。
- 共 5 次分析模型调用，reported tokens **90,292**；费用未知。嵌入与分析调用分别记录。引用/材料进入输入只证明传递与引用，不能证明方法知识已合理用于取证或改善结论。

## 质量与限制

功能传递和保存/读取范围通过；**模型质量 NOT_PASSED**。C3 仍从用户名推测监控/运维角色，云域把主机/网络材料视为适用；C6 重复引用有界纠正后仍失败，原答保持。知识在登录/网络主题下出现枚举资料命中，召回相关性及方法使用效果待后续针对业务资料完善，不额外采样或扩展测试。M01-A/M01-B 继续按用户决定后置，不由本次局部表达改善核销。

本次无新 A/I、H 后轮、Deep 动态再检索、真实厂商取证或自动消费验收。不做复杂可用性、压力/恢复矩阵、全仓回归、全表接口对账或多模型比较。

## 直接检查与页面

[20 项直接检查](../../../../docs/operations/evidence/case-knowledge-20261111-01/direct-checks.xml)通过（首次执行缺 PYTHONPATH、随后测试夹具把注释中的 runtime 标记也替换造成重复键，均在检查收集/夹具层修正并保留原失败回执，不涉及业务或模型重跑）。其中 6 项隔离知识检查覆盖两类目的/来源、元数据 hash、非空/查空、失败及旧索引、原生维度、无效索引输入；14 项处理 profile 检查覆盖已有配置与显式知识挂载。使用替身的边界检查不证明端到端。真实链路以[保存与读回](../../../../docs/operations/evidence/case-knowledge-20261111-01/local-flow/export/verification.json)为准。

用同一落库快照更新本机静态工作台至 65 份记录，保留历史。本地 4188 仅为 4177 源码的临时静态预览：浏览器实际点击 C2 知识节点，核两个目的查询/来源/筛选、原文输出和有效查空；C3 显示本次输入及引用路径，两个 Deep 显示未见引用；提示词/Schema 可见，C6 原因显示 duplicate_source。此查看未触发新查询/模型。生产 4177 已随统一 r3 发布并追加该批次，77 项静态读取通过；浏览器实际查看 C2 两类片段/查空及 C6 duplicate_source，[页面回执](../../../../docs/operations/evidence/case-knowledge-20261111-01/production-ui-check.json)。

## 交接与发布

[功能/数据库/字段对应](../../../../docs/investigation/case-knowledge-handoff.md)；无调查 DDL/告警字段变更。API/处理镜像与工作台以一次统一发布完成；四项无关运行服务保持，既有知识/情报集合和失败原件保留。独立结束审查及 21 实际读回完成前不宣称 change 已收口。

生产接线补充：既有验收账号为 viewer，正常登录可读，但空文档探针在正文写入前被既有 settings:write 拒绝；另一受控保存的旧环境管理员凭据未在 21 验证通过，两次均无业务写入。按负责人功能所需读写直接处理的要求，本次沿既有 API key 机制给该明确租户/账号建立 30 分钟临时导入 key，仅 settings:write、knowledge_base:read，不改用户角色、不改鉴权代码；验收完成后撤销。凭据仅在忽略提交的私密文件，不能把正常登录视为写入口已通过。

## 21 一次发布与读回

[统一交付](../../../../docs/operations/evidence/case-knowledge-20261111-01/delivery-summary.json)：r3 manifest `153c20699df47a1c0b5acffb4a63e3745b790a041c3e0055222c51d59ce3f00b`；API `14d4f66a`、处理 `e041fc00`，工作台同源。API 与 4177 各切换一次，四项无关容器和已有嵌入容器身份保持；处理入口/current 指针、真实挂载源码及策略已核。无调查 DDL/告警字段变化，自动消费者未启动。

[原 HTTP](../../../../docs/operations/evidence/case-knowledge-20261111-01/production/http.json) 7 次成功，保存 4 块并建立 `socai2_knowledge_qwen06b_1024` 原生索引；[实际 C2 adapter](../../../../docs/operations/evidence/case-knowledge-20261111-01/production/retrieval.json) 两目的各返回 2 块，实际配置 hash `2a20e05df7da87b60e720aa39423bde2d5b9c7abc1b6bd4707f1b825d03fa206`，原文/hash对应。探针使用已保存本地查询文本，只读正式库/真实嵌入和向量源，没有新 Case/Run 或分析模型。临时 key [已撤销](../../../../docs/operations/evidence/case-knowledge-20261111-01/import-credential-revoked.json)，读取返回 401，用户角色未改。

[静态批次](../../../../docs/operations/evidence/case-knowledge-20261111-01/static-publication.json)追加 1 份至 36 份，原记录及文件保留；76 文件/77 HTTP 读回。页面中的模型 Run 明确来自本地验收批次，不能把它当作生产业务执行。独审发布补核及归档回执接续于 audit.md。
