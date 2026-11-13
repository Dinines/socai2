# 三类列表查询发布证据

本批补齐告警、事件、调查的筛选、排序与分页，按获准方案仅在告警/事件封套新增filtered_total及next_cursor，数据库及行字段保持。实际服务为list-query-20261113-r1，两端Swagger为docs8。

- [完整验收](../../../../openspec/changes/archive/2026-11-13-query-investigation-lists/validation.md)与[独立审计](../../../../openspec/changes/archive/2026-11-13-query-investigation-lists/audit.md)。
- [交付摘要](delivery-summary.json)：15项离线检查；候选117次真实TCP/PG，正式入口本机30次、21上50次只读请求。实际输入输出和SQL快照均在对应子目录。
- [Swagger字段与示例检查](swagger-check.json)、[文档发布回执](../../../../deploy/api-docs/deployment-receipt.json)。两种架构的9入口HTTP摘要一致。
- 初次种子唯一约束失败已回滚并保留意图，随后新建独立批次；初次日期错误响应500已修正为422，原失败仍保留。后续验证不覆写旧失败。
- 21复用既有7主体/3关联，发布前后SQL保持，没有新增正式库测试数据、模型调用、迁移或消费者变更。并行模型修改未进入10文件发布范围。

只读发布脚本以本批显式profile和指定ID为输入；不重新创建样本或重派调查。Git尚未提交推送，发布后独立复核和归档状态以审计记录为准。
