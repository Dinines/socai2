# 3A-11-01：剩余准入阻塞只读复核回执

2026-10-20，批次`3a-admission-review-20261020`。已完成[固定范围](3a-admission-review-plan.md)的只读复核，**完整质量及常驻worker准入仍未通过**。[机器回执](3a-admission-review.json)、[审计程序](../../deploy/aisoc21/audit_triage_admission_3a.py)。本批没有运行源码、prompt、配置、schema、凭据或offset变更，没有重启、发布/消费消息或调用真实模型；新增的是证据和文档。

## 实际输入与检查结果

旧3A-09的162份原始文件hash全部保持。p01实际发送prompt给出`2026-10-20 11:01:15 UTC`现场行为、组织记忆的`02:00 UTC`备份惯例及“核实当次job”，模型却称行为发生在approved窗口，又把无匹配job当成确认未授权。直接破坏行为支持原TP判据；两句理由仍不受支持。没有窗口结束时间，不能在后续代码中擅自补成固定时长或只看小时差就宣称当前授权成立/不成立。原分类3/3、理由仅2/3得到支持的审阅及原5223 tokens保持，未新加judge或真人评分。

在当前Agents生产镜像中，将原理由交给现有`score_groundedness`，得到score=1.0、grounded/hallucinated均空：它没有提取到任何受支持类型的IOC。再用原TP调用worker gate，原verdict/.92保持、indicator score为null，因该gate只处理可自动关闭分类；将verdict改为BTP的**反事实接缝探针**仍保持BTP/.92、score=1.0。后者不是新模型输出或质量样本。现有IOC、KB标记和工具出处检查都不能据此被称为时间/授权语义检查。

当前四服务健康、36容器/18卷保持。API439及Agents184个Python文件与本地源码逐文件hash一致，Agents仍为`triage-budget-3a-20261020`，API仍为`triage-request-3a-20261020`；21层运行定义、19源码差异层未变。SDK仍retry0、45秒、输出512。五类reader映射在UID10001可解析，十枚reader的受控文件hash与PG scope/active/expiry元数据和上批相同；本批没有重新执行十类HTTP授权矩阵，不能当新的鉴权验收。

## 阻塞与所属路径

| 项目 | 本批实际观察 | 处理边界 |
| --- | --- | --- |
| p01时间与授权理由 | 已有prompt和输出冲突；当前indicator scorer不能识别 | 后续明确提示词时间/授权约束，另批新盲测；不靠分类正确或regex命中宣称语义质量通过 |
| 审批提案guard | 常驻`_approvals_enabled()`为True，`AISOC_AGENT_RAISE_APPROVALS`未显式禁用 | worker未启动不等于该guard为False；先显式置0，继续禁止自动执行。旧回执“审批OFF”过宽的表述由本条更正，旧文件不改写 |
| 常驻Kafka配置 | Agents缺bootstrap/TLS环境，production resolver拒绝默认PLAINTEXT；Fusion有bootstrap/SSL | 以往真实broker验收由隔离探针显式注入配置，不证明常驻已接；下一仅补配置，保持worker禁用 |
| 旧调查工具身份 | Agents/API的service token均不存在，Agents旧API key也不存在 | 五类专用reader不提供通用工具身份；本批只核配置/源码，未重测HTTP。专用graph reader也不补`ContextBundleBuilder(api_token=None)` |
| 旧增强与事件/UEBA | `enrich_ioc`仍指向未接的`enrichment:8082`；已有缺源回执保持 | Fusion本地IOC与五reader不等于旧工具可用；本批不新建来源或重查20历史数据 |
| 调查技能pin及引用 | pin缺失仍可能select当前头；KB标记能解析不代表引用支持具体结论 | 留在3B/质量准入，不扩展本批；无新模型、图或检索质量成绩 |
| 预算unknown与积压 | 三未知预约、A积压保留；没有证明无请求的证据 | 不按Run状态、TTL、DLQ提交或窗口经过退款/重算；不调大policy绕过unknown |

`_raise_approvals`只会为实际提出且需要审批的动作排队，worker结果固定`response_dispatched=False`；guard为True不等于已执行动作。本批没有调用该路径，也没有审计整个审批表或所有手工入口，不能据本批宣称历史上不存在审批记录。当前worker、graph升级、alert-trigger graph及记忆写回函数均False。

## 未知预约与积压合同

PG每次查询均在`BEGIN READ ONLY`/`ROLLBACK`内。14表材料hash、134迁移、预算完整行、Run/事件、reader元数据及policy前后相同；仍为67告警/37Run/92事件/106工件/21成本行。5份预约共100000固定准入单位，2份responded、3份未确认，observed_tokens五行均null；它们不是实测token或费用。

在本次观测的24小时窗口，A为calls2/40000单位/unsettled2，第三次会被unsettled上限2拒绝；B为calls3/60000单位/unsettled1，当前调用数/单位额度已满。窗口自然过期没有重新实测；所有时期的unsettled仍计数，不能假定到次日自动释放。完成Run的已存结果可在预算之前只读复用，但不能将unknown变成新miss。

| 旧批别名 | Run短ID | 当前产物/offset |
| --- | --- | --- |
| a_done | 88ea1135… | 仅开始事件[-1]，未确认预约；原group1/end1 |
| a_unknown | 77a2f558… | 仅开始事件[-1]，未确认预约；原group1/end1 |
| b_denied | b10ebbeb… | 仅开始事件[-1]，未确认预约；原group1/end1 |
| b_done / b_extra | 87e98b6e… / e0a60b02… | 完成、事件[-1,0,1]；各group1/end1 |
| a_denied | 无Run | group0/end1积压，没有发起本批处理 |

group前进是上批unknown确认DLQ后的既有事实，不证明取得模型结果，也不释放预约。本批仅通过现有Fusion的SSL配置，assign读取上述六组committed/end各两遍，没有poll、subscribe、join或commit；三条unknown未重放，没有改group或DLQ。保持该A积压，下一配置验收也只读取它。若将来需要人工处置unknown，须另有可核的请求/响应证据与显式处置合同；不能伪造responded/no_request、删行或自动退款。

## 失败、保持与下一单项

首次探针错误地断言所有guard为False，在实际approvals=True处停止；原程序与结构化失败保存。修正为如实报告后，首次Kafka观察在客户端创建前因常驻Agents缺TLS配置被production resolver拒绝；原程序、stderr hash及诊断保存。随后只读观察改用已有Fusion配置，不向Agents注入或修改配置，没有绕过TLS。恢复是补齐审计观察，不是修复运行缺口；不能写成首轮全通过。

审计结束前后完整观察相同，网关triage/recon/investigation/summary/report保持16/3/5/1/3，0新增模型、usage或成本。新证据位于21`/opt/sting-aisoc-socai2/evidence/3a-admission-review-20261020`及工作站忽略目录`.local/aisoc21/3a-admission-review-20261020`，目录0700/文件0600；旧材料未改。

**下一单项为[3A-11-02常驻分诊配置补齐](3a-triage-admission-config-plan.md)**：显式审批guard为0、接入已有SSL Kafka配置与CA，只核配置及offset而不启worker。之后再做p01提示词/新盲测小批。此排序不减少p01质量缺陷或旧调查工具阻塞，整个3A和服务端迁移仍未完成。本批未提交或推送。
