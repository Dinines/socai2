# Case分配、受理与关系HTTP本地验收

2026-11-15，第5步与调查侧联合完成本地验收。E01/E07/E08/E09返回真实多案分配，E01成功201；Case续建、两级关联列表、事件唯一接收目标已接通。候选81操作、无登录/Token/角色校验；Case新的调查提交入口仍未挂载。正式本地/21及71操作Swagger未变，未部署、提交或推送。

本批72次真实隔离PG/ASGI请求、23项直接HTTP/边界检查、目标Ruff和OpenSpec strict通过。见[最终汇总/源码摘要](final-checks-02.json)、[真实请求返回示例](examples.json)、[候选OpenAPI](candidate-openapi.json)、[接口逐字段指南](../../../integration/case-allocation-http.md)及[核心第5步回执](../case-allocation-20261115-01/README.md)。[前71次汇总](final-checks.json)保留；最后仅新增一次只读GET，不重跑此前23项检查。

## 实际保存与读回

| 批次 | 直接结果 |
| --- | --- |
| [writes-pg-01](writes-pg-01.json)，35请求 | 99+5→100/4；替换保留原成员、新增进接收案；移动源/目标同时保存；空数组只清空本案；后续续建后原key仍返回旧分配。操作/版本冲突和缺成员错误无部分保存。整事件当前263成员全部进入分配，未截成诊断100条。排除成员独立返回。7个新案initial任务均accepted，无attempt/Run；旧Case及源告警、事件成员、Run/attempt保持。 |
| [reads-pg-01](reads-pg-01.json)，29请求 | 14项关联按续建优先/共享事件其次，双重来源去重、全分页、共享独立案continuation=null；Case详情/列表/管理GET的continuation一致。事件正常/关闭/超期/无目标与真实接收标记准确，A字段不增加事件字段。读取前后13类记录摘要相同；另一次真实创建改变关联，旧游标409/cursor_stale，新查询能读新增关系。 |
| [added-only-pg-01](added-only-pg-01.json)，7请求 | 核心补正E07纯新增标记后，原案1→2、removed=[]但source.changed=true。SQL确认2成员、一个initial accepted且无Run；管理GET/修改回执/详情continuation一致，原PUT回执可重放。不重跑前两批。 |
| [alert-records-pg-01](alert-records-pg-01.json)，1请求 | 告警E30关联事件GET与真实SQL关联一致，保留原业务及关联字段，不透出内部active_case_id或事件详情专用case_receiving；13类记录前后摘要相同，0写库、0模型调用。 |

接收资格的三条新事件为明确标记的SQL测试夹具，用于读取closed/auto_window_expired/no_target；不冒称用户成功关联了已关闭案件。游标变化使用真实HTTP创建。模型、Redis和Case执行调用均为0；初轮受理不是调查完成。

数据来自调查侧独占交接的[pg-04](../case-allocation-20261115-01/pg-04/result.json)租户（无可用密码的记录人）。新HTTP操作只创建独立测试案件，并按明确整事件关联切换该测试事件的接收者；未清空、回填或改写历史批次。核心原事件最初260条，后续正常测试新增3条，故HTTP本批验证完整263；原260分配回执仍保留。真实profile指向隔离v12_upgrade_dev，129已由调查侧应用，不是正式环境验收。

## 边界及保留记录

[首次离线失败](write-contract-01-failed.json)发生于测试夹具给冻结DTO赋值，尚未发HTTP；改用model_copy后[四写11项装配检查](write-contract-checks.json)通过。最终23项还覆盖告警字段保持、事件范围读取、内部可信依赖、独立应用及旧同步A/I旁路为空，不以替身验证代替上述真实PG保存。

HTTP只在核心DTO副本上补case_url/status_url及公开错误，分配、排除、接收目标、资格、关系分页均来自核心；核心不依赖HTTP包。记录人配置失配映射服务配置错误，不增加调用方鉴权。

Case旧同步流程测试资料继续适用于原版本；本批只运行受影响的直接检查，不声称全仓回归通过。整个change后续Case实际执行、周期更新、定向/综合及最终独审/统一发布仍未完成，模型正文质量NOT_PASSED保持。
