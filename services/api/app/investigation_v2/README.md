**2026-10-28多告警分析：** case_synthesis提供逐成员判断、关联引用校验、来源时间线和未决问题，接入case_analysis的现有输出及报告。[字段和验证](../../../../docs/investigation/multi-alert-synthesis-20261028.md)。

**2026-10-28产品Tool：** case_product_tools绑定选定告警的精确CrowdStrike连接器，以现有Actions HTTP读取当前主机详情；Case预览、模型循环、证据及报告已接通。[合同和验证](../../../../docs/investigation/product-host-tool-20261028.md)。

**2026-10-28告警/事件关联：** application:create_app组合当前告警、事件、Case、成员关联和query路由，不依赖旧program网关配置。新增alert_context_api、事件investigations GET及include_investigations手动概况参数；[接口与范围](../../../../docs/investigation/alert-event-investigation-links-20261028.md)。

**2026-10-28 Case初版：** case_analysis_api新增材料预览、步骤列表/详情、报告下载；investigate支持previous_run_id追加问题及refresh_queries跳过历史查询复用。使用原ledger，无新迁移。当批范围从已有Case开始，F5不属该批目标；[接口与调用例子](../../../../docs/investigation/case-first-version-20261028.md)。

**2026-10-28：** 新增case_links_api的成员转Case及关联读取、case_history的新版Case历史列表，均注册到Case独立factory及program_result/start组合。需要迁移121（尚未执行），[实现与5项直接验证](../../../../docs/investigation/case-linking-20261028.md)。

**2026-10-27当前路径说明：** F1/F2 Incident及F3 Case已在本包实现。F3由本API进程直接执行模型/查询循环，使用自己的Case路由和原ledger，不走旧fixed/program结果网关或Agents M3。完整接口/数据/验证边界见[当前实现详解](../../../../docs/investigation/current-implementation-reference-20261027.md)，文档与证据见[审计导航](../../../../docs/investigation/audit-guide-20261027.md)。下方旧阶段“下一步/仅query”等按原记录解释。

`program_result_api.create_app`是新的显式兼容读factory，独立COMPAT_READ_URL/TOKEN，只读known fixed/program DTO，旧factory保持。原Bearer前置及cases/alerts双read权限、当前tenant/user_id转发；完整manifest/execution/candidate/材料版本与hash校验，1MiB有界后解析/单GET无fallback。105直接/独立、8hash/34离线回放限定通过；未知数量/范围保null，不混原声明与确认状态。回执docs/operations/investigation-compatible-gateway-20261025.json；仍无实际部署或启动入口，双进程离线组合d4与a4.2准入后续。

# Investigation v2 — 独立开发线

`result_api.create_app`是显式独立v2 query＋结果GET factory，复用原认证/双read权限且新GET强制Bearer无dev旁路；`ResultReadGateway`只向显式backend单次GET，核身份/manifest/MD/exec同版hash，不转外部凭据或写入口。33直接/独审和12 ASGI重放通过，真实两进程/PG后续；旧main/router未注册。回执：docs/operations/investigation-result-gateway-20261025.json。

旧版源码、入口、工具注册及配置保持原样。新功能在本包新增/修改，需要改旧函数时复制所需实现后在新版调整；只读复用稳定库能力。

本包没有注册到旧服务。`query_api.create_app`提供独立应用，仅接受`POST /api/v2/investigation/query`，复用原认证及`lake:query`权限，调用本包dispatch；不启动schema、worker或模型。API只负责认证tenant和全局查询边界，Run/问题scope和共享预算由可信Agents caller/M3校验，不能当正式M8持久启动授权。

可在自己的API依赖环境显式使用`uvicorn app.investigation_v2.query_api:create_app --factory --host 127.0.0.1 --port <local-port>`，另配本机最小只读PG/CH身份、CA及临时服务token；不要提交凭据。2026-10-24独立进程的1次真实查询接缝及清理已验，公开回执在`docs/operations/investigation-v2-query-seam-20261024.json`。进程已停止，未部署；完整循环、同版交付、Case衔接及正式业务入口尚未完成。新版运行须独立进程/配置和测试输入输出身份，不自动回落旧版重跑未知调用。

主方案：docs/architecture/investigation-planning-design.md 第1.10节；当前证据：docs/operations/unified-investigation-implementation.md 顶部。旧冻结回执指历史位置，搬迁后以新路径及直接测试记录为准。
