# 工作台任务2：本轮冻结来源的验收准备

**当前结论：任务2本机功能范围通过，未发现实质阻断。** [最终接收复核03](independent-review-03.json)核最终10份源码SHA、4份实际页面资产no-store及摘要、浏览器原始记录摘要、182GET包摘要均一致；浏览器R1/R2来源与独立预期相符，A/I/C6三份所见原答与真实GET原件逐字SHA一致。空I来源定向断言保持未知、不抛异常。已接收实现者18条原观察和14条通过断言，包含1366×900桌面、468×900窄屏及局部来源503后Case/C6/云领域可查。浏览器由实现者操作，本聊天只读复核保存证据，不称独立浏览器运行。21未部署，任务3/4、模型质量及整个change结束审计未完成。

以下保留准备和逐轮复核状态；其中“浏览器待交接”现已由03收口，旧JSON不改写。

最新独立复核：[independent-review-01.json](independent-review-01.json)记录任务2源码与保存证据范围通过，未发现实质阻断。现有8项新增及16项既有JS检查共24/24通过；另按本目录原准备映射核3个Case轮次、全部A/I来源身份/前轮关系/原件与交集，并核D4b两份历史组件材料，均一致。来源错误局部展示、Case自身流程继续可查的接线已读；本聊天未独立运行浏览器，尚未接收实现方最终浏览器回执，不据此宣告页面或部署通过。未改源码、未发新网络/数据库/模型请求。

末修补证：[独立复核02](independent-review-02.json)核缺units保持未知、质量checked不表示通过、业务标题仍保留完整原件，以及静态资源no-store；14项受影响JS及6项挂载检查通过。首次pytest缺PYTHONPATH的收集错误及修正命令保留，未修改应用解决测试入口。[真实GET保存包复核](live-http-review-01.json)核182响应SHA、16完整目录分页、31份正文与02原HTTP逐值一致、3Case/6上游Run身份关系和7份原答。这里复核的是实现方采集的真实GET文件，本聊天新增网络/业务/模型仍为0。最终浏览器JSON及最终版本摘要待交接；旧复核原件保留。

以下为本步原准备记录，`preparation.json`及其状态保持不变：

状态：**prepared_not_page_acceptance**。只读整理已保存材料，不代表新页面通过；本轮新增HTTP、数据库查询、业务写入和模型调用均为0。

[preparation.json](preparation.json)由[prepare.py](prepare.py)从新02的318份已保存HTTP响应提取。脚本核对Run→manifest→C1、实际目录返回的content_url、源Run/结果/材料身份和I输入/响应/回执摘要，不生成业务数据或合成HTTP响应。可在仓库根运行 `.local/conda-envs/socai2/bin/python docs/operations/evidence/test-workbench-frozen-flow-20261117-01/prepare.py`；已有文件只校相等，不覆盖。

| Case轮次 | 冻结告警分诊 | 冻结事件诊断 | 本步关键预期 |
| --- | --- | --- | --- |
| 整案R1 `1ae2cb6e-ee3e-483b-828c-0414d3529917` | 3个A Run，均有可用分诊 | I1 `10535c76-6a2e-5943-8cfc-efcc31c456a9`，总/选/覆盖3条 | 首轮引用，不标“沿用前轮”；切回R1仍是3条，不取I2 |
| 整案R2 `30c0c38c-ee33-4073-bd94-566a73017fed` | 原3个A Run/分诊/材料身份逐值相同，新增A04 `c3cbeebc-4538-52cf-8052-f661d068f418` | 同事件改用I2 `43477be5-cd39-5e48-a7b4-5e2faa69b6e8`，总/选/覆盖4条 | 对实际前轮R1标3A沿用、1A新增、I新诊断；不把沿用A画成再次执行 |
| 单案R1 `1422d925-f8e5-4f6a-84ed-3f9e2a15ca4e` | 仅A01 `83984491-9843-5221-9693-0ba45397f061` | 同样引用I1；原事件选/覆盖3，本Case选/覆盖交集1 | Case保持1成员，不隐去I1，不将I原范围压成1，也不把3成员都算进单案 |

完整ID、HTTP数组索引、源URL、工件摘要和沿用分类在JSON内。8次A引用只有4个实际A Run，3次I引用只有2个实际I Run；这些是跨Case轮次引用次数，不是本轮模型调用或新增执行数。“新增”表示相对本Case前轮首次引用某主体或新分析来源，不表示页面发起了新分析。

少量边界复用D4b原组件材料，与02正常链分开：

- [partial C1](../incident-signal-d4b-20261116-01/pg-partial-02/frozen-context.json)：Case4成员，I总4/选3，仅保留1成员分析；`diagnosis_scope=null`、`diagnosis_usable=false`，但`analysis_material`仍有源Run/输入/响应/回执。页面应保留来源与partial，不扩成3或4条已分析。
- [none C1](../incident-signal-d4b-20261116-01/pg-none-01/frozen-context.json)：I选4、保留0，仍有真实源Run/none回执，不等于没执行，不回落旧可用诊断。两份是受控依赖的历史PG组件读回，组件Case结束为`failed/component_capture_only`；不能冒称完整Case成功或02实际出现partial/none。
- 缺来源只做明确内存副本的最小断言：移除一个A冻结`source_run_id`，或单独令前轮C1不可读；保留真实母本。当前仅列判据，未执行派生测试。缺身份/前轮时标未知，不用latest或同主体ID猜沿用，其他已确认来源仍可查。

直接判据见[功能用例任务2](../../../../openspec/changes/schedule-streaming-investigation-updates/functional-test-cases-20261115.md#工作台任务2本轮冻结来源的直接验收准备2026-11-17)。先验来源解析与组合，再本机只读页面核R2→R1→单案、展开来源Run/原答；HTTP201/202继续绑定本轮实际task，跨Run引用不改变当前Case轮次。实现交接后另存定向复核回执，不改本准备为通过。

本步不开发Docker脚本，不发布21，不补新模型样本、不验证质量准确率，也不展开超时/恢复矩阵。
