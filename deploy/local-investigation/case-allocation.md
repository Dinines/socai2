# Case成员分配与受理配置

第5步本地候选，未部署。完整规则见[本步设计](../../openspec/changes/schedule-streaming-investigation-updates/stage5-case-allocation-design-20261115.md)，HTTP见[对接合同](../../docs/integration/case-allocation-http.md)。本步登记Case首轮任务，不启动Case执行器或周期任务。

先以显式profile执行`install_reader.py case-allocation --profile <配置文件>`，应用[129增量](../database/case_allocation.sql)。复用已有writer/reader与`[analysis]`的时限，不回填旧Case或清数据。新装入口复用同一增量。

- `SOCAI2_CASE_ALLOCATION_CONFIG_FILE`：绝对路径，示例[case-allocation.json](case-allocation.json)。`case.max_alerts=100`限制单Case成员；`source_page_size=200`是完整来源读取的分批大小，不是事件总量截断；关联Case列表`default_limit=50`、`max_limit=100`。
- `SOCAI2_ANALYSIS_TASKS_CONFIG_FILE`：绝对路径，沿[任务配置](analysis-tasks.json)。新案任务保存当时重试策略；事件接收资格按创建/最近正常完成后的自动窗口判断，与分析停止标记分开。
- 缺失/无效配置返回503，无默认环境/数据库回落。Case写入先核配置再开始事务。

新旧Case关系并存；旧记录没有续建字段时读取continuation=null，不自动猜选root。新分配入口对该旧记录返回case_continuation_unavailable，目标上线不另做迁入/回填；既有旧Run查询保持。

[发布片段](case-allocation-release-fragment.json)列明核心、ORM、配置与迁移依赖，配合HTTP第5步片段整体使用。原部署profile未改；原`validate_flow.py`是历史同步固定流程工具，不能用于验收本候选。当前验证用[本步真实PG批次](../../docs/operations/evidence/case-allocation-20261115-01/README.md)，后续第6–11步完成后再做完整异步流程联验。
