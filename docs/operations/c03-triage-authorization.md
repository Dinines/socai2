# C03-02C-01：分诊授权事实边界

2026-10-21。**本小批提示词及传输限定验收通过；真实理由质量、常驻准入和整体迁移仍未完成。** 见[执行卡](c03-triage-authorization-plan.md)、[来源](../handoff/c03-triage-authorization-source-manifest.json)、[补丁](../../deploy/aisoc21/patches/c03-triage-authorization.patch)及[机器回执](c03-triage-authorization.json)。原两批质量失败和原评分不改写，两批各三例、共六例未执行输入保持未发送。

仅将triage.system末条由v3改为v4并同步lock：区分有害行为与授权状态，明确行为可支持威胁判断，但只有适用的决定才能据以断言授权；授权缺证应保留unknown，仅在余下缺口妨碍判断威胁时使用needs_review。分类/schema、其余21个prompt及模型路由、风险算法、五类读取和原恢复合同保持。该指导不是代码级通用授权校验。

现有缓存镜像直接测试88项通过。候选`sha256:9ba6be09b682b451f6ce3b590c1e736e00b5baf1dcd13c00874781261ca8a3b3`中，实际build_state→AutoTriage→safe-call→egress→生产SDK的四个完整body分别为：case01：7814字符/7729字节；case02：7775字符/7690字节；case03：7754字符/7669字节；case04：7781字符/7696字节；均在默认8000字符账本与16000规范UTF-8字节上限内，保留retry0/45秒/输出512。四次均为同一A五源冻结材料上的断网构造，后三类替换尚未执行的来源字段；没有真实reader、provider、Invocation/Run/预约/QA写入。固定needs_review回复和每次18 tokens只是SDK/CostTracker合成fixture，不是理由质量或费用结果。

部署前独审发现host算子存在import副作用：prepare经旧finishB/prepareB安装全局观测hook，早期prepare/build/probe的四次只读观测将104次SQL helper及4次HTTP的started/finished追加成112个计数文件，写到了旧B目录。这些是本C-01的观测，不回填为旧B当时的模型运行计数；不代表旧B目录没有追加。旧844个冻结raw文件及20份旧公开回执/source原件逐字节保持，112个新增文件不删除，原地保留并复制到新E的`observer-import-side-effect/old-B/`，关联记录SHA绑定其全部路径、大小和内容。原prepare及revision同时保存；已移除执行import，改为内联相同metadata代码。未改prompt/test/probe/候选镜像，未重跑测试、构建或四个probe，没有业务写入或provider调用。五个算子当前SHA和旧prepare修订历史见机器回执与来源清单。104/4仅是这部分早期错位观测，不冒称整个C-01读取总数。

仅Agents一次重建，当前26 Compose/23来源层，184 Agents Py、四服务769 Py及非Py lock在测试/候选/运行对应；原env/7只读bind/60秒停止宽限保持。旧14表、7预约/140000固定预留单位/3unknown、六预算组/主与quality/raw metadata、十reader、其余35容器/18卷/134迁移保持；无新tenant/key/reader、真实模型、业务PG写或broker发布/应用记录交付/提交。readiness与gateway metrics属于真实只读HTTP，不声称零HTTP或所有后台Fetch为零。部署前、运行及结束独审均accepted；旧两个质量批只作为证据观察，不增加其源码层。

下一C03-02C-02另冻四条新代表输入、独立判据和有界逐例调用；不重调旧两条已执行告警，不退款或重发unknown。worker、graph、审批与记忆写回仍OFF。本小批不解除模型质量、引用质量或真实响应限制。
