# 第7步Case持续更新与上一轮比较

2026-11-15。沿[详细设计](../../../../openspec/changes/schedule-streaming-investigation-updates/stage7-case-updates-design-20261115.md)完成7A/7B核心直接验证；HTTP独占新案三任务已消费，7C终态读取及文档收口中。分支V1.1；真实隔离PG为v12_upgrade_dev（129、32表521列），专用本机Redis。模型与湖查询使用明确替身，**真实模型调用0**，没有部署21、启生产消费者或提交推送。

## 通过的程序验证

| 证据 | 直接覆盖 |
| --- | --- |
| [read-7a-01/result.json](read-7a-01/result.json)及原[pg-7a-01](pg-7a-01/result.json) | 同案8任务、5Run：4完成、1容量失败，3次无变化跳过。initial→check无变化→rerun→有效H后轮→同正文新revision不跑；比较实际上一轮，失败前轮无结论不回退早期采用结果；冻结输入、比较及19类读取前后相同 |
| [read-7b-03/result.json](read-7b-03/result.json)及原[pg-7b-03](pg-7b-03/result.json) | 2Case、8个完成Case Run；另有1A/3I通过可信保存入口生成的合成上游结果，非模型执行。周期无变化无Run；新事件成员跟随；运行中新增H留下一轮；晚到A/I触发；同业务新I Run不触发；只有当前活跃Case自动更新I，旧Case手动check可用I且不抢接收关系。23类记录读取前后不变 |
| [lifecycle-02/result.json](lifecycle-02/result.json) | 独立新案2Run：仅扫描时钟前移验证超期不受理；恢复实际时钟后手动check正常完成并续期；关闭后到期扫描不执行。没有修改时长配置或已结束执行时间；跨期已受理首试/不重试复用第2步直接证据 |
| [read-auto-capacity-01/result.json](read-auto-capacity-01/result.json) | 自动跟随将事件第101条告警放入续建Case，原案100/新案1；服务actor的created_by/submitted_by为空、唯一active_case_id指向新案、仅新案新增initial任务。只验分配及受理，没有执行这两个任务或调用模型 |
| [http-consume-01.json](http-consume-01.json) | HTTP独占Case三任务按initial/check/rerun消费：completed、skipped/no_changes且无attempt/Run、completed。两个Run身份不同，4次模型替身，0真实调用。消费者已退出，不重派 |
| [HTTP证据](../case-update-http-20261115-01/README.md) | 7A已结束样本28GET及新案20请求受理通过；发现并修正HTTP把核心结构化对象当字典读取的问题，原失败保留。最终新案终态回放/读取由HTTP模块继续记录 |

离线27项通过：case_update_inputs、case_execution_input、analysis_dispatch。覆盖相同业务新ID、A/I可用性、I范围/覆盖、H正文/范围/引用/撤回、非活跃I过滤及执行容量/调度边界。受影响核心Ruff通过；OpenSpec strict通过。未重跑全仓回归，未开展故障矩阵或模型质量采样。

主要验收批共17个Case Run（含HTTP2个、容量失败1个），32次模型替身。早期驱动失败批另有6个完成Case Run、12次替身；全批共44次替身、0真实模型。原模块输入、提示/Schema、可见原答、验证、装配及结果在snapshot/artifacts和calls.json中保留。合成上游结果是数据准备，不能算A/I真实模型通过。

## 原失败及补验方式

以下原result.json不改写，不重派已结束任务。补验文件独立，不把原失败追认为成功。

| 原记录 | 原因与处置 |
| --- | --- |
| pg-7a-01 | 五组业务断言已完成；最后快照摘要未转换UUID而失败。read-7a-01仅只读补验，与原保存快照相同 |
| pg-7b-01 | 驱动在next生成器中await，生成了异步生成器；已有两轮完成。修驱动后使用新租户新批 |
| pg-7b-02 | 合成A引用缺source_path，被正常校验拒绝；此前三轮Case已完成。明确没有模型执行，孤立合成A按失败收尾，另存[fixture-stop-01.json](pg-7b-02/fixture-stop-01.json)，原失败和快照保持 |
| pg-7b-03 | 四组业务断言、8轮Case完成；测试试图改last_normal_completed_at，被数据库一致性守卫拒绝。原事务回滚。read-7b-03只读确认所有已结束记录；生命周期改用独立新案和显式扫描时钟替身，不修改历史时间 |
| lifecycle-01 | 测试新建H时Scope缺必填字段；首轮已完成。改为读取该Run完整冻结scope，新批lifecycle-02通过 |
| auto-capacity-01 | 续建保存已完成；测试错误从CaseView取内部previous_case_id。read-auto-capacity-01只读核原始保存字段、任务和关系，未重复分配 |

第6步历史重复记录测试失败和此前模型正文NOT_PASSED仍保留，未借本步替身通过核销。

## 交付与后续

默认6小时、7天、60秒/一次重试保持。测试可缩短等待的要求已发测试模块，由独立测试profile明确记录；本步只对新测试对象设置到期检查时间或使用扫描时钟替身。配置/工厂与发布字段见[运行说明](../../analysis-case-updates.md)、[发布片段](../../../../deploy/local-investigation/analysis-case-release-fragment.json)。无新DDL或告警交接字段变更。

主验收保存快照按[export_saved.py](export_saved.py)加入仓库静态查阅页，新增4案，原20案保留；实际4177服务未切换。它们是归档，不冒充目标测试服务/4177 HTTP实时取数。

7C完成后与测试模块锁定本期1–7范围和21独立候选资源，执行最小分层验证、修复具体阻断，完成第11步交接与独立结束审计，再由调查负责人正式发布及读回。8–10保持后置；本步本地PG/Redis/ASGI证据不能代替最终候选TCP、真实模型和查阅验收。
