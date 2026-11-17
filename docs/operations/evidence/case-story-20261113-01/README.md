# 案件故事查询本机直接验收

对应[query-case-story](../../../../openspec/changes/archive/2026-11-13-query-case-story/design.md)。新批次只在本机v12_upgrade_dev创建合成告警、Case、程序提供的Run/Result和人工任务修订；无真实模型调用、无生产写入、无迁移。

- 独立候选18026由已发布采用版本冻结，仅覆盖8个本轮文件，见local-source-manifest.json。源码工作树不含入并行模型修改。
- 原64业务操作及原Schema逐项保持，现有HTTP分层3项检查通过。
- [local-http/verify-http.json](local-http/verify-http.json)：30次TCP读取及输入拒绝，混合排序/同时间分页/未知时间、主机账号及正文搜索、等级仅筛告警、源接口回查、旧人工完成修订和Case边界通过。
- 首轮最后SQL比较因核验脚本使用ORM对象映射而失败，原sql-before/after和[失败说明](local-http/initial-verification-failure.md)保留，不能作为原行证据。
- [snapshot-verification.json](local-http/snapshot-verification.json)：改为实际表列后，只补1次故事GET及11张相关表原行前后对比；源值一致、无业务数据变化。不重建Case或重派分析。
- [fixture.json](local-http/fixture.json)给出本机可复用测试ID。合成运行状态仅用于读取验收；没有实际模型执行，不核销主调查正文质量。

正式本机/21 API已发布并各7GET读回，Swagger docs14两端各10入口200且合同内容一致；运行源码8文件哈希一致，其他36容器保持。见[delivery-summary.json](delivery-summary.json)、[21-runtime.json](21-runtime.json)、[swagger-release.json](swagger-release.json)及[独立审计](../../../../openspec/changes/archive/2026-11-13-query-case-story/audit.md)。本批0生产业务写入，未提交/推送Git。
