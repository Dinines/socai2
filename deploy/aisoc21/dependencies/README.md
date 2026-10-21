# 21 依赖迁移包：1A

本目录是第一阶段的依赖快照，尚未安装或部署，不是完整应用。来源是用户指定的本地只读参考 `/Users/lychee/Documents/project/SOCAI/opensource/AiSOC`，固定 revision `34ca18c57dd4175539e5c6dd3d04a72dc057306b`。

用户随后限定[告警处理服务端范围](../../../docs/operations/alert-processing-scope.md)：不迁前端、采集/原始事件检测或独立Realtime。这里90个原件及13服务导出是既有参考快照，仍保留来源，不作为全量安装清单；Node/Go默认不属于当前前置工具。只为实际选用的服务构建依赖。

- `source/`：90个依赖声明、锁、Dockerfile及必要的上游辅助文件，原字节保留；许可在 `source/LICENSE`。目录内的Compose和Dockerfile用于核对依赖，其业务源码、SQL和挂载文件尚未齐备。
- `requirements/`：复用上游脚本，从13份服务锁分别导出的main/all版本清单。保留环境marker；每服务独立环境，不拼成全项目requirements。不含安装包、运行日志或私有密钥。
- [来源与hash](../../../docs/handoff/dependency-manifest.json)、[迁移计划](../../../docs/operations/dependency-migration-plan.md)、[环境盘点](../../../docs/operations/initialization.md)。

在仓库根执行：

```bash
python3 scripts/porting/dependencies.py --check --source /Users/lychee/Documents/project/SOCAI/opensource/AiSOC
python3 scripts/porting/dependencies.py --export
```

`--copy`用于首次按固定版本复制；目标文件有差异时拒绝覆盖，需先讨论变更。`--check`不依赖安装第三方库，要求Python 3.11及以上。导出的requirements用于环境盘点和后续测试环境的 `--no-deps` 安装；生产镜像仍按原Dockerfile由Poetry导出带hash的requirements，再使用 `pip --require-hashes`，不能把这些版本清单当作下载校验。

根 `.env.example` 仍是SOCAI2配置索引。1B已另行生成21 PG/Redis受控配置，见[回执](../../../docs/operations/1b-shared-services.md)；后续逐项映射AiSOC真实变量；不会直接加载20整份env。当前不要在本目录执行 `compose up` 或包安装，后续批次会准备完整的构建/启动输入。
