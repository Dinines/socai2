# 3c.1：已存会话状态与下一候选段

2026-11-17，按`schedule-streaming-investigation-updates`统一设计§12.11，仅实施离线`status --prepared --report`。本批不是业务重跑，不连接21或模型，不发送上下文/告警，不追加、改写历史或发布服务。

新增命令校验冻结session/wire和各段保存回执，按scenario声明顺序列出实际身份、task/attempt/Run/Result状态、执行问题及下一未发送候选。只有保存与读回闭环、所有执行已结束、Kafka及HTTP写入回执确定时才给候选。存在的段目录不能成为重发候选；质量问题与已结束任务失败保留。状态报告只反映已保存事实，不是实时运行许可；3c.2显式追加、3c.3交互/会话报告、3d镜像及任务4未实施。

## 直接验证

- [复验脚本](verify-saved-status.py)将历史01/02的`prepared/`与同批`runs/`原字节复制到新临时`prepared/runs`关系，调用真实CLI，报告写在副本外。临时副本用完删除，历史原件不改动。
- [来源摘要](offline-03/source-manifest.json)给出各文件原路径映射及SHA；[验证回执](offline-03/verification.json)保存CLI参数、返回码、报告读回、输入前后摘要核对及0连接/0投递/0模型边界。socket与连接文件读取被拦截检查，执行/连接客户端模块未载入。
- [01报告](offline-03/status-01.json)：原预检失败、0发送，仍为`incomplete`，总体`needs_review`且无下一候选。
- [02报告](offline-03/status-02.json)：原2上下文、1告警、1事件、1Case保持；Case任务failed、0Case Run、0Result，`completed_with_issues`保留。总体`waiting_append`，候选part2；不能重发part1，也没有混入后来本机续验03的成功Result。
- 源码包含新模块，包测试在源码树外执行status；不构建或发布3d Docker镜像。

[26项直接检查及strict](checks-01.json)通过；复验脚本的循环变量绑定静态告警修正后，[Ruff与实际报告补验](checks-02.json)通过，原首版offline/回执保留。初版[14文件冻结](source-freeze-01.json)对应第一轮复核。[初审](../test-acceptance-session-status-20261117-01/independent-review-01.json)发现S1坏嵌套结构抛AttributeError、S2孤立attempt.task_id仍有候选，结论changes_requested保持。补固定诊断兜底及主体/task/attempt/Run/Result最小关联核对后，[32项直接检查与strict](checks-03.json)通过；测试import排版修正后[Ruff](checks-04.json)通过。[修正冻结14文件](source-freeze-02.json)仅状态模块和定向测试改变；offline-03为修正后的实际副本复验，[测试模块第二轮独立复核](../test-acceptance-session-status-20261117-01/independent-review-02.json)已通过，原3个失败变体逐文件同SHA重放均保存固定诊断并无候选，正常基线仍可列part2；第一轮失败回执不改写。最初的顺序测试材料构造曾重复告警身份、随后缺少case级计划而被既有材料校验拒绝；已改用合法的非连续声明顺序材料，未更改业务校验规则。

可独立复验（输出必须是新目录）：

```sh
.local/conda-envs/socai2/bin/python docs/operations/evidence/acceptance-session-status-20261117-01/verify-saved-status.py \
  --output /tmp/socai2-status-review-new
```

本步[最终收口](final-validation.json)只关闭3c.1。没有新增业务连接/投递/模型，没有修改21、Git提交推送、数据库/HTTP合同或历史批次；下一步为3c.2显式追加与实时核对。模型质量及完整change验收不由本步核销。
