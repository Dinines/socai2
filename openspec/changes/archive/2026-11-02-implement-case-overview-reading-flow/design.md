# Design
统一由flowCaseOverview呈现所有Case首页，forCase仍负责原来源过滤和历史Run引用。首页按轮展示结果与原输入，当前成员只作案件范围；右侧使用已记录停止原因、建议和未完成任务，无内容就显示正常空态，不合成联合结论。

Run内容保原六视图与view键，process命名AI分析，已采用摘要和引用按原内容显示。引用只在同Run tools/artifacts中精确匹配；没有引用不按文本猜测采用。tools的query参数仅可选择当前Run中具有对应ID的记录，非法ID显示缺失，不回落其他Run。切换Run清除旧query/artifact，查看和返回均不改变数据。

修改app.js、investigation-workspace.js、investigation.css、index.html及直接测试/说明。完整示例、13条实际Run、原始数据与图谱源码保持。先跑相关脚本/测试，再全量现有前端检查，宽窄浏览与独立结束审阅。未接后台的启动流程不通过按钮冒充完成。
