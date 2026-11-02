## Why
助手更像说明表单，问答缺少左右层级；案件背景和来源挤占对话空间。用户要求按聊天布局重排，并把案件标题转化为可用的初始输入。
## What Changes
- 系统消息左侧、用户问题右侧，主区只突出聊天。
- 压缩案件与范围上下文，引用默认折叠；保持真实预览提示。
- 首次打开预填与案件/所选范围相关的可编辑问题，快捷问题只填入不发送；不覆盖用户已写内容。
## Capabilities
### New Capabilities
### Modified Capabilities
- `frontend-versioned-investigation-workspace`: 清晰的聊天呈现及未发送的首问。
## Impact
仅本地助手呈现/输入行为、当前PRD和定向验证；同一Case解析、历史、来源数据和未接后台边界保持。不发模型、工具或真实Run。
