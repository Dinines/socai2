# 4173 测试页面的启动、使用和数据

2026-11-12。现有页面仅作测试和设计参考，本轮不改页面。4173/4174 是可选的本机预览端口，18024 是实际 API，18080 是 Swagger，各自用途不同。

## 启动和入口

历史记录里的 4173 对应旧 V1；当前仓库保留的测试页面源码是 `prototypes/security-pages-v2`，旧 V1 目录已不在当前检出中。可将现有测试页面启动到熟悉的 4173，不代表恢复旧版或新增一套产品。本轮检查时本机 4173、4174 均没有监听进程。

在 socai2 仓库根目录执行（SpiritHub 中先进入 `server`）：

```sh
python3 prototypes/security-pages-v2/serve.py --port 4173
```

保持终端运行，Ctrl+C 停止。只需要 Python 3，不需要 npm install、打包、数据库或模型。只监听 `127.0.0.1`；其他电脑需在自己的检出中启动，不能把维护者的 localhost 当远程地址。已有端口占用时可用 `--port 4174`，下列 URL 相应替换。

| 查看内容 | 本地入口 |
| --- | --- |
| 告警列表、详情、材料和分析展示 | `http://127.0.0.1:4173/#/alerts` |
| 事件及成员 | `http://127.0.0.1:4173/#/incidents` |
| Case 列表 | `http://127.0.0.1:4173/#/cases` |
| 财务终端完整设计样例 | `http://127.0.0.1:4173/#/cases/outcome-case-01/case-info` |
| 故事/问答展示 | `http://127.0.0.1:4173/#/cases/outcome-case-01/story` |
| 部分交付和人工任务样例 | `http://127.0.0.1:4173/#/cases/outcome-case-02/overview` |
| 实际服务数据模式（仅已有 Case 测试入口） | `http://127.0.0.1:4173/?data=service#/cases` |

## 默认打开时的数据是什么

| 数据来源 | 文件 | 能说明什么 |
| --- | --- | --- |
| 产品设计与交互样例 | `data.js`、`case-outcome-data.js`、`case-exploration-data.js`、`page-showcase-data.js` 等 | 展示功能与预期交互；样例结论、助手回复不是当前 API 执行结果 |
| 保存过的实际验收记录 | `socai2-recorded-*.js`、`persisted-case-data.js`、`recorded-examples.js` 等 | 展示对应批次的冻结数据；保留失败、partial、unknown，刷新不会自动从21更新 |
| 浏览器本地编辑 | 当前 origin 下 localStorage 的 `aisoc-workspace-v2` | 普通预览模式的修改仅在当前浏览器保存，不写21；4173与4174的浏览器存储分别独立 |
| 实时服务模式 | `service-workspace.js` 使用填写的 API 地址 | 实际读取/操作选定环境；账号所属租户和实际响应决定数据 |

初始数据数量随已收录记录变化，浏览器历史编辑也会改变显示数量，不用固定条数作为接口验收标准。要看干净样例可开新的浏览器配置或无痕窗口，不需要清除原有 localStorage。静态样例 ID（例如 `outcome-case-01`）不能传给真实 HTTP 接口；使用[当前测试数据](backend-test-guide.md)中的 UUID。

使用顺序：先看三类列表 → 打开详情 → 查看材料/当前判断/运行记录 → 对照[功能清单](../../deliverables/investigation-validation-20261106/frontend-feature-list.md)理解设计 → 到 Swagger 验证真实接口。问答示例可以展示设计，但真实 E19–E21 当前仍返回501，不能据按钮存在判断已实现。

## 若需要用此页面读取真实 API

页面只提供已有 Case 服务模式，不承诺涵盖新加入的全部47接口。后端完整联调以 Swagger/HTTP 为准。

1. 按[Swagger 配置说明](../../deploy/api-docs/README.md#选择调用哪个-api)建立本机28024到21的转发。
2. 打开 `http://127.0.0.1:4173/?data=service#/cases`。
3. “服务地址”填 **`http://127.0.0.1:28024/api/v1/socai2`**，这里需要包含业务前缀；本机隔离服务可填 `http://127.0.0.1:18024/api/v1/socai2`。
4. “登录凭据 / 用户 API Key”填现有有效凭据值，点击连接；凭据只保存在页面内存，刷新后重新填写。
5. 先只读查看列表、Case、Run、结果和任务，再在自己新建的测试 Case 操作。服务模式的保存是实际写入，不是本地样例编辑。

现有测试页面拒绝非回环地址的明文 HTTP，所以直接填 `http://192.168.1.21:18024` 会被页面拒绝；本轮不改该页面逻辑，使用 localhost 转发即可。API 的 CORS 配置还需允许 `http://127.0.0.1:4173`；仅转发不自动解决跨域。不能连接时先用 curl/Swagger核对 API，不切回样例并当作真实数据。
