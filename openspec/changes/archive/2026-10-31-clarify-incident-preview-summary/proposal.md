# Why
用户指出事件侧栏不应将单告警分诊分数作为主体，需要事件整体描述，并询问缺失处理状态含义。

# What Changes
- 保存结果事件侧栏以事件概述替换告警评分块：成员/主机/线索及已关联调查进展，缺少事件整体结论和优先级仍明确。
- 侧栏缺状态显示“处理状态：未记录”，说明不是未调查或未处置。既有新建/进行中/已解决及计数不改。
- 原完整设计样例的优先级呈现保留，单告警详情和原数据不改。

# Capabilities
- 新增 incident-level preview presentation，归入frontend-versioned-investigation-workspace。

# Impact
仅本地4174的app.js/styles.css/index.html及定向测试、交接。无后端/模型/部署/数据改写/Git提交推送。
