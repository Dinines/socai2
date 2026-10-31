# 规划校验记录

2026-10-31；业务源码基线 `5b9513860c566ea9c7f17917ddb71cc199a1988e`。本文件只记录本轮规划/静态检查，不是实施结束审阅或业务验证回执。

## 工具与范围

PATH 无 openspec 命令；已找到并使用仓库 `.local/windows-local/openspec.ps1` 包装器及本地 OpenSpec **1.13.0**。包装器关闭 telemetry，本轮未安装工具、改 PATH/npm globals 或发业务网络调用。

- `list`：已核活动 change，fix-case-followup-gaps 保持 4/5；旧 continue-isolated-investigation-v2 保持 3/5，旧 worker 保持 0/17。
- `list --specs` / `show alert-investigation-integrity --type spec`：已读当前唯一主规格的历史范围及 17 条 requirement。本次不修改主规格。
- `new change fix-investigation-audit-gaps`：已建立 spec-driven、created=2026-10-31。
- 新建 proposal/design/tasks 和 3 项 capability 规格；17 项实施/验证/交付任务全部未勾选。

## 初次严格校验

`validate fix-investigation-audit-gaps --strict --no-interactive` 返回 exit 0：`Change 'fix-investigation-audit-gaps' is valid`。

关联旧 change 首次校验返回 exit 1：`Tool messages distinguish empty success from unavailability` 缺至少一个 Scenario。已只补其现有空结果/不可用行为对应的 WHEN/THEN，保留旧实现、原失败和原任务状态；这不是新增业务功能或测试通过。

## 最终结果

| 检查 | 实际结果 |
| --- | --- |
| 新 change strict 复验 | exit 0，`Change 'fix-investigation-audit-gaps' is valid` |
| 关联追加修复 strict 复验 | 补 Scenario 后 exit 0，`Change 'fix-case-followup-gaps' is valid` |
| `status --change fix-investigation-audit-gaps` | 4/4 planning artifacts complete；仅表示 proposal/specs/design/tasks 齐全 |
| 新规格静态计数 | 3 项 capability、8 条 Requirement、17 个 Scenario；均是目标合同 |
| 新任务静态计数 | 17 个唯一编号，0 项勾选 |
| 文档文件链接 | 14 份相关 Markdown、410 个本地文件链接，目标均存在 |
| 审计基线文件 hash | 47 个实现/依赖文件和 11 个测试文件均保持原 hash |
| `git diff --check`（相关范围） | exit 0，无空白错误；Git 有原工作区 LF/CRLF 提示 |
| 业务源码/测试范围 diff | 无变化；未运行业务测试、模型/湖/厂商调用或部署 |

未执行 apply/archive，未同步主规格、提交、推送或合并。原本地修复 6 项及真实 r1 失败记录均保持各自范围，本次不新增业务通过项；此记录由规划作者完成，不冒称未参与实现者的结束审阅。
