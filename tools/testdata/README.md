# 有界合成告警工具

`alert_scenarios.py` 将固定上游的场景生成器输出转换成当前 `POST /api/v1/alert-ingress` 的**已有告警**合同。默认只生成本地文件，不发送网络请求。稳定 `run-id + tenant + scenario-id` 产生稳定 UUID；相同输入生成相同字节。`event-time` 必须显式含时区，数量为 1–20（默认 3），输出目录拒绝覆盖。

```sh
.local/conda-envs/socai2/bin/python tools/testdata/alert_scenarios.py generate \
  --run-id local-example-01 --tenant 11111111-1111-4111-8111-111111111111 \
  --event-time 2026-10-22T08:00:00+08:00 --count 3 --out .local/testdata/local-example-01
```

产物是 `manifest.json`、`payloads/001.json` 等单条请求以及单独的 `expected/001.json` 等期望答案。Manifest记录来源提交、数量、文件hash与告警ID。发送端只读取payload，不把 `expected_tactics`、`expected_techniques`、`response_class`、`evidence_keywords` 送入模型输入。host/user/IP只取telemetry明确字段，存在多值时不猜选。不会预置Case、Incident或MITRE期望标签，也不会修改Fusion。

场景标题、描述与telemetry仍是上游人工编写的合成叙述，含有攻击解释；**它们适合接线/材料传递验证，不能据此宣称盲测准确率、检测质量或攻击链质量通过**。上游expectations是模板期望，不是本系统实际结果，也没有提供TP/FP标签。没有实际采集、检测或厂商动作。

只有明确执行 `send` 才发送；凭据从指定环境变量读取，使用当前API的Bearer认证。应先设置指向本批受控租户的短期凭据，并使用隔离测试入口：

```sh
.local/conda-envs/socai2/bin/python tools/testdata/alert_scenarios.py send \
  --input-dir .local/testdata/local-example-01 \
  --url http://127.0.0.1:24930/api/v1/alert-ingress \
  --token-env SOCAI_TESTDATA_TOKEN --receipt .local/testdata/local-example-01-send.json
```

发送最多20条，每条只请求一次，禁止重定向、不自动重试。回执文件拒覆盖，以0600权限创建；请求开始前先落 `started_outcome_unknown`。网络错误、非202、缺少确认坐标或合同不一致就停止，保留未发送数量。202与Kafka坐标只记为 `accepted_not_processed`，不能代表Fusion处理、图写入、分诊或调查成功。中断/超时后也可能已受理，应检查原回执和原告警，勿用新回执盲目重发。

上游 `services/demo-producer/` 四文件整体原样迁入，生成器原件位于 `upstream/generate_eval_incidents.py`，MIT许可及所有原件SHA256见 `upstream/LICENSE`、`upstream/source-manifest.json`。原Go producer面向 `/v1/ingest` 的事件批，不兼容本项目已有告警入口；本轮保留原件，未运行其演示/负载模式。

离线工具检查（标准库，无业务包/模型/网络）：

```sh
.local/conda-envs/socai2/bin/python -m unittest discover -s tools/testdata/tests -v
```

实际验证与边界见[测试工具回执](../../docs/operations/testdata-tools-20261022.md)：2026-10-22的3条新隔离输入已通过真实入口/Kafka/Fusion/PG，未进入模型或调查；离线/替身结果单独列出。逐步恢复及原失败见[执行记录](../../docs/operations/two-projects-resume-20261022.md)。
