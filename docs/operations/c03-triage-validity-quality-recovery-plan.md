# C03-02D-02：发送前合同拒绝的限定恢复

2026-10-21。补充[原执行卡](c03-triage-validity-quality-plan.md)，不覆盖原卡、输入、判据、操作脚本或失败记录。本批首次case01 ingress退出1；其inside脚本误留02C02的输入SHA和v4检查，这是本地验收脚本适配遗漏，不能归为上游缺陷或模型失败。

## 已有检查点与禁止重复的动作

`check_contract`在创建Evidence、进入ingress及HTTP计数上下文之前拒绝了输入SHA。因此本次没有发告警、读取消费消息或调用模型。失败host before与after字节相同，SHA均为`c2c8cf9abf252feaa15f69796d97fd2aa7ae6026e189275f6ac5a147278ee0a1`；E/cases不存在、发送和SDK开始检查点均0。原host日志SHA为`c7f2ce89f6bd7ea1231640325647a25f7851c11f09c456debb1d40351dd52897`，原safety-stop SHA为`8c32c8eaea7ed0966b2fd212104d2343fecdf3e634ba14abf0ee8298c3ab60d7`。恢复前另由独立审计者核实实际失败位置及无业务增量；相同hash不是单独的数据库无写证明。

原freeze、snapshot、provision、topics和authorize各已执行且保留。它们不重跑；三操作key、policy、两个topic及group不重复创建，不增加额度、不退预约、不删除stop、不覆盖旧state或host-phase目录。原pre-exec审计遗漏了inside两个旧常量，原accepted记录保留并由新恢复审计明确限定其可复用范围。

## 允许的最小修复及新门

1. 保存原五脚本、private状态、失败和审计的字节与SHA。新inside修订将输入SHA绑定本批`e80c04a5e9d2bc18b526c197af9b6e9ab8cbc5966e2615dca274e12b3949e3c2`，将prompt版本检查与错误文案改为v5，并增加只识别上述原stop SHA及新独审的显式恢复门；产品源码、prompt、lock、schema、输入、rubric不变。不删除或覆盖旧stop，不伪造证据目录，不将ingress伪称verify绕过检查。
2. 新恢复脚本及状态使用独立路径，绑定原状态、原五脚本及新修订SHA。只有上述唯一发送前失败、E/cases仍不存在、全部发送/SDK检查点0、当前业务和旧保护基线保持时才可准备。原stop当前root/0600，UID10001不能读取；准备时允许仅此文件改为UID10001/0400，记录前后metadata并核字节SHA仍为原8c32值，使实际只读探针可核原件，不造替代stop。独立恢复审计通过后才可继续。
3. 先在固定9cb719镜像、UID10001、只读rootfs及必要只读挂载中，以network none实际运行新inside的`check_contract('ingress','case01')`。探针不创建Evidence、不进入ingress、不访问PG/HTTP/Kafka/模型；保留实际退出和输出SHA。AST/文件可读检查不能代替此门。
4. 新runner使用独占恢复host-phase路径；仅精确识别原stop及原失败允许首次业务发送，任何新失败、发送不明或新的stop都停止后续。后续仍按原卡逐例ingress→preflight独审→单次invoke→verify→独立质量门，不自动循环、不重试模型。
5. 收尾绑定实际使用的原件及恢复脚本、状态关联、探针和恢复独审。原失败属于本批执行史，原预算和HTTP/SQL观测计数继续累计，不另起批掩盖失败。收尾先检查、独审、停用三key并核401，再封包及独审。

恢复额外允许一次断网合同探针、受控文件归档/状态准备及必要只读独审；业务、模型、消息、HTTP和数据增量仍受原卡总上限约束。0新服务重启/构建/DDL/身份/额度。若不能证明首次发送尚未发生，则本卡不授权重新发送，应停止并只读回查。
