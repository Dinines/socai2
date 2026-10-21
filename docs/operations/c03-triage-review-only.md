# C03-R01：review_only_v1 代码隔离与 worker OFF 部署

本批限定通过。只验代码隔离、直接离线测试和指定的 Agents 部署；R02 常驻、真实 reader/PG/Kafka 新 profile 分支及原自治质量均未通过。

实际镜像 `sha256:19f8f1a52875b0a16c75890046eeec3fc308995cf73a5bc52899afa076958110`；测试末行统计 `{"passed": 191}`，JUnit 实际收集 191 项。新两文件确实执行并通过；不把预计22项当实际总数。

Agents185 / 运行770 Py，prompt/lock 与依赖保持；28 Compose / 25 来源层。0真实模型、0业务写入，worker仍OFF；只替换Agents一次，35其他容器、18卷、134迁移、十reader、旧12预约/240000预留单位/3unknown及旧消息水位保持。

新部署仅改变 Agents image/profile。选定禁用开关与 profile 内效果阻断分别核对；SIEM 继承默认 on 不等于显式 flag0。未重新调用模型/旧四SDK探针。

首轮 prepare 因本批 observer 的 SET ROLE/tenant GUC 观测错误停止，原13文件及勘误保留；随后prepare/stage成功，首次191项为189pass/2夹具fail。唯一profile夹具修正后，新的同191项实际全过。继续链继承before/prepare/stage，未重复PG或metrics前置基线；历史41次PG与新实际次数分列，总限100。旧失败均不追认通过。

- R01 only: isolation code, offline direct tests and the specified worker-OFF deployment; R02 real reader/PG/Kafka resident profile and original autonomous quality remain unaccepted.

- SIEM writeback inherits its on-by-default source setting unless the actual inherited env says otherwise; review-profile code blocks the call. Overlay adds only image/profile, never a third SIEM flag.

- A legacy-entry asynchronous profile-drift test may have a zero local governor counter despite observed Mock usage and a recorded budget-update double; no PG budget persistence was exercised. Earlier static-review settlement wording describes the intended code path, not actual PG acceptance. Zero governor is not zero usage/cost.

- InvestigationState serialization gains a nullable receipt field. Legacy simplified timelines can show effective needs_review plus numeric0 sentinel; confidence is unknown and0 is not a model estimate. Full raw/effective relation is in versioned bound receipts/artifacts.

- Old12 reservations/240000 reserved units/3unknown remain; reserved units are not observed usage. No R01 model or business input was sent.

- Actual before observation already found host/container policy bytes and device/inode equal. Stale A7 was a precaution, not an observed defect. After recreation is checked separately; neither observation qualifies live budget use.

- Original prepare failed before stage/test/build/deployment/model because this batch observer added SET ROLE aisoc without a tenant GUC under forced RLS. Root admin diagnosis confirmed12/240000/3; no budget/RLS/application repair was made. The original13 files and static-review correction remain frozen.

[结构回执](c03-triage-review-only.json)；[来源清单](../handoff/c03-triage-review-only-source-manifest.json)；[执行范围](c03-review-only-profile-plan.md)。旧 D2 失败及所有冻结回执不改写。
