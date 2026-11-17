# 3b 单段实际流程：部分通过，Case 输入阻断

2026-11-17。21现有r4服务运行了新执行`acceptance-singlepart-20261117-02`，**2条上下文、1条告警、1个事件、1个Case**。程序结束为`completed_with_issues`；A/I完成，Case在准备输入时失败，**没有Case Run或Result**。3b和任务3整体均未完成。

| 步骤 | 实际结果 | 证据 |
| --- | --- | --- |
| 准备与预检查 | 全包5条记录生成新身份，业务时间/来源关系保留；目标tenant、既有connector、库/角色及历史实体检查通过 | [session](prepared/session.json)、[预检查](runs/part1/preflight.json) |
| 上下文 | 2条Kafka ACK后按真实湖记录核原值、ID、类型和时间，通过后才发告警 | [湖读回](runs/part1/context-readback.json) |
| 告警 | 1条ACK，材料和来源关系保存；自动分诊任务completed | [执行状态](runs/part1/state.json)、[保存记录](readback-02/saved-records.json) |
| 事件 | 首次诊断completed；一次显式check为no_changes，没有新增Run或模型 | 同上 |
| Case | POST201已建案；初始task在input阶段DBAPIError，attempt有结束时间、run_id为空 | [原任务与进度](runs/part1/state.json)、[保存记录](readback-02/saved-records.json) |
| 保存读回 | 修正版37次真实GET核A/I结果、引用集合、完整步骤/工件分页、原件和SHA；本批PG读前后相同 | [只读复核](readback-02/readback.json) |
| 第二段 | 1条告警和1条上下文只准备，未发送、未追加调查 | [session](prepared/session.json)、[原状态](runs/part1/state.json) |

本批为4个task、3个attempt、2个Run、7个步骤、21份工件；Case结果0。告警`ff80b9c5-259f-5926-b7b6-02af5e53367a`，事件`424a7957-0637-4163-b0a3-bdda56a7d209`，Case`9c43101a-961a-5608-9f6c-c4476937debb`。

## 模型与材料

[输入/原答索引](model-io/index.json)保存2次真实调用：A输出341tokens、I输出1161tokens，均`stop`，总usage4068tokens，无未知usage，费用未知。已知测试标记、批次、告警源及`tenant_uid`输入扫描均未命中；后台tenant与来源关联仍保存。程序引用诊断0，正文质量`not_checked`，不报准确率或全面质量通过。Case C3、Deep、C6均未执行。

材料是显式新作者配置下的统一原生包，选择1告警+2上下文，沿用21已经登记的中性来源；[作者映射](config/authoring.json)记录选取与connector绑定，不修改旧历史数据。新执行保留业务时间，使用新UUID命名空间；不是将旧批次重新投递。01仅GET预检失败、0投递，其[失败原件](../acceptance-singlepart-20261117-01/README.md)保留。

## 本机修正与实际边界

独立审阅发现的三项CLI问题已修：对象形式OCSF raw_data同步身份；A/I结果字段和结果引用集合核对；历史I对照本轮冻结范围。32项直接检查与Ruff通过；[测试模块复核](../test-acceptance-singlepart-20261117-01/independent-review-02.json)通过。运行中的客户端未替换代码，[source-freeze-01](source-freeze-01.json)是实际执行版本；[verifier-freeze-02](verifier-freeze-02.json)是仅重读同一结果的修正版，未新增业务写入或模型。[初版失败审阅](../test-acceptance-singlepart-20261117-01/independent-review-01.json)保留。

实际Case错误是C1嵌套SQL别名冲突：外层当前事件`i.id`被内部`incidents i`遮蔽，形成`i.id=i.id`。两个事件共存时标量子查询返回多行，SQLSTATE21000。最小修正使用唯一外层任务别名，没有加LIMIT掩盖来源，也未清空旧事件。[只读复现与修正核对](c1-readonly-02.json)表明：原SQL在新旧两个Case均失败；修正SQL分别准确读取1/4个成员和各自冻结I来源。17项终结材料检查、Ruff通过。源码绑定见[source-final](source-final.json)，探针见[c1-readonly-probe.py](c1-readonly-probe.py)。**这是隔离进程的只读修正验证，不是已保存C1、Case Run或正式任务恢复。**

[服务前后核对](services-after.json)确认Fusion、联合调度和HTTP容器/镜像均未改变。只运行临时验收客户端，依赖与配置均显式保存；不算3d专用镜像交付。未清历史、未改并发/预算、未部署新页面/核心服务、未提交推送。

本机静态查阅由既有导入器新增此失败Case，49→50，原49条及页面逐值保持；[导入回执](static-verification.json)明确Case无调查Run。未做本轮浏览器或21旧4177入口发布验收。实际任务、失败、A/I原件可由业务HTTP读取。

[实际批次独立复核](../test-acceptance-singlepart-20261117-01/independent-review-03.json)已确认3份ACK、湖/PG原值、严格顺序的37份HTTP原响应、2份模型请求/原答和两案C1只读证据；原失败保持、Case未恢复。[临时客户端清理](client-cleanup.json)仅移除了两个已退出客户端及各自临时密码副本，服务、原凭据与证据保留。

下一步先在包含C1修正的完整验证环境补Case执行、保存及读回，21同案恢复保留到既定统一发布后验证；不重投已完成A/I，不把失败task改写成成功。3c交互追加/全会话报告、3dDocker封装及任务4仍待。本轮设计及阻断范围见[§12.9](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#129-任务3b新执行身份与单段实际链2026-11-17)。
