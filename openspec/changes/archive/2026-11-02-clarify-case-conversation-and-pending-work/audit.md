# 验收与结束审计

## 本批范围

统一基础调查、AI对话调查记录、人工任务的页面职责。保留源记录和旧准备兼容，不实现后台执行、模型调用、部署或提交推送。

## 直接证据

- `npm run check --prefix prototypes/security-pages-v2` 语法通过。
- 5份定向套件：case-assistant、case-reading、case-workflow、case-exploration、functional-flow，共76项通过。覆盖23个Case和21个Run共享解析/呈现、无查看写入、范围隔离、图谱明确加入、人工任务源保留与去重、历史Run进度提示、三种告警入口进入助手。日志 `/tmp/case-three-flows-final-tests.log`。
- 全量初次检查171项131过40失败：3项本批功能预期变化已更新并在76项内通过；剩余37项为旧套件加载器/旧断言问题。6份旧套件用本批改前文件在临时副本与当前源码对照，各76项39过37失败，失败名称集合相同，不宣称全套通过。日志 `/tmp/case-three-flows-before-legacy-tests.log`、`/tmp/case-three-flows-after-legacy-tests.log`。
- 浏览验证概览单进度、人工摘要、旧准备任务编辑带原告警/对象/来源调查；案件故事基础调查记录；历史对话仍常驻三个建议；真实socai2案例同布局、无类型不补造；1265宽与700宽检查。窄屏面板改为左右8px，实际left=8/right=677，未横向溢出。
- 浏览未发送问题、启动调查、保存业务修改或重置数据；所有写入流程只在隔离VM测试。临时浏览标签结束关闭，用户原标签保持。
- 截图：`.local/versions/case-three-flows-overview-20261102.png`、`.local/versions/case-three-flows-chat-narrow-20261102.png`。改前文件：`.local/versions/case-conversation-pending-before-20261102/`。

## 独立复核

由未参与实现的current_workspace_review复核。初审指出历史Run入口丢失活跃提示、告警AI入口仍进旧草案，以及PRD现行段落冲突；均已修正。最终限定 **ACCEPT，0项剩余必须修**。独立复跑原相关61项及修复后30项通过；主线补齐700宽最终截图与边界值，恢复viewport并关闭临时标签。真实执行及结论保存闭环不在本次验收范围。

## 保持未接入

真实发送处理、按需工具、基础调查自动排队更新、AI结论保存成为正式记录尚待后端；本批不伪造结果。人工结果仅供引用，不自动覆盖案件判断。历史源数据除明确演示Run类型/标题元信息外保持。

## 归档结果

已归档并同步2条新增、5条修改规格。封后`--all --strict`为9过0失败，`--archived --strict`为77过0失败。未执行Git提交或推送。
