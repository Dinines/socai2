# C03-02D-01：检测有效性提示词边界

2026-10-21。**本小批仅对v5文本、离线传输和部署限定验收；模型理由质量、常驻准入和整体迁移未完成。** 见[执行卡](c03-triage-detection-validity-plan.md)、[父镜像来源勘误](c03-triage-detection-validity-source-note.md)、[来源](../handoff/c03-triage-detection-validity-source-manifest.json)、[补丁](../../deploy/aisoc21/patches/c03-triage-detection-validity.patch)和[机器回执](c03-triage-detection-validity.json)。前三批原质量结果保持，旧未执行共七例（02三、02B三、02C02一）未重调。

仅替换triage.system关于false_positive的原两行并由v4更新v5/lock：缺证不能证明规则误报；无法核验规则条件时使用needs_review，false_positive需要提供相反证据。其余21个prompt、schema、时间/授权段、路由、风险算法及恢复合同保持。它是提示词指导，未新增代码级通用检测有效性校验。

88项相关缓存镜像测试通过。候选`sha256:9cb719ff55d772ebf047f87a06863ae7102feb5be3b9471610113dd9d85728fd`内四次实际build_state→AutoTriage→safe-call→egress→生产SDK Mock完整body：case01：7832字符/7747字节；case02：7864字符/7779字节；case03：7917字符/7832字节；case04：7827字符/7742字节；均≤8000 literal字符及≤16000规范UTF-8字节，retry0/45秒/输出512保持。前三份分别复用02C02已执行case01/02/03的实际stored preflight材料；第四仅将未执行case04输入与受控A材料构造成transport fixture，不是B reader证据或当次授权证明。四次均断网、无真实reader/provider/Invocation/预约/PG写；固定needs_review/每次18 tokens仅合成SDK记账，不是实际usage、费用或模型质量。

首次source stage在host compile-before-exec发生SyntaxError，零远端动作，原失败和恢复记录完整保留；不能算成产品测试失败。实际测试、构建、probe、运行身份和三件源码哈希分别以本批证据核对。执行卡原scope-before和父来源勘误均保留：Dockerfile使用父标签，build前核常驻镜像和标签的完整image ID，再以--pull=false/--network=none构建；不称repository digest引用。

仅Agents一次重建，当前27 Compose/24来源层，184 Agents Py、四服务769 Py及独立lock逐hash对应。旧14表、10预约/200000固定预留单位/3unknown、十reader、六预算组及main/raw/三个旧quality和DLQ metadata保持；其余35容器/18卷/134迁移保持。无新业务行、tenant、key、reader、真实模型、broker发布、应用记录交付或提交。ready/metrics为真实只读HTTP，自有成功路径由实际五算子源码和检查点推得7次observation网关metrics及1次readyz，共8次显式HTTP helper调用；独审实际HTTP另列。这不是全网/内部health的流量仪表，不声称零HTTP或零后台网络Fetch。

历史C-01 observer导入问题的104 SQL/4 HTTP与112追加文件继续归原C-01；旧B844冻结原件及C-01冻结副本逐hash保持，不要求本地旧B存在其追加原路径，也不称旧B目录从未追加。七个prior completion和28份父公开原件冻结，本批不改原评分或unknown。

下一C03-02D-02另冻新代表输入和独立判据逐例验证v5；不重调旧失败，不继承旧版本TP为v5质量证明。worker、graph、审批和记忆写回仍OFF。
