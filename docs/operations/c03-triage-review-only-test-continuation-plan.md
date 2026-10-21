# C03-R01：单测试夹具修正后的独占继续

执行范围补充卡；root冻结本卡、单文件夹具fc444及wrapper独审后执行，当前未运行新测试/构建/部署。原R01范围9512和observer恢复卡c4df保持；runtime5、ledger测试、其余6直接测试、prompt/lock/SDK、Dockerfile/overlay及全部业务语义不变。

父prepare ae497和stage39c8已成功。首次离线191项为189pass/2fail，新22项中20pass/2fail，原6直接文件169pass。两个initial legacy drift分支被夹具预置的 prior-memory lookup AssertionError阻挡，尚未到SDK；不得把这轮写通过或算真实模型/业务失败。原123件证据（含最初13件observer失败）完整保留。

只将profile测试bf5a替换为fc444：在该legacy drift夹具使前置prior lookup返回None并精确核await，保留既有断言/调用/参数展开。独审f429、候选2764和root本地采用e578分别记录；不改变app来迎合测试。

新E为原observer恢复E/test-recovery-r03，新P为原P/test-recovery-r03。固定982纯stdlib base仅导入定义，不执行main或prepare/stage/finish。显式继承原before5fe0和四份原私有inspect/render/rollback原字节，仅记录路径/hash；不输出私密内容、不伪造新的prepare/stage。原P/test-results及失败记录不覆盖。

阶段仅stage-test→build→deploy→verify→finish。stage-test只改一个远端测试文件，再在全新test-results上同191项离线一次，cache017598/network none/source RO/空DSN/无真实凭据/≤300秒；真实191全过、新22及旧169均过才继续。失败保留，不自动重试。最多一次build、一次Agents recreate，只有image/profile差异，worker/effects保持原约束OFF，SIEM继承default on由profile禁止调用。

不重复PG/metrics前置基线。已用PG41（原observer及root诊断4+成功prepare37），剩余≤59；已用metrics before1，新after最多1，总2。Kafka仅metadata，无assign/poll/read/commit；0真实模型和0业务写入。初末及关键阶段精确核原123树（仅排除新子树），旧12预约/3unknown、十reader、14表、QA、134迁移、35其他容器/18卷及水位保持。

新pre/post独审同时绑定wrapper SHA、base982、parent binding668、继承prepare/stage/before/private继承清单hash、新测试实际结果及镜像/checkpoint，以及9512/c4df/本补充卡hash。自写finish只认可R01源码隔离/worker OFF指定部署；R02、原自治质量和整体迁移均false。旧prepare/test失败不追认通过，unknown不重发，回退由root另审。
