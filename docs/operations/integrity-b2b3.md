# B2/B3 人工调查首轮实测：技术链通过、报告质量未过

2026-10-21。沿 `restore-alert-investigation-integrity` 的B2/B3及I2执行；本记录不勾选整个人工调查、知识引用或整体迁移完成。产品由api_auth_review、triage_review实现，root部署/实测，源码交叉审计及实际内容独审由未参与对应实现者完成。

## 修复与运行

Case/Run租户归属不再依赖临时baseline开关；默认调查读取Case真实关联Alert及实体，使用既有租户reader，缺源/失败与合法空结果分开。默认四节点共用一次既有PG全文KB读取，并记录确切片段、来源和各模型实际引用。I2正常graph用量原子追加，普通完成不再用默认0覆盖已有汇总。

初轮I2的79项漏掉普通SQL状态实际更新断言，随后PG日志发现死CASE参数类型错误，其充分验收结论撤销，旧结果保留。最小修正并强化状态/iterations/error/完成时间及tenant断言后，冻结candidate02组合232项Agents与未变API25项，共257项通过；隔离PG无该参数错误。candidate01仅构建、未部署。

candidate02仅替换API/Agents，镜像分别为`1be37c38…`、`9f74c4a8…`；Fusion B1 `c52b9aac…`及其他容器保持。实际771个运行Python与冻结清单逐hash相符，API/Agents/Fusion相对各父版只变1/17/2文件，0删除。API补配既有Agents专用服务身份，未轮换旧reader；七只读bind、60秒宽限、worker OFF、review_only_v1及审批/自动graph关闭保持。见[运行审计](../handoff/integrity-candidate02-runtime.json)及[固定候选来源](../handoff/integrity-20261021-source-manifest.json)。

## 实际输入与结果

受控A租户新source-v1告警`5e34df71-4bd3-582f-8d17-895e05c36671`经HTTP→raw→Fusion→PG，关联新Case `efbdb359-8c50-41a6-9c4f-b79d0559bafd`。另建同租户空Case仅核错绑拒读，不启动第二次调查。主Case只POST调查一次，Run为`7bc46722-c6bb-41d2-b786-2178b3b82608`，未重调旧输入、unknown或积压。

- API服务身份→Agents及Case/Run归属通过；四节点均真实回复，25条持久事件seq0—24、一份MD工件。4次模型8062 tokens与Run、三行模型成本共4调用完全一致；4调用均unpriced，费用未知。
- 从旧知识源只读摘取带STIX/hash来源的ATT&CK T1110.003背景段落，正确A租户KB文档`351c3e7d-008a-4bd4-805a-a2bca754cad1`经真实PG全文查询召回。一次读取的nonce块SHA为`71777505360635a59600980839b9832c54c5e95c1c1de73328512fbbbd9900e0`，逐字进入四份实际prompt；四模型均无KB marker引用，不能计引用质量通过。准备时曾误用无reader映射的1F租户导入一份相同参考，返回not_configured；该失败和新增资料保留，未发模型，后改用已有五类reader的A租户。
- MD及Agents HTML均200；MD正文与PG工件及SHA一致。HTML当时只在进程态，不据此声称已经持久。B租户的Case/Run/工件/报告、错误Case及服务身份代B共7项拒读均404，无结果泄露。
- PDF实际500：WeasyPrint缺`libgobject-2.0-0`等原生依赖。随后仅构建依赖候选并在无网络、uid10001临时容器渲染同一HTML成功，尚未据此认定运行PDF修复。首次私有0600输入挂载权限失败及修正副本后的探针均保留，原输入不改。

## 正确性失败与后续修复

独审拒绝本报告质量：测试材料的migration/fixture字样进入模型并污染判断；Recon把KB中的常见口令定义当本案事实，Forensic把失败增强当已取证观察，并由缺证推断已授权/无危害，后续报告进一步放大。动作仍dry-run，告警未被自动关闭；不能称发生了真实响应。

报告末句截断，实际输出1024 completion tokens，与当时本地配置上限1024相符；旧事件未记录provider finish_reason，不能断言已观测到length终止。后续最小修复：失败增强不作证据、四默认prompt明确事实/假设/未知、传递真实timeline和行动内容、按实际length状态标失败并保留可查fallback，不自动重发模型；补PDF依赖，运行上限回到原默认2048有界。另用不含结论提示的新输入，旧Run及失败判据保持。

官方声明、实际接通及上游差距见[功能对照](alert-function-alignment.md)，二开关系见[架构](../architecture/alert-processing.md)。原始请求、事件、模型可见材料和报告留在21受控`private/completion-integrity-20261021/b2b3-*`及本地忽略目录；公开机器摘要见[JSON](integrity-b2b3.json)。可用性专项、playbook/反馈额外改测仍后置。

收尾侧注：B1两枚临时操作key已停用并逐枚真实401；后续人工/自动功能验收的两枚操作key暂保留，旧十reader不变。运行审计中一次命令曾误展开inspect字段，已保留该操作失误记录并改为白名单/布尔输出；未复制到文档或Git，未外发或擅自轮换旧凭据。
