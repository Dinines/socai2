# 直接验证

本change实现F23-04/D01，新增E44–E47。未改表、告警字段、模型流程或自动消费者。

## 本机

- `docs/operations/evidence/case-management-20261112-01/local-http/responses.json`：原应用TCP、正常测试key、真实隔离库，20次请求完成字段修改、幂等重放、过期版本拒绝、未完任务两种未确认拒绝、确认后结案、重开、清空可空字段及详情/列表/Run/活动读取。任务未改，Run仍pending_update。末尾脚本误用records而实际返回items；失败保留，修正脚本后仅复核已保存响应，`local-http-review.json`记录，不重复写入。
- `local-sql.json`：全部Case公开字段与HTTP详情一致，仅一个原pending Run，未启动。
- PG首次夹具试图直接插入running baseline被现有数据库守卫拒绝；`pg-checks.json`保留。夹具改为合法pending→running/unknown，仅定向复验该组，`pg-checks-02.json`通过；合成状态不代表实际执行。运行中/执行不明均阻止结案且字段不变；并发两编辑一成一409、同键不同意图冲突、无任务可不填理由结案、非法负责人和跨租户读取、无变化不增加版本、重开不产生Run通过。
- 初始17项定向单测15通过；新增Schema可空标注导致2项null校验抛TypeError，已在长度检查前明确拒绝null，8项本模块定向复验通过，旧9项不重复跑。原失败保留于unit-checks.txt，修复结果unit-checks-02.txt。
- Ruff F/E9通过。原43操作及109文档Schema结构完全保持；新增4操作/6Schema，合成请求响应均通过JSON Schema校验，见docs6-check.json；新输出字段逐项说明，现532个固定字段出现位置、28动态结构。

## 发布边界

21候选基于现独立镜像`1db7027b962b...`，仅覆盖`socai2_cases.py`、`case_management.py`、`case_management_contracts.py`；模型输入并行修改不混入。发布工具/profile显式47操作及替换现独立18024；原主API/旧隔离API保持。本机原生ARM64，21 Docker AMD64。限定独审通过后，按授权完成一次两端服务及Swagger更新。

## 发布后验收

证据目录：[`case-management-20261112-01`](../../../../docs/operations/evidence/case-management-20261112-01/delivery-summary.json)。

- 本机正式18024版本`case-management-20261112-r1-local`、21版本`case-management-20261112-r1`均47操作就绪。21镜像`sha256:4a7bf9bde482bddbc3753a421e4991a98d572ed2663e8a2e464d67b9ead407b6`与候选相同；两端加载三文件摘要匹配manifest，实际读写库分别v12_upgrade_dev/aisoc。
- `local-release-http`与`21-http`各20次TCP全部通过，无认证依赖替换。正式验收Case为`d5ef9c5a-00c9-564a-9fcb-fdb5810f890e`；两端完整Case字段SQL与HTTP相同，close/reopen各一条活动保留原理由及前后值。任务不变，仅一个原pending Run未启动，零模型调用。
- docs6本机ARM64/21 AMD64九入口均200且摘要一致，当前47操作（44已实现、3预留501）、115文档Schema、532固定字段、28动态结构，见[不可变发布回执](../../../../deploy/api-docs/receipts/20261112-docs6.json)。
- `21-start.json`确认原所有其他运行容器在API替换时保持；`21-final-runtime.json`确认文档发布后只有原Swagger变化，原主API/旧隔离API及其他业务容器保持。
- 无数据库迁移，原告警/事件合同、旧43操作和109文档Schema保持；前端页面、真实模型质量、其他缺失接口不由本项核销。主调查仍31/41。未Git提交推送或更新SpiritHub引用。
