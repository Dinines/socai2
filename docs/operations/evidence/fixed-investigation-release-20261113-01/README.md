# 固定调查功能版发布回执

21核心已发布 **v1.2-20261113-r1**，显式调查入口已激活 **processing-20261113-r1**。只切换`socai2-api-1`一次；独立18024、Swagger和工作台未发布。本阶段功能交付不等于模型质量或主调查整体通过。[机器回执](delivery-summary.json)、[接口接续说明](handoff.md)、[发布计划](../../../../openspec/changes/complete-socai2-investigation-chain/fixed-flow-release-20261113.md)。

本版包含A/I、C3、Deep、C6按任务筛选输入、必要前序和依据，以及程序覆盖/观察装配和综合结果保存读取。查询只给必要业务结果，未查询写未查询；原件、人工正文和失败保留。C3模型回答五项业务问题，程序补coverage后仍保存六问，旧冻结六问继续兼容。没有HTTP合同、告警交接字段或数据库表变化。

直接验收：

- 复用[10批真实固定Run](../fixed-investigation-20261113-10/README.md)及[第32节修复](../case-c3-coverage-20261113-01/README.md)，136项调查源码和已验策略逐项一致。此次零新增模型调用，未重复模型质量采样。
- 处理镜像构建核698文件，复用构建器的一项C6无模型检查；API候选核668源码。冻结文件和运行绑定文件核对一致，实际策略SHA为`a3298006f954f0a811e76a95bb26a1fbab866dd44260662a10af2bb4bc88d9d8`；A/I各首答加一次纠正、24000tokens，Case6次/131072tokens。
- 核心健康HTTP200；新容器内通过CaseService和真实`aisoc`数据库读取既有Case、1份Result和当前判断。前后完整读取摘要及该Case的cases/runs/results/case_assessments原行摘要均一致。业务读取是容器内服务调用，**不是本轮认证TCP业务接口验收或生产新模型Run**。
- 7个指定保留服务的容器ID、镜像、启动时间、挂载和Compose一致，包括独立18024、Swagger、工作台、Fusion、Agents、投影、网关；Agents自动分析继续关闭。未对其他所有容器做全面核验。
- 旧API启动时间后的running Run为空；此限定检查不代表全库无旧active/unknown。全程无新增调查、业务写入、迁移、清库或Git提交推送。

发布器已在21 private目录保留旧Compose、runtime/ingress配置和入口指针；旧镜像保留，回退不回滚数据库。原始读取失败`preflight-01/02`为检查脚本时间参数问题，`03/04`为核心生产模式不暴露OpenAPI的路径误判，均在切换前产生并保留；`05`及后续成功回执不覆盖它们。

未完范围：流式更新与任务合并队列、人工反馈自动重算、自动分析消费的实际闭环、AI对话和真实响应。M01/M02及F01/F02正文/知识/反馈合理使用质量按负责人决定后置，仍为NOT_PASSED。主change31/41不归档；限定独立审计见[audit-before.md](audit-before.md)及发布后[audit.md](audit.md)。

回执顺序为processing freeze/upload/build、unified freeze/upload/build/preflight、只读before、prepare、单次rollout、activate、只读after。`released-source-manifest.json`给接口侧所需完整源码摘要；实际冻结源码在本机`.local/unified-release/v1.2-20261113-r1`和21同名releases目录，使用指定目录，不按工作树的后来修改推断本次版本。
