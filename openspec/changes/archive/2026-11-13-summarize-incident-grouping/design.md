# 同范围事件归并统计

## 页面与口径

对应F06-06，依据`prototypes/security-pages-v2/app.js`的事件顶部卡片：处理中为事件handling_status=in_progress；压缩为1-事件数/去重成员告警数，表格关键词/负责人筛选不改变顶部统计。本批只交付后端接口，页面不改。

E57接受可选`source_namespace`（告警来源精确匹配，区分大小写，空白拒绝）、`time_from`/`time_to`（带时区、UTC归一化，[from,to)，允许单边，起点严格早于终点）。均省略统计当前租户全部告警。按alerts.event_time选范围，不以事件创建时间/归并时间/告警入库时间替代；时间筛选排除未知时间，无时间条件则包含。未知/不支持的参数422，不接受列表q/owner/状态/分页/排序，以免误认沿用事件表格筛选。

## 输入、处理、输出

范围内告警集合A；按当前incident_alerts关系找到集合中已归并的不同告警G和这些关系关联的不同事件I。一个告警的当前事件归属由既有唯一约束保证，统计仍按不同身份去重。

- alert_count=|A|，grouped_alert_count=|G|，ungrouped_alert_count=|A|-|G|。
- incident_count=|I|；in_progress_incident_count只数I中handling_status=in_progress的事件。已解决事件仍属于I，Case/Run状态不参与。
- compression_rate=(|G|-|I|)/|G|，返回0..1的小数，调用方乘100展示百分比；G为空时null，不补0。不包含未归并告警，也不是误报率、正确率或解决率。
- scope回显三个规范化输入；observed_at为该只读快照时间。结构固定为schema_version=`socai2.incident-grouping.v1`。

例如6条告警，其中4条归为2事件、2条未归并，则返回6/4/2/2，compression_rate=0.5；不是将6条都当作已归并。跨时间或来源的事件，只计范围内成员，事件身份一次；其他成员不扩入分母。没有范围内成员的空事件不计。所有数字使用同一REPEATABLE READ/READ ONLY事务；不保存统计副本、不写历史、不改变归并关系。

## 代码及兼容

核心查询`app/socai2/grouping_summary.py`及独立DTO；只依赖存储和合同。对外路由`investigation_http/external_routes/grouping.py`经port和adapter直接调用，无HTTP自调用。固定路径先于事件UUID路径注册。沿用alerts:read与页面读取开关，不新增角色流程。

原56路径/方法/组件Schema保持，本次仅增加新统计响应。原E26/E27的total/overall_stats含义、告警事实/分诊及数据表不变。JSON新字段只属于E57，不调整冻结告警交接字段。无可变地址/限额硬编码；部署地址、端口、版本和显式数据库沿各环境profile。

## 直接验收与交付

本机新合成批次覆盖已归并/未归并、同事件多成员、时间边界与未知时间、跨来源成员、无成员事件和各事件状态；真实TCP响应与独立SQL计数一致，前后目标行保持。必要离线检查验证0/null/比例、日期和未知参数、原56合同与边界；不加压测/故障矩阵。

更新E57输入输出逐字段、百分比示例、错误、F06-06及README/进展。未参与实现者结束审计后，基于当前list-export镜像只叠加本批明确文件，冻结本机同源候选；统一发布本机ARM64与21AMD64独立服务及Swagger docs10。21用既有合成范围只读复验，不新写生产库，不调用模型。实际版本/配置/读回与其他容器核对后归档，随后固定Git skill提交推送V1.1/main和父项目引用，保留并行模型工作。
