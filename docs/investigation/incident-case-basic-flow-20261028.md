# 事件→Case→AI概况基本运行验证（2026-10-28）

**结果：本轮真实基本运行通过。** 用户明确授权后，在21安装现有120/121迁移，并完成事件成员创建/关联Case、选定范围预览、引用已有报告的手动AI概况及读回。本轮业务源码未修改，已通过的Case主调查/追加未重跑；没有启用常驻API或worker。

## 已核对的输入

- 环境：21现有`aisoc`库，应用账号`aisoc_app`，现有`current_tenant_id()`可用。
- 执行前缺少`fusion_incident_summaries`、`investigation_case_links`；本轮安装后均已存在。
- 现有合成租户：`53824f24-d1d4-5820-8147-f6cfda8a1247`。
- 事件：`fbbe6415-3d73-5742-a91a-d1a9617d379d`；两条成员`3fcd245d-0496-54f3-875e-f9a7eb90ae2d`、`5272ae80-b48e-5ef3-8cdd-805885a558a0`归属正确，状态closed保持不变。
- 已完成报告：Case `d183bc94-1584-50d6-bdb2-53e47cf7e7b3`的Run `3265b5ee-8330-52e6-af44-d7cf98fe07e9`，实际状态completed。

## 实际执行步骤

| 步骤 | 输入/动作 | 判定 |
|---|---|---|
| 安装功能表 | 仅[120](../../services/api/migrations/120_fusion_incident_summaries.sql)和[121](../../services/api/migrations/121_investigation_case_links.sql)，同事务记录迁移名 | 两表owner=aisoc，RLS/force RLS启用；现有应用账号实际写读成功。迁移登记134→136 |
| 事件成员创建Case | `POST /api/v2/investigation/case-links`，来源事件、第一条成员、create；标题`TEST-INV-FLOW-20261028-01` | 首次201、subset；新Case为`467dc2a9-fa33-4aba-bb87-19595ecd176e`。同key重读200、回执相同 |
| 告警成员关联 | 同一路由，alerts来源选两条成员，attach刚创建的Case | 首次201；第一条already-linked、第二条added。同key重读200、回执相同 |
| 链接与材料预览 | 按事件/第二条告警GET关联；POST新Case的investigation-context，只选第一条，窗口09:58–10:03 UTC | 关联可查，Case已有两条成员；selected/read仅第一条。新Case历史为空，模型调用0 |
| 事件AI概况 | `POST /incidents/{id}/overview/refresh?include_investigations=true` | ready/succeeded、is_stale=false；一次模型，5476输入+361输出=5837已知tokens，费用记录成功 |
| 保存与跳转 | 再GET事件及旧报告，检查Case/关联/Run数量 | 概况及metadata相同，未再次调用模型。原告警成员记录及旧报告原文不变；新增1个Case/2条关联/0个Run |

迁移沿用原SQL，对新表设置RLS及现有运行账号的读写权限；未创建角色、修改凭据或开展权限专项。执行前两表及对应迁移名均不存在；脚本会拒绝覆盖未知已有状态。现有告警、Case和调查账本表结构未改动，新表及测试数据保留。迁移登记当前为136，旧134计数属于之前批次的历史状态。

创建操作key为`0f6bdb8e-5305-5e97-aed3-d67947d3db12`，关联操作key为`5e066062-c524-5ba9-8338-b4dbae8ea746`。目标Case/关联计数从0/0变为1/2；原Case及新Case合计Run数仍为9。旧Run `3265b5ee-8330-52e6-af44-d7cf98fe07e9`的报告SHA256保持`f3152d3be1d9efff4a62f1b624884e21b8c201c0acba4998672b98607a887870`。

概况采用`aisoc-investigation`既有模型配置，摘要复述已有报告中的网络连接观察和进程证据缺口，没有发起新查询。source_refs保存9份已有Run的引用及范围，其中包含失败/partial结果，不能理解为9次成功调查。文本说明两条告警当前closed，但无法确认流量性质或攻击成功。这里只确认模型请求、材料引用、保存与读取正确，不宣称模型判断质量全面通过。

API在一次性进程中通过ASGI运行，数据库和模型使用真实服务，CurrentUser由测试注入。通过不代表JWT/RBAC、前端、真实厂商HTTP、常驻部署或Fusion重新分组已经验证。

本轮没有重跑既有替身用例，只有一条顺序功能样例、一次真实模型调用。完整证据见[迁移结果、接口状态、回执、模型输入输出及读回](../operations/investigation-incident-case-flow-20261028.json)。相关代码合同见[成员转Case](case-linking-20261028.md)、[事件概况](incident-ai-overview.md)、[已有报告关联](alert-event-investigation-links-20261028.md)。OpenSpec CLI不可用，未宣称严格CLI校验或归档完成。
