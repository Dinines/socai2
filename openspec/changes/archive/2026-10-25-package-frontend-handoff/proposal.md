# 前端页面交接包

## Why
用户要将整个目录交给前后端同事，通过 HTML 浏览当前 4173 静态原型，并对照页面功能、数据库字段和已有展示数据。

## What Changes
- 将当前前端源文件原样复制到独立交接目录，根 index.html 直接打开现有界面。
- 附 README、可浏览的功能/字段说明及现有数据的 JSON 与只读 SQL。
- 只整理已有前端和证据，不修改页面设计、后端、运行环境或重新查询服务。

## Capabilities
纯工具和文档交接，无产品行为变更，使用 skip_specs。

## Impact
新增 deliverables/aisoc-frontend-handoff、打包脚本与交接记录；保留现有工作区、原型及业务代码。
