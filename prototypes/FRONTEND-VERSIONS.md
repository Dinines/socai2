# 前端当前入口与历史保存

更新：2026-10-31。当前只使用 **V2 / 4174**：[事件](http://127.0.0.1:4174/#/incidents)、[Case](http://127.0.0.1:4174/#/cases)、[调查运行](http://127.0.0.1:4174/#/investigations)。完整演示样例、实际 AiSOC 案例及边界统一见[当前页面说明](security-pages-v2/README.md)。

在 `prototypes/security-pages-v2` 运行 `python3 serve.py --port 4174`；只监听本机。浏览器状态仍使用 `aisoc-workspace-v2`，不重置已有编辑。旧来源筛选链接兼容为全部 Case，当前21个Case；原19个Case和其余历史数据均保留。

历史全部保存，不作为当前默认设计入口：

| 历史版本 | 保存位置 |
| --- | --- |
| 本次更新前 V2，含10月29日页面与设计文档 | [ZIP](../deliverables/history/security-pages-v2-before-20261031.zip)、[SHA-256 清单](../deliverables/history/security-pages-v2-before-20261031.manifest.json) |
| 冻结 V1 | [原目录](security-pages-v1/README.md)、[交接目录](../deliverables/aisoc-frontend-v1/README.md)、[ZIP](../deliverables/aisoc-frontend-v1.zip)、[原校验清单](../deliverables/frontend-v1-manifest.json) |
| 最初页面与交接 | `prototypes/security-pages`、[交接目录](../deliverables/aisoc-frontend-handoff/README.md) |

需要回看 V1 时，在其目录运行 `python3 serve.py --port 4173`。V1 仍用原状态键 `defender-reference-demo-v1`，文件与浏览器状态均不被本次更新覆盖。

当前页面不等于实时后台，也不代表独立调查 v2 已启用。[设计讨论与数据映射](../docs/design/incident-investigation-page-analysis.md)、[验证回执](../docs/design/frontend-v2-verification.md)保留各阶段日期及适用范围。
