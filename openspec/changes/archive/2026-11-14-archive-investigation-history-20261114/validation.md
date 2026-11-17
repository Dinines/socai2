# 本地归档验证

2026-11-14。按负责人本轮要求及“继续”执行本地资料归档，没有业务、模型、数据库或部署变更。

| 验证项 | 实际结果 |
| --- | --- |
| 归档边界 | 128份旧Markdown、2份汇总JSON、32个旧证据批次；共691文件、21,124,247字节。当前设计/合同/评审和程序配置依赖保留 |
| 原文及路径 | 237份文档原字节存ZIP，4份当前入口另有历史查阅快照；全部摘要核对通过 |
| 私有本机产物 | 21项、6,561文件、812,924,248字节，逐文件字节/模式保持；当前引用的5个核心/处理包保留 |
| 进程与挂载 | 本机进程命令/工作目录及42个容器挂载只读核对，移动候选无匹配；未操作容器或服务 |
| 现行依赖 | 3,342个代码、配置、机器合同及4177文件字节/模式不变；85项保留路径存在 |
| 文档引用 | 11,067条原有效链接的目标按映射仍存在；222份非手工维护正文按原文加链接重定位/历史标识核对，另保留已核实的并行新增段落；当前入口链接分次核验通过 |
| 任务与未完成状态 | 主调查41项任务逐行保持，31项完成；流式仍未实施，RV12尚未修复，模型质量NOT_PASSED |
| CLI与格式 | 本整理change、主调查及流式change strict校验通过；当前入口的git diff空白检查通过 |

最终回执见[validation-final-02.json](../../../../docs/handoff/history/2026-11-14-investigation-cleanup/validation-final-02.json)，[首次检查](../../../../docs/handoff/history/2026-11-14-investigation-cleanup/validation.json)保留。逐项映射见[manifest.json](../../../../docs/handoff/history/2026-11-14-investigation-cleanup/manifest.json)，现行文件基线见[protected-files.json](../../../../docs/handoff/history/2026-11-14-investigation-cleanup/protected-files.json)。本机完整逐文件清单在`.local/archive/2026-11-14-investigation-cleanup/manifest.json`；不把私密产物放入Git。

本轮没有删除模型原答或业务数据，没有新模型/业务测试、4177重建、数据库写入、服务重启、Git提交推送。文件归档未释放磁盘空间；CLI仅验证文档结构。[独立结束审计](audit.md)限定ACCEPT后，本整理change已通过CLI归档；其他活动业务change保持。

独审发现7个旧活动change的8处反引号Evidence路径未被Markdown链接重定位覆盖，已补成指向归档的链接，原路径保留为链接文字，各任务编号/勾选不变。根README的过期部署说明也已按现行回执纠正。新增原文均存ZIP，最终原件数237；首次validation.json记录补充前的229份，保留首次回执，最终定向复验另存，不覆盖它。

封后首次核验[validation-final.json](../../../../docs/handoff/history/2026-11-14-investigation-cleanup/validation-final.json)发现问题清单新增了并行实施规划引用，记录FAIL。逐字差异确认只有该新增段落，剔除该准确段落后与预期归档重定位完全一致；[并行变动回执](../../../../docs/handoff/history/2026-11-14-investigation-cleanup/concurrent-document-addition.json)记录观察时摘要。新规划及引用保留，未归档或覆盖；最终02复验PASS，文件/模式、237份原件、8处引用及主31/41均通过。

封后OpenSpec校验：`--all --strict --no-interactive`为36通过/0失败，`--archived --strict --no-interactive`为37通过/0失败，日志保留于归档证据目录。归档后已重定位本change内部的文档链接，不把CLI成功当作主调查或模型质量通过。

完整收口信息见[封后回执](../../../../docs/handoff/history/2026-11-14-investigation-cleanup/post-archive.json)。
