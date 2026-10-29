## Why
用户要求提供整合后的数据展示，原设计数据可以保留，同时包含AiSOC已有结果。当前默认Case排序/旧文档入口指向原样例，20历史Case的案件材料未汇集，历史告警的事件ID未加载时会落到默认样例。
## What Changes
- 保留全部原样例，AiSOC案件在默认列表靠前，标明资料来源，列表与筛选统计对应。
- 补齐20保存告警中已有事件关系；统一历史Case的查询/工件/活动入口，保持原Run输入与来源。
- Case与事件互相连接；不存在的对象显示空态，不回落原样例。
## Capabilities
### Modified Capabilities
- frontend-versioned-investigation-workspace: consolidated recorded Case materials and navigation.
## Impact
仅本地V2、既有离线材料适配及文档；不修改源快照、告警设计、V1、后端、运行数据、模型、部署或Git提交。
