# Case评论最小闭环

## 范围与输入输出

F24-01只要求阅读及提交，故本批不增加编辑、删除或回复线程。

- POST `/api/v1/socai2/cases/{case_id}/comments`：`operation_key` UUID、非空白`body`（最多20000字符，原文保持）。作者和时间由服务记录，不接收客户端作者。返回完整已保存CommentView。
- GET同路径：`limit`默认20、1–100，`offset`默认0、0–100000；返回items、total、next_offset、observed_at。按created_at、id升序，便于按时间连续阅读；同一请求使用只读一致快照。非法/未知参数422。
- 同案不存在404，参数错误422，幂等键换内容或操作者409；读取/写入复用现有开关及cases权限。成功评论不等于核实事实或采用结果。

## 保存与边界

独立`case_comments.py`用例复用Case事务、作者检查及活动收据；锁定Case后核幂等，新增comments、增加Case行版本/业务更新时间并记录case_comment_created活动。同键同意图返回原评论，不重复新增；不同案可独立使用同键。没有客户端预期行版本，因为评论是追加，不覆盖其他人的输入。

评论属于当前认证租户、指定Case；不写alert_id/incident_id，不按成员关系混入别案评论。已结案Case允许补充协作说明，状态保持；不会重开、创建任务、启动Run或修改当前判断。正文按纯文本交接，调用方应作为文本展示。评论没有接入模型事实或有效人工反馈，需核实的事实仍通过人工任务保存。

既有comments字段、表和告警/事件读取合同保持；不新增迁移。只写comments、cases管理时间/版本、activities和activity_targets，Run/Result/H/成员保持。活动包含Case和评论目标，E17可回查提交回执。

## 代码与发布

`app/socai2/case_comment_contracts.py`与`case_comments.py`负责DTO和业务；`investigation_http/external_routes/comments.py`经独立port与adapter调用核心，不导入SQL或内部HTTP。原Case调查实现不改。

本机ARM64冻结源码从已发布grouping-summary目录复制，21 AMD64从已核镜像派生，只叠加本批文件；显式profile定义地址、端口、库及路径，实际读取核对后发布。其他服务/消费者保持。不把工作区并行模型文件打入发布。

## 直接验收

本机新批次通过HTTP创建独立合成Case，只提交普通评论，不启动其待执行Run；核对原文/作者/时间、分页、空白拒绝、幂等重放/冲突、错误Case、活动读取及SQL。核对Case范围/当前判断、Run/任务/结果不变，业务时间及版本按提交次数增加。生产发布后仅创建本批明确标记的验收Case/评论，使用已有合成告警，读取核对；不写其他Case。原57操作保持，源码/配置/Swagger读回，独立结束审计后归档。回退只切回前版API/静态Swagger，保留新增评论和历史。
