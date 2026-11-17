# W3页面HTTP字段配合

2026-11-15。本步只读当前源码和W2已保存的34份响应，没有新HTTP、SQL、模型调用或部署，也未修改业务合同。测试侧负责页面实施/直接验证；调查负责人负责整体设计及独立页面查看；HTTP侧负责字段供给及最终保存回执的离线核对。

[路径及DTO说明](../../../../openspec/changes/schedule-streaming-investigation-updates/http-workflow-contract-20261114.md#w3页面http读取路径字段及独立核对2026-11-15)集中列出批次→操作→任务→Run→步骤/原件、结果、来源、新鲜度和错误显示，以及7项最小核验。

[field-map.json](field-map.json)仅从W2真实响应提取：本批7个实际操作、任务入口、真实attempt Run及results链接、必要A/I trace路径、原34份响应位置及摘要。它是页面接线参考，不能当作新业务响应或页面验收结果。批次的3个测试用例与两业务Case分别保存身份；`Operation.case_id`不能替代业务Case UUID。

当前业务80操作/55 GET足够现有S01/S04数据浏览，未发现需新增路由或DTO的缺口。测试服务待提供实际viewer版本与页面接线；A/I通过同Run的trace获取完整目录，Case Run直接提供目录链接。目录翻页和正文按已有content_url读取，Case元数据键artifact、A/I为metadata。

前置供给时W3页面尚未验收，实际读取核对见下方。Task.status只有accepted/running/completed/failed/skipped，unknown位于attempt.outcome或Run；无Run按真实空态显示。两Case仍首轮completed/accepted/uncertain/partial，当前新鲜度stale，比较initial/null；S04失败/3 skip、模型NOT_PASSED保留。实际unknown、大原件、steps直接reused和Case后轮未由本批真实样本覆盖，不通过新业务调用补造覆盖。

测试已提供页面动作和请求/响应回执，HTTP只离线核实际链接/身份、状态、范围、正文来源及必要分页，不重做W2或旧批GET。当前4177和业务HTTP版本未变，W4打包另步。

## 实际页面读取的HTTP独立核对

[browser-readback-review-01.json](browser-readback-review-01.json)复核[测试唯一浏览器回执](../test-viewer-w3-20261115-01/requests.jsonl)：51条请求记录，48个200、1个favicon404、2个静态304；其中26个业务GET全200、同环境及现行合同。40份落盘响应摘要核对通过。HTTP没有额外请求，也未单独打开另一浏览器；页面视觉和整体审阅由调查负责人完成，不能用此记录替代。

任务与结果来源、两案原partial/initial/空比较及当前stale、I失败current但valid=false、3条skip无Run均保持；Case48工件按20/20/8完整读回，C1及原I输入、I失败原答与W2相同。来源保持原主体/Run/content_url/摘要/3成员，不扩大为当前4成员。共享use_case_id造成的操作混入已由测试/根修正，每页按TestCase.id匹配Operation.case_id；原发现保留。临时端口已关闭，账本不变，终态30.94秒无新请求。

本记录通过的是本批真实页面HTTP读取和合同对应；实际unknown、超过1MiB原件、steps直接reused及Case后轮不由该样本覆盖。S04正向更新/比较和模型质量未通过保持，未发布或提交推送。


## 最终冻结补记

测试[最终验收](../test-viewer-w3-20261115-01/acceptance.json)和[source-final.json](../test-viewer-w3-20261115-01/source-final.json)已冻结为0.3.0；HTTP[最终摘要复核](final-freeze-review-01.json)核23份文件均一致，原51条请求及前述独立复核未变。末尾补充终态页面恢复不刷新、运行/中断恢复和目录展开暂停父级轮询，以及C1的“原事件冻结选入/覆盖”与“本案选入/覆盖交集”；这些修改使用受控测试/同组保存材料离线核验，未重开浏览器，不能描述为最终源码全部重新经过真实浏览器验证。8项Python及8项JS检查通过，HTTP没有重复运行测试或请求。S04正向链、模型质量和整个change仍未通过，原限制保持。
