# 4b 来源识别本机验收

2026-11-17。按[设计§12.15](../../../../openspec/changes/schedule-streaming-investigation-updates/test-service-and-4177-http-20261115.md#1215-4b当前子步按lyc来源直接识别测试材料2026-11-17)完成本步。新生成材料来源默认 `lyc-telemetry-01`，工作台示例前缀配置为 `lyc`。来源保留在后台用于关联和页面标识，不作为模型业务输入。

页面通过现有业务HTTP读取所选Run的冻结来源：Case用已核身份的C1，告警/事件用本轮输入工件。全部成员命中为“测试数据”，部分命中为“含测试数据”；缺失或读取失败显示未确认并保留流程。旧账本只补充精确主体和Run的登记，不能把同Case所有轮次染色。来源及租户字段、业务HTTP合同和历史原答未改。

| 验证 | 结果与证据 |
| --- | --- |
| 来源分类 | [5组Node检查](source-check-02.log)通过；使用21本批6个已存Run的HTTP原件，覆盖告警、事件和Case两轮。另用内存派生材料检查lyc、混合、缺失、换轮及失败，不冒称新lyc已投放 |
| 新模块和配置 | [7项挂载/配置检查](viewer-mount-check.log)通过；空前缀字符串被拒绝，旧配置无前缀时关闭新识别 |
| 生成配置兼容 | [19项及17子项](fixture-check-02.log)通过；新来源默认lyc，业务产品名仍为Endpoint Collector，历史转换不改来源 |
| 模型输入 | [测试模块20项](../test-lyc-source-20261117-01/input-boundary-review.json)通过：当前A/I/C3/Deep/C6构造器及prepare_request，后台直接字段、结构化数组、OCSF JSON和序列化封套中的唯一lyc标记均未进入messages。后台原件、业务同名字段及0/false/有效空列表保留；没有真实模型调用 |
| 浏览器 | [本机无账本预览](browser-verification.json)通过：Case与事件首轮1条/后轮2条逐轮识别，告警1条，实际流程继续可读。只读代理21，未更新21 |
| 独立复核 | [测试模块限定只读复核](../test-lyc-source-20261117-01/viewer-source-review.json)通过，无本范围发现；错Run原件、取消读取、关闭识别和普通后轮不继承测试登记另有直接探针 |

实际21旧来源仍为 `telemetry-channel-02`。浏览器预览仅为复用已有原件，在本机显式配置 `lyc` 和该旧来源前缀；交付示例只有 `lyc`。没有修改旧材料来冒充新前缀。未来真实投放须先按现有流程登记匹配的来源ID/类型，Docker镜像和21配置仍是上批已发布版本，本步没有重建或发布。

初次Node驱动缺A/I trace回执及夹具检查漏PYTHONPATH分别保留在[初次回执](direct-check-initial.json)、[初次夹具日志](fixture-check.log)；补充[4次只读trace GET](live-traces.json)和正确环境后通过。测试模块自己的驱动失败与后续修正也在其报告中保留；未改产品行为来掩盖失败。

本步0新投递、业务写入、模型生成和21部署。临时58481预览完成后已关闭，原4177保持。本次只关闭4b来源识别子步；报告直达指定主体/Run、D5/D6及完整change验收仍待。
