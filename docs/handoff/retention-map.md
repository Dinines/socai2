# 新项目知识保留清单

当前目标是[告警及后续数据处理服务端](../operations/alert-processing-scope.md)。保留资料用于复用和追溯，不等于其中所有上游模块都要迁入或启动；阶段与批次分别见[迁移路线](../operations/service-roadmap.md)、[依赖计划](../operations/dependency-migration-plan.md)。

## 已带入新目录

| 类别 | 新项目位置 | 保留理由 |
| --- | --- | --- |
| 需求原件 | `docs/requirements/AI SOC2.docx` | 当前唯一权威需求；按 hash 保留原字节 |
| 当前职责与执行 | 范围、服务端路线、依赖计划、根AGENTS/PROGRESS | 已有告警进入后的服务端处理，先依赖、逐批测试、冻结后二开；不续旧Basic |
| 模块知识 | `docs/reference/aisoc/`，M00—M21 | 业务链路、输入输出、状态、源码与测试位置 |
| 来源快照 | 同目录 `source-snapshot.json` | 上游 revision/199个引用文件 hash；不是运行验收 |
| 环境/实测/问题 | `docs/operations/` | 避免丢失20/43接线、已修缺陷和真实验证边界 |
| 部署适配 | `deploy/aisoc20/` | 可审查复用的 embedding helper、生成器、测试与override |
| 文件来源清单 | `docs/handoff/handoff-manifest.json` | 区分原字节复制、链接改写、新交接文件 |
| 需求 Markdown | `docs/requirements/ai-soc2-requirements*.md` | 全文阅读版与旧逐条覆盖对照，旧完成状态不继承 |
| 私有配置快照 | `.local/configuration/2026-10-20/`，Git忽略 | 用户后续要求保留真实模型/API/基础设施凭据，便于新项目使用 |

## 仍在旧工程/服务器保留

| 内容 | 位置 | 新项目的使用方式 |
| --- | --- | --- |
| 旧独立实现与测试 | `/Users/lychee/Documents/project/SOCAI/src`、tests、migrations | 日后按已测缺陷选取思想，不整体复制成移植前置 |
| 旧 OpenSpec/历史文档 | SOCAI/openspec、docs、告警处理分析 | 历史对照；任务勾选不代表新项目能力 |
| 调查原件 | SOCAI/.investigation-records，约2.7GB | 保持路径/hash/冻结事实；需要时定向引用/脱敏导出 |
| 大语料、模型 | SOCAI/knowledge、model | 用户已授权复用已有数据及旧知识/模型；已只读盘点，按[计划](../operations/knowledge-data-reuse-plan.md)选固定版本和20/21部署，不默认整目录复制 |
| 只读上游参考 | SOCAI/opensource/AiSOC | 固定revision的复制来源；只逐批迁入服务端范围内代码和直接依赖 |
| 运行密钥/管理员密码 | 20 `.env`、deployment/admin-credentials.json；21基础设施 `.env` | 原件保持；按用户后续要求已取回本地私有副本，索引见 [配置说明](../operations/configuration.md)，不入Git |
| 运行与embedding原件 | 20 `/home/lychee/beenuar/deployment` | 需要时定向取回受控证据，非全部复制 |
| 旧 Git 历史 | SOCAI/.git | 不移入新repo；旧工程继续保留 |

## 不继承为新项目默认的内容

不复制旧 AGENTS 长规则、旧 PROGRESS 数百KB历史、旧 pyproject/src/tests 的安装与接口假设、26个旧 change 任务树、旧21测试默认、旧模型上下文规模上限、未经当前验证的“已完成”标签。

本交接并没有删除上述资料。用户确认后，26个旧 change 已全部按历史封存：22个任务列表全勾选，4个共44项未完成保持；39份增量未同步主规格。原件/勾选不改，见 [封存摘要](legacy-change-closure.json)，完整原件与路径映射留在旧工程 `docs/project-archive/20261020/`。

21 是新项目部署目标；旧业务4容器已停止，基础设施及其他项目保持。20保留参考环境。不要把旧部署记录里的服务器职责直接当作新目标。

## 导入上游时保留

范围内服务源码及其真实构建输入：锁、构建文件、需要的规则/playbook、共享模块、数据库初始化、原测试、许可和来源revision。不能为缩小职责盲删共享文件，也不要求复制整仓全栈。README/AGENTS/docs/deploy重名先比较，原件另存并记录差异。

1A的90个依赖原件和13服务导出保留为当时参考快照，不是全部安装清单。早期全量路线及初始化过程保留在[历史目录](history/)，不作为当前任务或完成证明。
