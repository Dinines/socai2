# 本地Conda依赖统一检查与补齐

2026-10-22。用户要求先检查依赖并一次装齐，再继续Kafka写图联合验证。本轮只处理项目环境`/Users/lychee/Documents/project/socai2/.local/conda-envs/socai2`，Python 3.12.14；不修改旧socai环境、业务源码、服务pyproject/lock或21部署。

## 检查范围及实际安装

同时读取API与Agents的runtime、dev及必需extras，共56项唯一直接依赖。原环境缺21项、6项版本低于声明，`qdrant-client[fastembed]`缺fastembed。此前`pip check`通过只说明当时已安装包之间没有冲突，不能证明项目声明及extras齐全。补齐前后版本及检查结果均保留在`.local/aisoc21/dependency-check-20261022/`。

先统一解析完整依赖计划，再一批安装/调整90个Python包；包括LangGraph及checkpoint/sdk、LangChain、测试工具、OpenTelemetry instrumentation、数据库/图/消息客户端和其声明extras。未请求embedding模型或下载模型权重。通过Conda另安装37个包，含Pango/Cairo/XML动态库、字体及证书等；Python版本不变。WeasyPrint在API声明为必需，因此纳入环境，内存中的最小渲染仅验证动态库，不追加业务PDF报告验收。

API与Agents的独立镜像锁中有25个共享包版本不同。本地合用环境取直接锁版本并验证两边声明兼容，PyJWT采用API的2.15.1；其余传递项统一解析。导入检查另发现SQLAlchemyInstrumentor 0.66b0仅支持SQLAlchemy<2.1，初批锁版本2.1.4使追踪被跳过；仅在本地清单加2.0.52兼容覆盖（两服务声明均允许），保留初批结果，再定向调整并增加实际instrumentor启用检查。该环境不是任一部署锁的逐项复制，未修改锁文件来迁就本机。可复用的直接依赖清单为[local-api-agents-requirements.txt](../../deploy/aisoc21/local-api-agents-requirements.txt)，生成/检查入口为[check_local_dependencies.py](../../deploy/aisoc21/check_local_dependencies.py)。

安装后完整`pip check`发现克隆时带入的旧`SOCAI` editable项目`socai-fusion==0.1.0`仍要求`langgraph<0.7`，与当前Agents要求冲突。核其安装记录全部位于新环境后，只卸载新环境中的editable入口/元数据及脚本；旧`SOCAI`源码和原Conda环境保留。初次冲突输出及卸载日志保留，最终检查通过。

## 实际核验

- 56项直接声明：0缺包、0版本不符；已安装传递项及启用extras：0缺口。
- 最终`pip check`：`No broken requirements found.`。
- API/Agents离线检查分别33/32项：分别导入完整`app.main`、图路由/消费者/Bundle和所需第三方模块，另核API SQLAlchemy追踪实际启用；通过socket禁网保护，不启动应用lifespan或worker。全部通过，SQLAlchemy追踪实际启用检查通过。
- SQLAlchemy异步内存SQLite实际查询通过，验证greenlet/aiosqlite接缝；本地Pango/Cairo最小内存渲染和Conda激活动态库加载通过。
- 环境核心版本调整后复用既有直接合同：Agents四文件71 passed，API投影文件14 passed，共85项；不新增业务模型或组合验证。原弃用警告保留。

激活时已配置`DYLD_FALLBACK_LIBRARY_PATH`指向本环境`lib`，由Conda管理激活/退出的变量恢复。使用方式：

```bash
conda activate /Users/lychee/Documents/project/socai2/.local/conda-envs/socai2
python deploy/aisoc21/check_local_dependencies.py --report .local/dependency-check.json
```

需要从其他解释器环境调用时，可用`conda run --prefix /Users/lychee/Documents/project/socai2/.local/conda-envs/socai2 python ...`；直接运行绝对路径Python做native检查时需显式带上上述动态库路径。

## Kafka联合观察仍未完成

本轮依赖核验不代替[Kafka入口接线](kafka-graph-intake-20261022.md)的真实联合证明。依赖检查前，attempt1在沙箱连接预检被拒，无业务写；attempt2连接21后已留一条新合成PG Alert，但API因缺greenlet停在拒写检查，尚未创建测试topic或发布消息，本地子进程已停。attempt3的许可被用户中断，未执行。失败材料在`.local/aisoc21/kafka-graph-joint-20261022/`保留，不重写成通过。

本依赖步骤0模型、0新Kafka消息、0应用lifespan、0部署/常驻启用；旧Run/unknown/质量失败和change 5/15保持。完整包清单、安装与测试日志见本地证据目录，[机器回执](../handoff/local-dependencies-20261022.json)记录核验和独审范围；未参与实现者dependency_final_audit结束独审限定**ACCEPT，0剩余阻塞**，不扩大为业务全分支、Kafka联合或部署通过。

本地选定版本保存在`.local/versions/local-dependencies-20261022/`，16份检查源码/依赖输入/环境版本及直接日志的原件、副本、归档逐项一致；不是完整Conda环境、镜像或发布包。
