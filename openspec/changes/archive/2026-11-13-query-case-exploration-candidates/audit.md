# 独立结束审计

审计者：未参与本项实现的 `exploration_end_audit`。日期：2026-11-13。仅审查本 change，未修改业务代码，未启动模型、创建数据或操作服务。

## 当前结论

**最终结论 ACCEPT：代码、本地直接流程、交接/Swagger及两端正式发布读回均通过，可归档本 change。** 结论仅覆盖E66候选查询及已有E08明确关联的调用衔接；画布保存恢复、告警相似复核专项、AI对话、自动调查和模型质量不在完成范围。Git尚未提交或推送。

## 已核对

- 对外路由只依赖用例端口、DTO和依赖组装；SQL、对象规则和事务位于独立核心读取模块。核心不导入对外HTTP包，不经内部HTTP转调。旧 `related_alerts`、Fusion对象写入和C5构图未在本项修改。
- 起点来自真实当前告警/对象，Case告警来源范围、租户和对象namespace分别保留；旧材料对象409。普通类型按存储值精确匹配；哈希起点要求明确支持算法和合法值，SQL同时匹配算法和值，未借长度猜算法。
- 默认窗口来自种子实际告警时间及配置，用户窗口为包含起点、不包含终点；不拿入库或读取时间补未知。没有可用起点时返回明确空集合，不生成虚拟对象。
- SQL先匹配、按告警聚合/去重再排序分页；共享对象计数不因重复原字段增加，匹配对仍保留全部原件。游标绑定实际种子、材料、案件范围、窗口及模式，范围变化409；候选数据跨请求变化不承诺全库冻结。
- 每个请求使用只读一致快照；候选查询不写成员、Run、Result、图或对象。关联使用原E08，保留其他Case归属，不启动调查。
- 查阅[本地30次HTTP及显式加入回执](../../../../docs/operations/evidence/case-exploration-20261113-01/local-http/verification.json)与原请求/响应：26次查询/来源回查后，10张相关表的原行快照完全相同；之后显式关联及Case读回通过，旧游标因成员范围变化被拒绝。
- 独立以SQL原行核对全部成功响应中的28个匹配对出现位置：两端object/alert/material ID、类型、namespace、键、原值、存储值、来源路径与原行一致，均指向匹配时最新材料；共享对象去重数量及basis正确。该计数包含分页和不同查询中的重复对象，不作为28个独立案例。
- 11个候选覆盖文件的当前SHA-256与[冻结源码清单](../../../../docs/operations/evidence/case-exploration-20261113-01/candidate-source-manifest.json)一致。既有合同检查明确仅移除新路径及六个新输出Schema后比较旧合同，不通过放宽旧告警DTO追认兼容。

## 交接注意点

1. `time_delta_seconds`实际是距**参与匹配的起点告警**的最短时间差，设计和Swagger不应描述为任意未匹配起点。
2. `matches`只包含匹配对象及依据；展开候选的全部对象需沿已有E30 `objects`读取。默认起点是当前案件成员，不能宣称已读取任意保存的画布。
3. 只交付候选读取；画布保存/恢复、AI对话、自动调查和模型质量不在此审计结论内。

## 原待补核事项

- Swagger新接口的输入、所有输出字段、错误示例和实际实现状态，产品功能清单与交接指南一致。
- 本机/21实际加载源码或镜像、只读复验及静态Swagger一致性回执；最终冻结版本若变化，只复核差异。

以上两项已由下文发布前及封后复核完成，保留初次审查边界。

## Swagger候选复核

首版docs15候选（OpenAPI SHA-256 `5362afa6184e258c2481e138522352a02ed6accf48e6c4bd02ab2e8d4af5a330`）有两项需发布前修正的交接问题：

1. E66成功响应字段说明把9个缺description的新字段统一写成“固定合同版本socai2.incident-grouping.v1”：ExplorationPage.items/scope、ExplorationScope.seed_kind/case_scope_revision/window_basis、ExplorationObject.alert_id/object_type、ExplorationExcludedObject.object_id/reason。字段Schema合法不表示含义正确；需补真实语义并重新生成。
2. E66成功示例的候选alert.latest_material_id为null，但matches.candidate.material_id非空。实际查询只匹配最新材料，这两个示例值应一致。

其余输入、错误码与示例、类型匹配规则、默认窗口和scope、来源回查、E08明确加入、AI对话/探索保存未实现边界，与指南及功能清单一致。上述问题修正并定向复核后再给统一发布结论。

### 发布前定向复核通过

新候选OpenAPI SHA-256 `88e53f7bf49bde0d8bf98d693dcf7dcc088b7e032dfc315c223b388879f0aec4`：9个字段均有正确说明，E66响应说明不再混入归并统计合同版本；示例latest_material_id与匹配原件一致。完整示例校验仍为585 JSON响应、3 CSV、26请求；66操作/147类型/703固定字段位置。11个业务覆盖文件与已验冻结清单一致，没有因文档修正改变业务实现。指南明确匹配起点时间、E30补读全部对象、默认当前成员，F25/F19仅核销本次候选及既有明确关联的范围。

发布前结论：**ACCEPT，可统一发布**。此结论不代替两端实际加载、GET读回及静态Swagger最终一致性的封后核验。

## 封后复核通过

- 本机正式API为`case-exploration-20261113-r1-local`，21为`case-exploration-20261113-r1`、镜像`sha256:6c05adad8eeb0899551309c2e67e38070b209ff7738b677ec057da275adbf379`。本机/21的11文件加载哈希与已验冻结清单、当前仓库源文件一致；配置JSON和SQL一并核对。参见[本机运行](../../../../docs/operations/evidence/case-exploration-20261113-01/local-runtime.json)、[21运行](../../../../docs/operations/evidence/case-exploration-20261113-01/21-runtime.json)。21回执记录其余36个容器保持。
- 两端各11个正式GET均200，分别核对版本/66操作、整案及指定告警候选、下一页、告警原DTO、两端原对象与材料、Case前后读取。独立复核本机4对、21两对匹配引用均与各自E30原对象一致，候选AlertFacts与E28完全相同；两端Case完整返回前后相同。使用已有数据，0正式写入、0模型、0迁移。参见[本机读回](../../../../docs/operations/evidence/case-exploration-20261113-01/local-release-http/verification.json)、[21读回](../../../../docs/operations/evidence/case-exploration-20261113-01/21-release-http/verification.json)。
- Swagger两端均docs15，11个HTTP入口全部200且对应哈希一致。独立核对仓库生成包、本机实际挂载目录的33文件与发布清单、21运行回执的33文件哈希完全一致。最终OpenAPI为`8257566ac3103e6534b3499ddd40476722d5fef0b4f112998f7fe9efd7c93abe`，发布事实说明更新后，前述9字段和最新材料示例修正仍保持；校验585 JSON响应、3 CSV、26请求均通过。
- README、根交接、PROGRESS、HTTP服务/Swagger说明和实施计划当前入口为66操作/64实现/2对话暂缓，旧65/docs14仅保留在前批事实或旧合同参照。功能清单仍标探索保存恢复未实现；主调查31/41和模型质量NOT_PASSED保持，未以HTTP读取成功核销其他模块。

最终交付事实见[汇总回执](../../../../docs/operations/evidence/case-exploration-20261113-01/delivery-summary.json)。**无本项未解决阻断，可执行归档并记录归档后的CLI校验；本审计未代执行归档或Git操作。**

## 归档事实（主代理记录）

2026-11-13在最终独审ACCEPT后归档，5/5任务完成，新主规格case-exploration-candidates已创建并补齐Purpose。相对链接深度已修正；Totals: 33 passed, 0 failed (33 items)；Totals: 32 passed, 0 failed (32 items)。本轮没有执行Git提交/推送，未改写发布回执或原失败记录。
