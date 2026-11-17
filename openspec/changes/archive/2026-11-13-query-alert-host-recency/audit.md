# 独立结束审计

审计者：`alert_host_end_audit`，未参与本变更实现。2026-11-13。

## 当前结论

本地核心、真实HTTP/PG回执、冻结文件、E71文档及正式两端发布后回执独立审计通过，**最终ACCEPT，可归档**。未发现剩余阻塞；E70旧指南矛盾已修正。用户要求暂不提交/推送Git，保持执行。本结论不核销页面接线、AI对话、真实响应或模型质量。

## 规则与实现

- 原设计第4节将“相关告警：同主机最近发生7条”与人工反馈的相似历史复核分开；未限定起点前的历史时间窗。当前设计和指南明确查询已保存的最新发生记录，可包含起点之后，没有额外天数窗口或分页参数，7是条数。
- 起点与候选只使用latest_material_id下主机对象，限制同租户、同告警source_namespace、同对象namespace及normalized_value；排除起点自身。不要求战术相同，不根据IP/资产ID/名称相似补主机身份。多主机取并集，告警去重且保留全部对象对。
- SQL在过滤和告警分组后计算完整total，再按event_time/alert_id倒序取实际配置上限。未知候选发生时间排除，起点未知时间仍能查；没有材料/有效主机返回空范围。已关闭和误报判定原样返回。
- 单次事务为REPEATABLE READ READ ONLY。核心只读现有表，不调用模型或调度；外部路由只经contracts/dependencies/ports接入，不把SQL或内部调查实现混入HTTP包。沿用页面读取开关和alerts:read，不依赖Case写入能力。
- display_limit来自独立JSON文件，当前7，拒绝非法值/格式/文件503；新包络复用原AlertFacts/ExplorationObject，不修改原告警字段或E30/E66/E70规则。

## 独立复核证据

证据目录：[alert-host-20261113-01](../../../../docs/operations/evidence/alert-host-20261113-01/)。

- 独立复算verify-http：17次均GET，14次200、2次422、1次404。以sql-before的20条告警和实际最新材料/对象重新匹配，完整命中9条，HTTP恰好按发生时间及同时间ID倒序返回前7条；原记录中起点之后的候选、不同战术候选和早于30天的匹配均遵循本次规则。
- 对返回的16对主机来源逐一核对对象ID、告警/材料ID、类型、namespace、键、原值、规范值和字段路径，均与SQL快照相同。独立沿每个`$.raw_json.objects[index].value`访问实际材料JSON，原值相符；双方均是对应告警latest材料。多主机/重复来源全部保留，候选没有重复。
- 4表alerts、alert_materials、alert_objects、alert_assessments查询前后完整行相等；原误报及关闭状态保持。错误namespace/source、旧材料、仅IP、主机大小写不同与未知候选时间不混入；无主机/无材料为空，起点缺时用已知候选正常返回。
- 10个补丁文件当前仓库和`/private/tmp/socai2-http-runtime/alert-host-20261113-r1`分别计算hash，与frozen-files全部一致。独立比对前版OpenAPI，原70操作和150运行schema保持；新增1操作和3schema。
- 审计者运行本change严格OpenSpec校验及现有HTTP边界3项测试，全部通过；未执行新业务请求、全仓回归、模型或数据库写入。首次实现侧Ruff导入格式及pytest未设PYTHONPATH的失败已记录，后续修正不冒充业务失败或隐藏旧失败。
- 冻结候选读回7次GET均200，实际71操作；total9/returned7/source_hosts3，精确按源告警路径取得的前后完整facts相等。该结果是本机独立合成批，不冒称生产正例。

## 文档与收口

- [E71指南](../../../../docs/integration/alert-host-http.md)与候选Swagger docs18保持单一路径参数alert_id，无查询参数，归告警类。3个新schema共12个输出字段均有说明；成功/空页及7个错误响应示例由审计者另用JSON Schema验证（9个E71响应例）。示例起点、候选、主机对象和材料身份及共享值一致。
- 当前候选包记录71操作/69实现/2对话暂缓，162文档schema/764固定输出字段，125功能分组22/15/88保持；全部示例回执为27请求/637JSON响应/3CSV。空页不表示安全、原状态/判定保持、E70和E71条件分开均准确。
- 首次审计发现E70指南仍写同主机最近7条未实现。主代理已改为E71链接，并重新生成sources/alert-review-http.html；审计者复阅源文及静态页均正确。该改动不涉及业务代码或重跑业务测试。
- 两端实际加载、查询/来源读回、Swagger静态包与入口已按下节完成复核。0生产写入/0模型边界保持；主代理继续完成归档、相对链接更新和归档后严格校验。


## 发布后独立复核

- API实际为`alert-host-20261113-r1`，本机后缀`-local`、PID63814；21镜像`sha256:44e7886ab660016b63980126d91d61570e7b6f247aa41159629293455c7bee2a`。两端OpenAPI读回各71操作，数据库目标分别为v12_upgrade_dev和aisoc。
- 独立逐项比对两端`loaded-files`、冻结清单及当前仓库/正式本机源码，10个补丁文件hash均一致；未将并行模型变更冒称本批已发布。
- 正式本机7次GET均200，total9/returned7/source_hosts3；21既有记录8次GET均200，total2/returned2/source_hosts1。返回顺序、来源范围及主机匹配值相符，起点的前后完整facts逐值相等。两端均精确比对第一候选E28 facts，并沿双方E31材料的实际source_path取值：本机为`$.raw_json.objects[0].value`，21为`$.raw_json.hostname`，均与返回raw_value一致。21第二候选未另行逐条回查原件，不声称全库或模型质量验证。
- Swagger docs18两端39文件清单、14个HTTP入口回执相同且入口均200。审计者另计算当前仓库包和正式本机冻结目录hash，与清单及各HTTP内容hash一致；根`deployment-receipt.json`与本批回执相符。OpenAPI SHA为`20238ae3a7d5ddb17dd351829573d39357f319c4b7ca854e40ddaf9b01f93a7e`。
- 当前统计为71操作/69实现/2对话暂缓、162文档schema/764固定输出字段、125功能22/15/88；最终示例回执27请求/637JSON响应/3CSV通过。E70/E71的用途与规则区别、输入及来源字段保持；实施计划中旧版本数量已原位纠正。
- 两端Swagger首次首查分别遇启动未就绪的RemoteDisconnected/ConnectionRefused；initial-check-notes保留，未纳入成功回执；随后只重读静态内容，没有重复部署或重派业务。其他36个21容器保持。preview-stop记录61488/18026已停止、正式API保留。
- 本次最终审计只读既有回执和文件，未再发业务请求、未写数据库或调用模型、未提交和推送Git。发布事实、文档和聚合回执一致，满足本change归档前条件。

## 归档回执

主代理已执行`openspec archive query-alert-host-recency --yes`并同步2条主规格要求，更新Purpose与归档相对链接。归档后严格校验：全部36/36通过，归档35/35通过，0失败。未新增发布、业务请求或Git操作。
