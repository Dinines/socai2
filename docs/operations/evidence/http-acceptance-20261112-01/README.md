# HTTP 逐项验证

每项请求回执包含输入、完整输出和状态码；程序预期由对应测试断言核验。所有写入均为本机隔离库合成数据，模型为替身。正式库未写入。

| 接口 | 方法/路径 | 结果 | 本批直接回执 |
| --- | --- | --- | --- |
| E01 | POST `/api/v1/socai2/cases` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 24 项](final-case-readback-http.json) |
| E02 | GET `/api/v1/socai2/cases` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 44 项](initial-http.json) |
| E03 | GET `/api/v1/socai2/cases/{case_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 22 项](final-case-readback-http.json) |
| E04 | PATCH `/api/v1/socai2/cases/{case_id}/page-data` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 5 项](final-case-readback-http.json) |
| E05 | GET `/api/v1/socai2/cases/{case_id}/page-data` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 11 项](final-case-readback-http.json) |
| E06 | POST `/api/v1/socai2/cases/{case_id}/evidence-index` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 10 项](final-case-readback-http.json) |
| E07 | PUT `/api/v1/socai2/cases/{case_id}/members` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 21 项](final-case-readback-http.json) |
| E08 | POST `/api/v1/socai2/cases/{case_id}/associations` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 30 项](initial-http.json) |
| E09 | POST `/api/v1/socai2/cases/{case_id}/members/move` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 29 项](initial-http.json) |
| E10 | GET `/api/v1/socai2/cases/{case_id}/history` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 32 项](final-case-readback-http.json) |
| E11 | POST `/api/v1/socai2/cases/{case_id}/baseline/prepare` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 25 项](final-case-readback-http.json) |
| E12 | GET `/api/v1/socai2/cases/{case_id}/runs/{run_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 20 项](final-case-readback-http.json) |
| E13 | POST `/api/v1/socai2/cases/{case_id}/runs/{run_id}/start` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 33 项](final-case-readback-http.json) |
| E14 | GET `/api/v1/socai2/cases/{case_id}/results/{result_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 27 项](final-case-readback-http.json) |
| E15 | GET `/api/v1/socai2/cases/{case_id}/runs/{run_id}/artifacts/{artifact_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 29 项](final-case-readback-http.json) |
| E16 | GET `/api/v1/socai2/cases/{case_id}/artifacts/{artifact_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 12 项](final-case-readback-http.json) |
| E17 | GET `/api/v1/socai2/cases/{case_id}/activities` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 93 项](initial-http.json) |
| E18 | GET `/api/v1/socai2/cases/{case_id}/runs/{run_id}/materials/{material_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 30 项](final-case-readback-http.json) |
| E19 | POST `/api/v1/socai2/cases/{case_id}/ai/messages` | 未实现，501已确认 | [current-workflows-02-http.json 第 13 项](current-workflows-02-http.json) |
| E20 | POST `/api/v1/socai2/cases/{case_id}/ai/messages/{message_id}/save` | 未实现，501已确认 | [current-workflows-02-http.json 第 14 项](current-workflows-02-http.json) |
| E21 | POST `/api/v1/socai2/cases/{case_id}/results/{result_id}/adopt` | 未实现，501已确认 | [current-workflows-02-http.json 第 15 项](current-workflows-02-http.json) |
| E22 | GET `/api/v1/socai2/alerts/{alert_id}/analysis` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 73 项](initial-http.json) |
| E23 | GET `/api/v1/socai2/incidents/{incident_id}/analysis` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 79 项](initial-http.json) |
| E24 | GET `/api/v1/socai2/alerts/{alert_id}/analysis/runs/{run_id}` | 本机路由/真实隔离库直接验证通过 | [stage-readback-http.json 第 4 项](stage-readback-http.json) |
| E25 | GET `/api/v1/socai2/incidents/{incident_id}/analysis/runs/{run_id}` | 本机路由/真实隔离库直接验证通过 | [stage-readback-http.json 第 7 项](stage-readback-http.json) |
| E26 | GET `/api/v1/socai2/alerts` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 65 项](initial-http.json) |
| E27 | GET `/api/v1/socai2/incidents` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 66 项](initial-http.json) |
| E28 | GET `/api/v1/socai2/alerts/{alert_id}` | 本机路由/真实隔离库直接验证通过 | [page-recheck-http.json 第 4 项](page-recheck-http.json) |
| E29 | GET `/api/v1/socai2/incidents/{incident_id}` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 67 项](initial-http.json) |
| E30 | GET `/api/v1/socai2/{subject}/{identity}/records/{section}` | 本机路由/真实隔离库直接验证通过 | [assets-recheck-http.json 第 6 项](assets-recheck-http.json) |
| E31 | GET `/api/v1/socai2/alerts/{alert_id}/materials/{material_id}` | 本机路由/真实隔离库直接验证通过 | [page-recheck-http.json 第 2 项](page-recheck-http.json) |
| E32 | GET `/api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/trace` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 68 项](initial-http.json) |
| E33 | GET `/api/v1/socai2/{subject}/{identity}/analysis/runs/{run_id}/artifacts/{artifact_id}` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 70 项](initial-http.json) |
| E34 | GET `/api/v1/socai2/alerts/{identity}/artifacts/{artifact_id}` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 88 项](initial-http.json) |
| E35 | GET `/api/v1/socai2/incidents/{identity}/artifacts/{artifact_id}` | 本机路由/真实隔离库直接验证通过 | [initial-http.json 第 84 项](initial-http.json) |
| E36 | POST `/api/v1/socai2/alerts/{alert_id}/analyze` | 本机路由/真实隔离库直接验证通过 | [stage-readback-http.json 第 3 项](stage-readback-http.json) |
| E37 | POST `/api/v1/socai2/incidents/{incident_id}/diagnose` | 本机路由/真实隔离库直接验证通过 | [stage-readback-http.json 第 6 项](stage-readback-http.json) |
| E38 | POST `/api/v1/socai2/cases/{case_id}/tasks` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 13 项](final-case-readback-http.json) |
| E39 | GET `/api/v1/socai2/cases/{case_id}/tasks` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 19 项](final-case-readback-http.json) |
| E40 | PUT `/api/v1/socai2/cases/{case_id}/tasks/{task_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 15 项](final-case-readback-http.json) |
| E41 | GET `/api/v1/socai2/cases/{case_id}/tasks/{task_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 23 项](final-case-readback-http.json) |
| E42 | GET `/api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 17 项](final-case-readback-http.json) |
| E43 | GET `/api/v1/socai2/cases/{case_id}/tasks/{task_id}/revisions/{revision_id}` | 本机路由/真实隔离库直接验证通过 | [final-case-readback-http.json 第 18 项](final-case-readback-http.json) |
