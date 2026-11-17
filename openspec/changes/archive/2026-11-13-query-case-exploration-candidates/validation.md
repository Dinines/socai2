# E66候选查询验收

2026-11-13。本机实现、真实HTTP/PG直接验收、发布前独审及两端统一发布已完成。[汇总回执](../../../../docs/operations/evidence/case-exploration-20261113-01/delivery-summary.json)。

## 已完成直接验证

- 实施前 `openspec validate query-case-exploration-candidates --strict --no-interactive` 通过。
- 新本机合成批10告警/2Case，不调用模型；2次创建Case，然后30次HTTP走通匹配、显式/默认时间、分页、来源回查、旧材料/错误参数、明确加入E08及成员读回。查询阶段10张相关表原行一致；明确加入后本案成员改变，原案归属保留。未新建、迁移或清理表。
- 主机/账号/IP/域名/URL按同来源同类型值；哈希核算法和值。实际候选3条，首条3个共享对象但4对原字段引用，去重和来源均正确。
- 原65操作及全部旧Schema逐值不变；3项既有HTTP边界检查通过，核心不反向导入对外HTTP包；本项Ruff通过。
- Swagger候选docs15生成：66操作、64实现/2对话501，147类型，703固定字段位置，35动态组；125功能分组保持22/15/88。585 JSON响应示例、3 CSV、26请求示例通过Schema验证。
- 初次测试缺PYTHONPATH、初次文档生成顺序错误均在未发业务请求/未发布阶段发现并修正，[原问题说明](../../../../docs/operations/evidence/case-exploration-20261113-01/initial-check-notes.md)保留。

证据：[直接验证](../../../../docs/operations/evidence/case-exploration-20261113-01/local-http/verification.json)、[查询SQL保持](../../../../docs/operations/evidence/case-exploration-20261113-01/local-http/query-verification.json)、[合同兼容](../../../../docs/operations/evidence/case-exploration-20261113-01/compatibility.json)、[Swagger校验](../../../../docs/operations/evidence/case-exploration-20261113-01/docs-check.json)。

## 发布与结束审计

从当前E65镜像/冻结源码仅叠加本项11文件，已统一同步本机/21独立API和Swagger docs15。两端各11次已有数据GET，核版本/66操作、候选及一组双方匹配对象和原材料、Case原行保持；两端Swagger各11入口200且哈希相同，33个静态文件一致。实际API为case-exploration-20261113-r1（本机为-local），21镜像sha256:6c05adad8eeb0899551309c2e67e38070b209ff7738b677ec057da275adbf379。

并行模型修改未发布，消费者未改变，0模型/0迁移/0生产业务写入。保存恢复、告警相似历史专项查询仍未实现，AI对话暂缓。最终独审及归档另记audit.md。Git未提交/推送。
