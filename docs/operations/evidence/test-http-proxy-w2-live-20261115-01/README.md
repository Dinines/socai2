# W2：真实非空账本与跨Run只读代理

2026-11-15，本步[验收通过](acceptance-01.json)：沿既有测试服务0.2.0发布真实live映射，临时本机代理经SSH读取21当前18424。完整验证**34次GET全部200，107项直接检查通过**；测试/代理源码与原W2已验版本逐文件一致，没有改业务合同、服务镜像或提高版本。S04原业务失败、模型质量NOT_PASSED、无Case后轮的事实保持，不把本步读取通过计成调查成功。

## 实际读取与业务效果

| 读取 | 本轮证据 |
| --- | --- |
| 9次测试账本GET | 新账本`w2-live-s01-s04-20261115-01`，3个用例/7个真实操作/4条质量记录；两页operations保留真实主体/task/Run/Result，三个skipped任务无Run。mode=live表示当前HTTP取数，不重新执行源批次 |
| 24次业务代理GET | 7个原任务、A04/I和两Case原Run、两Case详情/Result、失败I trace/两页步骤/原答，以及Case C1→原I输入来源链 |
| 1次直接合同GET | 实际OpenAPI SHA `9bce09317ad13c411f2a299e4fbf34c89f41e2a48eb58020d8e5900fa5a67b83`与冻结合同及代理来源头一致，80操作/55 GET |
| 状态保持 | A04 completed；I failed/model_response_not_complete、原答length/output3000；3check skipped且无attempt/Run；两Case仍3/1成员，结果accepted/uncertain/partial，原initial比较链接均null，当前新鲜度stale |
| 原件与分页 | 测试evidence原字节/hash一致；I两页真实步骤无遗漏/重复；失败原答、C1和原I输入的JSON、size/hash与唯一PG快照一致 |

[完整请求、响应摘要及检查](tcp-02/result.json)对应本机时间22:37:52–22:37:56。实际原响应单独保存，正文按上游DTO原样传递：Case键为`artifact`，A/I键为`metadata`，没有为展示重造模型正文。

跨Run使用HTTP方[离线确认的现有来源链](../streaming-w2-http-cooperation-20261115-01/path-map.json)：Case Run `d1b17106-0ee7-4265-ac84-beb9ebf048eb` → C1 `bf3a8ed9-eedf-4bae-8f50-ebbf51eeba53` → `diagnosis_scope.source_run_id`指向原I Run `b5410c29-8134-544d-94e0-f8d59ee82958`。读取该真实Run的工件目录后，沿**返回的content_url**取得输入`1b43bb64-f8cb-473f-b57c-21e0995bec7b`；SHA/来源指纹`398fcb84...`一致。原输入仍3成员，未替换为当前事件4成员；URL保持incident及原Run归属，没有改写为Case路径。

## 准备、配置及保留的失败

- [冻结计划](plan.json)复用S04最终快照SHA `0af1dc0ae2b9b709070459c1d74e669d31a375a36514322dd25276d5ee8e4af3`、真实映射和两案首轮证据；[根侧运行核对](../streaming-w2-readonly-20261115-01/runtime-01.json)确认当前r3处理/r2 HTTP、8份配置不变、调度停止。
- [发布回执](publication-01.json)为现有CLI发布的本机revision1，不是21部署；[输入文档](inputs/document.json)保留真实发生时间、源S04执行failed和独立质量。GET前后整个账本摘要一致，原已结束账本没有更新。
- [当前实际TCP配置](tcp-profile-02.json)、[账本配置](service-config.json)、[上游配置](upstream-config.json)明确地址/端口/超时/目录；实际隧道目标为`192.168.1.21:18424`。临时端口64396/64397均已关闭，不是常驻入口。
- 准备时本机沙箱禁止端口bind以及一次端口字段替换错误均发生在启动/业务请求前，保留[准备失败01](preparation-failure-01.json)和[02](preparation-failure-02.json)，输入文档未被改写。
- 首次临时TCP运行误用远端回环目标，只有本机capabilities GET成功，直接OpenAPI读取遭连接拒绝，无成功业务GET；[原回执](tcp-01/result.json)及[修正记录](transport-failure-01.json)保留。修正当前地址后34次验证一次通过。因此本步合计35次成功GET（含首次1次本机读取）和1次无HTTP响应的传输失败，不隐藏前次失败。

## 结束状态与覆盖边界

[源码复用核对](service-source-reuse-01.json)证明原24项组件/空态/错误证据对应同一源码；本步不重复该矩阵。实际响应最大273212字节，超过1MiB受控流测试复用原证据，不宣称本次真实大原件覆盖。

两个临时进程已停止，服务日志完成正常shutdown（SIGTERM，退出码-15），SSH退出0，两个临时端口均关闭；账本/证据保留。0业务写、0直接数据库查询、0模型、0Kafka、0调度变更，当前4177入口未动。

本批没有步骤级直接跨Run `artifact_refs`复用、unknown真实Run或Case新后轮，不造数据补分支；这里完成的是实际C1业务来源跨Run追溯。W3页面、W4包、W5发布、S04成功更新/比较及整体独审仍按独立步骤推进。capabilities的`runtime_verified=false`仍表示服务启动不自动做健康验收；本步实际就绪/读取证据保存在上述回执。
