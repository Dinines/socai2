# 验证与发布回执

## 本机候选已完成

证据目录：[subject-management-20261112-01](../../../../docs/operations/evidence/subject-management-20261112-01/)。

- `local-http/verification.json`：独立新批3告警/3事件，86次真实TCP HTTP覆盖六个单条/批量入口、D02、事件管理、整体拒绝、幂等及读回；79次200、3次409、3次422、1次404。未选第三个主体保持，原分诊及成员等级保留；新Case仅pending，不启动调查。
- `local-sql.json`：6主体的全部facts与HTTP最终读回逐值相同，原分诊/等级保持；使用真实本机隔离PG `v12_upgrade_dev`。
- `contract-check.json`：原47操作及原Schema逐项一致，新增6组请求/响应示例通过实际Pydantic验证；当前53操作、127类型。
- `monotonic-time.json`：独审发现关联事件更新时间可能倒退，已用greatest修正；独立新合成对象直接PG验证较新时间保留且版本递增。

以上没有调用模型、恢复消费者或修改页面。合成fixture初次准备缺少Actor.name和来源操作ID，均在事务内报错并整体回滚；已修正，成功批次独立记录。SQL核验脚本首次使用ORM返回键导致读取失败，修正为表列读取后通过；HTTP保存结果没有因此改写。

## 两端发布与直接验收已完成

2026-11-13完成发布。21沿用现有 `case-management` 基底，仅叠加页面路由挂载、主体管理路由、管理服务、合同和批量配置五个文件。显式profiles在 `deploy/http-service/subject-management/`；本机ARM64原生Python、21 AMD64 Docker。

| 核对项 | 本机 | 21 |
| --- | --- | --- |
| 服务／版本 | `127.0.0.1:18024`，`subject-management-20261112-r1-local` | `192.168.1.21:18024`，`subject-management-20261112-r1` |
| 实际数据库 | `v12_upgrade_dev` | reader/writer均为`aisoc`，实际writer为`socai2_prod_processor` |
| HTTP业务验收 | `local-release-http/verification.json`：86次 | `21-http/verification.json`：86次 |
| SQL读回 | `local-release-sql.json`：6主体facts逐值一致 | `21-sql.json`：6主体facts逐值一致 |
| 新验收Case | `83ceb088-ee3b-54e1-8fe3-8428c437dc15` | `0407cdc9-141c-5cb6-95a5-13ecfbfe62a3` |
| 版本和来源 | `local-api-release.json` | `21-api-release.json`、`21-runtime.json` |
| Swagger | `127.0.0.1:18080` | `192.168.1.21:18080` |

两端各86次均按预期通过（79次200、3次409、3次422、1次404）；覆盖六个入口、正常保存和GET、版本／幂等冲突、整批拒绝、未选对象保留及原分诊／成员等级不变。新Case只用于验证关联活动，未启动Run。候选批与两端发布验收分别使用新合成对象，旧批没有重新派发。

21实际镜像为`sha256:8ebdf8ff7c727355cb0ec0a886f380eaf22056d9892d0f2b9244026d8045af1d`，五个文件摘要与发布清单逐项一致，批量上限从配置读取为100。两端实际挂载53操作；原47操作和原Schema保持。除本轮独立API及Swagger外，其他生产容器保持原状，模型修改未带入21镜像。

两端Swagger均为`2026-11-12.docs7`：53操作、50已实现、3预留501，按告警／事件／调查分类。`local-swagger.json`与`21-swagger.json`记录首页、OpenAPI、manifest、guide、examples、字段页6个实际入口均200且内容摘要逐项相同；当前发布回执在`deploy/api-docs/deployment-receipt.json`，本批固定副本在`deploy/api-docs/receipts/20261112-docs7.json`。

Windows中继曾不可达，首次远端命令在执行前失败；收到负责人“已恢复，可以重试”后重新核对原运行版本，再完成上述唯一一次服务发布。没有以本机回执代替远端结果。

汇总见[delivery-summary.json](../../../../docs/operations/evidence/subject-management-20261112-01/delivery-summary.json)。本change没有新增表／迁移、真实模型调用、自动消费者启用或页面修改；本批未执行Git提交／推送。模型质量及主调查未完项保持原结论。
