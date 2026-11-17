## 范围与接口
实现 F25-03，补足 F25-02 的状态保存。GET `/cases/{case_id}/exploration-base` 取得当前底图；PUT `/cases/{case_id}/exploration` 保存；GET 同路径恢复最近版本，尚无保存时 `snapshot:null`。不提供助手、自动加入成员、自动调查或独立版本管理页面。

## 底图与来源
默认选本案最近 completed baseline Run（ended_at、id 降序），保留 delivery_state。取该 Run 的 baseline Result 图原件；缺图明确 unavailable，不能改用另一轮或当前成员图。无 completed baseline 时使用当前 Case 成员最新材料中的对象关系。允许指定本案已完成 Run 作为历史阅读转当前探索的起点。纯 AI 对话结果不参与。
响应含 base_fingerprint。首次保存或重置时送回 run_id（成员底图为 null）和 fingerprint，服务端重建并核对，来源变化返回409。保存后以 base_snapshot_id 引用本案既存快照继续，底图直接复制原保存内容，因此新调查、材料和成员变化不替换已保存底图。重置由客户端重新 GET 当前底图并 PUT 空展开及新视角完成，GET 不写库。

## 展开及画布
输入 expanded_links 为 E66 的 seed/candidate 对象 ID 对；服务端读取真实对象及原材料标识，验证同租户、同案件来源、同对象 namespace、类型与 E66 精确值/明确哈希算法规则，拒绝不存在或不匹配对象。允许原材料版本，以便已保存探索继续；不宣称这是新的实时 E66 查询。每条新增连线必须从底图告警或前序展开告警出发，按输入顺序形成可追溯链路。保存匹配原件及涉及告警/对象快照；继续已有保存时保留原快照，新节点读取当前事实。匹配表示共有对象，不是因果或恶意判断。撤销通过去除相应展开及其后续分支再保存。
view_state 仅存客户端 JSON 展示状态（位置、选中、隐藏、视角、筛选等），原样返回；其节点键由客户端解释，不作为来源、证据或成员。配置限制总存储字节，超限422，不能静默截断。前端需提供自己的画布渲染，不在本轮修改测试页面。

## 存储与并发
artifacts.kind=source_snapshot，schema_version=socai2.case-exploration.v1，case_id 绑定、run_id=NULL；单独 schema 不进入调查结果/证据索引。每次保存不可变快照，GET 最新按 captured_at/id 排序。expected_snapshot_id 必填（首次 null），在 Case 行锁内与最新 ID 比较；冲突409防覆盖他人。operation_key 与用户/完整请求摘要绑定，原请求重试返回原保存，改请求409。活动表保存回执；不修改 Case 版本/时间、成员、Run、Result、任务或评估。

## 验收与发布
本机独立新 Case，走 GET 底图→E66→保存→读回→继续/撤销/重置，验证幂等、冲突、无保存、非法来源和缺图；SQL 对比不应改动的业务表。已有真实历史 Run 的底图只读检查，合成完成 Run 验证新结果不替换旧快照。离线 HTTP 边界及旧66合同保持。独立结束审计后，基于上一已发布镜像只叠加本变更文件，一次发布本机/21 API 和 Swagger，21 只读验证。
