# 前端版本入口

2026-10-26：当前前端及原交接包已保存为 V1；V2 从同一版本复制后独立优化。原 `prototypes/security-pages` 与 `deliverables/aisoc-frontend-handoff` 保持原字节。

| 版本 | 预览地址 | 文件 |
| --- | --- | --- |
| V1 冻结版 | [4173 原版](http://127.0.0.1:4173/#/cases/17420/overview) | [前端目录](security-pages-v1/README.md)、[整目录交接包](../deliverables/aisoc-frontend-v1/README.md)、[ZIP](../deliverables/aisoc-frontend-v1.zip) |
| V2 优化版 | [4174 整合版：全部 Case 数据](http://127.0.0.1:4174/#/cases?data=all) | [启动说明与范围](security-pages-v2/README.md) |

V1 保存了 52 份原文件（包含前端与已有交接资料），[SHA-256 清单](../deliverables/frontend-v1-manifest.json)记录每份源文件、冻结文件和压缩包校验值。V1 README 内的原路径是冻结时的历史说明，启动冻结目录请用下列命令。V1 不继续编辑。

分别在两个终端启动：

```bash
cd /Users/lychee/Documents/project/socai2/prototypes/security-pages-v1
python3 serve.py --port 4173
```

```bash
cd /Users/lychee/Documents/project/socai2/prototypes/security-pages-v2
python3 serve.py --port 4174
```

两者只监听本机。V1 使用原本地状态键 `defender-reference-demo-v1`；V2 使用 `aisoc-workspace-v2`，并通过端口隔离浏览器来源。保存范围为文件，不导出或重置用户已有 localStorage。不要在 V1 上使用 V2 的代码覆盖文件。

2026-10-29：V2 整合版默认保留全部 19 个 Case，7 个 AiSOC Case 优先展示；也可只看 [AiSOC 调查](http://127.0.0.1:4174/#/cases?data=aisoc)。其对应事件、工具、工件和报告按原来源跳转，均为已保存材料，非实时服务查询。

V2 按事件汇聚输入、调查呈现 AI 工作划分。以下是保留的原设计案例，可以直接打开[事件上下文](http://127.0.0.1:4174/#/incidents/262144/attack)、[候选链](http://127.0.0.1:4174/#/incidents/262144/chain)或[全部运行](http://127.0.0.1:4174/#/investigations)。实际 Run 的图谱、工具、输入与报告来自已保存回执；设计样例与实际处理结果的来源边界见 V2 README。

[分析文档](../docs/design/incident-investigation-page-analysis.md)保留完整逐项规划，[本批回执](../docs/design/frontend-v2-verification.md)列出此次真正实现与验证的范围。未实施实时后端接线、服务端新调查流程、模型调用或响应执行。
