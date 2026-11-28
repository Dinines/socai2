# Case M0f：明确 unmapped 材料选择

本回执只记录源码和本机生成结构的工程检查，不包含实际材料、业务结果、诊断或计量值。对应 [M0f 范围](../../../../openspec/changes/complete-socai2-investigation-chain/case-input-capacity-20261128.md#第一步-m0fcase-材料的-unmapped-选择边界)。任务勾选和独立结束验收由统筹收口。

实现仅改变 Case 新输入：两个配置声明的 OCSF 根下的 `unmapped` 及后代不进入 C3、Deep、C6。固定序列化入口只在严格 JSON 全结构、类型与同材料对象/排除容器一致时投影或省略；先处理容器副本，再处理完整 OCSF 镜像。引用保护不能恢复排除内容，已知 C1/C4 工件回取按不可见依赖处理。其他业务位置的同名字段、已映射值和未知业务扩展继续保留，原件及原始来源留后台，可见来源哈希对应实际投影值。

源码落点：

- `services/api/app/socai2/case_c3_input_selection.py`：精确路径选择、同源包装及不可豁免的共享筛选。
- `services/api/app/socai2/case_input_text.py`：在保留原始 guard 值的同时装配材料投影；可安全投影点号键父对象。
- `services/api/app/socai2/case_followup_input.py`：阻止已知工件依赖恢复排除原文。
- `services/api/app/socai2/case_program_output.py`：发生本步材料过滤时，程序装配的观察正文使用可见观察值，防止原文从前序正文回流；其余观察装配保持原行为。
- `services/api/app/socai2/case-input-v1.json`、`runtime_policy.py`：Case 配置 v7 及限定路径校验；未改预算、内容检查或 A/I 配置。
- `services/api/tests/test_socai2_case_material_unmapped.py`：生成结构的三阶段消息、JSON 存读、引用、包装及原件检查。
- `services/api/tests/test_socai2_case_material_mirrors.py`：原“保留未知扩展”夹具由 `unmapped` 改成普通业务扩展，保留旧镜像/类型/引用语义测试；新的排除规则由专门测试覆盖。

直接检查：新增测试、直接受影响的镜像/后台字段测试及两项既有观察装配测试（含参数化）合计 **50 项通过**，限定文件 Ruff 检查及 OpenSpec strict validate 通过。C3 输入工件 JSON 保存读回后，实际装配观察正文，再作为前序分析构造 Deep/C6 消息，核没有原文回流、可见哈希/成员/原件保持；不可见依赖覆盖直接引用、祖先引用及 C1/C4 已知工件来源。

私密日志、生成材料和源码前态在 `.local/validation/case-input-unmapped-m0f-20261128-01/`。各轮日志保留；最终直接检查为 `pytest-05.log`，Ruff 为 `ruff-05.json`，最终源码指纹/工程回执为 `implementation-review-final.json`。前两轮发现旧夹具对 unmapped 的保留预期已过时、测试 Context 为冻结对象，以及“点号键父对象同时带 raw_data”会被既有原始 guard 先拒绝。第三轮通过后补查发现观察正文可能使用完整原值，故追加窄修与实际装配检查；第四轮纠正代表引用的来源角色，第五轮通过。没有为测试修改 guard；被既有检查排除不能计作本次过滤成功。早期 `implementation-review.json` 和日志只对应当时源码，不充当最终基线。

统筹独立检查已另用生成结构核验 C3→JSON 存读→C6，以及实际观察正文装配→作为前序正文→C6，工程回执位于 `.local/validation/case-unmapped-m0f-independent-20261128-05/`。独立检查不替代实际冻结材料的容量与模型业务验收。

未覆盖：无法解析或无法证明同源的任意原文保持既有检查，不能据此宣称所有 raw_data/raw_text 已清理。上述核心实施批未执行真实快照重建、tokenizer、模型、网络、数据库、部署、提交或推送；统筹另批操作见下，真实容量、模型业务效果及运行环境验收分别记录。

同冻结材料的新批效果/容量复验由统筹接手，另建目录，继续使用已有计量入口与原预算/检查，不修改旧批或沿用旧源码 manifest。核心侧本机曾准备配置生成草稿，未执行，不纳入本步交付或后续执行安排。

统筹已在 `.local/validation/case-input-unmapped-effect-20261128-02/` 执行既有 tokenizer-only 入口，临时 SSH 连接已关闭。前后构建/消息长度/容量对照与独立核对保存为 `effect-redacted-report.json` 和 `coordinator-private-review.json`；负责人已确认完成审阅脱敏，并允许当前统筹会话限定读取这些实际统计和校验名/布尔结果。原始材料、数值和实际数据派生核验不写入本公开回执，也不转发给核心会话；不据文件存在认定容量通过。新批没有生成调用、数据库写入、旧 Run 续跑或 21 发布。准备后未执行的前一批留存并标明撤回，不充当测试结果。

统筹另从 Git HEAD 导出临时普通目录，只覆盖拟交付的六个 Case 产品文件、既有计量口径依赖、对应测试和容量工具/Schema；未夹带页面、HTTP、事件配置等其他工作区改动。生成结构的过滤/镜像/后台字段、计量和私密计量入口共 **84 项直接检查通过**；候选记录在同批 `git-candidate-plan.json`、`git-candidate-tests-03-private.log`。前两次因临时导出目录的导入路径及未包含的旧样本工具无法收集，未执行到业务检查；随后限定为本次必要的生成结构检查，并保留原日志。Ruff 及产品 diff 格式检查通过。此项验证拟提交内容自身可运行，不替代实际容量结果；根据负责人分阶段提交授权，统筹随后整理必要产品/测试/配置依赖及本轮文档到 V1.1；其他工作区改动、main 和父项目保持。本回执不包含私密实际结果。
