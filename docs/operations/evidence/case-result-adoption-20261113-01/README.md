# 固定调查结果人工采用：核心用例

2026-11-13。本项承接主调查3.12及Q02，按[OpenSpec设计](../../../../openspec/changes/complete-socai2-investigation-chain/result-adoption.md)先实施核心，严格校验后修改代码。HTTP适配仍未实施，E21保持501；没有迁移、模型调用、生产写入或部署。

## 本次完成

- `CaseService.preview_result_adoption` 读取原判断、新Result及其待核/限制、实际成员覆盖、新鲜度、未完人工任务和pending/running/unknown Run；明确可采用与拒绝原因。
- `adopt_result` 在Case锁内核对预览摘要、资格、理由及未完工作确认，原子保存新判断、来源/覆盖、当前指针及操作回执。只允许已完成whole_case基础调查的accepted模型结论、当前输入及全员有效覆盖；uncertain/partial本身不阻止采用。原Result、旧判断及任务/Run保持；人工actor与模型结论origin分开。
- `read_assessment_history` 读取旧/新判断、原Result、真实覆盖、采用人及理由。HTTP模块后续只适配这些用例，不复制事务或调度规则。

核心实现：[case_adoption.py](../../../../services/api/app/socai2/case_adoption.py)、[DTO](../../../../services/api/app/socai2/case_adoption_contracts.py)。

## 一条真实PG流程

明确连接本机`v12_upgrade_dev`/`v12_developer`，新建Case `2b09d101-8a2d-5fa9-a618-d66c61bfa158`。只有2条合成告警、4个C1冻结Run和4份程序提供的测试Result；没有执行A/I/C2–C6模型或外部工具。它验证采用存取，不证明调查或模型质量。

| 实际环节 | 结果与证据 |
| --- | --- |
| 初次连接 | [pg-01](pg-01/failure.json)因沙箱禁止本机TCP失败，无数据库读写；没有重派业务 |
| 资格/预览/采用 | [pg-02预览](pg-02/adoption-preview.json)显示uncertain/partial但全员覆盖的可用结论，以及1个未完任务、1个running和1个pending Run。失败且覆盖不全的另一Result拒绝；新增任务后旧预览拒绝；未确认未完工作拒绝。采用、同请求重试及不同理由冲突完成 |
| 脚本失败 | [pg-02失败](pg-02/failure.json)是验收错误假定Case状态为open，实际为new；业务采用已提交。原失败、快照和源文件保持，未重新建案或重启旧Run |
| 保存/读取续验 | [pg-03回执](pg-03/adoption-receipt.json)、[Case](pg-03/case-after-adoption.json)、[判断历史](pg-03/history-after-adoption.json)、[原Result](pg-03/result-readback.json)、[活动](pg-03/activities-after-adoption.json)与SQL快照一致；人工采用为第2版，旧自动判断保留，原Result逐字段与采用前预览一致，任务/Run和Case状态保持 |
| 后续覆盖顺序 | [程序发布回执](pg-03/automatic-order.json)：人工采用之前已启动的Run完成返回newer_assessment；之后显式启动的pending Run按既有规则自动采用为第3版 |
| H变化 | [反馈保存](pg-03/human-feedback.json)后，当前判断保持但[新鲜度stale/human_feedback_changed](pg-03/stale-preview.json)。旧预览和过时Result均拒绝采用；没有自动建Run。重试旧人工操作仍返回原回执，不回滚当前第3版 |

[pg-03检查](pg-03/verification.json)通过；pg-02的失败状态保持。最终[同一只读快照](pg-03/database.json)有1Case、4Run、4Result、3判断、1任务/2修订、8个C1输入工件；未覆盖成员没有被伪造为已分析。未做并发压力、全仓回归、真实模型/厂商或TCP HTTP测试。已结案拦截、其他材料版本/成员变化等代码分支未另建矩阵，原结案证据继续适用原范围。

## 阅读与重放

- [人工采用的实际预览](pg-02/adoption-preview.json)及[提交参数](pg-02/adoption-request.json)是核心用例输入，不是模型输入；[最终Case](pg-03/final-case.json)保留后续H造成的过时状态。
- [源码回放说明](source-replay.json)记录Git基线、完整相关工作区补丁及新文件；`first-attempt-source`与pg-02的11个源摘要逐一匹配，`after-source`与pg-03的11个源摘要逐一匹配。仅修测试对状态的假定并追加本批续验入口，业务实现两阶段一致。
- `run.py`使用显式数据库配置/受控环境文件；旧输出目录拒绝覆盖。pg-02已经采用、pg-03已经结束，不重新派发本批；未来重放须新输出目录及新合成Case，不使用本批`--continue-from`。
- [本机4177静态详情](../../../../deliverables/investigation-validation-20261106/processing-audit/cases/876f2dca252bf8282370190ac36e1f0e885ec82be3b34f100581d374e359db3c.html)已追加1份，本机84→85，原记录保持；在线4177未同步。[导入回执](workbench-import.json)记录实际详情与摘要；未核本机TCP入口可达性。

独立审计见[audit.md](audit.md)。主调查仍31/41，模型正文与知识使用质量仍NOT_PASSED；本项只完成核心本地能力，HTTP适配、部署及流式更新保持未完成。
