# C03-R01：预算只读观测的独占恢复

2026-10-21。执行范围补充卡；root冻结本卡、恢复算子与独立审计后实施，当前尚未执行。原[review-only范围卡](c03-review-only-profile-plan.md)9512ef88…932da、五个runtime及两个直接测试、prompt/lock/SDK、原预算/RLS/策略均不改。

首轮prepare在任何source stage、测试、build、recreate或模型之前失败。新host observer在BEGIN READ ONLY内新增SET ROLE aisoc，却未设置tenant GUC；预算表FORCE RLS隐藏旧预约，返回0行，触发正确的12行/240000预留单位/3unknown保护。本次错误属于本批观测算子，不是上游预算缺陷，不以放松预算/RLS或填写tenant来掩盖。

Root独立只读诊断确认管理员可见12行、240000预留单位、settled_at=null为3，aisoc无tenant时可见0行。首轮1次及诊断3次（含错误status列的失败只读事务）合计4次PG尝试；另一次SSH命令解析失败未进入Python/PG，不重复计数。原首轮13文件、失败及原算子/bindings/独审完整保留，原独审漏核已作另行勘误。0模型、0业务写入、0source stage、0测试、0build/recreate、0HTTP。

最小修复仅取消host observer的SET ROLE，恢复原既有管理员local psql BEGIN READ ONLY观测路径；不得据此宣称app tenant/RLS或TLS资格重新通过。管理员身份取自既有受控容器配置，不输出凭据、不赋新权限、不改变任何业务连接。

使用原E下独占 `observation-recovery-r02` 子目录重新走完整prepare→stage→test→build→deploy→verify→finish。原失败phase不能复用、删除或覆盖。原P和payload保留；只新增恢复算子、独立bindings、诊断原字节与新review alias四个私有文件。原review alias保持，新alias为 `payload/operator-observation-recovery-independent-audit.json`。

新prepare先按固定13文件map核原E全部原字节，排除仅本恢复子树；原prepare没有completed，stage/test/build/deploy/verify/finish不存在。P中parent-inspect/render/rollback、candidate-render/inspect、build-context、test-results须仍不存在；真实source仍父769、镜像9cb，handoff仍e351/573。任何不符都hold。诊断按f06fed02…fcd29原字节校验；补充卡原文及hash由新bindings承载并归档新E，不需覆盖旧payload。

剩余PG只读尝试上限96，与历史4次合计≤100；HTTP仍只before/after metrics各1、总≤2。模型、业务写入、Kafka assign/poll/read/commit均0；最多一次测试≤300秒、一次build、一次Agents recreate及其余原范围保持。预算阈值、旧12预约/3unknown、十reader、14材料表、QA、134迁移、35其他容器/18卷和所有消息水位保持。已有失败不算测试/部署失败或模型unknown。

新pre/post独审精确绑定恢复operator/bindings、原失败树、诊断、本卡、实际测试及镜像/checkpoint。只有新完整7phase及独立审计通过，才可继续R01限定收尾；不追认原prepare通过，不把observer修复写成自治质量/R02/迁移完成。失败保留，不自动重试或回退。回退方案由root另行审查，仍沿用户既有常规资源授权边界。
