# 阶段一步骤1：A/I原结论保留与引用问题独立记录

2026-11-14。本地直接验收通过，尚未发布。所属[OpenSpec change](../../../../openspec/changes/complete-socai2-investigation-chain/tasks.md)，整体目标、七步依赖及每步验证已先写入[详细设计第8节](../../../../openspec/changes/complete-socai2-investigation-chain/stage1-problems-and-plan-20261114.md#8-整体实施顺序预期效果与验证安排)。本轮止于A/I步骤，不代表阶段一或主change完成；主31/41、流式1/11及正文质量NOT_PASSED保持。

## 达成的效果与实现范围

- A/I执行器版本为v4。接收时保留模型原判定、置信度、理由、摘要、结论、成员分析、发现与建议；原文首尾空白也保留。结构、真实成员身份、定义ID唯一性仍校验。
- 重复、未知、空引用、角色不适用及跨成员引用记入`model_response.content_json.citation_review`，不触发引用纠正调用、不删除或降级结论。仅同列表保序去重；记录前后值、原编号、声明范围、实际来源归属和字段路径。适配字段有原答路径映射。
- 先提交`artifact_role=model_original_response`原答快照，再接收和派生；响应工件关联原答/请求/尝试并保存独立诊断及原答、派生hash，最终publication与业务表保持同一派生版本。未知编号不伪造来源；可解析跨成员来源保持原归属。A解释模板仍只关联真实程序事实，不能把这些链接当成模型原声明已正确引用。
- I输入冻结对应A原分析及简短质量回执，模型视图附相关质量提示，角色仍为`prior_analysis`；不把整份诊断台账送回模型。旧I冻结输入按原版本比较新鲜度；A v3查询回执仍能被新版I读取。
- 内部接收输出允许缺失有效引用，既有对外HTTP字段、类型、枚举及数据库表保持。原生成Schema仍约束实际编号及必要引用，接收诊断与生成要求分开。

## 直接验证

| 检查 | 实际结果与证据 |
| --- | --- |
| OpenSpec | 实施前及本步收口严格校验均通过；相关文件Ruff与diff空白检查通过 |
| 离线接收及兼容 | [59项直接检查全部通过](offline-direct.log)：新增10项原结论/空白/去重/错成员/主体结构检查，复用A/I边界、原局部接收和交付完整性检查；没有真实模型、数据库或厂商调用 |
| 真实隔离PG | [attempt-03](attempt-03/checks.json)使用`v12_upgrade_dev`的新2条A、1条I；3次模型替身各调用一次，查询因无选择对象真实跳过，0次厂商查询。三个Run均completed/complete、stage_output_saved，沿既有新鲜度规则成为当前结果 |
| 保存一致性 | [数据库快照](attempt-03/database.json)保留实际模型请求、原答、诊断、分诊/诊断行及publication；原结论/正文、原始回复、派生hash一致；引用范围诊断保留跨成员原归属，未知编号没有伪造链接 |
| 后续输入 | 同批两条A保持原判定、理由和source_run_id进入I冻结输入；引用质量提示进入实际请求，角色保持prior_analysis；可用性不因纯引用问题被置false |
| 现有HTTP读取 | [38次GET](attempt-03/api-responses.json)全部200，调用独立`investigation_http`现有路由的分析目录、单Run、trace及全部工件；原业务字段、原答、诊断与PG快照逐项一致。使用ASGI和认证/服务依赖替身，不是生产TCP或真实鉴权验收 |
| 无重复执行 | 同operation_key重入A/I以及全部GET均未增加模型调用；GET前后工件集合逐字一致 |
| 范围核对 | [verification.json](verification.json)：代码与通过批次的执行前hash一致，17个已撤出的Case/C3文件与撤出时字节一致；公共读取/共享引用合同保持。未部署、提交或推送 |

直接测试入口为[test_socai2_ai_citation_quality.py](../../../../services/api/tests/test_socai2_ai_citation_quality.py)及[test_socai2_ai_citation_quality_pg.py](../../../../services/api/tests/test_socai2_ai_citation_quality_pg.py)。批次由[配置](config.json)和[驱动](run.py)明确选择环境，`--attempt`要求新目录；已有Run不重派，旧数据不清理。复验会产生新合成身份，不能通过覆盖既有attempt重写失败。

## 失败、修正与未验边界

| 尝试 | 原始结果与处理 |
| --- | --- |
| attempt-01 | [连接失败](attempt-01/failure.txt)：沙箱拒绝本机127.0.0.1:28412连接，在写入前停止。后续按本机隔离库验证范围取得工具连接权限 |
| attempt-02 | 2条A和1条I保存成功，但[原文比对失败](attempt-02/failure.txt)：I旧`strip_whitespace`裁掉摘要首尾空白。[原快照](attempt-02/database.json)保留；修正接收器并补原文断言，使用新身份执行attempt-03，没有重写或重派旧Run |
| attempt-03 | 当前通过批次：3次模型替身、38次HTTP读回，见上表。两次数据库批次合计6次替身，真实模型调用始终为0 |
| 既有裁剪测试 | 首次未显式选择profile时7项未能检查；补指定profile后[15通过、2失败](offline-existing.log)。失败是3000字符命令和metadata应被裁剪的旧断言；[修改前源码同样2失败](offline-baseline-budget.log)，与当前field_limit=draft_limit口径不符。已在[问题清单](../../../investigation/current-issues.md)登记，未改裁剪代码或把失败改为通过；此15项与59项有重叠，不累加为74项 |

本批不证明模型正文准确性、厂商取证、生产HTTP或真实鉴权通过。Case/C3/Deep/C6结论保留、C3的8192/最多5/一次补答、超限存取、补查能力和4177展示修复尚未实施。本轮未改运行profile，C3仍4096。下一步按设计推进Case结论流转及采用，另做直接验证和汇报。

## 本地查阅快照

已运行既有`update_processing_audit.py`，将失败02和通过03两份A/I快照追加到本地静态目录，保留原3案，共5条记录，[更新核对](4177-after.json)。未修改展示程序；`stage_output_saved`等RV12展示问题仍待步骤7。

[实际端口读回](4177-http-readback.json)确认本机4177由SSH转发到21，返回200但仍为远端原3案；本地新文件尚未同步到该运行服务。未切换转发、重启服务或发布远端。可直接查看[本地通过批次快照](../../../../deliverables/investigation-validation-20261106/processing-audit/cases/bad02755611a66a7bcb2066cb80de5dc7d55ca613dc802842c7d33dda883b1ea.html)；该静态页不是本步HTTP业务读取验收的替代。
