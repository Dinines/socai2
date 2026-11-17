# 第5步：Case成员分配与受理

本步沿tasks第5步及HTTP合同8.3–8.4实施。用户于2026-11-15授权本地实施与HTTP联验，暂不部署。目标是一次业务操作保存正确的成员分配、续建关系、事件接收目标和新案首轮任务；第6步才接Case实际执行，第7步才接周期跟随驱动。只登记task，不预建pending Run，不调用模型。

## 保存与入口

新增迁移129：cases增加continuation_root_case_id、previous_case_id、receiving_case_id，incidents增加active_case_id，新增case_alert_exclusions。保留V1与128及历史业务数据，不回填旧对象；同租户外键、续建链校验和事件接收目标对应case_incidents关系在增量中约束。旧记录无续建信息读null，不猜选或激活旧对象。

CaseService的create_case、associate、change_members、move_members保持调用参数，统一进入容量分配用例。配置通过SOCAI2_CASE_ALLOCATION_CONFIG_FILE显式加载，case.max_alerts默认100，来源分页与列表分页另配；任务重试/生命周期复用AnalysisTaskPolicy。用例事务不调用Redis或模型，任务提交后由已有调度器拾取。

1. 先锁涉及的root，再锁实际Case，跨串移动按UUID确定顺序；同operation_key优先核意图并返回历史完整分配回执，不能根据最新指针重算。
2. 核请求Case版本和开放状态，沿root解析实际接收者；源事件成员在同一SQL语句快照内流式分批读取完整集合，不沿I选取的100条或HTTP数组200条截断。核告警存在及来源namespace一致。
3. 显式告警重新添加撤销本串相应排除；整事件选择和自动跟随仍尊重排除。本串已有成员记existing_alert_ids，不复制到新案；独立串可以共有告警。E07只移除请求Case未保留的成员，E09只移出请求源Case所选成员；移除记排除，原Run不改。
4. 填满当前接收案后，确有溢出才续建；新案沿首案title/description/severity/tags创建，保持独立状态、成员及任务，不复制旧结论/采用/执行。更新root接收指针，仅转交仍指向旧接收案的事件并补实际关联；手动明确选择的整事件在操作结束时指向实际接收者。
5. 各新案有成员后，在同事务调用AnalysisTaskStore.accept登记initial任务；已有案成员变更只更新scope_revision及活动，不立即提交调查。回执保存到既有活动operation_receipt，复用幂等记录，不新增回执表。全部成员/版本/指针/新任务一起提交，任何校验错误整笔回滚。

自动跟随用例作为后续可调用入口，本步直接验证其分配行为，不挂周期任务。它只处理事件当前接收者，按开放和创建/最近正常完成后的7天判断；同输入分析停止不影响新成员加入。目标关闭或超期不追加、不另建绕过限制；手动超期可追加，但关闭仍拒绝。接收目标在锁定后若已切换则本次不向旧目标写入，下次检查读取新目标。

## 返回与只读

核心提供CaseAllocationReceipt、CaseReplacementReceipt、CaseMoveReceipt及continuation；URL由HTTP适配填充。linked_incident_ids只列本次实际新增的显式关系；excluded_alert_ids列本次因本串排除未分配的源成员，避免将明确排除误认为漏分配。E07 source.changed反映请求Case最终是否变化，包括纯新增仍落本案的情况。初轮task仅返回已受理身份，最新状态沿已有任务GET读取。HTTP负责E01/E07/E08/E09的新响应及已确认状态码，取消这些回执的pending_run_id；新Case investigations入口仍不挂载。

关联Case查询在数据库先按Case ID归并真实来源，续建组优先，共享事件组其次，各组created_at/id升序；关系摘要绑定游标，关系变更409/cursor_stale。共享事件保留两侧explicit/member_alert来源，不改接收指针。CaseView的详情、列表、管理GET及管理回执均沿root读receiving。RelatedCaseItem只在同串时给continuation，共享事件独立案在该关联列表中为null。事件详情增加case_receiving（不受分析停止标记影响），事件cases每项增加is_active_receiver；告警DTO、告警cases及关联事件返回不变；新增active_case_id仅由事件专用合同提供，不随全行投影泄漏到告警接口，也不进入I原输入摘要或造成旧I新鲜度变化。

## 直接验证与交接

复用现有任务生命周期、公共task GET和页读取能力；新批次使用明确profile的隔离PostgreSQL，零模型调用、零Case执行，不启动正式服务。不建设压力/恢复矩阵。

| 输入与行为 | 直接判据 |
| --- | --- |
| 99条后加5条；整事件260条创建 | 分别100/4和100/100/60；每新案独立task、无attempt/Run，事件完整成员不截断 |
| 后续续建后重放原创建/关联 | 与原回执逐字段一致；不新增task/Case、不抢回事件接收者；同key不同内容409 |
| 事件分别关联独立Case；后续旧串续建 | 全部关联保留，仅新明确关联目标活跃；旧串续建不偷取新目标；告警跨独立案允许 |
| E07替换、E09跨案移动、显式排除/重新添加 | 只改指定源成员；保留成员留原Case，新增分配到接收案；本串不自动加回排除，显式单告警可恢复 |
| 版本/namespace/关闭冲突 | 整笔无部分保存；手动超期受理、自动超期/关闭不分配 |
| 续建/共享事件重叠、分页关系变化、接收资格 | 去重排序/来源真实，旧游标409；GET前后业务摘要相同；I新增字段不泄漏到A |

核心提供实际新批次Case/事件/task和保存读回回执，HTTP完成真实PG/ASGI输入→保存→读取联验及Swagger/交接文档。证据落新批次目录，tasks/PROGRESS原位更新；本步通过只完成原2.2/2.7的成员分配部分，不勾整项、不宣称Case自动调查或整个change完成。模型质量NOT_PASSED历史状态不变。
