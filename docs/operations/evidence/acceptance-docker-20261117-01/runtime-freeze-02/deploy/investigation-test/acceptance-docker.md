# Docker验收脚本

本入口封装已验的convert/inspect/prepare/run/append/status/report/session。运行需要Docker及Compose、明确的材料和配置、可写的宿主结果目录；无需宿主Python或源码挂载。镜像默认显示帮助。它连接已有业务服务，业务整链的实际验收见后续任务4。

## 镜像与配置

[acceptance-image.json](acceptance-image.json)固定基础引用、平台、Python、运行用户和依赖锁；[19项依赖锁](acceptance-requirements.lock)包含版本与wheel SHA。当前目标为linux/amd64，本机arm64通过amd64运行验证；21原生运行尚未验收。镜像构建从配置中的公开索引安装锁定依赖，运行默认禁网。

发布方先用现有build.py生成带manifest的独立源码包，再在包目录使用Dockerfile.acceptance构建；原Dockerfile仍是查阅服务。构建前按配置核基础平台ID，构建后保存目标RepoDigest、平台ID和包manifest SHA。构建示例（值均对应当前acceptance-image.json）：

```sh
docker build --pull=false --network=default --platform linux/amd64 \
  -f Dockerfile.acceptance -t socai2-investigation-acceptance:20261117-3d04 .
```

运行时优先使用回执中的不可变`仓库@sha256:...`引用；平台image ID用于核对，不直接把某些Docker版本返回的平台manifest ID当成可运行镜像名。完整镜像验证与ID见[3d回执](../../docs/operations/evidence/acceptance-docker-20261117-01/README.md)。

复制[acceptance.env.example](acceptance.env.example)为自己的`run.env`，明确填写以下项目；启动没有环境或路径回落：

| 配置 | 用途 |
| --- | --- |
| ACCEPTANCE_IMAGE / PLATFORM | 已核镜像tag或RepoDigest、平台；pull_policy=never，镜像须已存在 |
| ACCEPTANCE_USER | 非root UID:GID，须能读材料/配置并写结果；镜像默认10001:10001，宿主目录归其他用户时可显式配置该非root UID:GID |
| ACCEPTANCE_MATERIALS_DIR | 已存在的原材料目录，只读挂载；转换后改为转换产物目录再prepare |
| ACCEPTANCE_CONFIG_DIR | 已存在的受控配置目录，只读挂载，包含profile、执行身份及连接配置/凭据文件 |
| ACCEPTANCE_RESULTS_DIR | 预先创建的持久可写目录，保存转换产物、prepared、段回执或报告；与当前材料和配置宿主目录互不包含、不得重叠 |
| 三个TARGET | 稳定容器路径；示例为/materials、/run/acceptance-config、/results，同一execution后续保持一致 |
| ACCEPTANCE_NETWORK | 离线操作选择none；实际执行前由操作者明确填写可达目标的Docker网络，不把容器localhost当宿主或21 |
| CPU/MEMORY/PIDS/TMPFS | 此CLI容器的资源配置，与模型上下文、输出额度和业务任务并发配置分开 |

配置目录可从[acceptance-config.example](acceptance-config.example/)复制。`profile.json`的租户须与材料及http.json一致；连接文件和其引用的`secrets/*`均使用容器内路径。示例`.invalid`主机必须替换为实际地址；不提供或烘入真实凭据。Kafka TLS/SASL、数据库URL及湖密码按[文件说明](acceptance-config.example/secrets/README.md)提供，配置的UID必须可读。仅离线操作时不必提供连接JSON或凭据；只需要命令明确读取的profile/recipe/execution。

## 转换、准备与查看

以下命令从独立源码包根目录运行，`run.env`为上述显式配置；路径使用示例TARGET。普通离线调用加`-T`，交互会话保留终端。

```sh
docker compose --env-file /absolute/path/run.env \
  -f deploy/investigation-test/acceptance.compose.yml run --rm -T acceptance

docker compose --env-file /absolute/path/run.env \
  -f deploy/investigation-test/acceptance.compose.yml run --rm -T acceptance convert \
  --source /materials --recipe tools/testdata/acceptance-examples/streaming-conversion.json \
  --profile /run/acceptance-config/profile.json --output /results/converted
```

另一个旧模板包仅将recipe换为`tools/testdata/acceptance-examples/templates-conversion.json`，无需改镜像或执行源码。转换后，把刚生成的宿主`converted`目录设为新的MATERIALS_DIR，并将RESULTS_DIR改为**另一个独立目录**，避免只读材料从结果挂载的别名变为可写。随后检查、准备新执行：

```sh
docker compose --env-file /absolute/path/run.env \
  -f deploy/investigation-test/acceptance.compose.yml run --rm -T acceptance inspect \
  --materials /materials --profile /run/acceptance-config/profile.json \
  --report /results/inspection-01.json

docker compose --env-file /absolute/path/run.env \
  -f deploy/investigation-test/acceptance.compose.yml run --rm -T acceptance prepare \
  --materials /materials --profile /run/acceptance-config/profile.json \
  --execution /run/acceptance-config/execution.json --output /results/executions/run01

docker compose --env-file /absolute/path/run.env \
  -f deploy/investigation-test/acceptance.compose.yml run --rm -T acceptance status \
  --prepared /results/executions/run01 --report /results/status-01.json
```

execution.json明确新的execution_id。prepare冻结容器内source_directory、profile和全包wire，后续从同一持久prepared读取；修改外部profile不会改写已冻结profile。连接JSON在首次实际preflight保存摘要，追加会核对是否变更；变更目标应另准备执行。以上命令只处理文件，不发送。

## 显式执行与结束

```sh
docker compose --env-file /absolute/path/run.env \
  -f deploy/investigation-test/acceptance.compose.yml run --rm acceptance session \
  --prepared /results/executions/run01 --output /results/console-01
```

先查看计划和已存状态。`run part1`明确执行首段，`append part2`只追加当前候选；每次操作结束会重新等待选择。实际执行前须已配置业务网络及真实连接文件，仍由原执行器核目标、旧任务和身份，Docker封装不绕过门控。也可用同一Compose入口直接调用`run --prepared ... --part part1`或`append --prepared ... --part part2`。

`view`或空输入仅查看；`report`生成只读报告；`quit`/EOF退出查看；`finish`先生成报告再退出。Ctrl-C尽力留end观察，退出130，不表示远端已取消。容器退出并由`--rm`移除后，结果目录保持。用相同材料/配置/结果挂载、新output如`/results/console-02`重开，已执行段不会重派，未发段不变，未知操作不自动恢复。

独立报告命令：

```sh
docker compose --env-file /absolute/path/run.env \
  -f deploy/investigation-test/acceptance.compose.yml run --rm -T acceptance report \
  --prepared /results/executions/run01 --output /results/report-01
```

宿主结果目录中可直接打开report.md、report.json、models和manifest；JSON记录prepared相对来源路径及SHA。prepared和报告均位于同一结果树时，Markdown原件链接可在宿主继续定位。旧01/02可将原prepared作为只读MATERIALS_DIR挂入查看；其历史source_directory/连接路径不改写、不读取私密文件，跨挂载原件沿JSON来源和SHA定位，不把容器路径冒称宿主路径。

每次报告或console使用新目录，不写到原材料或prepared内部。0表示命令正常完成或正常退出，不代表模型正确/所有段执行；3表示已有报告但需核对执行或原件问题；2表示配置/材料/输出错误。错误及历史质量诊断保留。详细字段和流程见[验收CLI说明](../../tools/testdata/ACCEPTANCE.md)。
