# 工作台任务1：导航验收准备

当前补充：**任务1源码接线与已保存HTTP目录的独立只读复核通过，范围见[独立复核回执](independent-review-01.json)**。核对新增19份真实列表响应的SHA、17条完整目录查询、7主体/9Run/10task及分页与轮次/任务关联；现有JS直接检查16/16通过，未发现实质阻断。测试来源与业务发现解耦，no_changes没有被计为新轮次。未独立运行浏览器或验证21部署；实现者浏览器观察另由其正式回执记录。任务2冻结来源流程、Docker交互验收脚本及新批追加执行不在本步结论内。本次无新网络、业务写入、模型、源码修改或发布。

以下保留本步开始时的准备状态与当时缺口；列表原件缺口现由[新增只读HTTP回执](../workbench-subject-navigation-20261117-01/http-directories-01/index.json)补齐。

收尾补证见[独立复核02](independent-review-02.json)：当前源码SHA与01记录及实现者validation均一致；定向复核列表错误不再停留“加载中”、任务目录错误不显示假0。已接收[实现者浏览器回执](../workbench-subject-navigation-20261117-01/browser-review-01.json)的11项观察及453px窄屏证据，保留首次过早观察/等待超时及复验，不计为本聊天独立浏览器验收。宽屏覆盖未生效，宽屏仍未验；未重复运行测试或启动下一步。

状态：**prepared_not_navigation_acceptance**。本目录只保存已有记录的关系预期，未执行新页面/服务或业务测试。

[preparation.json](preparation.json)从新02的final-pg.json和final-http-01.json只读整理，保存原文件SHA与每个主体/Run/task实际HTTP详情的数组索引及路径。2Case共3轮、1事件2轮、4告警各1轮，共7主体/9Run/10task；整案no_changes任务无attempt/Run。未新增HTTP、数据库查询、业务写入或模型调用。

关键缺口：318GET包包含实际详情、步骤与原件，但没有三类顶层列表、主体Run目录列表或主体analysis-tasks列表的完整响应。旧4177读回摘要/hash也不能当完整响应回放。本步提供方需补必要只读GET，或明确将派生列表标为受控夹具，不能伪造来源。

直接判据见[功能用例：工作台任务1](../../../../openspec/changes/schedule-streaming-investigation-updates/functional-test-cases-20261115.md#工作台任务1主体与轮次导航的直接验收准备2026-11-17)：默认Case/三类读取、不依赖账本、列表/任务/Run分页、Case与事件多轮、简单告警分诊、无Run任务、选择隔离、合法空态/错误及只读。accepted无Run、多attempt和空/错响应复用明确受控组件样本，不创建新业务去制造状态。

本步不验证任务2的整套冻结A/I流程，不开发Docker验收脚本，不跑新Kafka/模型、不发布。已有结果数量和旧浏览器通过不等于新的主体导航已实现或已通过。
