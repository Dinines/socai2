# 成员告警页操作组对齐

2026-11-02，用户要求添加告警/事件按钮不要位于标题行中间。

原标题行有3个直接子元素，space-between将添加按钮分到中间。现标题保左，移动和添加作为右侧单组，添加置最右；局部CSS保8px间距与窄屏换行右对齐。按钮动作/样式/选中状态逻辑及数据不变；PRD6.2同步布局。index更新缓存。

改前4文件保留于.local/versions/case-member-actions-before-20261102。app.js语法通过；复用functional-flow既有14项全通过，无新增测试。默认1265px与700px浏览视觉核对通过，截图.local/versions/case-member-actions-wide-20261102.png和case-member-actions-narrow-20261102.png。临时tab32关闭，viewport恢复，未点击业务操作或保存数据。

未参与实现者current_workspace_review已完成源码、PRD、回执与宽窄视觉审阅，限定ACCEPT、0项必须修；按钮动作及选中逻辑不变，CSS范围明确。仅前端布局，不改业务流程，不发后台/模型/响应或部署，不提交推送。已按纯布局skip_specs归档；归档时Why篇幅较短提示为非阻塞。封后严格验证当前9项、归档73项通过，0失败。
