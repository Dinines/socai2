# F4：告警和事件成员转入Case

**2026-10-28真实联调：** 120/121现已在21安装。事件子集创建Case、告警成员追加、同key回执读取、按来源查询及选定范围预览已用真实PG通过；新增1个测试Case/2条关联/0个Run。[实际输入输出和对象](incident-case-basic-flow-20261028.md)。未常驻部署；下文测试描述保留原实现当批范围。

2026-10-28。已实现接口代码及5个直接用例，未执行数据库迁移或部署。此前[接口设计](interface-contracts-20261027.md)第4节和5.4节现有对应实现；F5自动入口、产品HTTP Tool和事件Case报告回显仍未接通。

## 已有入口

| 接口 | 功能 |
| --- | --- |
| `POST /api/v2/investigation/case-links` | 明确选择Alert成员，创建或关联Case；首次201，同key同意图200读取原回执，冲突409 |
| `GET /api/v2/investigation/case-links?incident_id=…` | 按来源事件读取转Case历史；也可按alert_id查，两种筛选必须恰有一个 |
| `GET /api/v2/investigation/cases/{case_id}/investigations` | 当前Case的case_analysis.v1调查历史，不混入旧fixed/program Run |

以上注册到独立`case_analysis_api:create_app`及兼容结果/启动factory；旧v1 app不变。列表均支持limit（默认20、1–50）及cursor，返回items/next_cursor；无记录为空列表，无Case为404。

POST复用已有`cases:write`、`cases:read`、`alerts:read`依赖；列表复用两个read权限。没有新增权限体系或运行权限专项。

## 请求与下一步

```json
{
  "operation_key": "44444444-4444-4444-8444-444444444444",
  "source": {
    "type": "incident",
    "incident_id": "11111111-1111-4111-8111-111111111111",
    "alert_ids": ["22222222-2222-4222-8222-222222222222"]
  },
  "target": {"mode": "create", "title": "主机异常外联调查"}
}
```

告警详情用`source.type=alerts`及明确alert_ids，不传incident_id。关联已有案件用`target.mode=attach`及case_id，不传title/description。返回case_id、selected_member_ids、新加入/原已存在成员、来源Incident、关联ID和跳转URL；不返回Run，不调用模型、Tool或ITSM。

要随后调查，调用返回的investigate_url，使用新的operation_key，明确传本次selected_member_ids、start/end及question。不能省略selected_member_ids而把已有Case其他成员也带入。仍由既有F3入口固定本次范围、分析和保存报告。

## 成员与保存规则

- 从当前租户PG读取canonical Alert；事件来源逐个核对归属，不依赖Redis成员ID。不存在404，归属变更409，不部分成功。
- “全部”只处理调用方显式提交的集合；同当前事件成员相等标all_current，否则subset。随后增加的事件成员不自动加入Case或Run。
- 新Case为new，严重度取所选成员最高已知等级。向已有Case去重追加，不移走其他Case成员，不改Alert.case_id；resolved/closed目标409。
- 新表`investigation_case_links`保存主体/规范化请求、所选成员、来源Incident和完整回执；与Case变更同事务提交。同操作锁避免相同key重复建案，已有Case行锁用于追加成员。这里只说明代码事务方式，未据替身验证宣称真实PG竞争已验证。
- 同key重读先返回原回执，不重新解析变化后的事件，也不再次写Case。关联GET返回转入时的历史，不冒充Case当前成员或报告。
- Case历史列表只从对应结果工件投影停止原因和completion；running无结果保持null，不读取完整Markdown，也不推断Case已解决。

迁移文件：[121_investigation_case_links.sql](../../services/api/migrations/121_investigation_case_links.sql)。原实现批次只新增文件；后续基本运行联调已安装120/121，迁移登记从134变为136，未启动常驻服务。

## 直接验证与边界

```text
python -B -m unittest discover -s services/api/tests -p test_case_links_api.py -v
```

本轮5项通过：

1. 事件全成员创建Case、最高严重度、顺序归一、同key回执重读及不同意图409。
2. 子集关联已有Case、区分新加入/已存在成员，再把选定成员交给实际F3上下文读取函数；未选成员不扩大进去。
3. 来源成员不匹配、已关闭Case、成员不存在和重复ID请求不写成员。
4. 单Alert来源建立关联；事件/Alert查询、分页及范围不匹配游标拒绝，空列表读回。
5. Case历史running/完成但partial状态、分页、tenant/Case/profile SQL条件、无Case404；没有完整报告或执行副作用。

用例使用实际ASGI路由与SQL生成/参数，但数据库返回由替身提供。没有真实PG事务/RLS/锁竞争证明，没有真实模型或事件湖调用；F4→F3验证止于选定范围传入实际context函数，不称新建Case后真实整链已运行。未重复执行既有未改的F1–F3用例，也未扩展恢复、压力或可用性测试。

源码：[成员转入](../../services/api/app/investigation_v2/case_links.py)、[路由](../../services/api/app/investigation_v2/case_links_api.py)、[Case历史](../../services/api/app/investigation_v2/case_history.py)、[直接用例](../../services/api/tests/test_case_links_api.py)。下一项仍按具体功能推进；F5需要先明确自动Case目标政策，本版不替它猜目标或开启自动调查。
