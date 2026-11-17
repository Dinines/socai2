# W1最小测试账本与只读API回执

2026-11-15。**W1组件实现及直接验证通过。** 独立包提供本地显式发布、不可变revision、8个只读HTTP接口；复用已保存业务证据，没有重新执行调查。W2–W4、4177接线及21完整测试未实施，本步不等于整个change或业务52组用例通过。

## 实现与配置

- [独立包与启动说明](../../../../services/investigation_test/README.md)：DTO、文件Store、API及CLI，无业务包依赖。
- [配置示例](../../../../deploy/investigation-test/read-only.example.json)：显式目录、回环监听、分页、文档/证据/游标大小上限；默认示例14178，没有启动该常驻服务。
- [本步设计](../../../../openspec/changes/schedule-streaming-investigation-updates/w1-test-ledger-design-20261115.md)及原测试服务规格已先核并strict通过后实施；未改业务DTO、表或执行器。

发布入口要求expected_revision，单写锁下保存完整revision和证据，原子替换current指针；旧revision及结束批次不覆盖。GET和启动不创建账本或文件、不恢复任务。passed用例须有实际核对和证据，质量未评估、有问题、已评估无问题分别记录。业务身份只保存真实来源映射，空Run和多个Run均保留。

## 直接验证

[组件原输出](direct-01.txt)、[JUnit](direct-01.xml)、[命令及源码摘要](direct-01.json)：**16 passed**，覆盖revision/CAS/终态、双向引用/通过证据/质量约束、分页和修订变更409、8GET/过滤/空态/错误、原字节及缺失/篡改503、相对路径/符号链接拒绝、GET及重新构造应用无写入。测试为本地文件与ASGI，不接业务依赖；不累计首次开发运行数充当更多覆盖。

[TCP原始回执](tcp-01/result.json)、[驱动](validate_tcp.py)及[服务器日志](tcp-01/server.log)：首次实际绑定`127.0.0.1:56595`，共**34次带断言的GET**（32个200、预期404/422各1）及3次成功启动探测GET，日志合计37次HTTP响应。三次启动分别为空账本、发布后读取、停止后再启动；均已正常停止。没有操作现行4177或其他服务。

验证生成的显式运行配置为`.local/test-ledger-w1-20261115-01/runtime/tcp-01/service.json`，验证参数为同批`.local/test-ledger-w1-20261115-01/verification.json`；账本保留在其runtime目录内。本次使用本机回环端口，不是21候选服务。配置hash、受测源码前后hash、每个请求/响应、发布命令与退出码已保存。

实际发布3个独立archive账本，均revision=1、finished：

| 账本 | 来源与实际核对 |
| --- | --- |
| `w1-f5-archive` | 读取F5已结束result，保留A/I/Case各自原task/Run/Result映射；5份模拟模型回复、0真模型的事实保持，不重派原Run |
| `w1-admission-archive` | 读取原Case HTTP受理时点回执，真实task为accepted、Run为空；这是历史观察，不声称该任务当前仍在排队 |
| `w1-quality-fixture` | 明确synthetic_fixture，展示failed用例、unknown操作和deferred质量条目；是假定状态用于组件显示验证，不记为真实模型缺陷或业务失败 |

[发布输入](tcp-01/inputs/w1-f5-archive/document.json)、[无Run输入](tcp-01/inputs/w1-admission-archive/document.json)、[合成状态输入](tcp-01/inputs/w1-quality-fixture/document.json)与每份原始source副本保留。实际GET覆盖所有页面及证据原字节；测试JSON/质量数据不会反写调查库。

读取前与重启后全部账本文件hash相同，两个历史源文件hash相同，受测源码与配置前后一致。空启动没有创建ledger目录；所有GET、停止和再启动均未发布新revision。实际业务数据库连接、模型、Kafka投递为0；未清理任何旧批次。

## HTTP合同与后续边界

[本次实际OpenAPI](tcp-01/openapi.json)含8个`/test-api/v1` GET：capabilities、batches、batch详情、cases、operations、preparation、quality-issues、evidence。metadata与content沿登记ID读取；没有业务代理/执行写接口。更细字段与状态见独立包README及Schema。

Ruff和OpenSpec strict通过。下一步按已对齐[总计划5.4](../../../../openspec/changes/schedule-streaming-investigation-updates/full-flow-test-plan-20261115.md#54-f5之后的21完整测试准入与实际下一步)进入T2最小S01/S04材料/wire/expected及候选参数对齐，随后按实际供给接W2、W3、W4。本轮不预建这些模块、不生成或投放Kafka数据、不缩短正式配置、不开始21真实模型整链；21拟定资源尚未创建的只读证据不能当作运行profile。
