# 整理版五字段指令：本轮测试结果

2026-11-08，按用户“旧对比不必留、做一轮测试”执行。**9 次真实模型调用全部完成，格式与核心解析均通过，但正文质量未通过，尚不能据此切换生产分诊。** 本轮仅使用 [v3 文案](../../../tools/testdata/alert_prompt_eval/five-field-system-v3.txt)，没有重新调用旧指令对照组。

## 执行范围与结果

3 份已有告警材料 A1–A3、6 份既有合成材料 S1–S6，各请求一次，无重试、无新样例或额外数据拼接。请求与原冻结五字段包逐值核对：只有 system 正文变化，用户正文、Schema、证据映射、模型路由、temperature=0、输出上限3000和300秒时限保持。此为隔离的模型边界测试，没有创建业务 Run、修改业务库或发起新的资产/历史/情报查询；输入中查询信息来自原有快照。

| 指标 | 本轮实际结果 |
| --- | --- |
| 调用 / 原答 / 重试 | 9 / 9 / 0 |
| Schema / 核心解析 | 9 / 9，均通过 |
| 输入 / 输出 / 总 tokens | 14,208 / 2,710 / 16,918 |
| 平均输入 / 输出 tokens | 1578.67 / 301.11 |
| HTTP平均 / 中位 / 范围 | 6.09 / 6.17 / 3.60–8.34 秒 |
| 判定 | 2 个 benign，7 个 needs_review |
| confidence / 建议 | 5 份为 null；共13条建议 |

HTTP耗时只覆盖模型请求，不代表整个告警处理耗时。本轮不计算旧版对比百分比。

## 逐样例核对

| 样例 | 模型判定 / 置信度 | 核对结论 |
| --- | --- |
| A1 账号登录 | needs_review / null | 待复核。本次三项查询均完成且返回0行，原答此处正确；仍依据账号名称猜测用途、复写查询状态，第二条建议的N1_S22只是connector_type=validation，不能证明情报查询。 |
| A2 PowerShell 启动 | needs_review / 0.85 | 待复核。只说启动命令，未声称命令完成；理由中的“无威胁情报命中”未注明是上游标签，本次TI实际未查询，仍存在来源混淆。 |
| A3 网络连接 | needs_review / 0.85 | 待复核，但把明确给出的TCP/443写成HTTPS，违反提示中的协议边界；仍按observer名称猜用途。查空表述符合本次资产/TI回执，但重复查询事实。 |
| S1 已批准的云运维 | benign / 0.95 | 良性，0.95。批准工单、MFA、企业出口与执行窗口支持主要判定；“最高权限”是额外解释，材料未给权限清单。 |
| S2 连续 MFA 请求 | needs_review / null | 待复核。把新增认证方法推断为用户主动响应安全提示，并称关键事实矛盾；材料只记录操作发生，还明确no registration flow open，不能证明本人意愿。 |
| S3 管理代理清点软件 | needs_review / null | 待复核。正确区分CrowdStrike上报与设备管理服务执行，未见主要行为字段改写；仍未形成确定性判定。原样例的良性/误报标注口径问题保留。 |
| S4 离职员工大量上传 | needs_review / null | 待复核。建议把目的分类uncategorised file sharing当成“目标域名”，导致核实对象不准确；原始材料没有具体目的域名。 |
| S5 凭证窃取邮件 | needs_review / null | 待复核。读对了演练登记=false，却用无证据的内部测试/新业务假设把恶意线索称为矛盾，判断仍过度依赖人工确认；待复核不计良恶方向误判。 |
| S6 客户表批量读取 | benign / 0.95 | 良性，0.95，但把180 prior runs改写为“历史180次成功运行”。原材料仅说明此前一小时无失败语句。样例活动时间与计划时间未对齐，不能计为确定判对。 |

## 为什么没有通过正文质量验收

明确的事实或字段含义错误包括：A3 在输入明确 TCP、只有目的端口443时写出HTTPS；S4 把 destinationCategory 的分类值当作具体目的域名；S6 把180次历史运行扩大成180次全部成功。它们不是材料没有送到模型，也不是输出格式错误：正确字段就在本轮实际请求中。

S2 把新增认证方法解释为用户主动响应安全提示，但记录不能证明操作者意愿，且有 no registration flow open。S5 正确保留 campaignRecordedInTrainingSchedule=false，却把未获证实的“内部测试/新业务”假设当成现有证据矛盾。两例 needs_review 按已确认口径允许，问题在理由的事实基础和推理，不把待复核本身计成良恶方向误判。

A2 的“无威胁情报命中”需谨慎定性：本次 TI 没有查询，但其引用 N1_S12 确有上游 no TI match。该答没有明确说“本次查询无命中”，因此本轮登记为来源含混，不直接写成已证实的“未查改写查空”。A1 的三项查空符合实际回执，但第二条建议引用的 N1_S22 是 connector_type=validation，不能支持情报查询主张。

当前解析器能确认格式、编号存在和来源角色限制，不能证明一段自然语言被引用内容支持。A1–A3 程序查询事实没有独立 execution_receipt 短编号，是继承原冻结输入/映射的缺口；本轮没有修改它，也没有以标签编号补造回执。

v3 已明确写出“端口443不证明HTTPS”，模型仍未遵守，说明仅把提示组织清楚不能保证事实正确。这里没有做逐句消融，不能断言某一句话是根因，也不在本轮自动修改提示或重跑。

## 验证限制

每样例只有一次调用，未验证稳定性。A1–A3没有独立良恶真值；S3原标注的误报/良性口径未对齐，S6活动时间03:06UTC与nightly 02:10的计划/时区仍未对齐，不把它的benign计为确定判对，不报告整体准确率。用户已明确：needs_review单列，既不是方向误判，也不是确定判对。

## 4177与归档

当前入口：[本轮测试](http://127.0.0.1:4177/comparisons/alert-prompt-validation-20261108-01/index.html)。实际输入正文、完整任务指令、输出Schema、模型原答、程序校验及装配结果均可展开；27份JSON下载、页面和manifest共29文件逐字节核对。9份页面数据与原始请求/响应逐值一致；34次HTTP读回含两条旧URL的预期404，浏览器样例切换、指令展开、单批列表核验通过。

按用户要求，原36调用和24调用两组对比已从4177列表移出，184份静态文件移到可恢复归档，两端逐文件hash一致，原始证据未改。远端3个既有Case、本机6个静态Case、工作台容器/镜像和其他容器保持；本次仅静态发布，没有重启服务。

- 本机归档：`.local/workbench-archive/alert-prompt-validation-20261108-01/`。
- 21归档：`/opt/sting-aisoc-socai2/private/workbench-alert-validation-20261108-01/retired-site/`。
- [模型测试配置](../../../tools/testdata/alert_prompt_eval/config-v3.json)与[工作台发布配置](../../../deploy/aisoc21/workbench-alert-validation-20261108.json)均在仓库；后续发布来源清单同步收录。

## 原件与回执

- [冻结计划/请求](../../../docs/operations/evidence/alert-prompt-validation-20261108-01/plan-and-packets.json)、[机器统计](../../../docs/operations/evidence/alert-prompt-validation-20261108-01/summary.json)、[逐样例审查](../../../docs/operations/evidence/alert-prompt-validation-20261108-01/semantic-review.json)。
- [21发布回执](../../../docs/operations/evidence/alert-prompt-validation-20261108-01/workbench-publication.json)、[展示核验](../../../docs/operations/evidence/alert-prompt-validation-20261108-01/workbench-verification.json)。

本批已结束，不再派发。任务3.26的测试与展示工作完成；3.23生产适配、模型正文质量和整体1.2验收继续待完成。无提交推送。
