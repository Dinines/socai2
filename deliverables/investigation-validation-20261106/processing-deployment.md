# 21 调查处理作业 · 部署与交接

## 21 生产部署

21 通过 Docker Compose 运行告警同步服务和内部调查工作台。生产库为 PostgreSQL `aisoc`。Fusion 首先写入原告警表 `public.alerts`，独立的同步服务接收已落库的告警通知，按原租户、告警和事件 ID 将调查材料写入同库的 `socai2` 模式。告警分诊、事件诊断和 Case 调查均可由有权限的调用者显式启动。

| 使用方 | 负责的内容 |
| --- | --- |
| 处理模块 | 部署时初始化 V1 的 29 张表。运行时写告警材料、事件成员、研判结果、Case、每轮执行、步骤和工件。后续变更表结构须人工确认。 |
| 业务后端 | 按租户与主体 ID 查询页面所需字段，查询和关联键见[服务端字段交接](../../docs/investigation/socai2-page-data-handoff-20261106.md)。建表由处理模块部署统一完成。 |
| 4177 工作台 | 通过专用只读角色查询同库，默认展示最近更新的五个 Case。管理员可按 Case 保存最新一份查看文件。 |

在配置了 `sting-infra21` SSH 别名的仓库工作站执行。安装依赖 21 上已经部署的 R3 基础镜像、PostgreSQL、Kafka、内网模型网关和证书。

```sh
python deploy/aisoc21/deploy_production_services.py apply
python deploy/aisoc21/deploy_production_services.py verify
```

`apply` 核对数据库设计和原告警表指纹，发布调查模块、启动两个常驻容器，健康检查通过后切换按需作业入口。`verify` 可单独执行。首次启用时，新消费组 `socai2-investigation-projection-v1` 从各分区当时的末端开始。重复部署会核对已有位点，遇到位点丢失或过期会停止并提示检查。

21 上的生产作业入口为 `/opt/sting-aisoc-socai2/ops/processing-production.py`。使用 `python3 /opt/sting-aisoc-socai2/ops/processing-production.py check` 可核连接和权限。执行业务作业时，命令前缀为 `python3 /opt/sting-aisoc-socai2/ops/processing-production.py job --tenant <租户UUID> --actor <操作员UUID>`，随后使用下文的操作和参数。作业从终端隐藏提示或标准输入读取调用者自己的 API key。

2026-11-06 部署时，两个常驻容器健康，本机与 21 的 4177 均已连到生产库。默认租户的 Case 起始为空。部署只核对了服务连接、权限和 Kafka 位点。新告警的实际落库、从建案到调查结束的输入输出和模型回复留给业务验收。

| 部署回执 | 21 上的实测值 |
| --- | --- |
| 处理作业与同步服务版本 | `production-processing-4e6113567051022f` |
| 工作台版本 | `production-workbench-1333f52d0b20a20c` |
| 原有 6 张告警、事件表的定义与授权指纹 | 部署前后均为 `33dd8182c6830ddfe9b9960b6ffaa3215fc69013b4615081737ec6ccd361306e` |
| 新消费组启用和重复部署后的位置 | 分区 0 为 34，分区 1 为 37，分区 2 为 42。首次启动时修正了激活目录的写挂载和客户端分区参数，沿用第一次保存的三个起点。 |

## 独立交接样本环境

合成案例使用独立库 `socai2_processing_handoff` 和 `/opt/sting-aisoc-socai2/ops/processing.py`。以下命令及样本 ID 用于复查该环境。

### 在 21 上检查交接样本

```sh
python3 /opt/sting-aisoc-socai2/ops/processing.py job check
python3 /opt/sting-aisoc-socai2/ops/processing.py job self-test
python3 /opt/sting-aisoc-socai2/ops/processing.py smoke verify
```

- `job check` 核数据库、角色、租户及 Case 页面所需 ORM 字段，然后核内网模型目录存在配置的别名，并用 `LIMIT 0` 验证湖表 `raw_events` 的读取权限。业务写入、模型推理与湖日志读取均为 0。
- `job self-test` 在内存中用两条告警验证 C6 在缺少有效模型结论时生成系统收尾、部分交付与覆盖范围。
- `smoke verify` 在独立库回查下表的固定样本、创建/准备回执和单一待执行 Run。该检查要求 0 步骤、0 次模型、0 次工具、0 份 Result。若日后启动了该 Run，应按其新执行状态和回执验收；原有待执行断言届时不再适用。

固定版本入口为 `/opt/sting-aisoc-socai2/releases/processing-20261106-r3/processing_host.py`。将以上命令中的 `/opt/sting-aisoc-socai2/ops/processing.py` 换成此路径，即可按版本执行相同操作。

| 合成样本 | 21 独立库中的 UUID |
| --- | --- |
| 告警 | `751f5387-7169-5a74-9dfe-ec085cee60ac` |
| 事件 | `8f374d64-ab10-55fa-91bb-944c5e1f455d` |
| Case | `8fb39b43-ba50-563d-9686-023ee0f5ae6a` |
| 待执行 Run | `ced9da4c-818e-4a1b-8e65-c1ec192e6e58`（`pending_update`，范围版本 1） |

### 作业参数与交接库命令

下表各行均接在 `python3 /opt/sting-aisoc-socai2/ops/processing.py job` 后。`<…>` 为需替换的值。请用该租户中实际存在的主体 UUID。每次新操作先生成并保存自己的 UUID 作为 `--operation-key`，与主体、参数、回执一同登记。同一次操作核对同一键；遇到超时、状态未知、部分交付或范围冲突，先查原执行记录，禁止换键重派。

| 操作 | 参数模板 | 操作后核对 |
| --- | --- | --- |
| 告警分诊 | `alert --subject <告警UUID> --operation-key <分诊键>` | 回查该告警的执行状态及已发布分诊。 |
| 事件诊断 | `incident --subject <事件UUID> --operation-key <诊断键>` | 核本事件的成员、诊断尝试及已发布摘要。 |
| 建 Case | `case-create --title "<标题>" --alert-id <告警UUID> --incident-id <事件UUID> --operation-key <建案键>` | 两种成员参数至少提供一种，可重复传入。保存回执的 Case、范围版本及待执行 Run。 |
| 准备基础调查 | `case-prepare --subject <CaseUUID> --scope-revision <当前版本> --operation-key <准备键>` | 从回执核 `pending_run_id`。已有待执行 Run 时可返回其原 ID。 |
| 显式启动该 Run | `case-start --subject <CaseUUID> --run-id <待执行RunUUID> --scope-revision <当前版本> --operation-key <启动键>` | 单独启动才会执行基础调查。查回执的 `run_id/state/delivery_state/stop_reason/result_ids`。需要限制时间时同时传 `--window-start` 和 `--window-end`（含时区的 ISO 8601）；需要与既有结果比较时传 `--comparison-result-id <ResultUUID>`。 |

作业退出码 1 表示请求或处理报错，错误回执会带可用的主体和操作键。无效主体不返回推算的 Run ID。`case-start` 错误中的 `requested_run_id` 仅用于核对输入。退出码 2 表示回执状态为 `unknown`、`failed`、`cancelled`、`running` 或 `pending_update`，应结合主体及停止原因判断。退出码 0 仍须核对实际交付范围和结论来源。

### 独立交接库的验证记录

`r1` 在验收目录权限检查处失败，该次验收写入 0 条样本数据。`r2` 调整权限后完成合成告警、事件、建案和准备。当前 `r3` 修正启动服务返回字典时的回执解析，支持时间窗和比较结果参数，并修正无效主体的错误回执。正式包 `release.tar.gz` 的 SHA-256 为 `505beaeebd39d88bacbb69c85cd654f93bd2c605afe49168ba09f6eefe9f3b54`。[安装与复核记录](../../docs/operations/socai2-processing-install-20261106.json)

本次固定样本验证到“已建案、已准备、尚未执行”，加上内存中的 C6 兜底验证。此前四案才有 21 内网小模型的真实调用及已保存结果，适合前端验证成功、拒收、超时和未建案的显示。两组材料分开签收，模型全链语义质量仍待验证。[四案数据与逐字段样本](page-field-samples.md) · [前端功能清单](frontend-feature-list.md)
