# W4独立测试服务包与21候选验证

2026-11-16。本步按[既定设计](../../../../openspec/changes/schedule-streaming-investigation-updates/w4-test-package-design-20261116.md)完成W4：独立包0.4.0可离开源码工作树运行，本机17次GET及21候选35次GET通过，重启后账本/证据保持。21候选于10:15（北京时间）正常停止，目录、镜像、容器及原证据保留。W5正式4177切换、完整change验收/独审与统一发布仍待，主31/41、流式2/11不变，未提交推送。

## 交付与实际身份

| 内容 | 实际结果 |
| --- | --- |
| 发布包 | `test-service-0.4.0-20261116-02`，56个登记文件及1份清单；[构建回执](build-02.json)、[逐文件清单](package-manifest-02.json) |
| 整包SHA256 | `844e37a6102d9d5d8db7067aacec42942ac26aa3aafbdb5b076afb28b5596f77` |
| 镜像 | `socai2-investigation-test:0.4.0-20261116-02`；实际ID `sha256:5590dbab1a7fe71988a984363d20c9d7378099267e7f2743d4830b9b216f5b77` |
| 21目录/容器 | `/opt/sting-aisoc-socai2/candidates/test-service-20261116-01`；`socai2-investigation-test-w4-20261116`，最终`exited/0` |
| 监听/上游 | 候选仅`127.0.0.1:18477`，容器内14178；调查上游显式`http://192.168.1.21:18424` |
| 合同 | 测试API 8个GET；调查OpenAPI 80操作/55 GET，实际上游读回与包内文件相同；[兼容清单](compatibility-02.json) |
| 持久数据 | 包外`state/ledger`，2批、15文件；原W2账本9文件保持；配置及状态均只读挂载 |

包包含测试API、页面、账本publish CLI、原S01/S04生成/校验与发送驱动、必要合同来源和配置示例；启动/重启不执行测试。构建使用21已有linux/amd64基础镜像，`--pull=false --network=none`，未安装新依赖。[部署入口](../../../../deploy/investigation-test/README.md)说明构建、运行配置、外置状态和升级/回退。发布包保存在本机忽略提交的`.local/investigation-test-release/`及上述21候选目录，Git证据不复制完整发布包。

## 直接验证

1. [10项本机检查](local-tests-01.log)通过：新包完整性与缺失/修改/额外文件拒绝、离开源码的生成/校验与发送CLI help，以及受影响的既有页面接线检查。离线S01为3告警/12上下文、S04为1/1，11份材料校验通过；没有实际发送Kafka或执行新调查。
2. [本机独立运行](local-validation.json)完成显式publish、17次HTTP读取和一次重启。新观察批次`w4-s04-readback-20261116-01`标明`saved_evidence`，引用[预算批次](../streaming-budget-20261116-01/README.md)已保存的新I、整事件Case第二轮及单案对照；不是新模型执行。原W2批次未变，新旧15文件在读取/重启后摘要一致。临时59477已停止。
3. 本机验证用包01；首次远端安装前将容器监听地址补入显式profile并冻结包02。[差异证明](package-revision-02.json)确认仅构建/候选profile变化，服务、页面、驱动和合同字节一致，复用已通过的本机读取。21实际使用最终包02，镜像内56文件校验通过，见[远端准备回执](prepare-remote-01.json)。
4. [21真实读取与重启回执](validate-remote-01.json)共35 GET，全200：17次调查代理、1次直接读取上游OpenAPI、其余17次测试API/页面资源。页面资源与包内字节一致；新I completed且选择4成员，整事件Case为4成员/2轮/current，单告警Case为1成员/1轮/stale。第二轮冻结的上一轮Run/Result链接正确，I/C6原答沿返回的content_url读取且摘要吻合，步骤和工件目录分页读全。
5. 两次启动/正常停止退出码均0，重启前后capabilities、新观察账本及质量证据一致，15文件摘要不变，配置摘要与挂载/命令匹配；原HTTP、Fusion及created状态的调度容器身份/镜像/状态未变。[实际请求及原文](remote/evidence/requests.json)、[服务日志](remote/evidence/service.log)、[回执收集核对](evidence-collection.json)保留35份响应原字节及43份取回文件的摘要。

## 未验边界

[本步验收](acceptance.json)及[结束检查](final-checks.json)已保存：OpenSpec strict、受影响Python的Ruff、定向diff检查和20条W4证据链接通过；当前打包来源文件与最终包清单摘要一致。这是W4直接验收，不是整个change独立结束审计。

本步0新模型调用、0业务写入、0直接数据库查询、0Kafka投递；调查HTTP自身正常读库。没有重新执行S01/S04、发送驱动实发或浏览器视觉联验；页面原交互证据沿W3复用。本步验证打包与实际HTTP接线，不扩大为完整业务/模型验收。

模型质量仍`NOT_PASSED`：原首轮10项引用问题、原3000/length失败以及预算续验的C3局部校验和C6引用问题均保留。整事件Case第二轮仍accepted/uncertain/partial，不能由读取成功推断正文正确。新观察账本两条质量记录分别指向C3与C6问题组，不等于只剩两个独立错误。

当前4177未切换，仓库静态查阅仍41卡。下一独立子步为W5实际展示入口接入与必要读回；整个change独立结束审计和正式发布条件仍按原方案办理。
