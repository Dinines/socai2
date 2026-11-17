# 事件异步HTTP本地验收

2026-11-15，事件E37已经在独立候选应用切为异步202，提交→真实任务保存→A/I调度器消费→Run/诊断保存→HTTP读回通过。事件专用E23/E25返回同Run的冻结选入范围和实际覆盖，告警共享Schema保持。Case新的异步POST未挂载，旧同步A/I旁路已移除；默认内部可信、无登录/Token/角色校验。

本批103次HTTP请求（91 GET、12 POST）通过；12项直接HTTP/边界检查、目标Ruff和OpenSpec strict通过。见[汇总与源码摘要](final-checks.json)、[实际输入输出示例](examples.json)、[80操作候选OpenAPI](candidate-openapi.json)、[提交指南](../../../integration/analysis-submission-http.md)及[逐字段查询指南](../../../integration/incident-analysis-http.md)。这是ASGI真实路由加隔离PG验证，不是本地18024或21上线回执；正式服务/静态Swagger保持上一版71操作。未部署、重启正式服务或Git提交推送。

## 实际流程

| 场景 | 回执 | 请求数与结论 |
| --- | --- | --- |
| 已保存事件同源读取 | [read-pg-03](read-pg-03.json) | 16次GET，任务/Run/诊断、目录、步骤及原件匹配 |
| check受理 | [submit-check-01](submit-check-01.json) | 8次请求，202/同key重放、409冲突、422字段/查询错误、Case新POST 404；只新增一个任务，无Run |
| check消费后 | [consume-check-01](consume-check-01.json)、[after-check-01](after-check-01.json) | 2次HTTP，skipped/no_changes，无Run/模型调用；终态POST回原accepted回执 |
| rerun受理 | [submit-rerun-01](submit-rerun-01.json) | 4次请求，只新增一个任务，调用返回前不执行 |
| rerun消费后 | [consume-rerun-01](consume-rerun-01.json)、[after-rerun-01](after-rerun-01.json) | 3次HTTP，实际执行器调用受控模型1次，新增唯一Run/诊断，旧记录保留，终态幂等 |
| 260成员部分覆盖 | [read-partial-01](read-partial-01.json) | 16次GET，选入100、遗漏160；0已判定/100待核/0未分析，delivery complete但全事件coverage partial |
| 容量失败 | [read-capacity-01](read-capacity-01.json) | 13次GET，failed和冻结范围保留，覆盖unknown，上一有效诊断保留 |
| 未知结果 | [read-unknown-01](read-unknown-01.json) | 13次GET，unknown原状态，计数/覆盖ID为null，不补0或成功 |
| 窗口内受理、跨期首试失败 | [read-expired-01](read-expired-01.json) | 13次GET，原失败及Run/任务关系可读 |
| 已结束真实模型批只读复用 | [read-real-01](read-real-01.json) | 15次GET，诊断原文、范围及工件同源；不再调用模型 |

所有GET阶段核对12类记录的逐行摘要前后一致。提交阶段只保存任务及主体登记，不创建Run、诊断或工件；消费后核原告警、材料、分诊、Run、步骤、工件和诊断未被覆盖。HTTP不操作Redis或调用模型。消费使用调查侧实际A/I factory、真实隔离PG及专用Redis，模型为明确受控答复；测试消费者结束后由调查侧停止专用Redis并保留数据。

核心供给及原始批次见[事件自动诊断回执](../analysis-incident-auto-20261115-01/README.md)。真实模型原文“N/A”仍为质量NOT_PASSED，不因为HTTP成功或覆盖完整而改判通过。本轮真实模型调用为0。

## 保留的准备与失败记录

- [preparation-checks](preparation-checks.json)、[read-checks](read-checks.json)、[read-candidate-openapi](read-candidate-openapi.json)记录当时仅准备、E37同步的状态，不作为当前入口。
- [read-schema-01-failed](read-schema-01-failed.json)、[read-schema-02-failed](read-schema-02-failed.json)：测试误以为Schema必有default:null；改为验证可空、非必填和实际HTTP null后通过，未变业务空值。
- [read-pg-01](read-pg-01.json)：断言未统一等价UTC日期的序列化形式；用响应DTO正规化后继续。
- [read-pg-02](read-pg-02.json)：核心交接样本误把initial任务配到periodic Run。保留严格同源断言，核心提供[修正配对](../analysis-incident-auto-20261115-01/http-samples-corrected.json)后read-pg-03通过，原数据库及旧回执不改。
- [activation-checks-01-failed](activation-checks-01-failed.json)：事件current/entries新字段描述触发旧全Schema比较；仅允许事件描述变化，继续严格核告警共享Schema。后续12项通过。

原[26次受理层验证](../analysis-submit-preparation-20261114-01/README.md)复用以覆盖不存在、关闭、空范围及配置不可用等错误；本轮补真实执行闭环，不重复整套核心调度或真实模型采样。整个change仍有Case等后续步骤及统一结束审计/发布，本步不等于change完成。
