# C03-02D-01 父镜像来源措辞勘误

2026-10-21。在本批prepare完成、测试/构建/部署前补充；原执行卡与scope-before原件保留。本补充不扩大资源或行为范围。

执行卡末段“Dockerfile固定父完整digest”措辞不准确。实际Dockerfile使用父标签 `socai2-agents:triage-authorization-c03-20261021`；build算子在构建前同时检查常驻Agents和该父标签的完整image ID等于 `sha256:9ba6be09b682b451f6ce3b590c1e736e00b5baf1dcd13c00874781261ca8a3b3`，并使用 `--pull=false --network=none`。这是固定父标签和完整ID前置核验，不是Dockerfile的repository digest引用。

只读源码/lock、实际构建结果及部署镜像仍须逐hash核对，不能用标签名称替代运行来源。保留当前实现及已冻结检查点，不因本措辞勘误重跑prepare、模型或业务输入。最终回执引用本补充并按实际实现表述。
