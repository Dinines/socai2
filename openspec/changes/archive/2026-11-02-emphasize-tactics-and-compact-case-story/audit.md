# 限定验收

## 范围
战术标签共享色表及故事紧凑布局。执行紫、命令与控制蓝、横向移动青；覆盖与故事一致，其他已知战术沿色表，未知中性。分类和严重程度分开，不改任何源数据、调查结果、计数或交互控制器。

## 验证
- case-assistant与investigation-workspace语法通过。
- 既有assistant/reading套件29项通过，初次2个精确HTML断言在加入class和前批icon后失配，改为忽略装饰再核业务值；未新增简单样式测试。
- 正文与浅底颜色对比最低5.92:1，各组5.92—8.11:1；标签文字保留，不仅依靠颜色。
- 1265宽故事首行时间/战术/等级，底行资产/提问，三卡均显示；700宽无页面水平溢出（scrollWidth685 < innerWidth700），标签与等级可读。最新在上保持。Case资料覆盖颜色已目视核对。
- 截图：`.local/versions/story-tactic-colors-compact-20261102.png`、`story-tactic-colors-narrow-20261102.png`、`attack-coverage-tactic-colors-20261102.png`。改前5文件在`.local/versions/tactic-colors-story-compact-before-20261102/`。
- 浏览只读，未发送/保存业务记录，临时标签已关闭、viewport已恢复。

## 参考
采用微软Fluent共享色用于标签强调、保留文字和语义颜色分工的原则：https://fluent2.microsoft.design/color 。已查看Microsoft Defender官方Attack story和Summary截图，具体战术色映射为本产品设计，不声称微软标准映射。

## 独立窄审
未参与实现者current_workspace_review限定ACCEPT、0必须修。独立29项、11输入色类/转义探针及diff检查通过，截图及交接相符。真实后台、模型、响应、部署、Git提交推送均未执行。

已按skip-specs归档；封后严格校验当前9项、归档80项通过。
