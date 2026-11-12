# 本轮直接验收

## 范围与结果

2026-11-12，`V1.1`，基线 `4d46f4d46a2b65539bf17bb200fa6ba85a28c7a4` 加本工作树增量。本地功能通过，21 已一次统一发布并读回；模型质量 NOT_PASSED。本轮不修改告警交接字段，无调查 DDL。

核心证据：[本地摘要](../../../../docs/operations/evidence/historical-knowledge-20261112-01/local-summary.json)、[执行](../../../../docs/operations/evidence/historical-knowledge-20261112-01/local-flow/execution.json)、[保存/读取](../../../../docs/operations/evidence/historical-knowledge-20261112-01/local-flow/export/verification.json)、[12 项直接检查](../../../../docs/operations/evidence/historical-knowledge-20261112-01/direct-checks.xml)。

## 实际路径

1. 本地 PG 的独立历史演练来源由 fixture 明确构造；KB 入库、重复入库、索引、完整卡片 GET 使用原 HTTP 路由和实际 PG/Qdrant/本地嵌入。人工与分诊均是测试输入，不能冒充真实业务历史或授权。
2. Case `20bff447-7e9e-5cd0-8081-9c348f3cf8c3`，唯一 Run `306f930e-7788-479f-9109-ee62b45eccb1`，三条 C02 原材料在独立身份上保持。正常 Case HTTP 创建、start、Run/Result/Case GET 均成功。
3. C2 三目的各 3 查询，共 9 查询、7 非空/2 查空、10 命中。历史目的返回 2 行，同一张卡 `91f7daf1-fb43-5812-aea9-1300fa94eb0d` 被两个查询命中；历史记录主体始终 `a788edb4-74bb-58a3-8ba5-f6698a0766de`，不能当作两份独立历史证据。
4. 共 5 次真实分析请求（C3 首次及现有纠正、两个 Deep、C6），98,629 reported tokens，费用未知。每次实际请求均有历史卡片的 6 个来源别名（2 命中 × 卡片/分诊/人工），分诊及人工原文保持，`alert_ids=[]`、`record_alert_ids` 为原历史告警。
5. 5 份原答的 source_ids/evidence_ids/support_ids/counter_ids 数组均未引用历史卡片/子字段。Deep seq16 正文提及 N3_S96/N3_S103，C6 正文提及 N4_S96/N4_S103；属于正文提及，没有结构化引用关系。证明信息已进入输入，尚未证明模型合理采用或改善调查结果。历史参考也命中登录主题，召回相关性仍须单列，未因非空命中宣称有效性提升。
6. C3 首次 `source_member_mismatch` 经原有一次纠正后通过；两个 Deep 为待核实交接；C6 `recommendation_needs_sources`，Result `partial/rejected`、`conclusion=null`，当前判断未采用。错误、原答和后续未执行纠正均按实际保存，不重采样。
7. 4177 本地静态站追加为 66 份。实际浏览器在临时本机 4188 查看同源页面：历史目的时间范围/排除成员，原卡片/分诊/人工输出，查空，模型输入可见/未见结构化引用及 C6 真实错误均成立。原本机 4177→21 转发保持。

## 直接检查与限制

- 既有两目的 6 项检查、历史卡片/角色/过滤 5 项、既有 C3 冻结角色 1 项，共 12 通过；只核本次直接行为，替身部分不视为真实模型。
- 受影响代码 Ruff、4177 JavaScript 语法通过；OpenSpec strict 通过。不重跑全仓、压力、故障恢复或权限专项。
- 真实链路中 DB/向量/嵌入/模型为实际组件；认证和模型传输沿原本机适配，历史来源是明确测试 fixture。没有生产分析模型、厂商或自动消费验收结论。
- 前置测试材料 JSON null 违反既有 enrichment 对象约束，事务回滚后修为对象；[失败记录](../../../../docs/operations/evidence/historical-knowledge-20261112-01/fixture-preflight-failure.json)保留。第二次重复入库后证据脚本排他写同名累计回执失败，已保存卡片不重建；[修订记录](../../../../docs/operations/evidence/historical-knowledge-20261112-01/local-flow/driver-correction.json)注明继续读取/索引的精确范围，未触发模型重跑。
- 业务来源/配置冻结在 `plan.json` 与 `knowledge-source-sha256.json`；证据脚本修订单独核 hash。12 项检查不替代正文质量，M01-A/M01-B/M02 与 F02 未核销。

## 发布验收

本地独审 ACCEPT 后发布 `v1.2-20261112-r1`，API 与工作台各切换一次。处理镜像为 `processing-20261112-r1`，源码及配置按冻结 manifest 验证；[最终读回](../../../../docs/operations/evidence/historical-knowledge-20261112-01/release-readback.json)核实发布指针、知识三目的配置和四项继承容器身份。

- [生产 HTTP](../../../../docs/operations/evidence/historical-knowledge-20261112-01/production/http.json)：指定已有演练告警生成卡片 `5837d5c7-2c53-53dc-9923-d75487f25c46`，入库、索引、GET 共 3 次成功。原告警、材料和分诊均保持，没有生成新模型结论。
- [历史检索](../../../../docs/operations/evidence/historical-knowledge-20261112-01/production/retrieval.json)：一次只读 adapter 查询返回同一卡片；这是显式探针时间范围，不冒充生产 Case Run。0 分析模型、0 Run 写入。
- [静态发布](../../../../docs/operations/evidence/historical-knowledge-20261112-01/static-publication.json)：以实际远端 37 份为基线追加到 38 份，76 文件/77 HTTP 内容读回，已有记录与文件保持，没有再次重启工作台。原根文档 36 份是前批快照，未改写前批回执；本次没有对额外既有记录推断业务结论。
- [临时凭据撤销](../../../../docs/operations/evidence/historical-knowledge-20261112-01/credential-revoke.json)：本批 key 已停用且 GET 返回 401，账号角色不变。
- 首次上传因本机沙箱拒绝 SSH，未触及远端；获得工具权限后上传成功。首次 activate 在 `service_not_ready_workbench` 停止，源码确认检查先于指针修改；工作台健康后仅重做激活核对，没有重发 rollout。两个失败回执保留。会话中断后先读实际状态再续做，未重复入库或模型调用。

发布补审见 [release-audit.md](release-audit.md)。业务源是明确的历史演练告警；本地与生产接线通过均不证明真实业务授权、历史经验正确性、召回或模型合理使用。M01-A/M01-B/M02/F01/F02 保留。
