# V2 字段对照核验（2026-10-28）

范围：只更新 `docs/design/incident-investigation-page-analysis.md` 第17节及最新说明、`docs/README.md`、`PROGRESS.md`和本change。复用既有告警九列、90项页面映射、表字典及原件；无业务/页面行为变化。

## 来源与统计

- 主来源：`.local/verification/alert-reset-replay-20261025/replay/observed-final.json`，保存时间 `2026-10-25T03:59:33.440538+00:00`，SHA-256 `e751eb2e57790dbc696c931d5179b4e780bcdb8bab089286c880ec497eae1ec9`。这是已保存样本，不是本轮线上查询。
- 本机直接重数：6Alert/6Run/92事件/77工件/11成本行；36调用157310tokens，全部未计价。6条告警有3个Fusion事件ID，每组2条；6条Case/负责人均NULL，资产关联查询0条。零关联只描述本批，不代表系统无资产/用户。
- 49条tool_call，48条非空preview/1条空，最长200字符，事件duration_ms均0；不能当完整返回或实测零耗时。
- 5份Chain中2success各1候选、3empty；5份Path均not_linked；5份Alert Graph均success。按工件JSON外层kind封装读status/data，避免把content根节点空数组误当真实链为空。
- V2保存的21 Run投影：81步骤/49工具/77工件目录。与92事件差额是6条llm_call+5条graph_usage，没有判成数据库缺记录。
- V2全新初始数据经本机Node VM只读组装：67告警/12事件/16 Case/15 Run，52条告警匹配12样例事件，追加真实记录无对应事件行。浏览器个人localStorage不在该统计范围。
- 20历史及10月21日Case依原manifest/原件分别引用；未与10月25日批次合并成线上库存。

## 直接检查

- 复核本地AlertResponse/AlertDetailResponse、CaseResponse及Case启动最多3条输入；本地源码不代表本轮线上部署验收。
- 第17节9个相对文件链接有效；统计、Fusion归组、Run锚点、完整性、图状态及步骤差额断言通过。
- 本轮前后31个V2文件hash一致，无新增V2文件；本轮没有编辑页面、后端、其他活动change或旧回执。前端hash范围不包含Python缓存。
- `openspec validate reconcile-v2-alert-flow-field-mapping --strict --no-interactive`通过，skip_specs允许零规格增量。
- 本机统计与校验记录：`.local/verification/v2-field-mapping-20261028/{field-coverage,ui-projection,frontend-before,verification}.json`。不放凭据或模型原文到本change。

本轮无新远端业务读取、数据重放/清理、模型调用、业务测试、运行配置变更、部署、Git提交或push。只核数据可对应性，不追认旧质量问题、新调查v2发布或整流程能力。

## 结束独审

由未参与本轮编写的 `/root/workspace_review` 独立只读复核，结论 **限定ACCEPT，0项必须修**。确认3个Fusion组/未进入事件行、49工具/77工件/92→81步骤差额、Chain/Path状态、字段路径及规则空值、状态/完整性/Case关系分离均准确；9个相对链接有效，31个V2文件hash一致。范围仅本节及文档change，不覆盖统一图实现、线上接口或调查内容质量；审阅没有修改文件、访问远端或执行业务/模型测试。

完成后以 `--skip-specs`归档；`openspec validate --all --strict --no-interactive`为9通过/0失败，`--archived --strict --no-interactive`为32通过/0失败。未修改业务规格。
