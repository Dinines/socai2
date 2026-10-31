# 图谱呈现恢复回执 · 2026-10-31

## 范围与实现
用户明确保留最新版功能，恢复之前参考 Microsoft Defender 的图谱呈现，重点图谱画布。本批仅修改调查关系图（事件进入的 Run 与 Case 内 Run 共用）：圆形图标、细灰线、蓝色聚焦、稳定的中心实体与外围布局、紧凑工具栏。桌面为左告警／中画布／右详情；实际容器较窄时详情下置、更窄时告警横排。分列布局及现有所有图层/筛选/分组/缩放/来源材料入口保留。

`build/defaults/visible/focus/ensureVisible/select/reconcile/display/selectedDetail/render/repaint/handle/change` 对照改前版本逐字节一致；仅 positions 和 HTML/CSS 呈现变化。index.html 相对本批改前仅更新两项图谱资源缓存版本。数据文件未修改。历史 V1、先前 V2 ZIP、完整演示与实际13Run保持。本批前的3文件和hash在 `.local/versions/graph-presentation-before-20261031/`。

## 验证
- `npm run check` 通过；`npm test` 68项通过，其中图谱7项。
- 独立审核另执行7项图谱合同，15Run渲染/坐标边界检查通过。
- 真实浏览器1600px检查完整演示与实际Case三栏显示。点击演示A3突出4条关系；实际A2显示3实体/1技术映射；边详情保留neo4j OBSERVED_ON与postgres TOUCHES；IP分组及展开可用；E3仍显示中间边未保存；关闭候选层清除已隐藏对象聚焦；技术选择显示对应告警和映射。
- 恢复浏览器默认约900px，验证告警横排、全宽可读画布和下方详情，截图已保存。后续一次选择器操作报控件失联，随后观察页面已切换到另一事件关系页，不计入成功验证；未据此修改交互控制器。
- 截图：`.local/verification/graph-reference-20261031/design-focus-wide.png`、`recorded-tech-wide.png`、`design-focus-narrow.png`；检查摘要 `checks.json`。

## 独立结束审计
未参与实现者 `current_workspace_review`：限定 ACCEPT，0项必须修。已独立对照改前hash、核心函数、资源版本并执行7项图谱测试、15Run渲染与坐标检查；查看两张宽屏图未见明显遮挡/缺项。窄屏及实点采用上述主代理回执。

仅验收本批呈现重构，不替代活动 `integrate-unified-investigation-graph` 的整体收尾，不据此宣称后台能力或实际调查质量通过。无后端/模型/新数据请求/部署/Git提交推送。

## 归档
已执行 `openspec archive restore-reference-graph-presentation --yes --skip-specs`；主规格未改。归档后全量与归档 strict 校验通过，`git diff --check`通过。CLI仅提示Why段少于50字的非阻塞文案建议。
