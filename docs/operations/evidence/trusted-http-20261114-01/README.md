# 内部可信HTTP：本地步骤验收

负责人2026-11-14明确确认：接口也去掉校验，默认内部可信。本轮按[OpenSpec设计](../../../../openspec/changes/trust-internal-investigation-http/design.md)只完成第1步；未切换正式本机/21的18024或在线Swagger，未提交推送，也不据此归档整个change。

## 实现与来源

独立应用不挂载登录接口，不调用Bearer/Token/角色依赖；直接加载SOCAI2_HTTP_CONTEXT_FILE中的tenant_id、actor_id、actor_name。该身份用于数据归属和操作记录，保存的名称明确是“业务后端（内部可信）”，不是已认证的调用者。旧主API对复用路由的原依赖仍在，调查核心、组件客户端和消费者未改。

候选从已发布investigation-sync-20261113-r1运行目录复制，仅叠加identity.py、runtime.py、main.py和本机上下文配置，原始测试摘要见patches.json；不携带11-14正在开发的调查修改。本机和21分别准备自己的上下文，21配置仅准备、未发布。

## 直接结果

- 5项定向检查通过：保留对外/内部依赖方向及旧业务合同；无Token查询、records/cases内联路径及执行端口得到配置tenant/Actor。执行端口用替身，不运行模型；原主API装配保持。Ruff通过。
- management/：真实TCP、真实隔离PG共20次请求，所有请求只有Content-Type，无认证头。新建1个Case及1个人工任务，修改/幂等/旧版本409/参数422、未完任务确认、关闭/重开、活动读取通过，Run仍pending_update且未启动。
- direct-check.json：无凭据追加读取告警及Case关联、Case/活动；SQL核tenant、created_by及标题与HTTP一致，记录操作人名称来自配置。无模型调用、无生产业务写入。
- candidate-openapi.json：原71业务操作输入输出不变；删除5个登录路径、5个仅认证使用的Schema，运行Schema从153到148。不含security或securitySchemes。
- docs-check.json：docs20-candidate保持71操作/125功能（22/15/88）/162文档类型/764固定字段。27请求、495 JSON响应、3 CSV示例通过；相较上一版减少142个通用认证/权限错误示例。业务数据关联错误保持，不当成Token或角色要求。

## 初次检查与修正

旧边界检查最初仍把已确认删除的登录/security算作必须保留，失败1项；明确仅规范化这次认证增量后5项通过。只读补验最初误读Actor.name，实际合同为name_snapshot；修正脚本后只读复验，未重派20次写入。文档生成首次直接使用运行OpenAPI路径顺序，旧生成器以固定顺序分配E编号，因此示例KeyError；按旧合同顺序排列业务路径后通过，未改变任何运行路径或DTO。首次Ruff三处导入/导出排序已修正，最终5项检查再次通过；格式修正未改变行为，原候选功能回执及摘要保留。

## 未完成

当前正式两端仍为investigation-sync-20261113-r1/docs19；仓库交接已明确可信候选和未发布状态。后续第2步为统一交付：独立结束审计、获准环境的API/Swagger发布、实际配置与既有数据读回，再归档。主调查31/41、质量NOT_PASSED和AI对话暂缓保持，不进行权限专项或模型采样。
