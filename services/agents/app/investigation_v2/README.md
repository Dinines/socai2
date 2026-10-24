# Investigation v2 — 独立开发线

`FixedReconRuntime`/`ReconExecutionStore`为M6.2固定路径：可信caller先创建新Run，begin冻结计划/版本，execute只在本次确认claim后通过M3 gate查一次并保存候选交接；重复不重查，取消/unknown不释放或接管。当前c已在新Run实际独立PG/HTTP/CH完成一次查询与5事件10工件读回，repeat/cold同交接不重查；112合同及probe独审15通过，真实结束独审限定ACCEPT/0必须修；候选不是M7发布或人工已接手。当前回执：docs/operations/investigation-fixed-runtime-seam-20261024.json。

`recon_material.prepare_alert_recon`为A3纯材料准备：正常返回实际EvidenceView文档及M6.1有限结果；仅在必要校验已通过的投影阻断时返回保全部refs/真实source状态的partial，无虚构视图/新事实。持久保存未尝试，view_ready也不替代I2完整messages门。A2结果携bounded_full_window_source_check.v1及目标/请求/确认/遗漏窗口。回执：docs/operations/investigation-material-projection-20261024.json。

地址身份使用`network_identity`：IPv4与mapped IPv6同一身份，原生IPv6压缩；scope/caller/证据参数/Deep指纹同规，SourceField仍保原值和出处。A1新增8＋相关103合同及独审限定通过，回执`docs/operations/investigation-network-identity-20261024.json`；不修改留存响应/hash，不证明真实服务或完整M6运行器。

旧版源码、入口、工具注册及配置保持原样。新功能在本包新增/修改，需要改旧函数时复制所需实现后在新版调整；只读复用稳定库能力。

本包没有注册到旧服务。2026-10-24已用本包受限caller/M3接独立API v2进程，1次真实查询与3事件/6工件独立读回通过，见`docs/operations/investigation-v2-query-seam-20261024.json`；模型0，profile仅作为已核输入留存。完整问题循环、Case衔接及正式业务入口尚未完成。新版运行须独立进程/配置和测试输入输出身份，不自动回落旧版重跑未知调用。

主方案：docs/architecture/investigation-planning-design.md 第1.10节；当前证据：docs/operations/unified-investigation-implementation.md 顶部。旧冻结回执指历史位置，搬迁后以新路径及直接测试记录为准。

`fixed_recon.evaluate_alert_recon`为M6.1查询后的纯政策层，接已核alert业务绑定、当前EvidenceView/引用和可选已观察停止原因，产program有限事实、六问题及停止交接。13新＋35相关合同通过；仅有限来源核对可ready，性质/授权仍未知。所有输出不授权新查询/模型，不发布Run完成；停止原因实际来源、M3 gate、查询去重及持久交接在M6.2另验，不能将本层当完整M6运行器。回执：docs/operations/investigation-fixed-recon-20261024.json。
