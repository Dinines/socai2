# 3c.3 交互入口与会话汇总

范围：OpenSpec `schedule-streaming-investigation-updates` §12.11 / 3c.3，先只读报告，再交互入口。复用 3c.2 已保存的实际原件；本批不启动业务服务、不向 Kafka 投递、不增加模型调用、不发布 21。

当前报告以 [02 v03](report-02-v03/report.md) / [01 v03](report-01-v03/report.md) 为准。报告第一步及交互入口限定结束独审均通过，3c.3本机交付完成。修前导出和冻结文件保留作问题证据，不作为当前展示结果。

## 第一步：只读报告

- [直接核对](report-direct-validation-01.json)：已完成 02 和未完成 01 分别生成报告，禁止 socket 和连接文件访问，生成前后源目录文件数量与哈希完全相同。
- [02 中文报告](report-02-v03/report.md) / [JSON](report-02-v03/report.json)：2 告警、1 事件、2 Case、9 任务、8 尝试、8 Run、83 步骤、245 工件、4 Result。逐段新观察 4+4 Run，后段累计 8；2 Case 各两轮，冻结成员 1→2 / 1→1。事件按自身input_selection为1→2，各A为1；8次attempt终结逐值显示。
- [01 中文报告](report-01-v03/report.md) / [JSON](report-01-v03/report.json)：原 incomplete / 缺少 prepared 内保存快照保持，实际总量未知；告警分诊等待处http_status_503显式保留。没有引用目录外的 stopped-batch 补查结果。
- 02 按请求工件 ID 去重为 13 个已存请求，输入 69894、输出 40101、总计 109995 Token，均 stop；可见输入、Schema、输出逐字核对。模型费用未知，原答空白保留，隐藏推理和认证字段不导出。
- 02 已存诊断按阶段为 C6 9、C3 6、I 2，共 17；步骤错误/跳过另 16。原 3c.2 的“C6 9 项”结论不改写，新增覆盖其他阶段诊断；正文正确性仍未全面验收。
- [定向验证](report-tests-01.json)：6 报告检查与 4 包检查，共 10 passed；[Ruff](report-ruff-01.json) 通过。开发阶段一条检查曾用仅支持 JSON 对象的读取器读 messages 数组，已更正检查读取器，原导出格式不变。
- [首次独审](independent-report-review-01.json)发现RP-R1 A/I范围误显示0、RP-R2坏消息role对象导致整份报告异常、RP-R3遗漏attempt终态。[report-freeze-03](report-freeze-03/manifest.json)分别修正，原输入定向复验后[第二轮独审通过](independent-report-review-02.json)。最终[11项检查](report-tests-03.json)与[Ruff](report-ruff-03.json)通过，01/02报告JSON除观察时间外与独立生成逐值相同；unknown、缺用量/原答和坏消息均保留独立可读内容。JSON来源SHA与导出文件SHA分开。

## 第二步：交互入口

- [console-freeze-01](console-freeze-01/manifest.json)接入`session --prepared --output`。先显示材料与已存进度，明确`run <首段>`或`append <下一段>`才调用原执行器一次；查看、空输入、无效命令和退出不发送。意图先保存，候选/会话/来源SHA变化要求重选，未知结果不重试且不算未发。
- [直接操作核对](console-direct-01/validation.json)由[验证脚本](verify-console.py)生成，socket与连接文件读取均禁止：真实02查看/报告/quit、真实01禁止重派/finish、EOF、中断共4种操作；原02的2750文件和01的19文件摘要保持。
- 同一直接回执另有**受控执行回调**：临时复制已存原件模拟首段完成→quit→新output重开→显式append→quit；核先intent、恰好两次选择、首段不变。不是新业务执行或新模型测试。真正Kafka/HTTP/调查后轮依赖3c.2已完成证据。
- `finish`保存报告后离开；`quit`/EOF仅保存end观察；中断退出130，不声称远端取消。未发段与未确认结果分别显示；会话不永久关闭。输出目录不覆盖，运行回执、报告和原件各自保留。
- [22项定向检查](console-tests-02.json)、[Ruff](console-ruff-02.json)及[OpenSpec strict](console-openspec-01.json)通过，包括源码包在仓库外直接运行报告与菜单EOF；不重跑全仓回归。

[菜单限定结束独审](independent-console-review-01.json)通过：22项独立复跑、同候选但来源SHA变化拒绝、未知动作不重试、原件和已通过报告证据哈希保持；无未关闭发现。根进度、任务、前后端交接和操作说明已同步。仅关闭3c.3；本记录不代表 3d Docker、任务4、21 恢复、新浏览器、D5/D6 或整个 change 完成。
