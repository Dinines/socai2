# E65案件故事查询验收

2026-11-13，本change完成本机实现、直接验收、独立审计，以及本地/21独立API和Swagger统一发布。[回执](../../../../docs/operations/evidence/case-story-20261113-01/delivery-summary.json)与[完整证据](../../../../docs/operations/evidence/case-story-20261113-01/README.md)。

## 实现和直接核验

- E65聚合本案当前告警、baseline Run/终态结果、人工完成修订；搜索/等级先筛全量，再按真实时间倒序及稳定游标分页。源身份和原文保留，无模型或写入，AI对话暂缓。
- 实施前strict通过；原64操作及Schema保持。现有HTTP分层3项检查通过，核心不反向导入HTTP，路由不导入数据库或执行器。
- 新本机合成批次：30次真实TCP功能检查；首次末尾SQL比较因核验脚本将ORM对象作为行而失败，原件保留。修正为实际表列后，仅补1次故事GET及11表原行/源值核对，前后一致。没有重复构造样本、重新执行调查或真实模型调用。
- 合成Run/Result只用于读取验证，当前主调查及模型正文质量的未通过结论保持。不会把HTTP成功说成模型质量通过。
- 文档候选检查发现StoryPage.items说明缺失，补充description后示例/Schema核验通过；后续独审发现F22-08旧句和README候选版本说明/指南链接缺失，已修正复核。原候选manifest保留，最终manifest仅该description差异。

## 发布读回

| 项目 | 实际结果 |
| --- | --- |
| 本机ARM64 API | case-story-20261113-r1-local；18024；v12_upgrade_dev；独立冻结源码，仅8个故事适配文件 |
| 21 AMD64 API | case-story-20261113-r1；18024；aisoc；镜像sha256:ae6e5181cd23d5e095e3dd545280b1297e6a471cb1e94828bf956cc36586418c |
| 本机/21直接读回 | 各7次GET，核对65操作、故事和原告警/Run/结果/人工修订；Case状态保持 |
| 其他服务 | 实际加载8文件hash与发布包一致；除API/Swagger外36个运行容器身份、镜像与启动时间未变 |
| Swagger | 两端docs14；告警/事件/调查三类；65操作，63实现，E19/E20仍501且对话暂缓；141文档Schema；新增13字段，共668固定字段位置，35动态组；571 JSON响应示例+3CSV，26请求示例 |
| 文档读回 | 两端各10入口200，新故事指南可直接打开；OpenAPI及其余相同静态入口hash一致 |
| 边界 | 0模型调用、0生产业务写入、0迁移；未启用任何消费者、调度或AI对话 |

OpenAPI SHA-256：`ac4b581ec42679daed7224659a5682b914d3a09f9e468cc60f7e407b2eb84f60`。21仅读取已有合成Case，未复制本机UUID到正式库或导出生产凭据。

代码和文档已在本地工作树；本轮没有执行Git提交、推送或父项目引用更新。归档/封后校验另记于独立审计。

发布后独审又发现接入指南表一处旧采用版本/64操作文字，已修正。最终静态挂载使用20261113-docs14-final，仅README/guide两个文件与首包不同，OpenAPI哈希保持；两端最终10入口读回一致。首轮Swagger回执保存为swagger-release-initial.json及原local/21-swagger.json，最终回执为*-swagger-final.json；业务API没有因此重启或重复验收。本轮18026候选已关闭，正式18024保留。
