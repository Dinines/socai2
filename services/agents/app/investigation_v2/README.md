# Investigation v2 — 独立开发线

旧版源码、入口、工具注册及配置保持原样。新功能在本包新增/修改，需要改旧函数时复制所需实现后在新版调整；只读复用稳定库能力。

本包没有注册到旧服务。2026-10-24已用本包受限caller/M3接独立API v2进程，1次真实查询与3事件/6工件独立读回通过，见`docs/operations/investigation-v2-query-seam-20261024.json`；模型0，profile仅作为已核输入留存。完整问题循环、Case衔接及正式业务入口尚未完成。新版运行须独立进程/配置和测试输入输出身份，不自动回落旧版重跑未知调用。

主方案：docs/architecture/investigation-planning-design.md 第1.10节；当前证据：docs/operations/unified-investigation-implementation.md 顶部。旧冻结回执指历史位置，搬迁后以新路径及直接测试记录为准。

`fixed_recon.evaluate_alert_recon`为M6.1查询后的纯政策层，接已核alert业务绑定、当前EvidenceView/引用和可选已观察停止原因，产program有限事实、六问题及停止交接。13新＋35相关合同通过；仅有限来源核对可ready，性质/授权仍未知。所有输出不授权新查询/模型，不发布Run完成；停止原因实际来源、M3 gate、查询去重及持久交接在M6.2另验，不能将本层当完整M6运行器。回执：docs/operations/investigation-fixed-recon-20261024.json。
