# 人工任务、确认结果与下轮基础调查

2026-11-04，OpenSpec `complete-socai2-investigation-chain` 3.5。本批使用现有 `tasks/task_revisions`，不增加表、列或公共枚举，当前仍29表459列。新链单开服务，旧版及页面不替换；任务接口沿用 `SOCAI2_CASE_API_ENABLED` 和 `cases:read/write`。

## 职责与完整流程

H 是用户确认系统数据以外的事实，不是人工Agent或机器Run。保存任务、完成任务、修改反馈都不会自动调用模型/Tool、采用案件判断、解决Case或生成pending。

1. 用户提供事项、说明、负责人、期限、状态及可选结果/明确范围；已完成必须有非空结果和显式范围。请求不得自带租户、实际完成者、完成时间或事实角色。
2. 服务验证认证用户及负责人同租户，按 Case→Task 顺序加锁，校验 Case 范围版本及任务行版本。Task ID只在首次创建产生，后续编辑同一任务。
3. `tasks` 保当前版本指针。每次有效内容变化都 INSERT 一条 `task_revisions`，更新指针/行版本/业务时间和活动；旧revision受数据库不可变保护，不覆盖正文。
4. 已完成任务只改标题、说明、负责人或期限时，保留原完成者与完成时间，并记录本次修改者与修改时间。改结果、范围或参考来源时由当前操作者重新确认；重新进入已完成同样重新记录完成事实。
5. 未开始、进行中、已完成、已取消均可编辑。取消或重新打开的当前revision不带完成时间/人，旧已完成revision仍可读取。取消表单无调用；同内容明确保存返回 `changed=false`，不新增revision或刷新Case业务时间。
6. 所有修改按操作键保存原回执，重复请求即便任务已被后来修改也返回原结果。相同操作键换内容拒绝；并发编辑用 `expected_row_version` 使一个成功、另一个冲突。正文、指针、Case业务时间与活动一起提交，提交失败整体回滚。

来源调查仅在创建时指定同案正式Result；来源finding必须确实属于该Result。该原始来源关系固定，编辑请求不允许重写它。补充参考可编辑，但只接受服务端能核验的内部材料/工件/结果/任务版本ID；不支持在这个接口上传附件或填任意外部链接。

## 事实范围与历史引用

新增或重新确认结果时，`result_scope.alert_ids` 必须非空且属于当前Case，`whole_case`须明确列全当时成员；所选对象必须来自这些成员当前材料的对象集合。范围同时保存可选时间窗口和限制。客户端不能传“全案”标签让后台随未来成员自动扩范围。

纯元数据编辑允许保留原确认范围，即使成员已经移出Case，也不偷偷改其适用范围。读取历史revision仍显示原成员和原完成事实。

Case领取基础调查时，C1在原单条快照中保存当时当前任务revision及当前判断引用的旧revision。**完成、有非空结果、范围可解析、范围非空且全部仍属于本轮成员**，才可作为 `human_statement` 进入新模型。任何成员已移出时，本批采取保守规则：整份反馈仍保存在C1原件，标记 `feedback_scope_extends_beyond_case`，但不把其中部分声明截出来泛化。无范围、空范围、未完成也只作为执行记录留存。新成员加入不扩大旧反馈的明确成员集合。

模型读取的是那次冻结版本，完成者、时间、结果和范围一并保留，引用身份/角色不由用户自称。之后用户改任务或移成员，不改旧Run的C1/工件、Result或引用。任务当前页与 `/{task_id}/revisions/{revision_id}` 可分别读取现状和历史依据。

## 成员不变时如何使用新反馈

审计发现原来只有成员变化会产生pending；基础调查完成后若只补了人工结果，用户没有准备下一轮的入口。本批新增显式操作：

`POST /api/v1/socai2/cases/{case_id}/baseline/prepare`

请求仅含 `operation_key` 和 `expected_scope_revision`。服务在Case锁内复用现有pending，或新建一条 `kind=baseline,state=pending_update,trigger=manual`，purpose为“根据当前材料和人工确认重新调查整案”；不改成员范围版本，不执行或排队。原枚举没有 `manual_refresh`，因此使用已存在的 `manual`，不新增DDL。

已有running/unknown时允许准备下一pending，但原start会返回活跃冲突。当前轮结束后仍须用户手动调用原 `/runs/{run_id}/start`；启动事务才冻结最新H及其他输入。已解决、空Case或预期范围版本过期时拒绝准备。重复操作重放原回执，原pending后来已启动也不会再造一条Run；新的用户操作键才代表一次新的准备意图。

这是服务端为后续页面接入准备的差异点：完成H后页面应允许用户显式准备并启动新一轮；本批不修改页面，也不把保存H改成自动触发。

## 字段与真实出口

| 编号 | 字段/语义 | 持久来源或派生 | 出口/边界 |
| --- | --- | --- | --- |
| H01 | 任务身份 uuid | tasks.id | TaskView.id；编辑保持 |
| H02 | 案件身份 uuid | tasks.case_id / task_revisions.case_id | 路径及DTO，所有引用同案 |
| H03 | 当前revision uuid | tasks.current_revision_id | current_revision_id/current |
| H04 | 来源正式调查 uuid/null | tasks.origin_result_id | 创建可选，真实同案，之后固定 |
| H05 | 来源发现 text/null | tasks.origin_finding_id | 必须在来源Result.findings中 |
| H06 | 创建人 uuid | tasks.created_by | 服务端认证用户 |
| H07 | 创建时间 timestamptz | tasks.created_at | DB时间 |
| H08 | 最近修改时间 | tasks.updated_at | 内容变化更新，GET不写 |
| H09 | 并发版本 bigint | tasks.row_version | edit.expected_row_version |
| H10 | 版本身份 uuid | task_revisions.id | 历史引用精确身份 |
| H11 | 版本序号 bigint | task_revisions.revision | 每次有效编辑加1 |
| H12 | 事项 text | task_revisions.title | 非空白，最多200字符 |
| H13 | 工作说明 text/null | task_revisions.description | 最多10000字符 |
| H14 | 负责人 uuid/null | task_revisions.assignee_id | 同租户用户，NULL未分配 |
| H15 | 截止时间 timestamptz/null | task_revisions.due_at | 有时区，不由运行状态推导 |
| H16 | 状态 enum.task_state | task_revisions.state | not_started/in_progress/completed/cancelled |
| H17 | 人工结果 text/null | task_revisions.result_text | 完成必填，最多20000字符 |
| H18 | 范围种类 | result_scope.kind | whole_case/selected_alerts/explicit_objects |
| H19 | 确认成员 uuid[] | result_scope.alert_ids | 明确当时成员，最多200，不自动扩展 |
| H20 | 确认对象 text[] | result_scope.object_keys | 核当前所选成员对象，最多200 |
| H21 | 事实时间窗口 | result_scope.window_start/end | 成对、有时区、起点不晚于终点 |
| H22 | 范围限制 text[] | result_scope.limitations | 原值保留，进入模型仍受原guard/预算 |
| H23 | 参考资料身份 | task_revisions.source_refs | 最多50，核同案材料/工件/结果/任务版本 |
| H24 | 参考角色 | 服务端生成EvidenceRef | material=observation、result=prior_analysis、artifact=execution_receipt、已完成task revision=human_statement |
| H25 | 实际完成者 uuid/null | task_revisions.completed_by | 服务端认证用户，不等于负责人 |
| H26 | 实际完成时间 | task_revisions.completed_at | 首次/重新确认用DB时间；元数据编辑不改 |
| H27 | 本次修改人/时间 | changed_by/changed_at | 与完成事实分开，全部revision保留 |
| H28 | 操作回执 | activities/activity_targets | 操作键、请求指纹、前后revision及原响应 |
| H29 | Case范围前提 | 请求expected_scope_revision | 只校验，不因H增加scope_revision |
| H30 | 历史/列表总数与下一页 | 独立count及稳定排序 | total/next_offset，每页1–100 |
| H31 | C1人工材料适用性 | usable_feedback、limitations、citation_roles | 只适用同轮范围；旧冻结不回算 |
| H32 | 下轮准备回执 | case_id/scope_revision/pending_run_id/created | 真实runs行或复用原行，不伪造已执行 |

补充参考请求只允许 `{type,id}`，持久EvidenceRef由服务端补 `role/external/source_path/row_keys`，防止客户端伪造观察身份或任意路径。已保存且未改参考的元数据编辑保留原引用；历史材料无需追随当前指针。

## 接口

前缀 `/api/v1/socai2/cases/{case_id}/tasks`：

| 方法/后缀 | 返回 |
| --- | --- |
| POST 空后缀 | TaskMutation，创建身份及首版本 |
| PUT `/{task_id}` | TaskMutation，明确保存同一任务 |
| GET 空后缀 | TaskPage，当前版本列表 |
| GET `/{task_id}` | TaskView，当前版本 |
| GET `/{task_id}/revisions` | TaskRevisionPage，版本倒序 |
| GET `/{task_id}/revisions/{revision_id}` | TaskRevisionView，精确历史 |

六条路由共四个模板，运行时合同见[H OpenAPI](../design/socai2-human-tasks-v1.openapi.json)。准备基础调查为原Case API新增一条独立POST，见[Case OpenAPI](../design/socai2-case-api-v1.openapi.json)。所有读取使用只读可重复读事务；接口不暴露tenant/内部请求指纹，不访问旧版表作回退。

## 四个完整例子

1. **确认授权**：A、B进入Case但无法从接入数据得知维护审批。用户建“核对维护授权”，负责人U1，完成时用户U2记录“只确认A属于维护”，范围选A。completed_by保存U2，不拿负责人U1冒充实际确认人；后续模型只能把反馈用于A。
2. **修订反馈**：版本1确认A，某轮C已冻结版本1。之后用户改结论“仍待核”，完成状态下保存为版本2，记录新的完成/修改时间。旧轮继续引用版本1；当前任务显示版本2，下一轮再使用版本2，绝不回写历史报告。
3. **移出部分范围**：原反馈确认A、B，后来B移出Case。用户仅改任务标题，原完成者/时间和A、B范围保留。下一轮C1标记超出范围并不将整份反馈供模型判断；用户若要单独确认A，须明确把结果/范围改成A后保存。
4. **人工确认后的重查**：上一轮C已完成、成员仍A、B。用户完成H，系统只保存H，不新建Run。用户显式prepare后出现一条manual pending，再手动start才冻结最新H并执行完整C。如果旧C还running，prepare可复用下一pending，但start返回409；旧轮结束不会自动启动。

## 验收范围

[固定回执](../operations/socai2-human-tasks-20261104.json)记录10项H新检查、相关C1/model-view回归，以及显式prepare闭环检查；每批保实际源码指纹和原失败（如有）。真实PG事务、延期FK提交失败回滚、不可变revision、并发冲突、租户/权限和历史读取均使用21既有独立合成库验证；无真实模型/湖或业务数据。H不需要新增表，未替代旧服务、未改页面；独立服务总体验收另由主任务记录。
