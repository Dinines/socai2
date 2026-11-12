# 发布补充独立审计

## 结论与范围

2026-11-12，未参与实现和发布的独立审查者，对 `use-historical-alert-knowledge` 的 `v1.2-20261112-r1` 发布回执做限定审计。**发布接线、读回及记录保留范围 ACCEPT；模型质量仍为 NOT_PASSED。** 本地功能结论沿用 [本地独审](audit.md)，本补审不将历史知识传递等同合理采用，不核销主调查未完任务。

本审查仅读取工作树内源码、冻结包和[本批证据](../../../../docs/operations/evidence/historical-knowledge-20261112-01/)，以标准库执行已保存 JSON、SHA-256、UUID 和容器身份的离线比较。没有访问网络、数据库、模型、嵌入、浏览器或部署，没有重跑测试或操作 Git；仅新增本文件。

## 核对结果

| 对象 | 已保存证据及独立核对 |
| --- | --- |
| 冻结来源 | 统一包 manifest 为 `64df79b7ce2bd80c96b4a3c5bc967bc97b7dd3c071bed2b24132d3195ed7e7b5`；657 项冻结文件 hash 全部一致，对应工作树文件亦一致。构建回执、prepare、activate 和最终读回使用同一发布身份 |
| API / 处理镜像 | API 实际镜像 `sha256:7546def9d9f477b326e7deb38552ab1904959ffca61d2be3e0d5e920c3e458be` 与构建/目标/读回一致；处理镜像 `sha256:7043441754b7f59194975249642fd68ea53d67e2dc9f320393adec4aa8bb7417` 对应已保存处理构建和 production profile。处理构建自检是原回执，本审查未重跑 |
| 切换范围 | 已保存 rollout 回执仅 API、workbench 各一次。最终两个容器 ID 均与 prepare 的 before ID 不同；fusion、agents、projection、litellm 四个容器 ID 与镜像逐值保持。最后状态均 healthy；发布指针和处理入口指向本轮目录 |
| 实际知识配置 | 最终容器读取的 profile hash 为 `811764e72c5f8206230c8f5f08497dfaaff59557ac1ffe3f21dc31a892a17970`，与冻结/工作树配置、索引回执和检索 metadata 一致；启用三个目的，模型及原生维度为 `qwen3-embedding:0.6b` / 1024 |
| 生产业务 HTTP | `production/http.json` 保留入库、索引、完整卡片 GET 共 3 次 HTTP 200。文档 `5837d5c7-2c53-53dc-9923-d75487f25c46` 在三个返回中一致，原来源是已存在的演练告警，未新建生产分析 Run |
| 卡片与索引 | GET 卡片、检索中的序列化正文、history 加 triage/feedback 的拆分还原逐值相同；重新计算稳定 UUID 与文档 ID 一致。内容及分类元数据 hash `e8b94b955b08af198f14448b2a3ae3b9b0ed23f87d8c307e361abf204846bb67` 与索引 payload、检索行一致。源 alert/material/triage/feedback ID 与 source-selection 回执一致，版本状态为 current，verification 仍为 not_independently_verified |
| 生产检索 | `production/retrieval.json` 记录一个历史目的查询、一行命中，无截断；命中就是上述卡片。嵌入/向量均有实际调用回执。该步骤使用显式探针时间窗，是只读 adapter 核对，不是生产 Case 完整调查或知识合理使用证明 |
| 临时凭据 | issue/revoke 回执的凭据 ID、租户和用户一致；已撤销且原 key 再读返回 401，账号角色未改。私密原值未进入本审计 |
| 4177 | 静态 manifest hash 与 publication 回执一致；76 个文件与本地对应内容逐值/hash 一致。生产回执记录 77 次静态 HTTP 内容读回、37 → 38 份记录、增加 1 份；旧记录/旧文件保留，静态发布未改变容器。浏览器功能查看沿用本地已有证据，本审计没有新增浏览器验收 |

上述生产路径的回执及验收脚本均限定为 0 次分析模型调用、0 次 Run 写入；入库/索引和临时凭据生命周期本身有各自写操作，不混称整个发布过程“无写入”。

## 失败与适用边界

- 首次上传回执为 SSH 连接 `Operation not permitted`、退出 255，未收到远端上传结果；后续获准上传成功，原失败保留。
- 首次 activate 返回 `service_not_ready_workbench`。冻结的 `activate()` 先执行完整 verify，再切指针，因此此失败发生于指针更改前；随后保存的成功 activate 和最终指针读回完成收口，没有第二次 rollout 回执。
- 生产检索复用本地技术主题，但按 `production.json` 使用 `[2026-08-14, 2026-11-12)` 的显式探针边界，并在远端加载当前 profile hash。复制的 intent 中仍保留本地 context/selection 信息，不能将其当成新生产 Run 的实际范围或 C2 九查询证明。
- 源卡来自已有演练资料，不是经独立真值核实的真实业务历史。current 只表示当前源指针对应；它不证明历史判断正确。
- 本地 C6 `recommendation_needs_sources`、Result `partial/rejected`、`conclusion=null` 和原答保留。M01-A/M01-B/M02、F01/F02、召回相关性与方法使用效果继续开放。自动入库/消费、A/I 新知识检索、Deep 动态检索、产品页面和真实处置没有随本发布验收。

## 交接文字复读

已复读更新后的 `PROGRESS.md`、`FRONTEND_BACKEND_HANDOFF.md`、历史知识/两目的知识交接、模型输入输出、执行账本、21 部署说明、本 change 的 validation 及 delivery-summary。当前发布 `v1.2-20261112-r1`、生产 3 次业务 HTTP/1 次历史探针、4177 38 份、凭据撤销、NOT_PASSED 与未验范围均和上述证据一致。

复读曾发现交接末段和部署说明仍用“本次”描述前批 7 次 HTTP/36 份记录，实施者已明确改为“前批”并保留原证据链接；已复读确认，不再与本轮数据混淆。后续优化明确在本 change 收尾后独立提出，尚未作为现有功能交付。

本审计不预报 OpenSpec 归档、Git 推送或父项目引用同步成功；这些动作须按实际完成另记回执。当前没有发现本 change 发布交接范围的剩余阻断，可以继续归档前条件核对及 Git 交付。
