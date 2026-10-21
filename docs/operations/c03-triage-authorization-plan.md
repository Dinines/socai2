# C03-02C-01：分诊授权事实边界

2026-10-21。承接[02B受控停止](c03-triage-quality-recheck.md)与[C03总卡](c03-triage-reasoning-plan.md)。02B新阳性材料支持TP，模型仍无据断言确定未授权；本批只澄清这个已复现的理由缺口，不改变旧两批评分、原输入或模型结果。两批各三条、共六条未执行输入保持未发送，不重调旧两条已执行告警。

## 实施与直接验收

仅将`services/agents/app/llm/prompt_registry.py`中`triage.system`末条替换为下文，版本3→4并更新对应`prompts.lock.json`；修改直接受影响的既有C03测试版本及末段断言，保存父源与原测试快照/hash。分类/schema、其余21个prompt、风险分算法、五类读取、模型路由、retry0/45秒、输出512和8000字符/16000规范UTF-8字节上限保持。

```text
- Distinguish observed harm from authorization status. Harmful behavior may
  support true_positive while authorization remains unknown. Assert an
  authorization decision only when an applicable decision is supplied.
  Use needs_review when remaining gaps prevent judging threat.
```

复用88项现有直接测试。在断网候选镜像中，以恶意、完整授权、材料不足、时间反例四类固定资料，每类一次走实际build_state→AutoTriage→safe-call→egress→生产SDK MockTransport，保留完整请求的默认JSON字符数与规范UTF-8字节数及实际末条。资料只作为离线fixture，五源状态不冒称真实reader调用；固定needs_review回复不是质量得分。禁止私有评分表、真实key/env/private挂载、真实模型与预算/Run/QA写入。探针不借助Invocation认领或数据库，CostTracker persist=False。

## 运行与资源边界

父镜像`sha256:039f2cb09684c29e170b8907572196ff5559c9d7991837fc431a12d113350985`，v3；25 Compose/22源码层、Agents184 Py、四服务769 Py。以02B封包后的7预约/140000预留单位（含3旧unknown）和实际观测为基线。保存父配置、两份运行源及受影响原测试；0新tenant/key/reader、0真实模型、0业务PG写、0broker发布/应用记录交付/提交、0DDL或共享服务重启。不外推metadata探针零后台fetch。

最多构建并重建Agents一次，精确父镜像overlay；新`compose.triage-authorization-c03.yml`预计带来26 Compose/23源码层，依赖、env、7个只读bind和60秒停止宽限保持。worker、graph、自动审批与记忆写回继续OFF，其他35容器/18卷/134迁移与旧材料/组/十reader保持。部署前独立核源码差异、直接测试、四个完整SDK body；部署后独立核实际运行源/lock与持久数据不变。失败保留检查点，不盲目重建；必要时仅回退Agents父定义并保持OFF，镜像回退不撤销已有业务结果。

## 结束与下一项

结束审计后发布来源/回执并更新PROGRESS；断网测试只证明版本、约束传输和预算门，不解除模型理由质量或常驻准入。下一C03-02C-02另冻结四条全新代表输入、独立判据与最多四次逐例真实调用；不重发旧两例，不改原判据，不将已知失败覆盖为通过。若再有原版非阻塞缺陷，按[统一问题登记](upstream-issues.md)记录，不扩张为无限提示词优化任务。
