## Why
用户选定近24小时有新告警的事件及高严重程度事件，与已有活跃事件、待分配组成四项统计，撤去状态未提供统计。当前窄屏隐藏该区域，也需使四项可见。

## What Changes
- 右侧摘要改为四项，原有关联调查/队列压缩卡保留。
- 24小时按当前浏览器时间与成员告警发生时间计算，事件去重，排除未来/无效时间。
- 四项摘要按可用宽度换行，窄屏不隐藏。原例子、时间及状态不改。

## Capabilities
### Modified Capabilities
- frontend-versioned-investigation-workspace: incident summary metrics.

## Impact
仅本地4174前端、直接验证和交接。无后台、模型、真实数据操作、部署或Git提交推送。
