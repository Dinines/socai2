# D3 C3单元恢复独立测试

当前状态：D3a原26项通过，D3b独立8项及受影响D3a 26项合计[34/34通过](d3b-attempt-03/execution.json)，D3c同一保存/HTTP包的[59项只读复核通过](d3c-readonly-03/review.json)。**D3本机范围通过；D4–D6、21发布及新版本4177尚未验证。** 测试模块本轮未连接数据库或网络、未调用真实模型；调查模块唯一PG/Redis任务使用3次明确受控回放，非新真实模型生成，正文质量仍not_checked。

母本来自D2 real-02同Run的完整真实C3原答，实际请求和来源身份见[fixtures-01/manifest.json](fixtures-01/manifest.json)。正文7,516个Unicode字符，22个完整原值单元；原件`c6791985-b981-4a6c-b12d-3a848d9fe845`，正文路径`$.raw.choices[0].message.content`。F1/F2是observed且原答没有statement；原unit.value不补写statement或把模型别名改成UUID，程序恢复与下游使用另外核对。

[prepare.py](prepare.py)只解码完整母本，用原字符位置及独立边界标定预期，不读取产品恢复器结果。[8个前缀变体](fixtures-01/manifest.json)包括完整stop/length、F1闭合F2半项、根结束符缺失、空正文和固定seed=20261116的3个随机切点1724/1753/5207。F1半F2的独立预期为summary、4成员、F1共6单元，F2和后续章节不可从完整母本补回。

[prepare_boundaries.py](prepare_boundaries.py)另生成[10个边界变体](boundaries-01/manifest.json)：空白、含括号/转义的完整正文、半个Unicode转义、未终止数字、单元内重复身份键、根重复members段、未知成员、显式空followups/缺失followups、完整followup缺已保留问题。它们均明确标为受控派生数据，不冒充新真实模型输出；缺陷分支的允许/禁止项由合同显式列出。

[prepare_structure.py](prepare_structure.py)按明确策略补充[2个列表保护变体](structure-01/manifest.json)，此时共20个夹具：F1/F2使用同一ID时两项均隔离；第6条发现超出冻结5条上限时只隔离第6条，保留前5条合法原项，明确`section_item_limit_exceeded`和partial，不把原6条答复伪装成模型只给了5条。原数组序号与全部原答保持。

[字段顺序对照](order-01/manifest.json)另加1个语义完全相同的母本：domains/conflicts在findings前，仍应使用最终保留发现集合做引用诊断。当前共21个夹具，不能因JSON键顺序制造缺失发现；各自span仍按对应原字符串核对。

补答失败、C6实际输入、保存回执及HTTP已按下述D3b/c实际交接复核。功能入口按调查设计：`case_c3_sections.read_units`、`case_c3_delivery.receive`、严格`stage_delivery`；单元span为原正文Unicode左闭右开，SHA取原区间UTF-8，缺失与显式空列表分别核对。来源和准备校验记录不替代接收/保存/读取验收。

本批HTTP沿现有Run返回的steps_url/artifacts_url完整游标分页，再取content_url。工件查询仅有limit/cursor/step_id，不虚构kind/type/schema过滤；步骤的input/output/reused三指针不等于全量工件，step_id也不递归子步骤。新stage_delivery已挂同一C3阶段step_id并由完整目录发现，正文逐值读回通过。HTTP availability/material_state和正文delivery/quality分别判定，不能把回执可读当模型完整。本批为ASGITransport接真实隔离PG，未验证21 TCP或4177浏览器。


## D3a实际执行

[独立测试文件](../../../../services/api/tests/test_socai2_d3_units_independent.py)显式加载当前r3引用的r2正式policy，C3输出16384；使用D2 real-02同请求冻结context/source_map/binding和当前接收实现。测试中禁止socket，不加载旧本机默认配置。21夹具分别走实际receive→严格stage_delivery→原字符串来源复验，5项保护核错原件、错正文路径、越界span、原件变化及未保留动作被拒绝。

26/26通过，64份源码/配置/原件/预期文件运行前后摘要不变；[JUnit](attempt-01/junit.xml)、[执行输出](attempt-01/pytest.txt)、[运行时源码归档](attempt-01/tested-sources.zip)、[来源摘要](attempt-01/source-manifest.json)及21份逐夹具stage_delivery/派生analysis均已保存。每份原单元value/span/SHA、声明与实际引用范围、原数组序号和下游资格分别核对，不将程序观察正文或UUID恢复冒充原模型value。

完整length和缺根闭括号仍保留完整内容；F1闭合/F2截断只保留预期6单元；重复定义双隔离、超额第6项明确无效/partial、根字段重排不污染诊断、未知身份不接收、未闭合内容不产生单元、显式空与缺失分开，缺问题的完整计划保留但不能派发。质量仍not_checked，C3不产生采用/比较资格。保存/HTTP及实际C6继续不由这些离线回执代替。

## D3b接线独立验证

[独立用例](../../../../services/api/tests/test_socai2_d3_continuation_independent.py)显式加载当前r3引用的r2 policy和最新case profile，C3/C6输出均16384。用D2冻结告警原件重新构造当前C3业务输入，使用新离线context/view/run身份；历史D2原配置、请求和正文不修改。[派生说明及实际输入](d3b-attempt-03/cases/derived-fixture.json)逐项说明变更，F1/F2引用仍核原字段路径、角色及成员范围。此次无可选富化和工具候选，不能称作复跑完整D2。

6种控制器情形覆盖补答禁用、预算未发出、空白、无效、F1冲突且F2完整/F3再次截断、补回剩余发现：最多一次补答，初答6单元保持，补答的完整独立项按自己的原件和span保留，冲突不覆盖初答。每种情形均调用实际C6输入构造器，按实际保留集合传递prior_analysis；未收到F2时不补回，未收到questions/followups时不伪造空列表，模型正文不含回执ID/span/hash台账。另核空findings不丢4个undetermined领域，以及C4原索引0缺依赖skip/索引1仍handoff。

最终34项通过（D3b 8项+D3a 26项），86份源码配置在执行期间未变。[首次收集失败](d3b-attempt-01/pytest.txt)来自测试启动漏设PYTHONPATH，未运行功能检查；补环境后的[第二次34项通过](d3b-attempt-02/execution.json)保留。第三次仅在Ruff整理测试import后核对最终源码。准备时使用相对policy路径曾被明确拒绝，改为绝对当前路径；未回落旧环境或修改业务代码。

## D3c同批保存与HTTP只读复核

调查模块唯一执行包见[pg-http-01](../c3-unit-continuation-d3-20261116-01/pg-http-01/result.json)：新Case `1576d3fa-a518-5db2-9781-33347eec1fa2`、Run `1dd4d4dc-b303-4bf8-abb1-8347208a4e17`，真实本机隔离PG/Redis任务链、3次受控响应、0次新真实模型。链路为C3闭合F1/半F2→空白补答→C6→保存Result；16步骤44工件，C3为partial，Result为accepted/uncertain/partial。

[可复用只读脚本](review_d3c.py)只读冻结database/calls/http等JSON，无网络访问。最终59项核对通过：真实母本hash、F1业务字段及显式身份/来源映射、6个原单元的值/span/SHA、初/补答4个请求和原件、同Run阶段回执、实际C6前序F1且无F2/假章节、零C4派发、C6原结论保存、当前配置及预算、完整目录游标和44份内容等值、60次已保存GET及读取前后摘要一致。源包未变，测试模块没有重复业务执行。

[首次只读脚本失败](d3c-readonly-01/review.json)是把HTTP的status误用于数据库task行（实际为state），保留失败；修脚本后[55项通过](d3c-readonly-02/review.json)，随后增加F1真实母本及映射4项，最终59项通过。未改业务数据或核心实现迎合检查。

HTTP模块另外对同一保存包[23组核对通过](../c3-unit-continuation-d3-20261116-01/http-readback-review-01.json)，没有重复请求。当前源码与本批161项来源manifest一致，但该清单未独立覆盖HTTP源码，不能据此称部署包版本已核；本批未实际执行step_id筛选或跨Run读取。

本批受控usage明确标为explicit_test_substitute，不能作真实模型耗费或质量统计。D3网络超时/断连继续不在本步范围，保留D5；A/I及其他阶段恢复属于D4/D5。全change结束审计、部署21及新4177展示仍待后续。
