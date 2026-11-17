# 第6步Case首轮执行与材料准备

2026-11-15，本机候选验证；分支V1.1，隔离PostgreSQL `v12_upgrade_dev`（129，32表521列），新专用Redis `socai2-case-initial-20261115`。未操作21/正式业务、未部署/提交/推送、不启旧消费者。按[本步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage6-case-execution-design-20261115.md)实施。

## 实际结果与来源

核心5个Case共5个task/attempt/Run：4 completed、1 capacity_exceeded失败；真实C1–C6和PG/Redis，10次明确模型替身调用（C3/Deep/C6），背景和日志查询亦为替身，**0真实模型**。另1个独立Case直接验证早期准备字节超限，1 task/attempt/Run失败，0生成调用。[只读最终回执](readback-02/result.json)与[补充容量回执](byte-capacity-01/result.json)通过；这些结果不判断模型正文质量，历史NOT_PASSED保持。

| 直接行为 | 保存与读回结果 |
| --- | --- |
| 受理与执行 | 受理时只登记initial task、0Run/attempt；调度实际执行后绑定独立Run、输入和策略工件，同任务读取结果 |
| 准备前与运行中新增 | 最终claim前新增纳入：Run固定2条；模型开始后再加1条：Case变为3条、Run仍2条，输入工件和摘要不改 |
| 时间与缺口 | 按可靠时间生成前后各1小时；缺时不造窗口、不查日志，C3/C6仍完成。相隔一个月的完整跨度由离线检查验证 |
| 日志条数/截断 | 测试配置75、Run政策200，实际SQL允许75并探测第76条；保存75行和1条overflow，标明截断、不虚构总量、不翻页。候选默认仍50 |
| 查询失败 | 明确失败回执保留，C3/Deep/C6仍完成，失败不被写成查空 |
| Token容量 | 预检拒绝时保存准备body/Schema/来源映射/计量，明确not_sent；0生成、程序收尾、Run/task失败、不入重试pending |
| 早期字节容量 | 测试替身将准备上限设为1，保留unsent_messages、全部成员和来源；0生成、失败收尾及Result可读，未改运行政策文件 |
| 队列与只读 | 总N=1，容量失败后下一Case完成；attempt均local_ended、Redis运行集合为空。任务/Run/Result/原件读取前后17类快照摘要相同 |

核心身份全部在[readback-02/result.json](readback-02/result.json)，逐案读回见同目录`*-readback.json`，[完整快照](readback-02/snapshot.json)包含源告警、材料、Case/成员、task/attempt、Run/步骤/原件/结果及采用。时间、额度、缺口在冻结C1和策略原件；后台查询参数不整包送模型。

离线直接组35项通过：本步准备和预检、既有分流及C3模型视图。复用的后续输入组另27通过/1失败：`test_history_duplicate_presentation_preserves_c3_and_final_dependencies`预期2份历史记录，实际选择0；去掉本次新增query_preparation序列化字段的对照仍失败。保留为后续历史夹具/映射问题，不将其写成通过，不影响本批正常输入→保存→读取。Ruff、OpenSpec strict及受影响文件diff检查见最终检查回执。

## 批次与失败原件

- `pg-01`：夹具导入缺仓库根路径，数据库连接前失败，0执行；修正后使用新pg-02。
- `pg-02`：5Case实际执行完成；导出脚本误将复合主键表按id排序而失败。只读保存任务/Run/结果事实，未重派任务，[原失败](pg-02/result.json)保持。
- `readback-01`：只读断言误用ended_at，实际字段local_ended_at；原错误和快照保留。
- `readback-02`：修正读取断言后，对原pg-02记录只读完成7组核验，0新增模型或业务写入，不改原失败。
- `byte-capacity-source-01` / `byte-capacity-01`：另一个新租户、新Case，专验早期字节超限，0生成。
- `http-source-01`：HTTP专用新租户的两条合成告警，当时0Case/task/Run；HTTP独占E01和consume.py，不混用核心结束批次。

核心驱动[validate.py](validate.py)，明确替身[controlled.py](controlled.py)，只读补验[readback.py](readback.py)，HTTP消费[consume.py](consume.py)。私密连接只通过忽略目录`.local/case-initial-20261115-01/verification.json`及引用文件加载；证据不保存密码或完整连接串。

## HTTP、展示与剩余边界

HTTP依[§8.19](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md)联验E01→task→Run→Result/步骤/原件，回执见[HTTP批次](../case-initial-http-20261115-01/README.md)。外部E11/E13在首轮闭环通过后退役；Case check/rerun留第7步，不因initial就绪而开放。内部prepare/claim保持，候选CLI不再提供case-prepare/case-start旁路。

`saved-export`为pg-02的5案保存快照，`saved-byte-export`为额外字节容量1案；均用update_processing_audit.py加入仓库静态查阅页，已有13条保持、核心导入后19条。随后导入HTTP独占1案保存快照，累计20条。实际4177仍为旧运行版本，没有部署或切换。静态快照不冒充后续测试服务/4177 HTTP实时联验。

双方确认无在途任务后已停止本批专用Redis，容器与数据保留；[停止状态读回](redis-final-state.json)为exited、退出码0。没有重新消费已结束批次。

第7步待接Case6小时检查、手动check/rerun、活跃事件跟随及上一轮比较。第8–10步按负责人决定后置，保留设计及未完成状态。第11步结合测试对话方案验证本期1–7步代表性真实模型/TCP/4177链，再做独立结束审计及获准统一发布；本步直接验证、ASGI或工件存在不等于最终验收已通过。
