# 4177 节点详情

用户要求将流程向左收紧，在右侧直接查阅点击节点的输入、输出、模型提示词及失败原因。本批只修改内部查阅工具和其部署；复用已保存的 Case、A/I 原件，不触发模型、调查、消费者或业务写入，不改变告警交接字段和数据库。

## 设计与直接验收

- 桌面采用左侧流程、右侧详情；窄屏上下排列。选择模块或轮次后清除旧选择，避免串轮展示。节点可用键盘操作，保留原件锚点和无脚本查阅。
- 使用本页已保存的步骤、Run 和工件建立索引，按需解析、展示，不再嵌入一份完整 JSON。模型节点分开显示 system/developer 提示词、输入消息、输出约束、模型原答、校验/执行原因及完整原件；有多次调用时每次独立可选。
- 阶段显示自己的输入、输出和关联子步骤；查询显示实际参数、返回行数及错误/跳过原因。Deep 模型失败时仍显示实际调用节点，不以没有动作回执隐藏调用。
- 未记录、未分派、跳过、失败、零行和部分交付各按原状态说明；没有原答不补造，错误码保留；执行完成不代替模型质量通过。文本使用转义或 textContent，原始证据保持。
- 用现有两案快照检查 C3、Deep、C6、A/I、零行查询、跳过和空节点；浏览器检查点击、切换轮次、键盘、长文本及宽窄屏。核对展示值与原件，更新 21 的工作台及保存页面，验证实际加载来源。

## 实施与验证

- 实现使用原件的 DOM 索引按需解析，未复制整份证据 JSON。详情标签分开提示词、消息／Schema、模型原答、执行／校验原因和完整记录；保留原件锚点。Deep 每次实际调用可选，未生成动作继续显示未记录。
- 独立审计发现冻结输入工件被当作输出，已修正并在 C1 与 I 浏览器逐值复核。原件打开后重选同一节点的锚点滚动也已修正。跳过节点提示不宣称一定保存了模型原答。
- [30 项定向测试](../../../docs/operations/evidence/workbench-node-inspector-20261110-01/tests.json)通过；[两案 307 条 Run／步骤／工件](../../../docs/operations/evidence/workbench-node-inspector-20261110-01/record-preservation.json)与输入快照逐值一致。没有新模型调用或业务写入，告警字段、表设计和原失败保持。
- 21 工作台组件为 `workbench-20261110-r2`，固定镜像保持；[发布](../../../docs/operations/evidence/workbench-node-inspector-20261110-01/runtime-publication-02.json)验证其他服务及数据挂载不变，[现场复核](../../../docs/operations/evidence/workbench-node-inspector-20261110-01/runtime-publication-02-verification.json)验证 645 个源码文件和 5 个实际加载的变更文件。主服务仍是 `v1.2-20261110-r4`。
- [静态更新](../../../docs/operations/evidence/workbench-node-inspector-20261110-01/static-publication-02.json)刷新两条登记，199 文件／200 次 HTTP 核对通过；20 条在线登记（含两案缓存）及本机 49 条记录保留。打开线上 Case 已实际触发渲染器指纹更新，快照内容和业务结果保持。

[浏览器核验](../../../docs/operations/evidence/workbench-node-inspector-20261110-01/browser-checks.json)覆盖 C01/C02、A/I、Deep/C6、提示词及输入／原答逐字对应、冻结输入分类、错误／零行／空态、轮次切换、键盘与原件返回；1440×1000 与 390×844 无横向溢出。[线上效果](../../../docs/operations/evidence/workbench-node-inspector-20261110-01/desktop.jpg)保存实际失败节点，未修改原失败。[独立审计](../../../docs/operations/evidence/workbench-node-inspector-20261110-01/independent-audit.json)为 ACCEPT，0 个未解决必须修正项；Git／父项目接着按实际发布回执收口。C3 范围、C6 发现关联和正文事实问题仍归原任务，本批不核销模型质量。
