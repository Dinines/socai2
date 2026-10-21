# C03-02D-01：检测有效性 v5 提示词最小修订

2026-10-21。执行前冻结卡，按用户持续迁移授权实施；先完成独立源/算子预审，再依次执行。本change尚未运行测试/构建/部署/模型/HTTP/PG/Kafka动作。当前父C03-02C-02已stopped seal，3次真实调用5971tokens，前2质量通过、第3FP/.95而冻结NR、理由不受支持，第4未执行；实测未auto-close，不能写成已错关或已修质量。

## 变更

仅prompt_registry.py旧Reserve FP两行替换为README短版，triage4→5和lock；其他21prompt、schema/时间/授权段逐字保持。现directtest只版本/新增两条文本断言，88相关项由既有cached runner后续验证，不新增真实模型测试。预计父184 Agents/四服务769 Py+lock保持，来源23→24、Compose26→27；一个Agents镜像构建/单次重建，保60秒grace/env/mount/依赖。

父镜像9ba6be09…，父seal ef957aad…/finish 1af6c9f8…/closeout b418979b…已写require_parent精确门，未匹配或父仍未关闭则每host phase拒绝。执行顺序仍prepare→root stage三件→cached test ATTEMPT→build→断网baked probe→独立predeploy审→deploy→独立runtime审→finish→closeout审。各phase独占checkpoint，不自动重试/loop/回滚业务。父公开交付由root先闭合，本草案不代替其授权。

## 断网验证

4 Mock在同一networknone/UID10001/RO容器串行，空DSN与dummy key，无真实env/reader/private挂载；actual build_state→run_auto_triage→safe_ainvoke→egress→生产SDK+MockTransport，CostTracker persistFalse、无Invocation/claim/PG写。三份用当前case01/02/03实际stored preflight材料各自冻结，读/字段/hash保真；第四仅未执行input+controlled A case01的显式transport构造，不称B reader已验，也不称当次授权成立。只验证完整messages≤8000literal/≤16000UTF8、同body传输和fixtureusage，不给语义质量打分。模型0、业务写0、新key/tenant/reader/message/commit/DDL0。

固定prompt+32；纯文件重构actual三份v4 body后，v5反事实literal7832/7864/7917、canonical7747/7779/7832，需候选实际baked Mock再核；不是已经运行v5。旧case和原失败不重调。

## 保护

旧14材料/10预算200000预留单位/3 unknown、10 readers/积压和policy保持，预约不退不作usage。main/raw、六budget组和三个旧quality/DLQ（02/02B/02C02）metadata前后全同；本批探针不assign/poll/record-read/commit，不把metadata等同物理交付仪表或0网络请求。仅Agents更新，其他35容器/18卷/134迁移保持；worker/escalation/writeback/approval/graph继续OFF。总旧未执行7=02三+02B三+当前case04一，三批旧raw与公共回执不改写。

只导入configure_triage_admission_3a纯基础helper和新D1 prepare/deploy；旧quality operator一律不import，METADATA为AST提取的字面量，PRIOR26层为当前父manifest字面量，旧shared OFFSET不改。没有新workerguard、新平台或通用semantic gate；强制review/关闭副作用若后续采用，另冻scope。

## 退出与下一项

88有效tests+4baked Mock+新镜像/lock/184map实际身份、前后保护/三审与公开索引均通过后，仅可称v5文本/传输/部署限定验收。质量仍未通过、常驻仍禁用，另冻全新对照输入与独立判据后再受控验证；不为旧case追标签、不继承旧有界分类成功为v5质量证明。

## 固定候选与来源

父公开交付已核543索引、22定向文件和769运行Py/lock；父交付证明SHA `06a6c355b18a0b18aa328be1044d61fa6b2a0469377e78b4959c4955cd460b20`。本卡不修改父失败、判据或验收原件。

- `services/agents/app/llm/prompt_registry.py`：父 `fcc9f4ecea6df2ff99029a24158d58900fbf8c9746f6531ddd68d65bfd14aca1` → 候选 `2187b951becb78d3d3726adf303e943113c04728c54e7792ed7db0d92a9501b4`。
- `services/agents/app/llm/prompts.lock.json`：父 `93f289ace617f202b6a5f319d5a85236bc9819f1ae9988c374ebc7d90f51731f` → 候选 `2ca1f08ba84ee146b00f25bd5e44cf728c99a6af70f0b1c87c4a8f96f9b70d2c`。
- `tests/porting/test_triage_reasoning_prompt_c03.py`：父 `bffb78894079f62dbc7577f9d25247a550fb8f39b503773b23a38252d0ed830e` → 候选 `7c3bec84936ba665ca543b03487480f4762e3c5fcc1ac1769af6abdec39518f7`。

五算子为 `prepare/test/deploy/probe/finish_triage_detection_validity_c03.py`，公开支持文件为 `compose.triage-detection-validity-c03.yml` 和 `build/Dockerfile.agents-triage-detection-validity-c03`。镜像标签 `socai2-agents:triage-detection-validity-c03-20261021`，Dockerfile固定父完整digest。

结束状态保持worker OFF、无新预算预约/业务行/凭据/消息；实际metrics/ready请求需分别记录，0真实模型不等于0HTTP。源码与运行保护、独审未通过不进入下一phase，失败检查点保留后定向修正，不自动重复部署或重新调用。
