# Investigation v2 — 独立开发线

旧版源码、入口、工具注册及配置保持原样。新功能在本包新增/修改，需要改旧函数时复制所需实现后在新版调整；只读复用稳定库能力。

本包没有注册到旧服务。`query_api.create_app`提供独立应用，仅接受`POST /api/v2/investigation/query`，复用原认证及`lake:query`权限，调用本包dispatch；不启动schema、worker或模型。API只负责认证tenant和全局查询边界，Run/问题scope和共享预算由可信Agents caller/M3校验，不能当正式M8持久启动授权。

可在自己的API依赖环境显式使用`uvicorn app.investigation_v2.query_api:create_app --factory --host 127.0.0.1 --port <local-port>`，另配本机最小只读PG/CH身份、CA及临时服务token；不要提交凭据。2026-10-24独立进程的1次真实查询接缝及清理已验，公开回执在`docs/operations/investigation-v2-query-seam-20261024.json`。进程已停止，未部署；完整循环、同版交付、Case衔接及正式业务入口尚未完成。新版运行须独立进程/配置和测试输入输出身份，不自动回落旧版重跑未知调用。

主方案：docs/architecture/investigation-planning-design.md 第1.10节；当前证据：docs/operations/unified-investigation-implementation.md 顶部。旧冻结回执指历史位置，搬迁后以新路径及直接测试记录为准。
