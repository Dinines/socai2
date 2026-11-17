# 3d Docker封装与入口交接

范围：统一设计§12.12及测试§9.13 DK01–07。镜像/依赖先独审通过，再做实际挂载与持久读回；保留3a–3c实现和全部旧原件。本批0新业务执行、0Kafka投递、0模型调用，不启动被测服务、不部署21。**最终交付为3d04；直接验收、操作交接及[限定结束独审](independent-runtime-review-01.json)均通过，仅关闭3d。**

## 使用入口与最终交付

[镜像与包索引](delivery-index.json) · [Docker操作说明](../../../../deploy/investigation-test/acceptance-docker.md) · [Compose](../../../../deploy/investigation-test/acceptance.compose.yml) · [运行配置](../../../../deploy/investigation-test/acceptance.env.example) · [连接文件示例](../../../../deploy/investigation-test/acceptance-config.example/)。操作者只需Docker/Compose、明确配置与材料及可写结果目录，无需宿主Python或源码挂载。默认帮助，查看不发送，显式run/append沿原门控。

- 最终包`test-service-0.6.0-20261117-3d04`，109文件。[归档/manifest回执](source-package-04.json)、[包清单](delivery-package-package-manifest.json)、[兼容信息](delivery-package-compatibility.json)、[Dockerfile](delivery-package-Dockerfile.acceptance)。源码包位于本机`.local/investigation-test-release/`，运行镜像已本机构建，未上传镜像仓库或部署21。
- 最终tag：`socai2-investigation-acceptance:20261117-3d04`；可运行不可变引用：`socai2-investigation-acceptance@sha256:6504fdad4ed0e965d16ee027302ddd0d666d2f13172ffa70108876dfd7bb5297`。平台image ID：`sha256:d43e94a27e7d1e313bc9283a64a56ca6caa98a3582d43014c149133bf02e553c`。两者用途分开，运行使用RepoDigest。[实际构建](image-build-04.json)、[镜像内核验](image-direct-04.json)。
- [最终源码冻结](runtime-freeze-02/manifest.json)含32文件。全部运行Python、Compose和依赖锁与完成全套挂载验证的03包逐字保持；[03→04差异](package03-to04-delta.json)仅7项文档/发布标识/生成元数据。独审发现的说明首段旧状态已修正，[原问题记录](documentation-correction-01.json)保留。01–03中间包/镜像及回执不覆盖。

## 第一步：镜像与运行依赖，已独立通过

[设计与固定配置](../../../../deploy/investigation-test/acceptance-image.json)采用Python3.11.17、固定基础摘要/实际平台ID、linux/amd64。Docker主机实际为arm64，验证为本机amd64运行，不称21原生实测。镜像默认UID/GID10001；无需宿主环境补驱动。

[依赖下载](dependency-download-01.json)及[19项wheel锁定](dependency-lock-01.json)记录实际版本/SHA。镜像构建按配置从公开PyPI取得固定依赖，pip --require-hashes/--only-binary；运行禁网，不能把0业务连接写成构建无网络。[初始包](source-package-01.json)、[镜像直接检查](image-direct-01.json)证明12模块导入（含6驱动）、RawAlert/OCSF身份入口、19版本、pip check、99文件SHA与默认帮助。原serve Dockerfile保持。

[第一步独审](independent-image-review-01.json)通过9项包检查、Ruff/strict与实际容器检查。测试3条旧断言位置误移已纠正，[开发失败](development-note-01.json)保留；独审首次裸platform ID启动失败后，改用核准RepoDigest通过，不是产品修复。第二步新增文件配置示例后[10项包检查](package-tests-03.json)、[Ruff](package-ruff-03.json)、[strict](openspec-03.json)通过；最终镜像也核全部109文件及19依赖。

## 第二步：挂载、实际命令与持久读回

[3d02直接验证](mounted-direct-01/validation.json)与[3d03完整复验](mounted-direct-02/validation.json)各有41条实际Docker/Compose命令及退出码；后一轮对应[显式配置](mounted-config-02.json)。[最终04必要读回](delivery-direct-01/validation.json)使用最终包的Compose及不可变镜像，复核默认帮助、02报告和新容器EOF退出。完整旧批没有重派。

| 已核路径 | 实际结果 |
| --- | --- |
| 同镜像换两包 | 旧streaming-v2的17条及模板v2的2条均convert→inspect→prepare；业务原值、计划、上下文关系与3a逐值一致，新身份保存读回。未创建runs或发送；仅挂profile/execution，不提供连接JSON/秘密 |
| 路径和只读 | 原材料/配置RO，结果RW，三个宿主目录不重叠。转换后重挂产物为RO材料并切换独立结果目录；冻结source_directory=/materials及配置路径。实际写入材料/配置被拒，非root UID501:GID20按显式配置可写持久结果，镜像默认10001另已验证 |
| 容器退出和重开 | 每条命令使用run --rm；首容器prepare/quit后另容器EOF查看，同execution/session/wire SHA保持。报告与console都写独立新目录；结束不永久关闭、不自动派发 |
| 完成02 | 2A/1I/2Case、9task/8attempt/8Run、83步骤245工件、4Result；13保存请求109995tokens。报告除观察时间外与3c.3 v03逐值一致，可见输入/输出及manifest宿主SHA核对通过 |
| 未完成01 | 原503、incomplete及needs_review保持；prepared没有快照，实际总量和usage保留null，不导入目录外快照补成功 |
| 原门控和问题 | 02/01 run及append均在原门控拒绝；菜单相同请求0执行。C6 9/C3 6/I 2共17诊断，步骤问题另16，原质量未全面通过，不因封装变为成功 |
| 输出保护 | status写prepared内部、report写材料内部、重复report目录、缺profile均明确失败，未覆盖输入或旧结果 |
| 原件保留 | 两类源材料11+5文件、历史02/01的2750+19文件、各新包config/converted/prepared摘要前后一致。只移除本轮CLI容器，没有删除镜像、数据或别的容器 |

[实际挂载](mounted-direct-02/actual-mounts.json)、[前摘要](mounted-direct-02/sources-before.json)、[后摘要](mounted-direct-02/sources-after.json)可核；模型报告入口为[02](mounted-direct-02/legacy02/output/report/report.md)及[01](mounted-direct-02/legacy01/output/report/report.md)。跨材料/结果挂载的历史原件沿report.json中的prepared相对来源路径与SHA定位，不把容器链接当宿主路径。新prepared/report在同一结果树时保留相对链接。

[测试模块第二步证据独立核对](independent-mounted-evidence-review-01.json)已通过，明确非最终结束结论；[最终04镜像限定结束独审](independent-runtime-review-01.json)已通过，32冻结文件、10项包检查/Ruff/strict、最终镜像12项必要命令及报告逐值/原答读回均核对，无未关闭发现。宿主回执脚本只为本批证据，不新增通用测试框架。回执路径解析错误在Docker调用前停止，[驱动说明](development-note-02.json)保留，未改变产品行为。

## 未覆盖与后续

本步没有实际连接PG/Kafka/湖/业务HTTP，不以驱动导入成功冒称目标可达。任务4才用Docker执行新小场景及显式追加并接工作台；21部署/恢复、新浏览器、自然4h/6h、D5/D6、模型质量、完整change结束审计及Git同步均未据3d验收。未提交推送、未归档。
