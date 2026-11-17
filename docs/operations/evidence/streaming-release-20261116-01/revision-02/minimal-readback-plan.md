# 第二版正式发布最小读回

范围按三个模块确认：一条v2网络观察告警和三条上下文，经当前正式Kafka→A/I→HTTP建一个Case首轮→4177。复用历史真实S04后轮/比较和F1–F5，不新增第二轮或缩短4h/6h周期，不以质量问题追加采样。此计划只补本次环境、会话修正和v2材料影响。

1. 先完成独审、显式aisoc的128/129和support GRANT，verify32表521列；普通reader/processor/ingress的PG/TLS及必要读写回滚探针、Redis目标、模型alias/tokenizer65536和知识集合配置读回。已清空库不再次清空。
2. 固定第二版处理/HTTP镜像，唯一Fusion/dispatcher；先HTTP和Swagger，核18024/18080与80项合同；再新核心和4177正式上游。原候选HTTP/Swagger只在新入口就绪后停止；旧五业务入口等停止清单逐一核对，不启动旧消费者。每步失败保留状态，不自动重发。
3. 生成新批`release-smoke-20261116-01`（若执行日变化则先改新批profile再生成）、当前UTC时间窗口。v2生成器及依赖/RawAlert模型/传输helper独立冻结；业务观察保持原字段，来源为telemetry-channel-01，Case标题不带测试/作者答案。登记该中性connector仅供FK/来源关联；测试分类只在账本和源映射控制文件，业务事件不带预期。
4. 本批发送入口只接受显式formal profile、固定1/3数量和冻结字节，复用alert_kafka.send_records的独占意图/逐ACK/unknown语义，不修改现有CLI的候选Topic限制。先核就绪回执及offset，再只投三条raw_events；真实湖保存核tenant/主机/event_id/时间/原观察，且未生成告警/任务后，才允许投一条source-v1告警。ACK不是处理通过。
5. 观察A/I真实task→attempt→Run/保存结果，必要HTTP读取同身份原件；程序结果可用后POST /cases（新operation_key）并保存201真实回执，沿其initial_task/status_url观察首轮，记录实际模型原答/usage、领域/工具状态、结果及采用关系。初轮比较保持空，查询按实际前后1小时/主机/类型验，不套用fixture5分钟/目的IP排除预期。
6. 显式publish新live_execution账本及http-exchanges证据，使用同正式environment/tenant。4177浏览器核实际POST→任务→步骤/组件→原答/结果，同Run；紫色测试标识只在查看层，真实未命中领域/查询不伪造。完成必要保存快照与HTTP原件一致性核对，保留质量NOT_PASSED/部分交付/待复核的实际结果。

发布成功后保留正式唯一执行器运行；其他项目和旧批备份保持。Git按已有授权在实际读回/交接之后一次同步，整个含后置项change不归档。
