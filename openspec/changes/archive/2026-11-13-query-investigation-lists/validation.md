# 三类列表查询验收

2026-11-13，三类列表实现、直接验收、发布前独立审计及两端统一发布已完成；下列实际读回通过，发布后限定复核通过并已归档，见audit.md。

## 实现范围

扩展 E26 告警、E27 事件、E02 调查三个 GET 列表，新增条件见 design。仅告警/事件封套增加已确认的 `filtered_total`、`next_cursor`，原行字段、整体统计、默认顺序和旧调用保持；Case 原 total/metrics 保持。数据库无迁移，不调用模型或启动 Run。

对外参数/错误适配位于 `investigation_http/external_routes/`、`errors.py`；只读 SQL 和与 HTTP 无关的查询 DTO 位于 `app/socai2/`。核心不导入对外包，不经本服务 HTTP 调用自身。部署在已发布 HTTP 边界版本上仅覆盖 list-query profile 列出的10个文件，保留并行模型修改。

## 直接证据

证据目录：[list-query-20261113-01](../../../../docs/operations/evidence/list-query-20261113-01/)。

- 定向离线检查：原 Case/Page 读取和 HTTP 边界检查14项通过；新增无效日期等真实ASGI错误适配1项通过。包括旧Case v1指纹的独立构造、未知等级置后、正反排序、三接口之外完整合同保持及核心不依赖对外HTTP包。
- [本机 TCP + PostgreSQL](../../../../docs/operations/evidence/list-query-20261113-01/local-http-02/verification.json)：117次GET，实际目标 `v12_upgrade_dev`；8告警、6事件、6Case、7成员关系。9种排序分别升降序连续翻页不漏重，查全量命中数、字面搜索、状态/等级/负责人/分配/日期、事件人工覆盖及同成员时间命中；与旧18024实际响应和v1游标比较兼容。服务无依赖替换，查询前后SQL目标行完全一致。
- 第一份样本计划因复用成员告警违反唯一约束回滚，确认四类目标行均为0后使用全新批次；原意图和失败保留在 `seed/failure.json`。不修改旧批次追认成功。
- 第一轮HTTP发现倒置时间区间的校验异常携带 datetime，JSON错误响应序列化为500；已在对外错误适配中省略无必要的input字段，恢复JSON422。保留 `local-http/failure.json`，补三类列表无效输入回归后复验117请求通过。

这是查询功能验收，不是模型正文质量、自动消费或页面接线验收。完整CSV导出、统一归并统计与跨设备列偏好不在本change。

## 文档及发布

Swagger docs8保持53操作/125功能/三类分组，固定输出字段出现位置540→542；E02/E26/E27补参数、时间含义、排序、总数、分页兼容和422示例。发布前独立审计已通过；修正功能清单分页用法、排序缺值表述、Case读取403和旧before_id不存在404，448个响应示例符合Schema。


| 实际发布 | 结果与证据 |
| --- | --- |
| 本机18024 | `list-query-20261113-r1-local`，ARM64原生Python，PID35101；冻结源为普通项目目录中的list-query版本。30次GET、三类样本SQL逐值一致；reader postgres / writer v12_developer，同为v12_upgrade_dev。候选18026已停止。 |
| 21:18024 | `list-query-20261113-r1`，AMD64镜像 `sha256:bf0b7beb96d72b25bc92e31da4eae631e93dddc6fce9aaed0954779dd2275bbd`；reader aisoc_app / writer socai2_prod_processor，同为aisoc。50次GET与既有3告警/3事件/1Case及3关系的SQL逐值核对，发布前后完全保持。 |
| 实际源码与其他服务 | 两端10个覆盖文件逐一核对当前源码摘要；21除API与Swagger外其他容器ID、镜像、启动时间保持。原主API、处理服务及消费者未变。 |
| 两端18080 | docs8，53操作、50实现/3预留、125功能、542固定字段/28动态结构；9个入口均200，完整HTTP响应摘要相同。本机aarch64、21 x86_64，既有Swagger镜像保持。 |

证据：`local-api-release.json`、`local-release-http/verification.json`、`local-sql-after.json`、`local-runtime.json`；`21-api-release.json`、`21-http/verification.json`、`21-sql-before.json`、`21-sql-after.json`、`21-runtime.json`；`local-swagger.json`、`21-swagger.json`和[文档发布回执](../../../../deploy/api-docs/deployment-receipt.json)。21未新建业务测试记录，没有模型调用；查询只读，不改变数据库表结构。

本批授权是实现与本机/21服务、Swagger同步；尚未Git提交/推送，前批远端和父项目引用不据服务发布自动改变。完整CSV导出与统一归并统计仍后续实施。

归档后的仓库导航链接已指向归档目录；已发布docs8静态包保留发布时快照，未为归档路径文字再次替换运行文档包。HTTP合同、参数、示例及其读回摘要保持。
