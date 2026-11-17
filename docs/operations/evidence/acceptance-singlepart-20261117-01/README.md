# 3b 首次预检查：未投递

2026-11-17。执行`acceptance-singlepart-20261117-01`在预检查读取业务HTTP时结束为`incomplete`。显式配置误用`127.0.0.1:18024`，实际服务只绑定`192.168.1.21:18024`；Fusion就绪地址仍为本机18003。回执为GET的`ConnectError`，没有POST、Kafka投递或模型调用。

- [原状态](runs/part1/state.json)及[失败HTTP](runs/part1/http/00001.json)保留，不覆盖、不重派。
- [准备身份](prepared/session.json)、[执行时源码](source-freeze-01.json)、[临时客户端](client-launch.json)保留。
- 修正连接后使用另一执行ID与输出目录，见[02实际流程](../acceptance-singlepart-20261117-02/README.md)。原生材料业务值保持；未清理任何旧数据。

本目录的准备文件不等于业务已执行。当前材料/命令说明见[验收脚本](../../../../tools/testdata/ACCEPTANCE.md)。
