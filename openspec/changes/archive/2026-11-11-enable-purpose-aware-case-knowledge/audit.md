# 独立结束审计

审查者：`/root/current_release_audit`，未参与本 change 实现。基线 `V1.1@f95331d76984cc8aac4b3a2861597ceed68dc40c`，审查日期 2026-11-11。

**本地功能结论：限定 ACCEPT，未发现剩余功能阻断，可以进入本 change 的一次统一发布。模型质量仍 NOT_PASSED。** 此结论覆盖 C2 两目的检索、既有文档索引、后续输入/引用传递、保存读取和 4177 展示；不代表 21 已部署或生产连通验收完成。实际发布、生产知识接线与工作台读回须在同一次审计后续补核，归档和 Git/父项目按实际交付完成。

## 范围与方法

只读审阅当前业务差异、设计/规格/交接、20 项直接检查回执及唯一实际 Run 的原件。独立使用本地 JSON/hash/HTML 读取核对查询、输入、引用、失败、落库及页面原件；未重跑业务测试、模型、嵌入或向量查询，未连接数据库/厂商/网络，未执行部署或 Git 操作。仅新增本审计文件，未触碰其他未提交工作。

范围依据：[设计](design.md)、[验收](validation.md)、[任务](tasks.md)、[知识字段交接](../../../../docs/investigation/case-knowledge-handoff.md)。本次未开展权限、可用性、压力、恢复矩阵或全仓/全表/全接口检查。

## 实现审查

- [配置与主题](../../../../services/api/app/socai2/knowledge_config.py)：从本 Run 冻结成员/材料和配置路径生成技术解释、取证指导两个不同查询；原观察与标题/检测线索分别记角色、来源路径及文本截断情况。模型/原生维度、集合、模板、过滤、数量及长度限制均显式配置，配置后的失败不会回退为文本检索成功；未配置环境的既有来源边界保持。
- [索引与检索](../../../../services/api/app/socai2/knowledge_source.py)、[向量连接](../../../../services/api/app/socai2/knowledge_vectors.py)：索引只处理指定租户的已保存块，按目的类型/标签登记分类；验证原生向量维度、有限值及集合空间。查询按租户、模型、维度、目的和资料类型筛选，再从 PG 回读原件并核包含身份/分类元数据的 hash。失败和过期索引明确失败，不记为成功查空。知识不是独立案件观察，原文及适用限制保留。
- [C2 接线](../../../../services/api/app/socai2/baseline_enrichment.py)沿用原步骤、工具额度/预留、截止时间和保留限制；内部查询另受 profile 上限限制。目的级查询/调用回执存入汇总 `source_metadata`，原 `tool_response` 顶层合同不扩展。知识 source_map 沿用 `source_label`、`query_binding_only`，没有把查询成员归属升级为记录主体事实。
- [C3 输入](../../../../services/api/app/socai2/case_model_boundary.py)保留检索原件，仅从模型业务视图去掉 similarity/hash；Deep/C6 复用本轮输入及其依赖。没有新增模型环节、任意工具派发、告警字段或 V1 表列变化。
- [4177 详情](../../../../docs/operations/processing_audit_inspector.py)按同 Run 的工件及汇总定位目的回执，查空、未查、失败、缺历史字段分别呈现；模型节点按自身 request/response 的别名及原答字段解析引用，保留拒收原答和错误。页面说明引用不代表接受或合理使用，原文使用 textContent 展示，查看不触发查询。既有 renderer revision 包含 inspector 源码，可使展示缓存随本次源码变化失效。

## 独立核实的直接证据

原件位于 [local-flow/export/database.json](../../../../docs/operations/evidence/case-knowledge-20261111-01/local-flow/export/database.json)及同批请求/回执；[摘要](../../../../docs/operations/evidence/case-knowledge-20261111-01/local-flow/export/verification.json)与下列独立比较一致。

1. 8 次业务 HTTP 成功：两次原 `/kb/ingest` 返回 201，其余索引、建案、start 及读取返回 200。4 个索引块的 payload hash 与 C2 回读保存的块 hash 一致；原数据与响应保留，未以索引成功替代生成模型质量。
2. 3 个成员各有两个不同目的/文本，共 6 条查询。实际记录为一次 6 文本的批量嵌入及 6 次向量检索；嵌入输入 hash 与已保存查询文本逐项匹配。模型为 qwen3-embedding:0.6b，原生 1024 维；本地集合是独立验收集合，不能冒充生产集合。
3. 5 条查询非空、1 条 completed/empty/0，共 8 个查询命中、4 个唯一块。逐行重算原文及身份/分类 hash 均匹配；每个目的的原查询、过滤和真实数量可定位。8 个命中不是 8 个独立来源。
4. 5 份模型请求均有 8 个知识行引用及其完整正文，行引用角色为 source_label；另有执行回执，未混计为知识块。C3 原答在 `questions[2].evidence_ids` 引用两类知识，两个 Deep 原答没有知识引用，两个 C6 原答在对应问题引用知识；实际传递成立，合理使用和取证效果未由此证明。
5. 两次 C6 原答均在 `analysis.findings[0].support_ids` 重复 `N4_S66`，记录 duplicate_source；这不是知识行身份或传递失败。原有一次纠正后仍拒收，Result 保持 partial/rejected/unavailable、conclusion=null，Case 无当前 assessment。Result 的 conclusion、conclusion_state、validation_state、findings、questions、recommendations 与原 GET 逐值一致。
6. 原模型回执为 5 次、合计 90,292 reported tokens，费用未知；未重复采样。三份演练材料原字段与冻结计划一致。102 个 plan 来源文件 hash 及额外 4 项知识 HTTP/语料配置冻结 hash 与当前文件匹配；导出 manifest 的三个文件 hash 均匹配。
7. 本地实际 HTML 中 49 个 artifact 原始 JSON 与数据库导出逐值完全一致，包含失败原答。源码的同 Run 过滤、目的回执及引用解析与本批引用关系相符。另复用[本地浏览器回执](../../../../docs/operations/evidence/case-knowledge-20261111-01/local-ui-check.json)：已查看 C2 输入/过滤/原文/查空、C3 引用、Deep 未见引用、提示词/Schema 和 C6 duplicate_source；独审未另开浏览器或扩展 UI 测试。

[direct-checks.xml](../../../../docs/operations/evidence/case-knowledge-20261111-01/direct-checks.xml)记录 20 项、零失败/错误；6 项知识边界使用替身，14 项处理 profile 检查不代替真实链路。先前导入路径及 TOML 测试夹具错误回执保留，不计业务失败。首次模型预检缺 timeout 参数也保留，未变成一次已执行模型 Run。

## 审查中修正的文档偏差

原 design 第 17 行写“按原文身份去重”，但本批保存并输入 8 个命中行，4 个唯一块正文在 C3 分别出现 2/2/1/3 次。实现没有合并这些重复正文。已将设计修正为保留目的/成员归属、按 record_id/content_sha256 识别重复而不计独立来源，并明确本次未合并模型输入重复正文。独审已复读确认，与交接/实际证据一致；未据此要求新增去重机制、改变原件或重跑模型。

## 发布范围与未验证项

候选为 r3：API 和按需处理组件采用本次源码，4177 更新展示源码；fusion、agents、projection、litellm 四项继承服务保持。API 环境键清单及允许变更键均包含知识 profile 与 allowlist；API/处理入口的 profile 和私密 key 挂载路径与知识配置一致，挂载只读，通用 API 数据库没有被本次映射替换。生产 profile 与发布清单的处理镜像相同，为 `sha256:e041fc0065d4fa91482aa8199b40eae99b047bbfadf3bf3ae277aae4f90eaa76`；工作台根目录与两个单文件覆盖均指向 r3，避免旧覆盖遮蔽本批代码。

已保存的[统一 preflight](../../../../docs/operations/evidence/case-knowledge-20261111-01/unified-preflight-20261111T144359557753Z.json)为 exit 0、runtime_changes=false，manifest `153c20699df47a1c0b5acffb4a63e3745b790a041c3e0055222c51d59ce3f00b`。这仅证明候选前置核对，不能当作服务已切换、生产 KB 导入/索引或原生检索已通过。

本地认证和分析模型 SSH 传输为明确适配器，KB 使用隔离库 developer 连接，嵌入/向量服务真实。生产计划采用正常登录的原 KB HTTP 导入/索引/GET，以及显式标为只读 adapter probe 的两目的查询；不启动新 Case/Run 或分析模型。生产身份、挂载可读性、网络、专用集合和工作台实际读回仍待发布回执，不将本地结果或静态配置冒充这些结果。

模型质量继续 NOT_PASSED，M01-A/M01-B 和 F01 不核销；登录/网络主题召回枚举资料的相关性、方法采用效果、广泛质量和准确率均未证明。A/I 新检索、Deep 动态补检索、独立处置检索、产品页面及自动消费不属于本次已验范围。当前剩余工作为按实际完成交接/发布及归档前一致性，随后归档、Git 与父项目远端回执；不增加额外模型采样或复杂专项。

## 发布后补核（2026-11-11，同一次审计）

**交付结论：限定 ACCEPT，未发现阻止本 change 归档的新增问题。** 上文保留发布前审查时点；此处仅对新增[交付汇总](../../../../docs/operations/evidence/case-knowledge-20261111-01/delivery-summary.json)、统一发布、生产 KB/adapter、凭据撤销及工作台回执作本地只读比较，没有新增测试、模型、嵌入、数据库、网络或部署操作。

- r3 的 prepare、两次指定服务 rollout、activate、verify 均 exit 0；两次 rollout 分别且仅为 API、workbench。最终 verify 的 manifest 与本地接受的 `153c20699df47a1c0b5acffb4a63e3745b790a041c3e0055222c51d59ce3f00b` 一致，六服务健康，API 镜像匹配摘要，实际挂载核验包含 API 的两份配置和工作台 656 个文件。将 prepare 的 before_id 与[容器读回](../../../../docs/operations/evidence/case-knowledge-20261111-01/container-readback.json)逐项比较，fusion/agents/projection/litellm 四容器 ID 保持；同一回执记录已有嵌入容器未变。消费者仍暂停，处理组件仍是本审计接受的 e041fc00 镜像。
- 实际身份与发布前计划有明确区别：既有 viewer 登录没有 KB 写能力，最终[生产 HTTP](../../../../docs/operations/evidence/case-knowledge-20261111-01/production/http.json)使用临时 API key，不能记为该账号经普通登录完成写入。公开创建回执记录的 scope 仅 settings:write、knowledge_base:read，用户角色未改。[撤销回执](../../../../docs/operations/evidence/case-knowledge-20261111-01/import-credential-revoked.json)与创建记录为同一 key ID，is_active=false、撤销后读取 401，与交付摘要逐值一致。审计未读取或复制私密凭据。
- 生产 7 次业务 HTTP 中，两次导入为 201，索引及四次块 GET 为 200；返回的四个文档 ID 与索引登记及[实际 adapter 查询](../../../../docs/operations/evidence/case-knowledge-20261111-01/production/retrieval.json)一致。两目的各 completed/data/2；实际记录为一次双文本嵌入及两次向量检索。逐块按原字段重算身份/分类/正文 hash，与查询行及索引 payload 完全匹配；实际 profile hash 与当前知识配置文件一致，模型/维度/集合分别为 qwen3-embedding:0.6b、1024、socai2_knowledge_qwen06b_1024。该探针使用保存的本地查询文本，调用真实 API 环境中的只读 adapter，未创建生产 Case/Run，也未调用分析模型；不将其描述为生产完整调查或新的 C2 落库流程。
- [静态发布](../../../../docs/operations/evidence/case-knowledge-20261111-01/static-publication.json)为 35→36、76 文件/77 HTTP，原记录和文件保持，摘要字段相符。这一回执的“静态更新”只指批次追加步骤，工作台展示源码另由上述统一 rollout 更新。[生产浏览器回执](../../../../docs/operations/evidence/case-knowledge-20261111-01/production-ui-check.json)明确访问 SSH 转发到 21 的 4177，已查看两类片段、有效查空和 C6 duplicate_source；页面 Run 来源是已发布的本地验收快照，不能冒充生产分析执行。独审复用该浏览器回执，没有另开浏览器。

最新 PROGRESS、根交接、部署/知识说明、validation 和任务均区分本地完整 Run、生产 HTTP、只读 adapter、临时身份及静态页面，并保留模型 NOT_PASSED、C6 rejected/null 和主调查 31/41。原普通登录验收计划已由实际 API key 结果及撤销事实取代；角色、鉴权实现及持续模型问题未冒称修复。限定功能可归档；最终 Git/父项目推送与远端 hash 仍按后续真实交付收口，不在本次审计中提前确认。

## 封后记录

主流程于 2026-11-11 在本地/发布两次限定 ACCEPT 后执行 `openspec archive enable-purpose-aware-case-knowledge --yes`：全部任务完成，新增 case-purpose-knowledge 3 项及 investigation-knowledge-inspector 2 项主规格，归档目录为本目录。修正移动后的交接链接及 CLI 为新主规格生成的 Purpose 占位段；未改变冻结运行源码或重跑模型。最终 Git/父项目 hash 以实际远端引用读回和最终交付消息为准。
