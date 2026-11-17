# 首次离线检查说明

首次Ruff发现新路由import格式，已修正；首次pytest命令未设置PYTHONPATH，导致旧app导入失败（1失败/2通过），没有业务调用。补PYTHONPATH=services/api后3项HTTP边界检查通过。未改写旧失败或重派业务操作。

本机Swagger切换后立即首查，首个HTTP请求返回RemoteDisconnected（容器启动尚未完成）；原失败保留，未重新部署或重复业务写入。待服务启动后仅重读静态入口与文件。

21 Swagger切换后立即首查同样早于监听就绪，首个请求ConnectionRefused；随后只重读静态内容，不重复重启。两次就绪前失败均不计入成功回执。
