# Tasks

## 当前阶段：统一43操作的独立HTTP入口

- [x] 1.1 固定本轮范围、两套入口证据和配置方案，严格校验规格；明确不带入并行模型改动。
- [x] 1.2 实现显式同目标启动校验、A/I调查写连接与连接池释放；定向测试和旧合同不变检查。
- [x] 1.3 准备本机/21运行profile及限定文件发布包；凭据留受控文件，记录基础镜像与覆盖文件摘要。
- [x] 1.4 本机原应用真实TCP HTTP建案→H创建/修订→GET/SQL读回，核43操作/501与数据目标；复用已有模型替身证据。
- [x] 1.5 未参与实现者完成限定结束审计，修复阻塞后记录结论。
- [x] 1.6 一次发布21新独立正式服务，读回路由、版本、目标和Case/H结果；保留旧服务、旧库、消费者状态，无真实模型调用。
- [x] 1.7 同步Swagger、环境交接、PROGRESS和来源回执；记录实际通过与未通过范围，完成归档前检查。

## 历史阶段：2026-10-28

- [x] Inspect current runtime image, networks, mounts, model configuration presence and candidate port.
- [x] Add liveness/schema entry, caller and explicit deployment files.
- [x] Perform minimal local entry/caller verification and prepare a source-only upload bundle (475 files; no runtime environment).
- [x] Obtain authorization and start only the new loopback investigation container (`socai2-investigation-api`, image2fde05d5).
- [x] Record HTTP entry checks and caller limitations; leave current business containers intact (18 OpenAPI paths, liveness200, unauthenticated401, core/Agents ID and start time unchanged).

OpenSpec CLI unavailable; no strict CLI validation or archive is claimed. No deployment is authorized by this task file itself.

Evidence: `docs/investigation/resident-api-20261028.md`, `docs/operations/investigation-api-entry-local-20261028.json` and `docs/operations/investigation-api-resident-20261028.json`. Normal-user authenticated resident business HTTP remains unverified without an operator-supplied existing token; no users/permissions were created for the check.
