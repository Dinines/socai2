# 默认调查报告语义修复：candidate05

2026-10-21。属于现有 `restore-alert-investigation-integrity` 的B2/B6正常结果修复，目标、范围及完成口径仍见[总计划](completion-plan.md)。旧[R01](integrity-investigation-r01.md)的内容质量失败保留，不重调或回填。

## 问题与实际修改

R01技术链及MD/HTML/PDF交付成立，但报告混用事件事实、模型假设、知识背景、查询失败和源发生时间。两个默认调查节点做最小材料投影修正：

- Forensic保留原模型响应审计，结构化影响范围分别呈现已提供告警中的观察范围、未经核实的模型判断及更大范围未知；不按关键词删除结论或预填期望分类。
- ReportWriter明确前序结论属于假设/判断，区分源事件、资料覆盖与处理过程。实际审计时间有时区偏移才标明确时区；naive时间保持时区未知，不补Z或借源事件时区。

只改 `investigator/forensic_agent.py` 与 `investigator/report_writer_agent.py`，不改prompt/lock、schema、编排或工具权限。它们不覆盖[B4 C2](integrity-autonomy-r01.md)另外发现的graph评分、ATT&CK映射、deep字段和cap结果问题。

## 验证与部署

24项断网直接测试通过（4项新增），日志SHA256 `07ab6c2ace78c5b1748f08c8481dadb2a0d45a7304754bee61d0949b330f9be1`；首轮23项及后续时区语义补充分别保留。未参与实现者 `api_auth_review` 审核源码、测试、真实预构建镜像及部署脚本通过。

固定[candidate05来源清单](../handoff/integrity-candidate05-source-manifest.json)以c311为父镜像，773个运行输入中771个保持；新镜像 `sha256:4ccf3a6d71695484a89b9f520484bfc2cfafee20a76a010442a69311ac7dba5a` 继承父层和运行配置，只增加两文件COPY，非root用户10001保持。清单为构建时冻结原件，部署状态另以运行回执记录。

B4两次有限消费退出且C2失败STOP封存后，仅Agents一次替换到新镜像，健康；原28层加同一integrity层仍为29层。API/Fusion/Actions及其余托管容器ID保持，全部环境值、七个只读挂载、60秒停止宽限、workerOFF/review_only及2048输出上限保持。远端完整773来源前后分别按candidate04/05核对，修改前源码和Compose留私有备份。当前Compose SHA256 `a2b7ac4ae38111156eacb3497a914ba6df754f43c7bad114278cd4479d8bb26b`。部署后[独立只读审计](../handoff/integrity-candidate05-runtime.json)通过：实际773运行来源及远端source匹配，父层/两COPY与全部运行配置保持，质量STOP仍在。

本批新增真实模型、消息和业务行写入均为0，未运行可用性矩阵。直接测试及运行来源核对证明投影修复已经交付，不证明未来模型报告质量，也不把旧R01或C2追认为通过。整体迁移仍未完成，继续最小修复自动调查实际阻塞。
