# 先看这里：x86_64 离线模型测试

交付版本r5（2026-10-28 x86_64重打包），目标为 **Linux x86_64 / amd64（64位 Intel/AMD）**。测试逻辑、提示词、案例及判据沿用原ARM64 r5；仅调整目标架构、帮助文字和交付说明。本文和另外两份说明在交付目录及容器`/app`内都有。

## 1. 包里有什么

| 内容 | 位置/说明 |
|---|---|
| 完整Docker镜像 | `image.tar`，包含基础镜像层，使用docker load离线导入 |
| 快速使用 | 本文`START_HERE.md`；容器`/app/START_HERE.md` |
| 完整命令、配置、案例 | [README.md](README.md)；容器`/app/README.md` |
| 看懂结果和错误 | [docs/RESULTS.md](docs/RESULTS.md)；容器同路径`/app/docs/RESULTS.md` |
| 加载/启动/测试脚本 | `load.sh`、`run.sh`、四个`test-*.sh` |
| 配置/校验 | `config.env.example`、`SHA256SUMS`、`image-inspect.json` |

**镜像内置Python 3.12、标准库及系统运行库、Bash、CA证书、测试代码、自测、提示词和合成案例。客户端没有第三方Python包依赖，运行时不需要pip/apt安装、下载模型或访问公网。** 不依赖宿主Python、Conda、Node、源码目录或其他业务组件。

本包不适用于32位x86（i386/i686）。宿主需可运行x86_64 Linux容器的Docker，以及解压/外层脚本所用的tar、Bash、SHA256校验等基本命令。已有vLLM-Ascend模型服务是被测对象，模型权重、驱动和CANN由该服务提供；测试容器无需NPU/GPU。必须能从测试容器访问内网模型接口，纯禁网模式只用于客户端自测。

## 2. 导入与配置

将整个`.tar.gz`文件带到隔离机器，解压后进入生成的目录：

```bash
tar -xzf model-preflight-x86_64-实际时间.tar.gz
cd model-preflight-x86_64-实际时间
./load.sh                         # 校验包内文件，再docker load；不会拉镜像
./run.sh selftest                 # 完全禁网，验证客户端自身
cp config.env.example config.env
vi config.env
```

先把`MODEL_BASE_URL`改为模型服务实际地址，例如`http://10.0.0.12:8000/v1`；按需填写`MODEL_API_KEY`。配置值不加外层引号、不写export。然后：

```bash
./run.sh models                   # 查看实际模型列表
vi config.env                    # MODEL_NAME填data[].id原值
```

镜像不含vi；上面的配置编辑发生在宿主机，也可用宿主其他文本编辑器。Linux包装脚本采用host网络，可访问宿主127.0.0.1或隔离网IP。

## 3. 对话与完整测试

```bash
./run.sh                         # 进入容器Bash，自动打印菜单
modelcheck chat                  # 对话；/reset清空上下文，/quit退出
modelcheck suite --pause         # 容器内完整测试，逐项回车继续
exit
```

也可直接在宿主运行，不先进入Bash：

```bash
./run.sh chat
./test-all.sh --pause            # 全部22项，固定按下面三组执行
./test-model.sh --pause          # 一、模型可用性6项
./test-tools.sh --pause          # 二、工具调用8项
./test-cases.sh --pause          # 三、业务案例8项
```

每项终端直接显示要求/参考、实际结果、检查及失败原因；不要求能看HTML或导出文件。默认输出摘要，`--full`显示全部可见内容，`--pause`每个项目后等待回车，非TTY不等待。默认配置下完整测试最多118次HTTP请求，可能较慢；Ctrl+C停止，不自动重发。

## 4. 在原机器回看

运行结束会打印结果目录。宿主`results/`映射为容器`/results`：

```bash
./run.sh show /results/实际结果目录 --pause
./run.sh show /results/实际结果目录 --case C01 --full
./run.sh compare /results/第一次目录 /results/第二次目录 --pause
```

上述回看不发模型请求。HTML位于宿主`results/实际结果目录/report.html`，可选打开。容器内可用`cat /app/docs/RESULTS.md`阅读错误解释。

## 5. 不使用包装脚本

镜像导入后，直接用Docker也可以启动；这条命令不要求宿主安装Python或携带测试源码：

```bash
mkdir -p results
docker run --rm -it --pull never --platform linux/amd64 --network host \
  --env-file config.env -v "$PWD/results:/results" \
  socai2-model-preflight:amd64-20261028-r5 bash
# 进入后：modelcheck chat 或 modelcheck suite --pause
```

若不用配置文件，将`--env-file config.env`替换成`-e MODEL_BASE_URL=实际地址 -e MODEL_NAME=实际ID`，有鉴权时再传`MODEL_API_KEY`即可。代码、文档和Python都从镜像读取，挂载目录只用于保存结果。
