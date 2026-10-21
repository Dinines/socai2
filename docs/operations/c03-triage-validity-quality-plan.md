# C03-02D-02：v5检测有效性与时间授权的新对照验证

2026-10-21。执行前冻结卡。按用户持续迁移授权推进，先完成D1公开交付及本批独立准入审计，再依次执行；本卡建立时尚未执行本批freeze/provision、业务输入、HTTP或模型。旧02、02B、02C02三批质量失败、原判据和七条未执行输入保持，不重调旧例。

## 父版本、输入和判据

父[D1](c03-triage-detection-validity.md)仅对v5提示词、88项直接测试、4个断网SDK和部署限定验收，不能作为模型遵循证明。镜像固定`sha256:9cb719ff55d772ebf047f87a06863ae7102feb5be3b9471610113dd9d85728fd`，27 Compose/24源码层、Agents184及四服务769 Py和独立lock。本批0源码/prompt/schema/路由变更、0构建/重启/DDL；worker、graph、审批和记忆写回继续OFF。

父seal SHA为`3999189db4c42b0ca9a7d54e59a049996030a7744c8e15c63f02848deadc355f`；部署前、实际运行及收尾独审分别为`3c71169fcf85a4048e5d1e230bc11b54362e115c9551c9e35ed209d441013dd5`、`b1e4bbe79438a5c95181600d465c29a8757da01383235ab292cca79ab6053c76`和`215e4fe5d8312e796514fac11efcd442f44fd3b7d15f19380cc2c5ad04b06ed2`。freeze须再核实际父及公开来源对应，使用新真实只读before，不将父after文件复制成新观测。

新输入为[c03-triage-validity-quality-inputs.json](c03-triage-validity-quality-inputs.json)，SHA`e80c04a5e9d2bc18b526c197af9b6e9ab8cbc5966e2615dca274e12b3949e3c2`，A三/B一，新UUID、source、rule、host/account。分离的private rubric SHA为`07e944d4c43d7d93ef1968a4316f74efc20565aa1c2b406202b9aa92797443b1`；相对已审草案只移除过时父状态标记，四例与common判据不变。rubric不放source目录、不挂执行容器、不提供给模型；输入没有expected/评分标签。

四例分别检验有明确检测反证的FP、完整范围授权及跨日offset的BTP、检测谓词无法核查且维护范围不足的NR、event早于授权窗而created在窗内的NR。分类与短理由分别独审；自报时间/数值须正确，缺证不能推断误报或不存在批准。本四例没有TP，不宣称v5 TP已复验；后续常驻新TP须实际模型及独评通过才满足该窗口条件。

## 保护基线与资源

父10预约/200000固定预留单位、3旧unknown，A7/B3行，十枚按用途分离reader及其映射保持。旧unknown不退款、不重发、不删除；主group的历史无提交及A旧积压保留。保存项目PG备份、必要private配置、36容器/18卷/134迁移、旧14表及Case/source-link/QA、预算、主/raw/六预算组和三个旧quality/DLQ元数据。

当前policy A7 calls/140000单位/max_unsettled3、B4/80000/2、window86400。本卡只加A三call/60000容量至A10/200000/3；B保持，使用原未用的一槽。本批最多4新预约/80000单位，单位不等于tokens或费用，旧3unknown始终占未确认槽。以freeze时PG时钟和实际policy复核，不借滑窗或清理腾额度。

| 对象 | 上限 |
| --- | --- |
| 真实模型 | ≤4次SDK发送，每例≤1，串行，retry0/整次45秒/输出512；无重试或fallback重发 |
| 数据 | ≤4新Alert/Run/预算/成本/shadow，≤12事件/28工件；原QA策略保持、≤4pending QA，QA关联缺口仍未修 |
| broker | 2新单分区topic、1group、初始commit0；≤12发送尝试及≤12正常交付边界，失败/重投也计；raw推证slot与直接物理yield分开 |
| 观测 | 显式真实HTTP≤240，SDK Mock另≤4；共享sequence不重复计，host SQL与独审读取分列，不称全内部流量计数 |
| 身份 | 3新≤3小时操作key，最终停用并逐枚实际API401；0新tenant/reader，原十reader保持 |
| 运行 | 同固定镜像fresh临时worker使用实际五reader、LiveWriter/ShadowPolicy/BusinessContext；0常驻启用、真实响应、外部通知或共享服务重启 |

新topic为`socai2.c03.triage-validity-quality.20261021`及其`.dlq`，group为`socai2-c03-triage-validity-quality-20261021`。旧02、02B、02C02 quality组分别end/commit1、1、3及DLQ0保持。旧主group和六预算组提交保持；本批临时算子不提交旧group。**真实Fusion处理本批新raw时允许对应分区提交精确前进**，不能将raw全部提交不变当作验收要求；其他raw分区及历史事实保持。元数据检查不subscribe/assign/poll/getone/getmany/commit，不冒称消息回读。

## 执行与停止

仅用新`prepare/run/acceptance/snapshot/finish_triage_validity_quality_c03.py`。quality算子只导入本批prepare/runner及纯基础helper，不导入旧quality模块来取常量；新计数hooks仅属新E。每phase独占started/command/exit/accepted，失败原件保留，禁止自动循环或故障后盲重做。

1. `freeze`：父关闭门、source/lock/OFF、真实before及项目备份，准备private身份和policy候选，无PG key写/模型/输入。`snapshot`另冻Case/QA、raw/main、三旧quality/DLQ及Fusion metrics；UID10001/networknone/SHA+AST只读算子可读探针先于业务。
2. 独审后`provision/topics/authorize`：一次限定key事务及A容量更新，建本批2topic/1group空commit0。独立pre-exec审计绑定全baseline、输入与算子SHA，后续才允许业务phase。
3. 单例`ingress`：真实HTTP→raw/Fusion→PG/fused，绑定canonical Alert、incident、tenant、source和ack。发送不明只回查，不重复POST/publish。
4. 单例`preflight`：实际五reader、v5完整safe-call/egress/生产SDK Mock，无Invocation/claim/Run/预约，CostTracker persistFalse；完整messages≤8000 literal字符/16000规范UTF-8字节。独立核实际材料、nonce规范fact/request和传输，不用Mock评分。
5. 单例`invoke`一次：原fused信封到本批topic，实际live worker→预算→SDK→原策略→持久产品。只存可见body、短content/usage/finishreason，不存headers/key、隐藏推理或完整provider body。
6. 单例`verify`：PG/API/offset和Run、Alert、五源工件、成本/usage/预算关系；独立rubric评分并写绑定输入/completion/rawanswer SHA的gate。前例gate未accepted不发送下一例。
7. 任一unknown、长度/schema、来源漂移、分类或理由失败，立即停后例。已收到但不合schema的回复不是unknown，保生产原处理与独立拒绝。按实际passed或stopped执行`finish inspect`→独审→`revoke`/三401→收尾独审→`seal`，保原失败、预约和offset；不重调追分。

仅本四例全过才称限定新对照质量通过；不能称全taxonomy、统计质量、真机授权或常驻准入通过。美元费用未知保留null，预约单位不作实际usage；模型与原始权重身份仍按既有43服务的已知边界。公开封包、来源/数据保留及本轮独审完成后再进入下一单项。
