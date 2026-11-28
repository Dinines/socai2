# 告警资产匹配：后端接口与供给支撑

2026-11-24。**最新决定：本步资产关联未通过，后置到清洗模块在 OCSF 中提供明确的资产关联 ID。** 本轮刚形成的、未测试的 evidence IP 提取和定向恢复草稿及其新增规格已撤出交付；原在运 host/IP 行为、原件和冻结字段合同保持。不自行规定 OCSF 字段路径、ID 命名空间或 fallback，不做正式对象恢复、库存补写或程序发布。第 4 步管理/反馈停在[已记录的安全边界](alert-management-feedback-backend-support-20261124.md#实际结果与候选交接)，等待组织者下一条具体安排。

## 原诊断范围和顺序（诊断保留，修正方案已停止）

1. 从现行源码和运行配置确认 `records/assets` 实际读表、当前材料对象、同租户和 host/IP 匹配规则，以及原生资产与 identifier 到该供给的路径。
2. 复用前端交付的当前未匹配主体私有定位，按同一告警、当前材料和对象只读核对库存与 HTTP。没有定位前不任意挑已成功记录代替当前问题；旧单条成功证据只作原范围参考。
3. 将实际表/字段、最小供给缺口及私有定位交前端补充。若发现具体后端程序阻断，先交组织者最小依据和方案，本步不自行扩展匹配语义或写资产。
4. 前端保存后沿同一定位读回对象、库存和 `records/assets`，核对象/资产 ID、标签及匹配依据；原生资产独立读取、页面列表/预览/详情和资产链接由前端与组织者验收。读空、失败和未匹配分别保留。

本步先为只读支撑，无新增规格级行为；若需要修正供给或程序，先补对应现有规格增量和直接验收，严格校验后实施。所有业务值、身份、运行地址、原始查询/HTTP 回执只保存在受控 `.local` 目录；本文只记录结构与工程结论。

## 源码已确认的合同

| 环节 | 实际来源或规则 |
| --- | --- |
| 对外入口 | `GET /api/v1/socai2/alerts/{alert_id}/records/assets`，沿已配置租户读取；现行适配器的 `pages()` 直接实例化 `PageReadService(AsyncSessionLocal)`。 |
| 库存关系 | 此适配器没有传入 `read_sources`，因此 `lookup_relation('assets')` 使用 `public.assets`。其他独立读取服务可以显式传关系，但不能据其配置推断本入口已切换。实际数据库及关系类型仍须运行核对。 |
| 告警对象 | `socai2.alert_objects` 与 `socai2.alerts` 按同租户、告警 ID 和 `a.latest_material_id=o.material_id` 关联，只匹配当前材料对象。对象缺失或仅旧材料有对象，不会由原始正文临时补解析。 |
| 租户 | 库存 `tenant_id` 必须等于对象和请求租户。其他租户同名/IP 不进入结果。 |
| host | `object_type='host'`，`lower(normalized_value)` 与 `lower(name)` 或 `lower(fqdn)` 精确相等；不自动补域、截短主机名或查 identifier 别名。 |
| ip | `object_type='ip'`，`normalized_value=ANY(ip_addresses)`；按文本元素精确比较，不做网段包含或 IP 格式重写。 |
| 其他对象/标识 | 此路径不直接匹配 device UID、账号、MAC 或任意 identifier，也不读取已有 `alert_asset_correlations` 作为替代依据。 |
| 返回 | 每条为对象—资产匹配边，含 `object_id/alert_id/material_id/object_key/namespace/asset_id/name/fqdn/asset_type/tags/criticality/os/os_version/ip_addresses/match_basis`；同一资产可因不同对象出现多条。 |
| 匹配依据 | IP 为 `exact_ip`；host 优先 `exact_name_casefold`，否则 `exact_fqdn_casefold`。库存无对象 namespace，匹配不把 namespace 当库存归属依据。 |
| 分页和保存 | 按对象 ID、资产 ID 排序后 offset/limit；total 统计边数，不是去重资产数。读取不保存身份关联、不改告警或材料。 |

库存最低读取投影为 `id,tenant_id,name,fqdn,asset_type,tags,criticality,os,os_version,ip_addresses`。原生资产的 identifier 若没有进入这条关系的 `name/fqdn/ip_addresses`，单独补 identifier 不会被此查询直接使用；如何进入必须沿现有供给实现和运行结构核实，不据字段相似推断已同步。

源码依据：`services/api/investigation_http/adapters/services.py`、`services/api/app/socai2/page_reader.py`、`services/api/app/socai2/read_sources.py`。`ReadSources.check()` 只核读取投影可用，不能证明原生库存已同步或某条告警已匹配。

## 运行核对和交接

当前主体由 SpiritHub 最近的 8181 预览定位，私有选择器为 `.local/validation/spirithub-alert-assets-recheck-20261124-01/target-selector-private.json`；没有使用第 3 步或旧成功样本代替。对接方已保存同 ID 详情、对象、资产及指定材料回执；对象与匹配结果为空。

本步私有证据目录为 `.local/validation/alert-asset-match-backend-support-20261124-01/`。`supply-structure-01/` 核正式服务运行版本、数据库与租户仍与现行 profile 一致，实际 `lookup_relation/assets/pages` 方法与当前源码一致。供给为该数据库的普通 `public.assets` 表，非视图或外部表；所需读取列全部存在。该表唯一非内部触发器调用 `public.update_asset_ts()`，其函数体仅把 `NEW.updated_at` 设为当前时间，没有原生资产同步行为。这里只排除该关系自身的视图/外部表/触发器供给，不能据此断言没有另行运行的同步程序。

原生 SpiritHub `assets` 是资产身份表，`asset_identifiers` 保存类型、namespace 与 canonical/display 值，台账及来源链接提供业务属性；它与调查 `public.assets` 的投影不同。现行调查适配器既不查询这些标识，也不读取原生台账。前端另已核旧调查资产 ID 在原生资产详情返回 404：该事实属于前端回执，说明旧库存匹配正例未证明原生资产详情可达。原生当前运行 profile、有效供给适配和 ID 对应仍待对接方交付，本步不另造资产或只补调查表追认整链成功。

`target-readback-01/` 对固定租户/告警/当前材料做正式只读 SQL，并仅恢复其已有 Fusion 首次快照，在现行 Fusion 容器运行纯 `project()` 函数。告警及材料身份保持，数据库原件与前端保存原件一致，实际投影模块指纹与本机一致，纯计算仍输出空对象，与实存一致。没有执行保存、消费者、分析任务或模型。

### 当前对象缺口的直接依据

| 检查 | 结论 |
| --- | --- |
| 当前材料与 selector | 同一告警、同一当前材料；正式 PG 与前端冻结原文一致。 |
| 已支持路径 | `device.hostname/name/ip`、`src_endpoint.hostname/ip`、`dst_endpoint.hostname/ip` 以及 RawAlert `hostname/src_ip/dst_ip` 均无可用值。 |
| 原始标准结构 | `evidences[].src_endpoint.ip` 和 `evidences[].dst_endpoint.ip` 有合法 IP 字符串，与保存原始文本同路径一致。值仅留私有文件。 |
| 重复与不确定字段 | `unmapped.spirithub.legacy.source/destination.ip` 与上述观察重复，不另作独立证据。`unmapped.vendor.host` 含义尚无结构合同，不按名字猜为设备主机。 |
| 实际程序 | `socai2_projection.project()` 只遍历顶层端点；湖接收 `ReceivePolicy.entity_paths` 的语法只接受点路径，不支持数组。现行纯投影与数据库均为空，故只补库存不足以使此主体匹配。 |

这一缺口与已有 [2004 数组端点设计](lake-evidence-tools-design-20261119.md) 相符；该文已有设计不代表数组提取已经实施。本步不扩展十一类全解析或 Case 工具查询。

探针首份工程检查把 PostgreSQL 单字符类型的字节表示误判为非普通表，同时对源代码提取时的 SQL 字符串缩进差异误判为源码不一致。按同一原回执解码类型、统一方法提取后，两项均确认一致，原检查与 `derived-structure-checks.json` 一并保留；没有为此重跑业务查询或修改服务。

## 本轮候选草稿撤出记录

组织者曾准许本机候选实现，规格严格校验通过后形成了一次未验证源码草稿；负责人先要求暂停审计设计，随后决定由清洗模块提供明确资产关联 ID，停止数组 IP 扩展及定向恢复。本轮草稿从未运行 Ruff、单元测试或候选 PG/HTTP，从未建立本批新夹具或执行 apply。

撤出前核对四个文件与暂停指纹完全一致，没有他人续改。仅精确撤出本轮新增内容：

- `socai2_projection.py` 的 IP 校验导入、`evidence_endpoint_objects()` 及其 `project()` 接线；撤出后整个文件指纹与本轮候选前一致，原有修改和在运顶层行为保留。
- 本轮新建的 `services/fusion/app/services/alert_object_repair.py` 与 `deploy/database/repair_alert_evidence_objects.py`。
- `socai2-investigation-data/spec.md` 中本轮新增的数组端点提取和限定恢复两个 requirement 及对应场景。没有回退整份规格或其他人的变更。

未验证草稿和当时方案仅在私有 `withdrawn-draft/` 留存追溯，不再是交付或待执行方案。`withdrawal-checks.json` 核撤出范围与原投影指纹；正式文档证据见[本批回执](../../../docs/operations/evidence/alert-asset-match-backend-support-20261124-01/README.md)。原活动排序草稿保持原暂停状态。

本轮未改原始 OCSF/材料、告警或资产记录、旧 Run/步骤/工件，未恢复对象、调用模型、消费消息或部署。没有因这次诊断取得资产关联通过结论。下一步等清洗方给出明确字段路径及该 ID 对应的原生资产库；其他命名空间、唯一性和页面合同依实际对接澄清，当前不发明规则或回落逻辑。

SpiritHub 已交当前原生运行结构：实际平台服务连接 `spirithub` 数据库，相关文件与 8181 checkout HEAD 一致；四张原生表无 tags 列及用户触发器，台账创建在本库保存，未发现该保存路径向调查库存供给。当前固定端点的原生 identifier 查询均无精确匹配。原生 ID、调查租户及标签供给的缺口继续保留，不能用调查表孤立写入或 IP 值补造原生身份。

## 设计审查暂停边界与原依据

**暂停时的事实：** 当时规格校验通过、源码草稿刚写入，但没有代码测试、候选保存或 apply。随后按负责人最新决定精确撤出，见上节；私有 `paused-candidate-state.json` 保留当时指纹，不将撤出写成完成。以下审计只说明已有资料能支持的边界，不追改历史结论。

| 既有资料 | 可以支持什么 | 不能据此推出什么 |
| --- | --- | --- |
| [V1 字段字典 §3.4](../../../docs/design/socai2-field-dictionary-20261103.md#34-socai2alert_objects) | 观察对象与库存匹配分开；同 object_key 可有多来源路径；matched 要有引用/依据；当前对象读当前材料，历史 Run 读冻结材料。 | 没有定义 SpiritHub 原生主键到调查库存 ID 的具体映射或跨库供给。 |
| [本机验证安排 §3](local-first-validation-plan-20261105.md#3-已接来源与真实缺口) | 资产行已要求主机/FQDN/IP、缺失及歧义验证，库存不证明当时状态或授权。 | 这是既有实现的验证安排，不是原生资产供给的完整设计。 |
| [已有 2004 字段/接线设计](lake-evidence-tools-design-20261119.md) | 已明确 evidence 数组端点、数组同元素关系及对象提取缺口；设备身份段明确 host/IP 是候选、保留全部匹配，外部 UID 不能直接当资产 ID。 | 该记录含实现核对和后续设计，不能把其中对现行 SQL 的描述当作更早的完整匹配设计，不能称数组能力已实现。 |
| [剩余流程 §6 业务后端依赖](remaining-flow-interface-design-20261121.md#6-业务后端依赖及联调接口) | 明确应由业务后端确认稳定资产主键、来源/租户、字段映射、同名/同 IP 多匹配、查空及详情；表/视图供给要交地址、库、schema 和映射。 | 文中明确是待确认的联调草案，不证明这些供给合同已经落定。 |
| [主设计的告警资产供给核对](design.md#告警资产与负责人供给核对) | 留有原生表结构核对、同租户投影/ID/标签待核，以及单条合成库存写入与列表/预览读回的历史范围。 | 历史记录只证明当时调查表匹配和链接 ID 一致，未证明原生资产详情实际存在；不重写旧结论为完整身份链。 |

当前可以证实有对象/库存分离的设计原则、来源路径合同、后续数组处理设计和外部接口待确认项；**尚未找到一份已经确认并落实的完整原生资产供给方案**，覆盖原生资产稳定身份如何投影、调查租户范围、标签来源、增改同步，以及歧义/外部端点如何显示和详情跳转。因此不能回答“资产全链已完整设计并实现”，也不能拿已有 SQL 补充这个证明。

此次数组 IP 草稿只补观察提取，不创建资产，IP 不是 asset_id，也不证明端点属于受管资产。现行查询返回同租户全部 host/IP 匹配边，不能据单次 exact_ip 命中推断唯一资产、历史归属或内部管理范围。当前不继续该草稿，资产关联等待清洗方提供明确的 OCSF 资产关联 ID 及原生库对应；本步未通过，不开展其他独立任务。
