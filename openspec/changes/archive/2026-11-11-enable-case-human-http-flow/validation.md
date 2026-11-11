# Case/H HTTP 功能验收

## 本地结果

本轮沿原 HTTP 路由走通建案、首轮调查、人工完成/修订、下一轮 prepare/start 和保存读取。13 次请求成功；两轮分别 5/4 次真实模型调用，reported tokens 为 71,723/45,452，费用未知。没有重新采样追求质量通过。

Case `dac58811-c58d-5a75-9e7e-d0daf2f0740b`，首轮 `d938c1a4-a5b9-4a68-9606-05f4f9c91b6f`，后轮 `02412f50-3384-4c35-aa79-672b6a1939e7`。后轮选中修订 `fb5d503e-f4b5-4c6a-9684-7fa711d56424`；第 1 修订原文保留，第 2 修订原文、范围和 `human_statement` 引用进入冻结输入，4 份实际模型请求 body 均包含修订后正文，不含修订前正文。

两轮均 `completed/partial`。首轮 C6 在已有一次纠正后仍为 `delivery_source_not_visible_or_duplicate`，Result 为 rejected、conclusion=null；该失败保留，没有冒充模型成功。后轮 C6 accepted，并明确人工核查不是业务授权、命令结果和外传影响仍未确认。该变化只能证明本批部分使用了反馈，不能证明 F01 整体质量通过。首轮正文仍有标签推测及时间/因果扩大，M01/M02 保持开放；M01-B 既有失败证据也保持，不因本批 coverage 正确而关闭。

两份 Result 的 `conclusion,conclusion_state,validation_state,findings,questions,recommendations` 与数据库逐值一致，原始演练材料保持。没有 DDL、告警字段变更或新增权限设计。一个 Case 的快照用于数据关联、模型原答和 4177，同批复用，未做全库/全接口对账。

## 覆盖与限制

| 内容 | 实际覆盖 |
| --- | --- |
| HTTP/服务 | 原 cases/tasks routers、原 get_service、原 CaseService/HumanTaskService、原 C1–C6 执行器和保存/GET；未替换业务服务或数据库会话依赖 |
| 数据库 | 本机隔离 PostgreSQL `v12_upgrade_dev`；读取连接与已有 processor 写连接均实际使用；登录使用本机受控管理员凭据加固定 role，仅为隔离环境连接方式 |
| 身份 | 本地只替换 `get_current_user` 为明确测试主体，保留原 permission dependency；不声称本机登录或产品页面已验收 |
| 模型 | 真正的现有模型/计数接口，SSH 仅改内网传输；本机 TenantChatGateway 凭据解析未在该链执行，21 既有路由证据复用 |
| 数据源 | 演练原件复制到独立身份；没有厂商/ClickHouse 接入，来源不可用/跳过/查空按实际保存 |
| 直接检查 | 11 项连接/读开关/配置映射检查通过；隔离替身仅用于这些直接检查，不作为整链证据 |
| 展示 | 本地 4177 静态资料追加本 Case 到 64 份；产品页面 P01–P04 和交互接线仍在后续范围 |

证据入口：[本地核验](../../../../docs/operations/evidence/case-human-http-20261111-01/real-http/export/verification.json)、[实际请求 body 核验](../../../../docs/operations/evidence/case-human-http-20261111-01/real-http/export/model-input-verification.json)、[原 HTTP 请求回执](../../../../docs/operations/evidence/case-human-http-20261111-01/real-http/api-responses.json)、[只限本 Case 的落库快照](../../../../docs/operations/evidence/case-human-http-20261111-01/real-http/export/database.json)、[直接检查](../../../../docs/operations/evidence/case-human-http-20261111-01/direct-tests.txt)。

发布前只读配置比对发现 API 缺少处理 profile 的来源开关；清单已补四项 SOCAI2_SOURCE_*_ENABLED 与 SOCAI2_LAKE_DATABASE。API 已有湖连接目标同为 aisoc，保持原配置；没有增加权限设计或模型测试。依据 [配置差异](../../../../docs/operations/evidence/case-human-http-20261111-01/api-source-prerequisite.json)。运行后仅格式化配置模块导入，AST 与执行时一致；[本地收口](../../../../docs/operations/evidence/case-human-http-20261111-01/local-closeout.json)记录源码与既有 lint 限制。

## 发布与结束审计

[独立结束审计](audit.md)限定 ACCEPT。随后一次更新 21 API 为 `v1.2-20261111-r2`，镜像 `sha256:41ee6f3b2e42c0d3772a773c741f4e32c57650f01db9f0a488e30cb883ddf863`；其他五容器保持，处理镜像复用 r1，六项服务健康。实际写开关 true、写连接为 aisoc/socai2_prod_processor；五项来源配置与选定 profile 一致，通用 API 数据库连接保持。

生产以既有账号正常登录，独立验收 Case `9c1b65d3-e7e7-5b99-8bf1-eea8ebd8283c` 的建案、H 创建/修订/读取共 8 次业务请求成功，任务 8 项字段与库一致；2 次认证请求的敏感响应不保存。Run `20d99ae9-11a6-47ef-aee1-49afbd0d5cb3` 保持 pending_update，无模型调用、自动调查或消费者恢复，原 Case 只有读取操作。[生产回执](../../../../docs/operations/evidence/case-human-http-20261111-01/production-http/verification.json)

4177 静态记录由 34 增到 35，143 文件/144 HTTP 读取核验通过，原记录与展示源码保持。模型质量、产品页面、非空知识和自动处理的限制均不因发布核销。[完整交付回执](../../../../docs/operations/evidence/case-human-http-20261111-01/delivery-summary.json)

归档后最终 Git 交付以包含本回执与源码 manifest 的 V1.1 提交为锚点，父项目 SpiritHub/add-server-submoudle 的 server 指向该提交；远端实际 hash 另读回，不在当前提交内记录自指 hash。
