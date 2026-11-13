# 设计

## 接口及边界

路径统一前缀 `/api/v1/socai2`：E48 POST `/alerts/{alert_id}/feedback`，E49 POST `/alerts/feedback-batch`，E50 PATCH `/alerts/{alert_id}/management`，E51 POST `/alerts/management-batch`，E52 PATCH `/incidents/{incident_id}/management`，E53 POST `/incidents/management-batch`。读取继续使用E28/E29和E30活动，不重复建GET。

单条带operation_key、expected_row_version及变化字段；批量带operation_key、items（id和expected_row_version）、共用feedback或changes。max_batch_items从配置文件读取，默认交付配置100；重复ID、空选择、超限拒绝。单条返回kind、facts（现有AlertFacts/IncidentFacts）、changed、feedback_id、activity_id；批量返回operation_key、items、changed_count。最新完整派生摘要从既有GET读。

反馈disposition和reason必填，复用四个判定枚举；写入kind=human_feedback的不可变assessment，绑定提交时latest_material_id，confidence=null、score_state=not_provided，actor由服务端认证身份生成；source_run_id为空。更新latest_feedback_id/disposition，模型latest_triage_id及其原答保持。误报／正常关闭为completed；已关闭改为true_positive/needs_review恢复in_progress，清空当前关闭字段并记录reopened_at，旧值在活动中保留；其他反馈不自动改状态。

告警管理仅owner_id、tags和handling_status；事件另含severity_override及severity_override_reason、resolution_note。省略不改，owner_id=null取消分配，tags=[]清空，状态不可null且不允许人工写unknown。人工关闭／解决需非空理由；重开记录恢复时间。仅分配不改告警状态；事件新分配进入in_progress，resolved事件只改负责人不重开。显式状态优先于分配的默认推进。事件等级覆盖须有理由，清空覆盖同时清空理由、操作者和时间；成员等级保持。

## 事务与保存

复用BaselineService事务及tenant上下文。按操作键取得事务锁以串行化同键请求，再按UUID排序锁目标行；版本逐项核对，所有校验完成后事务内更新。哈希包含主体、动作、操作者、明确字段和目标版本；相同key相同意图重放原回执，异意图409。批量一个activity、多target；回执沿既有target.after_value.operation_receipt保存，不新建幂等表。各目标均有真实前后字段；无变化不增加row_version，但仍保存可重放回执。反馈新请求总是追加人工记录。

人工反馈后按Alert→Incident顺序更新相关事件business_updated_at/row_version以标明成员判断变化，不改诊断指针或处理状态；Case用既有输入新鲜度读取比较feedback指针，活动经真实成员关联可读。旧Run/结果/输入不变，不自动准备或启动调查。管理修改只作用所选主体。

## 冻结合同核对

保持原AlertFacts、IncidentFacts、SubjectView、SubjectPage及原47操作Schema不变。已定义字段latest_feedback_id、disposition、handling_status、closed_at/by、reopened_at、owner_id、assignment_state、assigned_at、tags、row_version/business_updated_at按原含义写入；人工反馈结构复用现有alert_assessments与actor。没有改名、改类型、改空值/枚举/关联或现有GET返回，不新增合同确认环节。若实施发现必须更改冻结合同，先列差异与兼容再确认，不能用测试追认。

## 验证及发布

直接验证单条与批量正常保存、D02反向改判、人工关闭保留原判定、事件分配／解决／等级覆盖、重复和冲突、批量整体回滚、旧读取和历史保持。仅用新建带synthetic标记的告警／事件；不覆盖既有业务记录，不派发模型。HTTP和SQL逐项核本批字段与活动，复用原Case验证，不扩展矩阵。

本机ARM64原生Python先在18026候选验证；21 AMD64基于当前case-management镜像叠加本change文件；配置显式选aisoc和v12_upgrade_dev。候选通过独审后替换本项18024并发布Swagger。保留旧镜像／配置作限定回退，不改其他服务、卷或消费者。记录实际源码hash、镜像、profile、版本、操作数及读回。
