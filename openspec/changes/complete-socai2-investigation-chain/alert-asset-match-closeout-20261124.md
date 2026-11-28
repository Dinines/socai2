# 告警涉及资产匹配复验

2026-11-24。优先处理负责人刚反馈的 8181「涉及资产未匹配」。范围限当前告警、其当前材料关联对象、Spirit Hub 资产库存以及调查服务实际读取的资产投影。第 4 步管理与反馈停在隔离写入前，已有前端 TypeScript 和 9 项定向用例通过。

**本轮资产关联验收为「等待清洗模块明确资产 ID，未通过」。**

## 本轮只读核查范围

| 步骤 | 直接核对 |
| --- | --- |
| 确定本次告警 | 从最近的 8181 预览定位唯一告警，并用详情和该 ID 的资产回执确认未匹配。仅保存告警与当前材料 ID 到私有选择器。 |
| 确定匹配输入 | 独立读取 `records/objects` 与所选材料的 OCSF 正文，检查当前材料是否已索引可用于资产匹配的主机或 IP。按原对象类型、规范值和命名空间对照，保留告警原材料。 |
| 核库存及供给来源 | 核原生资产的标识和同租户范围，核调查服务当前加载的库存关系与投影。主机按不区分大小写的名称/FQDN，IP 按地址数组精确查找。对象命名空间用于核查输入来源，现行库存查询的匹配条件不包含该字段。 |

## 当前只读定位

本机最近四小时 8181 的告警预览或详情仅定位到一个不同的告警 ID，最近一次为当前复验前数分钟。实际已读详情、对象和资产接口，均为 HTTP 200，详情有当前材料版本，当前对象及资产结果均为 0 条。当前浏览器无业务写请求。私有定位为 `.local/validation/spirithub-alert-assets-recheck-20261124-01/target-selector-private.json`，仅用于本条告警的后端联验。

## 对象与原生库存读回

| 读取环节 | 当前告警的实际结论 |
| --- | --- |
| 8181 固定材料 | 现有材料链接返回 HTTP 200。OCSF 原文有 `metadata.uid`，源、目的端点 IP 均在 `evidences[]` 内。根层 `device`、`src_endpoint`、`dst_endpoint` 没有现行投影所需的主机或 IP 值，规范化正文的 `hostname`、`src_ip`、`dst_ip` 也为空。 |
| 对象及匹配 | 当前告警的 `records/objects` 和 `records/assets` 均返回 HTTP 200、0 条。正式在运投影只读取根层端点，实存对象和同材料的在运纯投影均为空。8181 继续按实际结果显示「未匹配」。 |
| Spirit Hub 原生库存 | 按同一材料证据段的 2 个唯一 IP 查询原生 `/api/v1/assets`，均返回 HTTP 200，精确标识命中 0 条。此前调查库存正例的资产 ID 本轮请求原生详情返回 404，同 ID 的原生详情仍待打通。 |
| 调查实际库存 | 沿 21 正式服务同租户 `aisoc.public.assets.ip_addresses` 以完全相同的 2 个端点逐一比对，匹配 0 条。SQL 限定同一告警及其当前材料，以只读事务执行。 |

## 在运库存供给及写入范围

8181 的原生资产请求依现有 A Run 候选 profile 中的 `platform_origin` 转发到 21 的 Spirit Hub 8080。`spirithub-api-1` 实际连接 `spirithub` 库。原生 `assets` 保存资产身份，`asset_identifiers` 保存 IP／主机标识，`asset_ledger_profiles` 和 `asset_source_links` 提供台账及来源。已核四表无 `tags` 列和用户触发器。运行中的原生资产、台账路由、仓库和模型五个文件与 Spirit Hub 8181 checkout HEAD 的对应源码指纹一致，可从容器 `/app/backend/src/spirithub` 或 sparse checkout 的 Git HEAD 读取。 [工程回执](../../../docs/operations/evidence/alert-asset-match-20261124-02/verification.json)

原生资产 ID 是 `assets.id` 的 UUID，由台账登记时生成。IP 是 `asset_identifiers.canonical_value` 中的查询标识，经 `asset_identifiers.asset_id` 关联真实库存。调查 `records/assets` 用 IP 匹配 `ip_addresses`，返回的是命中行的 `id AS asset_id`。页面库存详情链接跟随这个 ID。

原生写入调用 `POST /api/v1/asset-ledger/assets` 或该 ID 的既有更新合同，仓库在原生库事务中创建／修改资产身份、台账和标识。调查查询实际读取独立 `aisoc.public.assets`，同租户匹配依赖 `name/fqdn/ip_addresses`，展示使用该表 `tags`。本次已核路径中未找到从原生写入到该调查表的供给接线。 [调查端供给核对](alert-asset-match-backend-support-20261124.md#运行核对和交接)

## 设计与实现记录

| 环节 | 可核对的依据 |
| --- | --- |
| Spirit Hub 原生库存和同步 | 2026-08-22 原生资产设计提交 `dfc2744a` 早于资产身份归并 `04094c41` 和同步实现 `5ce99782`。该同步把外部源归并到 Spirit Hub 原生库。原生资产列表按 `asset_identifiers.canonical_value` 检索，台账登记生成 UUID，详情按 UUID 读取。对应 Spirit Hub 仓库的 `docs/superpowers/specs/2026-08-22-asset-inventory-sync-design.md`、`backend/src/spirithub/db/asset_repository.py` 和 `backend/src/spirithub/db/asset_sync_repository.py`。 |
| 调查侧匹配 | 现有匹配设计与 `PageReader` 最早同见于 2026-11-05 的检查点 `a1be19316`。Git 只能确认二者在该检查点已存在。正式 `pages()` 沿独立调查库存读取，`ReadSources` 在本地只读入口可选择关系和核对结构。 [查询实现](../../../services/api/app/socai2/page_reader.py#L346) · [正式适配](../../../services/api/investigation_http/adapters/services.py#L120) · [只读入口](../../../deploy/local-investigation/remote_readonly_api.py#L114) |
| 原生资产关联给调查侧 | 11-21 交接草案已有稳定资产主键、匹配字段、标签及空结果／歧义要求。仍待确认清洗输出的资产 ID 合同，以及正式调查读取如何用该 ID 定位同一原生资产和标签。已核的 Spirit Hub HTTP 转发负责提交请求并返回调查结果，现有候选范围未证实跨库资产映射或同步。 [交接草案](remaining-flow-interface-design-20261121.md#6-业务后端依赖及联调接口) |

## 本轮收口

本轮资产写入和告警写入均为 0，8181 调用与已发布合同保持。端点字段继续作为告警观察留存。数组 IP 对象候选保留在暂停状态，资产关联以清洗模块提供的明确资产 ID 为后续输入，字段路径、类型和来源以实际交接为准。已核两端库存均未命中，当前端点没有已核的受管资产归属。 [工程回执](../../../docs/operations/evidence/alert-asset-match-20261124-02/verification.json) · [后端候选暂停记录](alert-asset-match-backend-support-20261124.md#设计审查暂停边界与原依据)

此前 4001 正例只证明在运 host/IP 规则下调查库存命中及 8181 资产标签展示。原生库存详情同 ID 正例仍待验证。收到清洗模块明确资产 ID 后，以同一原生资产 UUID 检查 OCSF、调查资产返回和 8181 详情跳转，核标签和未匹配状态。 [4001 正例原范围](es-ocsf-test-chain-20261124.md#8181-正式资产标签复测)
