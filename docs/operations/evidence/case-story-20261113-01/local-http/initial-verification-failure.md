# 首轮核验限制

全部30次HTTP及搜索/分页/源记录断言通过后，最后SQL快照比较失败。脚本误用select(ORM类)，映射保存了Python对象地址，原sql-before/after不是原始行证据。原文件和失败保留；修正为select(table.__table__)，只补一次原始SQL快照→故事GET→SQL快照及源值核对，不重建样本或重派模型。首次沙箱网络访问被阻止，未执行写入；随后受控本机seed执行成功。
