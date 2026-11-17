# 当前调查评审证据

2026-11-14。[评审报告](../../../investigation/investigation-current-review-20261114.md)记录13项发现及对应已有change的处理建议。本目录只新增只读评审证据，不是新模型或业务执行批次。

- [saved-evidence-review.json](saved-evidence-review.json)：读取11-14三案保存快照、请求及原答；汇总结果、实际步骤、调用、时长和来源SHA。三份已拒收原答均通过当时发送的JSON Schema；接收错误读取既有回执，未重新采用或保存这些原答。
- [inspect_saved_evidence.py](inspect_saved_evidence.py)：离线复核脚本，使用本机既有jsonschema；不连接服务、不运行调查、不改原证据。输出存在时要求完全一致，否则停止。
- [runtime-readback.json](runtime-readback.json)：本轮SSH只读所得相关容器、Agents开关和投影位点。只记录获读结果，不把健康状态当业务验收。
- [workbench-readback.json](workbench-readback.json)：本机4177转发的首页读取、页面SHA及三条活动记录；其内容是已保存快照。
- [workbench-conclusion-review.json](workbench-conclusion-review.json)：按负责人指出的“本轮停止原因 / stage_output_saved”补核当前C01详情HTML。内嵌脚本与本地源码一致，4条A/I Run与快照逐值一致，3份成功发布工件的业务正文与结果表一致；确认正常结束码误报错误及Run交付入口未直接展示业务结果。保存页面SHA、节点链接、结果关联和来源SHA，不改旧证据或页面。浏览器控制宿主不可用，本次仅HTTP源码/数据/渲染逻辑核对，未完成实际点击或视觉验收。

复核命令：

```sh
.local/conda-envs/socai2/bin/python docs/operations/evidence/investigation-current-review-20261114-01/inspect_saved_evidence.py
```

初版脚本仅在导出的主要用户正文中查“无可用查询候选”，遗漏独立的工具目录消息，错误输出了4个false；[初版汇总](preliminary-user-body-only.json)保持。最终脚本改为读取实际请求的全部messages，4次均为true；来源文件由22份补为26份。其他计数和三例Schema结果不变，没有修改11-14批原件。这是本轮评审脚本的字段取数修正，不是业务修复。

主调查与流式change的strict校验通过。没有新模型调用、Kafka消息或offset提交、业务数据库写入、服务启停、Git提交推送。报告不替代主change的独立结束审计。
