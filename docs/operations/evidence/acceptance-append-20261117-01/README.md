# 3c.2 首批：HTTP 接线失败保留

2026-11-17，本机独立批次 `acceptance-append-20261117-01`。不是 21 部署或历史数据恢复。

首段已发送并保存 **2 条上下文、1 条告警**。告警、事件两次真实分析均结束，2 Run、无 Case；CLI 在任务列表读取时收到 HTTP 503，原状态保持 `incomplete`。原因是本批本地 HTTP 环境遗漏 `SOCAI2_ANALYSIS_READ_ENABLED=true`。未重发本批，后续使用全新 [02 批](../acceptance-append-20261117-02/README.md)。

- [原执行状态](prepared/runs/part1/state.json)、[503 请求及回执](prepared/runs/part1/http/00003.json)。
- [结束后只读快照](stopped-batch-records.json)、[收尾摘要](closed-batch-summary.json)：A/I 已完成、无在途，2 次模型均 stop，共 4013 tokens；费用未知。
- [模型输入输出](model-io/index.json)，沿保存原件导出，未再次生成。
- [准备时租户不一致拦截](setup-attempt-01.json)、[本地 TLS 配置修正](startup-attempt-01.json)均发生在业务投递之前。对应原错误不追改。
- [本批进程停止](stopped-processes.json)；共用的本轮专用依赖在 02 验收后[停止](../acceptance-append-20261117-02/cleanup.json)，数据库、Topic、湖记录、Redis 分区和证据均保留。

本批不能用后来的 02 成功回执补成 completed，也不作为可追加会话。
