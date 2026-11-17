# 21新版：新材料两段完整流程测试

2026-11-17，按负责人要求先[部署并清理历史](../acceptance-release-20261117-01/README.md)，再运行新材料。**本批正常业务链、保存/HTTP读回、测试与HTTP限定独审、实际4177查阅通过；模型正文质量未全面验收。** 目标始终为21正式aisoc.socai2，未切换本机隔离库。

| 步骤 | 实际结果 |
| --- | --- |
| 最终容器准入 | 3d04不可变验收镜像；四连接、目标/身份、新材料、并发及预算通过；[准入](admission-02.json) |
| 首段 | 2独立进程上下文→1告警→自动A/I→201创建1整事件Case→首轮保存/HTTP读回；[检查点](part1-checkpoint.json) |
| 显式追加 | 首段通过后只读核关联索引，PTTL 3146214ms；37.65秒后append一次，1网络上下文→1新告警→A/I→202检查原Case→后轮；[TTL](ttl-01.json) |
| 保存/关联 | 同事件、同Case，冻结成员1→2；R2比较实际R1 Result，旧轮原答保持；7任务、6Run、2Result、48步骤、142工件；1个no_changes无attempt/Run/模型 |
| HTTP | 473 GET 200、1 POST 201、3 POST 202；目录分页、实际content_url、源Run及原答读回一致 |
| 模型与并发 | A/I/C3/C6各2次，共8次均stop；30612输入+14595输出=45207tokens，费用未知；实际并发峰值1，结束无在途 |
| 输入过滤 | 8份实际消息未带tenant_uid/tenant_id、后台来源控制ID/标签、execution/test_batch/expected；tenant/告警/来源关联仍在后台 |
| 展示 | 4177默认Case，事件/告警独立列表；两轮HTTP、冻结来源、具体领域、查询、原答和5项质量问题可读 |

程序负责投递顺序、关联、等待、保存/读取验证与报告去重汇总；模型负责A/I/C3/C6业务分析。首段验完才追加，不同时把全部告警送入模型。唯一执行接管见[回执](execution-takeover.json)，测试模块及HTTP模块只读复核同批，没有重复发送或追加采样。原4a冻结44文件不改，5条业务记录各ACK一次。

## 在页面查看

打开[4177工作台](http://127.0.0.1:4177/viewer/)，选择Case“进程活动及后续外联调查”，在顶部选择第1轮/第2轮。点击左侧HTTP请求、C3领域、查询或C6模型调用查看对应数据；“测试记录→质量问题”查看本批5项后置问题。紫色仅标测试来源，不进入模型。

- Case：`8bf67e9e-a46a-58ba-a3ad-73a70ca64258`；事件：`93fbd228-68a1-4ecf-b9dc-014a269a2bf7`。
- R1：`c068a7b9-b33d-45a5-b0c0-c2b296ba5d5d`；Result：`e51072c6-1dab-4101-ac8d-85bc08654d86`。
- R2：`57683158-b770-4697-8ca3-a2707ed0af1b`；Result：`0823a02c-2270-43e4-891a-ffa3a2a95314`。

[程序生成报告](results/report-01/report.md)逐段列主体、步骤和模型输入/Schema/完整原答文件；[JSON报告](results/report-01/report.json)保留机器可读来源。两轮C6原答分别见[首轮](results/report-01/models/8a7d1ca0-4fed-4e0e-ba01-bb2e60fe71cf/output.txt)、[后轮](results/report-01/models/67c52c10-5e94-45d7-9470-8271172046d1/output.txt)。

## 问题与边界

| 所在阶段 | 问题 | 处理 |
| --- | --- | --- |
| 首轮C6 | impact缺来源、影响范围引用未覆盖，共2项 | 原答/结论保留，记录后继续；并非输出截断 |
| 后轮I | 两个open_questions声明两个成员，引用只覆盖其中一个，共2项 | 原答及来源范围诊断保留，继续Case后轮 |
| 后轮C6 | 比较类型withdrawn与正文“范围扩大、核心结论不变”不一致，人工核对1项 | 程序按原答保存，记录后置，不重写比较或再次采样 |

自动4项见[业务核对](final-validation.json)，人工1项见[定向质量记录](manual-quality-review.json)；报告自动部分仍为4项，4177辅助质量列表合并显示5项，不追改原报告。两轮均accepted/uncertain/partial，正文未全面评估，不报告准确率。

每轮C2威胁情报/历史告警因工具额度预留给证据补查而跳过，UEBA/身份关系因来源未接入而跳过；两轮共8项步骤记录。C4认证两轮查空，网络首轮查空、后轮读到1条真实记录；查空不证明安全。本批未选择Deep模型，未覆盖自然4h/6h到时、D5/D6异常继续。4b精确报告链接及自动来源映射仍待；本批使用已有账本发布入口补证，不算4b自动能力。A/I概览通用卡片部分无对应字段显示“未记录”，执行状态和原分析可读，展示细化留后续。

## 核对证据

- [19项直接业务核对](final-validation.json)、[测试模块10组限定独审](independent-test-review.json)、[HTTP模块11组限定独审](independent-http-review.json)。
- [4177发布](viewer-publication.json)、[13GET及两轮C6原答一致](viewer-http-verification.json)、[实际浏览器](viewer-browser-01.json)。
- [原件复制](results-copy.json)：1036文件，原件扫描无凭据或非空隐藏推理；[静态导入](static-verification.json)：53→54，原53条不变。

准入01字段假设、TTL驱动初次键定位、关联读取初次主键假设、HTTP独审初次member_count字段假设均保留原失败/修正回执，没有触发重新投递、改原答或新模型。浏览器读回脚本初次直接比较时区字符串差异，按同一DTO归一化后通过；不是业务数据变化。整个change未完成，未提交、推送、归档或重做清理。
