/* Offline demonstration records. Never mixed into saved AiSOC objects. */
'use strict';
window.pageShowcaseData = {
  "version": 1,
  "fixture": true,
  "recorded": false,
  "fixtureSet": "incident-alert-20261031",
  "sourceEnvironment": "design-showcase",
  "sourceTenantId": "showcase-contoso",
  "incidents": [
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-incident-01",
      "title": "财务终端钓鱼附件与脚本外联",
      "description": "财务用户打开邮件附件后，同一终端先后出现脚本启动、凭据进程读取和外部连接告警。告警共享终端与账号，文件哈希贯穿附件和执行记录；事件用于呈现这些关联事实，联合研判及处置由关联 Case 承接。",
      "correlationReason": "关联依据：同一终端 FIN-LAPTOP-07、同一账号 lin.chen@contoso.com，12分钟窗口内连续出现邮件、进程与网络记录；附件和进程记录包含同一文件哈希。",
      "status": "In progress",
      "owner": "Alex Wilber",
      "severity": "高",
      "priority": 92,
      "classification": "Not set",
      "tags": [
        "联合核查"
      ],
      "first": "2026-10-31T01:10:00Z",
      "last": "2026-10-31T01:22:00.000Z",
      "updated": "2026-10-31T01:45:00.000Z",
      "entityIds": [
        "showcase-finance",
        "showcase-analyst",
        "showcase-mailbox",
        "showcase-attachment",
        "showcase-external"
      ],
      "critical": true
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-incident-02",
      "title": "服务账号跨主机访问与归档上传",
      "description": "报表服务账号先后访问跳板机、应用服务器与文件服务器，随后生成归档并向外部地址传输数据。现有记录可串联账号、主机和归档对象，但没有取得完整文件传输清单，尚不能确认外传内容或完整范围。",
      "correlationReason": "关联依据：svc.reports@contoso.com 在12分钟窗口中访问三台主机；文件服务器归档日志与上传进程记录共享 finance-export.zip 的哈希。",
      "status": "New",
      "owner": "未分配",
      "severity": "高",
      "priority": 78,
      "classification": "Not set",
      "tags": [
        "联合核查"
      ],
      "first": "2026-10-31T03:00:00Z",
      "last": "2026-10-31T03:12:00.000Z",
      "updated": "2026-10-31T03:35:00.000Z",
      "entityIds": [
        "showcase-service",
        "showcase-jump",
        "showcase-app",
        "showcase-share",
        "showcase-cloud",
        "showcase-archive",
        "showcase-upload",
        "showcase-cloudapp"
      ],
      "critical": false
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-incident-03",
      "title": "已核实的授权备份与维护活动",
      "description": "备份服务器上的脚本、文件归档与存储上传告警对应批准的维护工单 CHG-2026-1031。分析员核对操作账号、目标存储和维护窗口后，确认属于预期备份行为并手动解决事件。",
      "correlationReason": "关联依据：三条告警共享 BACKUP-SRV-01、backup.ops@contoso.com 和维护工单 CHG-2026-1031，均位于批准的备份时间窗内。",
      "status": "Resolved",
      "owner": "Patti Fernandez",
      "severity": "低",
      "priority": 24,
      "classification": "Informational",
      "tags": [
        "授权维护"
      ],
      "first": "2026-10-29T02:00:00Z",
      "last": "2026-10-29T02:08:00.000Z",
      "updated": "2026-10-29T02:35:00.000Z",
      "entityIds": [
        "showcase-backup",
        "showcase-operator",
        "showcase-automation",
        "showcase-repository",
        "showcase-internal"
      ],
      "critical": false,
      "resolutionNote": "已人工核对维护工单、执行身份、时间窗和传输清单，属于预期备份活动。"
    }
  ],
  "alerts": [
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-01-1",
      "title": "可疑邮件附件在财务终端被打开",
      "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。",
      "severity": "高",
      "source": "邮件安全网关",
      "category": "初始访问",
      "entityIds": [
        "showcase-finance",
        "showcase-analyst",
        "showcase-mailbox",
        "showcase-attachment"
      ],
      "incidentId": "showcase-incident-01",
      "caseId": "showcase-case-01",
      "status": "In progress",
      "owner": "Alex Wilber",
      "classification": "True positive",
      "disposition": "true_positive",
      "tags": [
        "重点核查"
      ],
      "event_time": "2026-10-31T01:10:00.000Z",
      "first": "2026-10-31T01:10:00.000Z",
      "last": "2026-10-31T01:11:00.000Z",
      "hostNames": [
        "FIN-LAPTOP-07"
      ],
      "tactics": [
        "初始访问"
      ],
      "iocKeys": [
        "file:46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af"
      ],
      "investigation": "Completed",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1566.001"
        ],
        "raw": {
          "id": "showcase-alert-01-1",
          "tenant_id": "showcase-contoso",
          "source": "邮件安全网关",
          "source_ref": "SEC-20261031-11",
          "event_time": "2026-10-31T01:10:00.000Z",
          "title": "可疑邮件附件在财务终端被打开",
          "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。",
          "severity": "高",
          "status": "In progress",
          "incident_id": "showcase-incident-01",
          "case_id": "showcase-case-01",
          "mitre_tactics": [
            "初始访问"
          ],
          "mitre_techniques": [
            "T1566.001"
          ],
          "rule_id": "RULE-11",
          "entities": [
            {
              "id": "showcase-finance",
              "type": "device",
              "name": "FIN-LAPTOP-07"
            },
            {
              "id": "showcase-analyst",
              "type": "user",
              "name": "lin.chen@contoso.com"
            },
            {
              "id": "showcase-mailbox",
              "type": "mailbox",
              "name": "lin.chen@contoso.com"
            },
            {
              "id": "showcase-attachment",
              "type": "file",
              "name": "quarterly-review.exe",
              "sha256": "46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af"
            }
          ],
          "raw_event": {
            "event_id": "evt-1-1",
            "hostname": "FIN-LAPTOP-07",
            "username": "lin.chen@contoso.com",
            "observation": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。",
            "approval_reference": null
          }
        },
        "confidence": {
          "score": 93
        },
        "risk": 96,
        "explanation": {
          "generatedAt": "2026-10-31T01:11:00.000Z",
          "summary": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。 请结合事件中的共享对象和时间线核查授权与影响。",
          "evidence": [
            "源记录 SEC-20261031-11",
            "规则 RULE-11",
            "对象 FIN-LAPTOP-07、lin.chen@contoso.com、lin.chen@contoso.com、quarterly-review.exe"
          ],
          "gaps": [
            "处置建议尚待人工审批"
          ],
          "suggestedActions": [
            {
              "title": "核对授权、进程和目标记录",
              "rationale": "检测命中需要结合上下文研判。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-31T01:10:00.000Z",
            "title": "告警发生",
            "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。"
          },
          {
            "time": "2026-10-31T01:10:15.000Z",
            "title": "告警被检测到",
            "description": "邮件安全网关 · RULE-11"
          },
          {
            "time": "2026-10-31T01:10:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-11"
          },
          {
            "time": "2026-10-31T01:11:00.000Z",
            "title": "告警关联到事件",
            "description": "财务终端钓鱼附件与脚本外联"
          },
          {
            "time": "2026-10-31T01:26:00.000Z",
            "title": "告警分配",
            "description": "负责人：Alex Wilber"
          },
          {
            "time": "2026-10-31T01:26:00.000Z",
            "title": "自动分诊完成",
            "description": "进入自动调查核查材料"
          },
          {
            "time": "2026-10-31T01:32:00.000Z",
            "title": "调查结果交付",
            "description": "本次材料已齐备，处置仍待人工审批"
          }
        ],
        "runs": [
          {
            "id": "showcase-run-01",
            "time": "2026-10-31T01:26:00.000Z",
            "status": "Completed",
            "completion": "completed",
            "stop": "",
            "findings": [
              "邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。",
              "输入范围的材料已齐备，处置尚待审批。"
            ],
            "actions": [
              "核对业务影响后隔离财务终端"
            ],
            "calls": null,
            "tokens": null,
            "report": "# 财务终端钓鱼附件与脚本外联\n\n## 输入范围\n告警 showcase-alert-01-1；关联事件 showcase-incident-01。其余成员记录仅作查询上下文。\n\n## 调查发现\n邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。\n\n输入范围的材料已齐备，处置尚待审批。\n\n## 查询依据\n- showcase-run-01-query-1：asset_activity，已取得记录\n- showcase-run-01-query-2：process_and_file_context，已取得记录\n\n## 完整性\n本次输入范围的材料完整，事件仍处理中。\n\n## 建议与执行\n核对业务影响后隔离财务终端\n未执行真实响应。\n",
            "steps": [
              {
                "name": "自动分诊",
                "agent": "自动分诊",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-01-1"
                },
                "output": {
                  "verdict": "true_positive",
                  "confidence": 0.96,
                  "auto_closed": false
                }
              },
              {
                "name": "调查工具",
                "agent": "调查工具",
                "status": "Completed",
                "input": {
                  "hostnames": [
                    "FIN-LAPTOP-07"
                  ],
                  "username": "lin.chen@contoso.com",
                  "start": "2026-10-31T01:10:00Z",
                  "end": "2026-10-31T01:26:00.000Z"
                },
                "output": {
                  "tool": "asset_activity",
                  "args": {
                    "hostnames": [
                      "FIN-LAPTOP-07"
                    ],
                    "username": "lin.chen@contoso.com",
                    "start": "2026-10-31T01:10:00Z",
                    "end": "2026-10-31T01:26:00.000Z"
                  },
                  "result": {
                    "records": [
                      {
                        "alert_id": "showcase-alert-01-1",
                        "time": "2026-10-31T01:10:00.000Z",
                        "hostnames": [
                          "FIN-LAPTOP-07"
                        ],
                        "username": "lin.chen@contoso.com",
                        "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。"
                      },
                      {
                        "alert_id": "showcase-alert-01-2",
                        "time": "2026-10-31T01:14:00.000Z",
                        "hostnames": [
                          "FIN-LAPTOP-07"
                        ],
                        "username": "lin.chen@contoso.com",
                        "description": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。"
                      },
                      {
                        "alert_id": "showcase-alert-01-3",
                        "time": "2026-10-31T01:18:00.000Z",
                        "hostnames": [
                          "FIN-LAPTOP-07"
                        ],
                        "username": "lin.chen@contoso.com",
                        "description": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。"
                      },
                      {
                        "alert_id": "showcase-alert-01-4",
                        "time": "2026-10-31T01:22:00.000Z",
                        "hostnames": [
                          "FIN-LAPTOP-07"
                        ],
                        "username": "lin.chen@contoso.com",
                        "description": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。"
                      }
                    ],
                    "scope": {
                      "hostnames": [
                        "FIN-LAPTOP-07"
                      ],
                      "username": "lin.chen@contoso.com",
                      "start": "2026-10-31T01:10:00Z",
                      "end": "2026-10-31T01:26:00.000Z"
                    }
                  }
                }
              },
              {
                "name": "调查工具",
                "agent": "调查工具",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-01-1",
                  "start": "2026-10-31T01:10:00Z",
                  "end": "2026-10-31T01:26:00.000Z"
                },
                "output": {
                  "tool": "process_and_file_context",
                  "args": {
                    "alert_id": "showcase-alert-01-1",
                    "start": "2026-10-31T01:10:00Z",
                    "end": "2026-10-31T01:26:00.000Z"
                  },
                  "result": {
                    "status": "success",
                    "parent_process": "WINWORD.EXE",
                    "process": "powershell.exe",
                    "sha256": "46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af",
                    "host": "FIN-LAPTOP-07"
                  }
                }
              },
              {
                "name": "侦察分析",
                "agent": "侦察分析",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-01-1"
                },
                "output": {
                  "summary": "按当前输入及可用证据交付",
                  "evidence_ids": [
                    "showcase-run-01-query-1",
                    "showcase-run-01-query-2"
                  ]
                }
              },
              {
                "name": "取证分析",
                "agent": "取证分析",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-01-1"
                },
                "output": {
                  "summary": "邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。；输入范围的材料已齐备，处置尚待审批。",
                  "evidence_ids": [
                    "showcase-run-01-query-1",
                    "showcase-run-01-query-2"
                  ]
                }
              },
              {
                "name": "响应分析",
                "agent": "响应分析",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-01-1"
                },
                "output": {
                  "summary": "按当前输入及可用证据交付",
                  "evidence_ids": [
                    "showcase-run-01-query-1",
                    "showcase-run-01-query-2"
                  ]
                }
              },
              {
                "name": "报告整理",
                "agent": "报告整理",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-01-1"
                },
                "output": {
                  "summary": "按当前输入及可用证据交付",
                  "evidence_ids": [
                    "showcase-run-01-query-1",
                    "showcase-run-01-query-2"
                  ]
                }
              }
            ],
            "tools": [
              {
                "id": "showcase-run-01-query-1",
                "name": "asset_activity",
                "args": {
                  "hostnames": [
                    "FIN-LAPTOP-07"
                  ],
                  "username": "lin.chen@contoso.com",
                  "start": "2026-10-31T01:10:00Z",
                  "end": "2026-10-31T01:26:00.000Z"
                },
                "resultFormat": "saved_result",
                "time": "2026-10-31T01:27:00.000Z",
                "success": true,
                "result": "{\n  \"records\": [\n    {\n      \"alert_id\": \"showcase-alert-01-1\",\n      \"time\": \"2026-10-31T01:10:00.000Z\",\n      \"hostnames\": [\n        \"FIN-LAPTOP-07\"\n      ],\n      \"username\": \"lin.chen@contoso.com\",\n      \"description\": \"邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-01-2\",\n      \"time\": \"2026-10-31T01:14:00.000Z\",\n      \"hostnames\": [\n        \"FIN-LAPTOP-07\"\n      ],\n      \"username\": \"lin.chen@contoso.com\",\n      \"description\": \"父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-01-3\",\n      \"time\": \"2026-10-31T01:18:00.000Z\",\n      \"hostnames\": [\n        \"FIN-LAPTOP-07\"\n      ],\n      \"username\": \"lin.chen@contoso.com\",\n      \"description\": \"终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-01-4\",\n      \"time\": \"2026-10-31T01:22:00.000Z\",\n      \"hostnames\": [\n        \"FIN-LAPTOP-07\"\n      ],\n      \"username\": \"lin.chen@contoso.com\",\n      \"description\": \"FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。\"\n    }\n  ],\n  \"scope\": {\n    \"hostnames\": [\n      \"FIN-LAPTOP-07\"\n    ],\n    \"username\": \"lin.chen@contoso.com\",\n    \"start\": \"2026-10-31T01:10:00Z\",\n    \"end\": \"2026-10-31T01:26:00.000Z\"\n  }\n}",
                "status": "已返回完整记录"
              },
              {
                "id": "showcase-run-01-query-2",
                "name": "process_and_file_context",
                "args": {
                  "alert_id": "showcase-alert-01-1",
                  "start": "2026-10-31T01:10:00Z",
                  "end": "2026-10-31T01:26:00.000Z"
                },
                "resultFormat": "saved_result",
                "time": "2026-10-31T01:28:00.000Z",
                "success": true,
                "result": "{\n  \"status\": \"success\",\n  \"parent_process\": \"WINWORD.EXE\",\n  \"process\": \"powershell.exe\",\n  \"sha256\": \"46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af\",\n  \"host\": \"FIN-LAPTOP-07\"\n}",
                "status": "已返回完整记录"
              }
            ]
          }
        ],
        "responseRecommendations": [
          {
            "action": "核对业务影响后隔离财务终端",
            "target": "FIN-LAPTOP-07",
            "reason": "相关终端记录已齐备，隔离需确认业务影响。",
            "approval": "待审核",
            "execution": "未执行"
          }
        ]
      }
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-01-2",
      "title": "文档进程启动隐藏脚本解释器",
      "description": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。",
      "severity": "高",
      "source": "终端检测与响应",
      "category": "执行",
      "entityIds": [
        "showcase-finance",
        "showcase-analyst",
        "showcase-attachment"
      ],
      "incidentId": "showcase-incident-01",
      "caseId": "showcase-case-01",
      "status": "New",
      "owner": "Alex Wilber",
      "classification": "Not set",
      "disposition": null,
      "tags": [
        "重点核查"
      ],
      "event_time": "2026-10-31T01:14:00.000Z",
      "first": "2026-10-31T01:14:00.000Z",
      "last": "2026-10-31T01:15:00.000Z",
      "hostNames": [
        "FIN-LAPTOP-07"
      ],
      "tactics": [
        "执行"
      ],
      "iocKeys": [
        "file:46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af"
      ],
      "investigation": "Not started",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1059.001"
        ],
        "raw": {
          "id": "showcase-alert-01-2",
          "tenant_id": "showcase-contoso",
          "source": "终端检测与响应",
          "source_ref": "SEC-20261031-12",
          "event_time": "2026-10-31T01:14:00.000Z",
          "title": "文档进程启动隐藏脚本解释器",
          "description": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。",
          "severity": "高",
          "status": "New",
          "incident_id": "showcase-incident-01",
          "case_id": "showcase-case-01",
          "mitre_tactics": [
            "执行"
          ],
          "mitre_techniques": [
            "T1059.001"
          ],
          "rule_id": "RULE-12",
          "entities": [
            {
              "id": "showcase-finance",
              "type": "device",
              "name": "FIN-LAPTOP-07"
            },
            {
              "id": "showcase-analyst",
              "type": "user",
              "name": "lin.chen@contoso.com"
            },
            {
              "id": "showcase-attachment",
              "type": "file",
              "name": "quarterly-review.exe",
              "sha256": "46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af"
            }
          ],
          "raw_event": {
            "event_id": "evt-1-2",
            "hostname": "FIN-LAPTOP-07",
            "username": "lin.chen@contoso.com",
            "observation": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。",
            "approval_reference": null
          }
        },
        "confidence": {
          "score": 90
        },
        "risk": 92,
        "explanation": {
          "generatedAt": "2026-10-31T01:15:00.000Z",
          "summary": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。 请结合事件中的共享对象和时间线核查授权与影响。",
          "evidence": [
            "源记录 SEC-20261031-12",
            "规则 RULE-12",
            "对象 FIN-LAPTOP-07、lin.chen@contoso.com、quarterly-review.exe"
          ],
          "gaps": [
            "处置建议尚待人工审批"
          ],
          "suggestedActions": [
            {
              "title": "核对授权、进程和目标记录",
              "rationale": "检测命中需要结合上下文研判。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-31T01:14:00.000Z",
            "title": "告警发生",
            "description": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。"
          },
          {
            "time": "2026-10-31T01:14:15.000Z",
            "title": "告警被检测到",
            "description": "终端检测与响应 · RULE-12"
          },
          {
            "time": "2026-10-31T01:14:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-12"
          },
          {
            "time": "2026-10-31T01:15:00.000Z",
            "title": "告警关联到事件",
            "description": "财务终端钓鱼附件与脚本外联"
          },
          {
            "time": "2026-10-31T01:26:00.000Z",
            "title": "告警分配",
            "description": "负责人：Alex Wilber"
          }
        ],
        "runs": [],
        "responseRecommendations": []
      }
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-01-3",
      "title": "同一终端出现凭据进程读取",
      "description": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。",
      "severity": "高",
      "source": "终端检测与响应",
      "category": "凭据访问",
      "entityIds": [
        "showcase-finance",
        "showcase-analyst"
      ],
      "incidentId": "showcase-incident-01",
      "caseId": "showcase-case-01",
      "status": "New",
      "owner": "Alex Wilber",
      "classification": "Not set",
      "disposition": null,
      "tags": [
        "重点核查"
      ],
      "event_time": "2026-10-31T01:18:00.000Z",
      "first": "2026-10-31T01:18:00.000Z",
      "last": "2026-10-31T01:19:00.000Z",
      "hostNames": [
        "FIN-LAPTOP-07"
      ],
      "tactics": [
        "凭据访问"
      ],
      "iocKeys": [],
      "investigation": "Not started",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1003.001"
        ],
        "raw": {
          "id": "showcase-alert-01-3",
          "tenant_id": "showcase-contoso",
          "source": "终端检测与响应",
          "source_ref": "SEC-20261031-13",
          "event_time": "2026-10-31T01:18:00.000Z",
          "title": "同一终端出现凭据进程读取",
          "description": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。",
          "severity": "高",
          "status": "New",
          "incident_id": "showcase-incident-01",
          "case_id": "showcase-case-01",
          "mitre_tactics": [
            "凭据访问"
          ],
          "mitre_techniques": [
            "T1003.001"
          ],
          "rule_id": "RULE-13",
          "entities": [
            {
              "id": "showcase-finance",
              "type": "device",
              "name": "FIN-LAPTOP-07"
            },
            {
              "id": "showcase-analyst",
              "type": "user",
              "name": "lin.chen@contoso.com"
            }
          ],
          "raw_event": {
            "event_id": "evt-1-3",
            "hostname": "FIN-LAPTOP-07",
            "username": "lin.chen@contoso.com",
            "observation": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。",
            "approval_reference": null
          }
        },
        "confidence": {
          "score": 87
        },
        "risk": 88,
        "explanation": {
          "generatedAt": "2026-10-31T01:19:00.000Z",
          "summary": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。 请结合事件中的共享对象和时间线核查授权与影响。",
          "evidence": [
            "源记录 SEC-20261031-13",
            "规则 RULE-13",
            "对象 FIN-LAPTOP-07、lin.chen@contoso.com"
          ],
          "gaps": [
            "处置建议尚待人工审批"
          ],
          "suggestedActions": [
            {
              "title": "核对授权、进程和目标记录",
              "rationale": "检测命中需要结合上下文研判。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-31T01:18:00.000Z",
            "title": "告警发生",
            "description": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。"
          },
          {
            "time": "2026-10-31T01:18:15.000Z",
            "title": "告警被检测到",
            "description": "终端检测与响应 · RULE-13"
          },
          {
            "time": "2026-10-31T01:18:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-13"
          },
          {
            "time": "2026-10-31T01:19:00.000Z",
            "title": "告警关联到事件",
            "description": "财务终端钓鱼附件与脚本外联"
          },
          {
            "time": "2026-10-31T01:26:00.000Z",
            "title": "告警分配",
            "description": "负责人：Alex Wilber"
          }
        ],
        "runs": [],
        "responseRecommendations": []
      }
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-01-4",
      "title": "脚本执行后连接外部 HTTPS 地址",
      "description": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。",
      "severity": "中",
      "source": "网络流量检测",
      "category": "命令与控制",
      "entityIds": [
        "showcase-finance",
        "showcase-analyst",
        "showcase-external"
      ],
      "incidentId": "showcase-incident-01",
      "caseId": "showcase-case-01",
      "status": "New",
      "owner": "Alex Wilber",
      "classification": "Not set",
      "disposition": null,
      "tags": [
        "重点核查"
      ],
      "event_time": "2026-10-31T01:22:00.000Z",
      "first": "2026-10-31T01:22:00.000Z",
      "last": "2026-10-31T01:23:00.000Z",
      "hostNames": [
        "FIN-LAPTOP-07"
      ],
      "tactics": [
        "命令与控制"
      ],
      "iocKeys": [
        "ip:203.0.113.77"
      ],
      "investigation": "Not started",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1071.001"
        ],
        "raw": {
          "id": "showcase-alert-01-4",
          "tenant_id": "showcase-contoso",
          "source": "网络流量检测",
          "source_ref": "SEC-20261031-14",
          "event_time": "2026-10-31T01:22:00.000Z",
          "title": "脚本执行后连接外部 HTTPS 地址",
          "description": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。",
          "severity": "中",
          "status": "New",
          "incident_id": "showcase-incident-01",
          "case_id": "showcase-case-01",
          "mitre_tactics": [
            "命令与控制"
          ],
          "mitre_techniques": [
            "T1071.001"
          ],
          "rule_id": "RULE-14",
          "entities": [
            {
              "id": "showcase-finance",
              "type": "device",
              "name": "FIN-LAPTOP-07"
            },
            {
              "id": "showcase-analyst",
              "type": "user",
              "name": "lin.chen@contoso.com"
            },
            {
              "id": "showcase-external",
              "type": "ip",
              "name": "203.0.113.77"
            }
          ],
          "raw_event": {
            "event_id": "evt-1-4",
            "hostname": "FIN-LAPTOP-07",
            "username": "lin.chen@contoso.com",
            "observation": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。",
            "approval_reference": null
          }
        },
        "confidence": {
          "score": 84
        },
        "risk": 84,
        "explanation": {
          "generatedAt": "2026-10-31T01:23:00.000Z",
          "summary": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。 请结合事件中的共享对象和时间线核查授权与影响。",
          "evidence": [
            "源记录 SEC-20261031-14",
            "规则 RULE-14",
            "对象 FIN-LAPTOP-07、lin.chen@contoso.com、203.0.113.77"
          ],
          "gaps": [
            "处置建议尚待人工审批"
          ],
          "suggestedActions": [
            {
              "title": "核对授权、进程和目标记录",
              "rationale": "检测命中需要结合上下文研判。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-31T01:22:00.000Z",
            "title": "告警发生",
            "description": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。"
          },
          {
            "time": "2026-10-31T01:22:15.000Z",
            "title": "告警被检测到",
            "description": "网络流量检测 · RULE-14"
          },
          {
            "time": "2026-10-31T01:22:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-14"
          },
          {
            "time": "2026-10-31T01:23:00.000Z",
            "title": "告警关联到事件",
            "description": "财务终端钓鱼附件与脚本外联"
          },
          {
            "time": "2026-10-31T01:26:00.000Z",
            "title": "告警分配",
            "description": "负责人：Alex Wilber"
          }
        ],
        "runs": [],
        "responseRecommendations": []
      }
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-02-1",
      "title": "服务账号从跳板机访问应用服务器",
      "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。",
      "severity": "中",
      "source": "身份与目录检测",
      "category": "横向移动",
      "entityIds": [
        "showcase-service",
        "showcase-jump",
        "showcase-app"
      ],
      "incidentId": "showcase-incident-02",
      "caseId": null,
      "status": "New",
      "owner": "未分配",
      "classification": "Not set",
      "disposition": "escalate",
      "tags": [
        "重点核查"
      ],
      "event_time": "2026-10-31T03:00:00.000Z",
      "first": "2026-10-31T03:00:00.000Z",
      "last": "2026-10-31T03:01:00.000Z",
      "hostNames": [
        "OPS-JUMP-01",
        "APP-SRV-02"
      ],
      "tactics": [
        "横向移动"
      ],
      "iocKeys": [],
      "investigation": "Completed",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1021.002"
        ],
        "raw": {
          "id": "showcase-alert-02-1",
          "tenant_id": "showcase-contoso",
          "source": "身份与目录检测",
          "source_ref": "SEC-20261031-21",
          "event_time": "2026-10-31T03:00:00.000Z",
          "title": "服务账号从跳板机访问应用服务器",
          "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。",
          "severity": "中",
          "status": "New",
          "incident_id": "showcase-incident-02",
          "case_id": null,
          "mitre_tactics": [
            "横向移动"
          ],
          "mitre_techniques": [
            "T1021.002"
          ],
          "rule_id": "RULE-21",
          "entities": [
            {
              "id": "showcase-service",
              "type": "user",
              "name": "svc.reports@contoso.com"
            },
            {
              "id": "showcase-jump",
              "type": "device",
              "name": "OPS-JUMP-01"
            },
            {
              "id": "showcase-app",
              "type": "device",
              "name": "APP-SRV-02"
            }
          ],
          "raw_event": {
            "event_id": "evt-2-1",
            "hostname": "OPS-JUMP-01",
            "username": "svc.reports@contoso.com",
            "observation": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。",
            "approval_reference": null
          }
        },
        "confidence": {
          "score": 93
        },
        "risk": 72,
        "explanation": {
          "generatedAt": "2026-10-31T03:01:00.000Z",
          "summary": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。 请结合事件中的共享对象和时间线核查授权与影响。",
          "evidence": [
            "源记录 SEC-20261031-21",
            "规则 RULE-21",
            "对象 svc.reports@contoso.com、OPS-JUMP-01、APP-SRV-02"
          ],
          "gaps": [
            "文件传输清单不完整，需补查范围"
          ],
          "suggestedActions": [
            {
              "title": "核对授权、进程和目标记录",
              "rationale": "检测命中需要结合上下文研判。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-31T03:00:00.000Z",
            "title": "告警发生",
            "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。"
          },
          {
            "time": "2026-10-31T03:00:15.000Z",
            "title": "告警被检测到",
            "description": "身份与目录检测 · RULE-21"
          },
          {
            "time": "2026-10-31T03:00:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-21"
          },
          {
            "time": "2026-10-31T03:01:00.000Z",
            "title": "告警关联到事件",
            "description": "服务账号跨主机访问与归档上传"
          },
          {
            "time": "2026-10-31T03:16:00.000Z",
            "title": "自动分诊完成",
            "description": "进入自动调查核查材料"
          },
          {
            "time": "2026-10-31T03:22:00.000Z",
            "title": "调查结果交付",
            "description": "部分交付：文件传输清单不可用"
          }
        ],
        "runs": [
          {
            "id": "showcase-run-02",
            "time": "2026-10-31T03:16:00.000Z",
            "status": "Completed",
            "completion": "partial",
            "stop": "文件传输清单不可用，保留部分结果供人工接手。",
            "findings": [
              "已确认同一服务账号跨主机访问和归档操作。",
              "缺少完整传输清单，不能确认外传内容及范围。"
            ],
            "actions": [
              "补查文件传输清单并核对授权"
            ],
            "calls": null,
            "tokens": null,
            "report": "# 服务账号跨主机访问与归档上传\n\n## 输入范围\n告警 showcase-alert-02-1；关联事件 showcase-incident-02。其余成员记录仅作查询上下文。\n\n## 调查发现\n已确认同一服务账号跨主机访问和归档操作。\n\n缺少完整传输清单，不能确认外传内容及范围。\n\n## 查询依据\n- showcase-run-02-query-1：asset_activity，已取得记录\n- showcase-run-02-query-2：transfer_inventory，资料不可用\n\n## 完整性\n部分交付，缺少文件传输清单。\n\n## 建议与执行\n补查文件传输清单并核对授权\n未执行真实响应。\n",
            "steps": [
              {
                "name": "自动分诊",
                "agent": "自动分诊",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-02-1"
                },
                "output": {
                  "verdict": "needs_review",
                  "confidence": 0.72,
                  "auto_closed": false
                }
              },
              {
                "name": "调查工具",
                "agent": "调查工具",
                "status": "Completed",
                "input": {
                  "hostnames": [
                    "OPS-JUMP-01",
                    "APP-SRV-02",
                    "FILE-SRV-03"
                  ],
                  "username": "svc.reports@contoso.com",
                  "start": "2026-10-31T03:00:00Z",
                  "end": "2026-10-31T03:16:00.000Z"
                },
                "output": {
                  "tool": "asset_activity",
                  "args": {
                    "hostnames": [
                      "OPS-JUMP-01",
                      "APP-SRV-02",
                      "FILE-SRV-03"
                    ],
                    "username": "svc.reports@contoso.com",
                    "start": "2026-10-31T03:00:00Z",
                    "end": "2026-10-31T03:16:00.000Z"
                  },
                  "result": {
                    "records": [
                      {
                        "alert_id": "showcase-alert-02-1",
                        "time": "2026-10-31T03:00:00.000Z",
                        "hostnames": [
                          "OPS-JUMP-01",
                          "APP-SRV-02"
                        ],
                        "username": "svc.reports@contoso.com",
                        "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。"
                      },
                      {
                        "alert_id": "showcase-alert-02-2",
                        "time": "2026-10-31T03:04:00.000Z",
                        "hostnames": [
                          "APP-SRV-02",
                          "FILE-SRV-03"
                        ],
                        "username": "svc.reports@contoso.com",
                        "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。"
                      },
                      {
                        "alert_id": "showcase-alert-02-3",
                        "time": "2026-10-31T03:08:00.000Z",
                        "hostnames": [
                          "FILE-SRV-03"
                        ],
                        "username": "svc.reports@contoso.com",
                        "description": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。"
                      },
                      {
                        "alert_id": "showcase-alert-02-4",
                        "time": "2026-10-31T03:12:00.000Z",
                        "hostnames": [
                          "FILE-SRV-03"
                        ],
                        "username": "svc.reports@contoso.com",
                        "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。"
                      }
                    ],
                    "scope": {
                      "hostnames": [
                        "OPS-JUMP-01",
                        "APP-SRV-02",
                        "FILE-SRV-03"
                      ],
                      "username": "svc.reports@contoso.com",
                      "start": "2026-10-31T03:00:00Z",
                      "end": "2026-10-31T03:16:00.000Z"
                    }
                  }
                }
              },
              {
                "name": "调查工具",
                "agent": "调查工具",
                "status": "Failed",
                "input": {
                  "alert_id": "showcase-alert-02-1",
                  "start": "2026-10-31T03:00:00Z",
                  "end": "2026-10-31T03:16:00.000Z"
                },
                "output": {
                  "tool": "transfer_inventory",
                  "args": {
                    "alert_id": "showcase-alert-02-1",
                    "start": "2026-10-31T03:00:00Z",
                    "end": "2026-10-31T03:16:00.000Z"
                  },
                  "result": {
                    "status": "unavailable",
                    "reason": "未取得完整文件传输清单"
                  }
                }
              },
              {
                "name": "侦察分析",
                "agent": "侦察分析",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-02-1"
                },
                "output": {
                  "summary": "按当前输入及可用证据交付",
                  "evidence_ids": [
                    "showcase-run-02-query-1",
                    "showcase-run-02-query-2"
                  ]
                }
              },
              {
                "name": "取证分析",
                "agent": "取证分析",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-02-1"
                },
                "output": {
                  "summary": "已确认同一服务账号跨主机访问和归档操作。；缺少完整传输清单，不能确认外传内容及范围。",
                  "evidence_ids": [
                    "showcase-run-02-query-1",
                    "showcase-run-02-query-2"
                  ]
                }
              },
              {
                "name": "响应分析",
                "agent": "响应分析",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-02-1"
                },
                "output": {
                  "summary": "按当前输入及可用证据交付",
                  "evidence_ids": [
                    "showcase-run-02-query-1",
                    "showcase-run-02-query-2"
                  ]
                }
              },
              {
                "name": "报告整理",
                "agent": "报告整理",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-02-1"
                },
                "output": {
                  "summary": "按当前输入及可用证据交付",
                  "evidence_ids": [
                    "showcase-run-02-query-1",
                    "showcase-run-02-query-2"
                  ]
                }
              }
            ],
            "tools": [
              {
                "id": "showcase-run-02-query-1",
                "name": "asset_activity",
                "args": {
                  "hostnames": [
                    "OPS-JUMP-01",
                    "APP-SRV-02",
                    "FILE-SRV-03"
                  ],
                  "username": "svc.reports@contoso.com",
                  "start": "2026-10-31T03:00:00Z",
                  "end": "2026-10-31T03:16:00.000Z"
                },
                "resultFormat": "saved_result",
                "time": "2026-10-31T03:17:00.000Z",
                "success": true,
                "result": "{\n  \"records\": [\n    {\n      \"alert_id\": \"showcase-alert-02-1\",\n      \"time\": \"2026-10-31T03:00:00.000Z\",\n      \"hostnames\": [\n        \"OPS-JUMP-01\",\n        \"APP-SRV-02\"\n      ],\n      \"username\": \"svc.reports@contoso.com\",\n      \"description\": \"服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-02-2\",\n      \"time\": \"2026-10-31T03:04:00.000Z\",\n      \"hostnames\": [\n        \"APP-SRV-02\",\n        \"FILE-SRV-03\"\n      ],\n      \"username\": \"svc.reports@contoso.com\",\n      \"description\": \"应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-02-3\",\n      \"time\": \"2026-10-31T03:08:00.000Z\",\n      \"hostnames\": [\n        \"FILE-SRV-03\"\n      ],\n      \"username\": \"svc.reports@contoso.com\",\n      \"description\": \"文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-02-4\",\n      \"time\": \"2026-10-31T03:12:00.000Z\",\n      \"hostnames\": [\n        \"FILE-SRV-03\"\n      ],\n      \"username\": \"svc.reports@contoso.com\",\n      \"description\": \"上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。\"\n    }\n  ],\n  \"scope\": {\n    \"hostnames\": [\n      \"OPS-JUMP-01\",\n      \"APP-SRV-02\",\n      \"FILE-SRV-03\"\n    ],\n    \"username\": \"svc.reports@contoso.com\",\n    \"start\": \"2026-10-31T03:00:00Z\",\n    \"end\": \"2026-10-31T03:16:00.000Z\"\n  }\n}",
                "status": "已返回完整记录"
              },
              {
                "id": "showcase-run-02-query-2",
                "name": "transfer_inventory",
                "args": {
                  "alert_id": "showcase-alert-02-1",
                  "start": "2026-10-31T03:00:00Z",
                  "end": "2026-10-31T03:16:00.000Z"
                },
                "resultFormat": "saved_result",
                "time": "2026-10-31T03:18:00.000Z",
                "success": false,
                "result": "{\n  \"status\": \"unavailable\",\n  \"reason\": \"未取得完整文件传输清单\"\n}",
                "status": "资料不可用"
              }
            ]
          }
        ],
        "responseRecommendations": [
          {
            "action": "补查文件传输清单并核对授权",
            "target": "OPS-JUMP-01",
            "reason": "连接记录不足以确认具体传输对象。",
            "approval": "无需审批",
            "execution": "未执行"
          }
        ]
      }
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-02-2",
      "title": "应用服务器读取文件服务器共享目录",
      "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。",
      "severity": "高",
      "source": "文件访问审计",
      "category": "收集",
      "entityIds": [
        "showcase-service",
        "showcase-app",
        "showcase-share",
        "showcase-cloud"
      ],
      "incidentId": "showcase-incident-02",
      "caseId": null,
      "status": "New",
      "owner": "未分配",
      "classification": "Not set",
      "disposition": null,
      "tags": [
        "重点核查"
      ],
      "event_time": "2026-10-31T03:04:00.000Z",
      "first": "2026-10-31T03:04:00.000Z",
      "last": "2026-10-31T03:05:00.000Z",
      "hostNames": [
        "APP-SRV-02",
        "FILE-SRV-03"
      ],
      "tactics": [
        "收集"
      ],
      "iocKeys": [],
      "investigation": "Not started",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1039"
        ],
        "raw": {
          "id": "showcase-alert-02-2",
          "tenant_id": "showcase-contoso",
          "source": "文件访问审计",
          "source_ref": "SEC-20261031-22",
          "event_time": "2026-10-31T03:04:00.000Z",
          "title": "应用服务器读取文件服务器共享目录",
          "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。",
          "severity": "高",
          "status": "New",
          "incident_id": "showcase-incident-02",
          "case_id": null,
          "mitre_tactics": [
            "收集"
          ],
          "mitre_techniques": [
            "T1039"
          ],
          "rule_id": "RULE-22",
          "entities": [
            {
              "id": "showcase-service",
              "type": "user",
              "name": "svc.reports@contoso.com"
            },
            {
              "id": "showcase-app",
              "type": "device",
              "name": "APP-SRV-02"
            },
            {
              "id": "showcase-share",
              "type": "device",
              "name": "FILE-SRV-03"
            },
            {
              "id": "showcase-cloud",
              "type": "cloud",
              "name": "finance-reports-store"
            }
          ],
          "raw_event": {
            "event_id": "evt-2-2",
            "hostname": "APP-SRV-02",
            "username": "svc.reports@contoso.com",
            "observation": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。",
            "approval_reference": null
          }
        },
        "confidence": {
          "score": 90
        },
        "risk": 69,
        "explanation": {
          "generatedAt": "2026-10-31T03:05:00.000Z",
          "summary": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。 请结合事件中的共享对象和时间线核查授权与影响。",
          "evidence": [
            "源记录 SEC-20261031-22",
            "规则 RULE-22",
            "对象 svc.reports@contoso.com、APP-SRV-02、FILE-SRV-03、finance-reports-store"
          ],
          "gaps": [
            "文件传输清单不完整，需补查范围"
          ],
          "suggestedActions": [
            {
              "title": "核对授权、进程和目标记录",
              "rationale": "检测命中需要结合上下文研判。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-31T03:04:00.000Z",
            "title": "告警发生",
            "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。"
          },
          {
            "time": "2026-10-31T03:04:15.000Z",
            "title": "告警被检测到",
            "description": "文件访问审计 · RULE-22"
          },
          {
            "time": "2026-10-31T03:04:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-22"
          },
          {
            "time": "2026-10-31T03:05:00.000Z",
            "title": "告警关联到事件",
            "description": "服务账号跨主机访问与归档上传"
          }
        ],
        "runs": [],
        "responseRecommendations": []
      }
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-02-3",
      "title": "服务账号生成财务文件归档",
      "description": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。",
      "severity": "中",
      "source": "文件访问审计",
      "category": "收集",
      "entityIds": [
        "showcase-service",
        "showcase-share",
        "showcase-archive"
      ],
      "incidentId": "showcase-incident-02",
      "caseId": null,
      "status": "New",
      "owner": "未分配",
      "classification": "Not set",
      "disposition": null,
      "tags": [
        "重点核查"
      ],
      "event_time": "2026-10-31T03:08:00.000Z",
      "first": "2026-10-31T03:08:00.000Z",
      "last": "2026-10-31T03:09:00.000Z",
      "hostNames": [
        "FILE-SRV-03"
      ],
      "tactics": [
        "收集"
      ],
      "iocKeys": [
        "file:aed14ebc5fd55e6fc3ce4a88d43ab8a87b638f493d0674231ea524271207f445"
      ],
      "investigation": "Not started",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1560.001"
        ],
        "raw": {
          "id": "showcase-alert-02-3",
          "tenant_id": "showcase-contoso",
          "source": "文件访问审计",
          "source_ref": "SEC-20261031-23",
          "event_time": "2026-10-31T03:08:00.000Z",
          "title": "服务账号生成财务文件归档",
          "description": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。",
          "severity": "中",
          "status": "New",
          "incident_id": "showcase-incident-02",
          "case_id": null,
          "mitre_tactics": [
            "收集"
          ],
          "mitre_techniques": [
            "T1560.001"
          ],
          "rule_id": "RULE-23",
          "entities": [
            {
              "id": "showcase-service",
              "type": "user",
              "name": "svc.reports@contoso.com"
            },
            {
              "id": "showcase-share",
              "type": "device",
              "name": "FILE-SRV-03"
            },
            {
              "id": "showcase-archive",
              "type": "file",
              "name": "finance-export.zip",
              "sha256": "aed14ebc5fd55e6fc3ce4a88d43ab8a87b638f493d0674231ea524271207f445"
            }
          ],
          "raw_event": {
            "event_id": "evt-2-3",
            "hostname": "FILE-SRV-03",
            "username": "svc.reports@contoso.com",
            "observation": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。",
            "approval_reference": null
          }
        },
        "confidence": {
          "score": 87
        },
        "risk": 66,
        "explanation": {
          "generatedAt": "2026-10-31T03:09:00.000Z",
          "summary": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。 请结合事件中的共享对象和时间线核查授权与影响。",
          "evidence": [
            "源记录 SEC-20261031-23",
            "规则 RULE-23",
            "对象 svc.reports@contoso.com、FILE-SRV-03、finance-export.zip"
          ],
          "gaps": [
            "文件传输清单不完整，需补查范围"
          ],
          "suggestedActions": [
            {
              "title": "核对授权、进程和目标记录",
              "rationale": "检测命中需要结合上下文研判。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-31T03:08:00.000Z",
            "title": "告警发生",
            "description": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。"
          },
          {
            "time": "2026-10-31T03:08:15.000Z",
            "title": "告警被检测到",
            "description": "文件访问审计 · RULE-23"
          },
          {
            "time": "2026-10-31T03:08:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-23"
          },
          {
            "time": "2026-10-31T03:09:00.000Z",
            "title": "告警关联到事件",
            "description": "服务账号跨主机访问与归档上传"
          }
        ],
        "runs": [],
        "responseRecommendations": []
      }
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-02-4",
      "title": "归档进程向外部目标上传字节",
      "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。",
      "severity": "高",
      "source": "网络流量检测",
      "category": "数据外传",
      "entityIds": [
        "showcase-service",
        "showcase-share",
        "showcase-archive",
        "showcase-upload",
        "showcase-cloudapp"
      ],
      "incidentId": "showcase-incident-02",
      "caseId": null,
      "status": "New",
      "owner": "未分配",
      "classification": "Not set",
      "disposition": null,
      "tags": [
        "重点核查"
      ],
      "event_time": "2026-10-31T03:12:00.000Z",
      "first": "2026-10-31T03:12:00.000Z",
      "last": "2026-10-31T03:13:00.000Z",
      "hostNames": [
        "FILE-SRV-03"
      ],
      "tactics": [
        "数据外传"
      ],
      "iocKeys": [
        "file:aed14ebc5fd55e6fc3ce4a88d43ab8a87b638f493d0674231ea524271207f445",
        "ip:198.51.100.42"
      ],
      "investigation": "Not started",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1567.002"
        ],
        "raw": {
          "id": "showcase-alert-02-4",
          "tenant_id": "showcase-contoso",
          "source": "网络流量检测",
          "source_ref": "SEC-20261031-24",
          "event_time": "2026-10-31T03:12:00.000Z",
          "title": "归档进程向外部目标上传字节",
          "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。",
          "severity": "高",
          "status": "New",
          "incident_id": "showcase-incident-02",
          "case_id": null,
          "mitre_tactics": [
            "数据外传"
          ],
          "mitre_techniques": [
            "T1567.002"
          ],
          "rule_id": "RULE-24",
          "entities": [
            {
              "id": "showcase-service",
              "type": "user",
              "name": "svc.reports@contoso.com"
            },
            {
              "id": "showcase-share",
              "type": "device",
              "name": "FILE-SRV-03"
            },
            {
              "id": "showcase-archive",
              "type": "file",
              "name": "finance-export.zip",
              "sha256": "aed14ebc5fd55e6fc3ce4a88d43ab8a87b638f493d0674231ea524271207f445"
            },
            {
              "id": "showcase-upload",
              "type": "ip",
              "name": "198.51.100.42"
            },
            {
              "id": "showcase-cloudapp",
              "type": "app",
              "name": "Report Transfer Client"
            }
          ],
          "raw_event": {
            "event_id": "evt-2-4",
            "hostname": "FILE-SRV-03",
            "username": "svc.reports@contoso.com",
            "observation": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。",
            "approval_reference": null
          }
        },
        "confidence": {
          "score": 84
        },
        "risk": 63,
        "explanation": {
          "generatedAt": "2026-10-31T03:13:00.000Z",
          "summary": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。 请结合事件中的共享对象和时间线核查授权与影响。",
          "evidence": [
            "源记录 SEC-20261031-24",
            "规则 RULE-24",
            "对象 svc.reports@contoso.com、FILE-SRV-03、finance-export.zip、198.51.100.42、Report Transfer Client"
          ],
          "gaps": [
            "文件传输清单不完整，需补查范围"
          ],
          "suggestedActions": [
            {
              "title": "核对授权、进程和目标记录",
              "rationale": "检测命中需要结合上下文研判。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-31T03:12:00.000Z",
            "title": "告警发生",
            "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。"
          },
          {
            "time": "2026-10-31T03:12:15.000Z",
            "title": "告警被检测到",
            "description": "网络流量检测 · RULE-24"
          },
          {
            "time": "2026-10-31T03:12:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-24"
          },
          {
            "time": "2026-10-31T03:13:00.000Z",
            "title": "告警关联到事件",
            "description": "服务账号跨主机访问与归档上传"
          }
        ],
        "runs": [],
        "responseRecommendations": []
      }
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-03-1",
      "title": "备份服务器在维护窗口运行脚本",
      "description": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。",
      "severity": "低",
      "source": "终端检测与响应",
      "category": "执行",
      "entityIds": [
        "showcase-backup",
        "showcase-operator",
        "showcase-automation"
      ],
      "incidentId": "showcase-incident-03",
      "caseId": "showcase-case-03",
      "status": "Resolved",
      "owner": "Patti Fernandez",
      "classification": "Informational",
      "disposition": "benign",
      "tags": [
        "授权维护"
      ],
      "event_time": "2026-10-29T02:00:00.000Z",
      "first": "2026-10-29T02:00:00.000Z",
      "last": "2026-10-29T02:32:00.000Z",
      "hostNames": [
        "BACKUP-SRV-01"
      ],
      "tactics": [
        "执行"
      ],
      "iocKeys": [],
      "investigation": "Completed",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1059.001"
        ],
        "raw": {
          "id": "showcase-alert-03-1",
          "tenant_id": "showcase-contoso",
          "source": "终端检测与响应",
          "source_ref": "SEC-20261031-31",
          "event_time": "2026-10-29T02:00:00.000Z",
          "title": "备份服务器在维护窗口运行脚本",
          "description": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。",
          "severity": "低",
          "status": "Resolved",
          "incident_id": "showcase-incident-03",
          "case_id": "showcase-case-03",
          "mitre_tactics": [
            "执行"
          ],
          "mitre_techniques": [
            "T1059.001"
          ],
          "rule_id": "RULE-31",
          "entities": [
            {
              "id": "showcase-backup",
              "type": "device",
              "name": "BACKUP-SRV-01"
            },
            {
              "id": "showcase-operator",
              "type": "user",
              "name": "backup.ops@contoso.com"
            },
            {
              "id": "showcase-automation",
              "type": "robot",
              "name": "Backup Validation Assistant"
            }
          ],
          "raw_event": {
            "event_id": "evt-3-1",
            "hostname": "BACKUP-SRV-01",
            "username": "backup.ops@contoso.com",
            "observation": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。",
            "approval_reference": "CHG-2026-1031"
          }
        },
        "confidence": {
          "score": 88
        },
        "risk": 96,
        "explanation": {
          "generatedAt": "2026-10-29T02:01:00.000Z",
          "summary": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。 已核对维护工单、账号和操作范围，当前判断为预期行为。",
          "evidence": [
            "源记录 SEC-20261031-31",
            "规则 RULE-31",
            "对象 BACKUP-SRV-01、backup.ops@contoso.com、Backup Validation Assistant"
          ],
          "gaps": [],
          "suggestedActions": [
            {
              "title": "保留工单与备份清单供复核",
              "rationale": "后续同类告警可按相同范围复核。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-29T02:00:00.000Z",
            "title": "告警发生",
            "description": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。"
          },
          {
            "time": "2026-10-29T02:00:15.000Z",
            "title": "告警被检测到",
            "description": "终端检测与响应 · RULE-31"
          },
          {
            "time": "2026-10-29T02:00:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-31"
          },
          {
            "time": "2026-10-29T02:01:00.000Z",
            "title": "告警关联到事件",
            "description": "已核实的授权备份与维护活动"
          },
          {
            "time": "2026-10-29T02:16:00.000Z",
            "title": "告警分配",
            "description": "负责人：Patti Fernandez"
          },
          {
            "time": "2026-10-29T02:32:00.000Z",
            "title": "人工复核并关闭告警",
            "description": "已核对 CHG-2026-1031、执行账号及备份清单，符合批准的维护范围。"
          },
          {
            "time": "2026-10-29T02:16:00.000Z",
            "title": "自动分诊完成",
            "description": "符合批准的维护任务，未升级调查"
          }
        ],
        "runs": [
          {
            "id": "showcase-run-03",
            "time": "2026-10-29T02:16:00.000Z",
            "status": "Completed",
            "completion": "not_escalated",
            "stop": "分诊判断为预期维护活动，未升级调查。",
            "findings": [
              "维护工单、账号、执行窗口与备份目标匹配，判为预期活动。"
            ],
            "actions": [],
            "calls": null,
            "tokens": null,
            "report": null,
            "steps": [
              {
                "name": "自动分诊",
                "agent": "自动分诊",
                "status": "Completed",
                "input": {
                  "alert_id": "showcase-alert-03-1"
                },
                "output": {
                  "verdict": "benign_true_positive",
                  "confidence": 0.96,
                  "auto_closed": false
                }
              }
            ],
            "tools": []
          }
        ],
        "responseRecommendations": []
      },
      "feedbackReason": "已核对 CHG-2026-1031、执行账号及备份清单，符合批准的维护范围。"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-03-2",
      "title": "备份任务批量归档业务文件",
      "description": "归档目录和文件集合匹配维护工单，未发现超出备份范围的访问。",
      "severity": "低",
      "source": "文件访问审计",
      "category": "收集",
      "entityIds": [
        "showcase-backup",
        "showcase-operator",
        "showcase-repository"
      ],
      "incidentId": "showcase-incident-03",
      "caseId": "showcase-case-03",
      "status": "Resolved",
      "owner": "Patti Fernandez",
      "classification": "Informational",
      "disposition": "benign",
      "tags": [
        "授权维护"
      ],
      "event_time": "2026-10-29T02:04:00.000Z",
      "first": "2026-10-29T02:04:00.000Z",
      "last": "2026-10-29T02:32:00.000Z",
      "hostNames": [
        "BACKUP-SRV-01"
      ],
      "tactics": [
        "收集"
      ],
      "iocKeys": [],
      "investigation": "Not started",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1560.001"
        ],
        "raw": {
          "id": "showcase-alert-03-2",
          "tenant_id": "showcase-contoso",
          "source": "文件访问审计",
          "source_ref": "SEC-20261031-32",
          "event_time": "2026-10-29T02:04:00.000Z",
          "title": "备份任务批量归档业务文件",
          "description": "归档目录和文件集合匹配维护工单，未发现超出备份范围的访问。",
          "severity": "低",
          "status": "Resolved",
          "incident_id": "showcase-incident-03",
          "case_id": "showcase-case-03",
          "mitre_tactics": [
            "收集"
          ],
          "mitre_techniques": [
            "T1560.001"
          ],
          "rule_id": "RULE-32",
          "entities": [
            {
              "id": "showcase-backup",
              "type": "device",
              "name": "BACKUP-SRV-01"
            },
            {
              "id": "showcase-operator",
              "type": "user",
              "name": "backup.ops@contoso.com"
            },
            {
              "id": "showcase-repository",
              "type": "cloud",
              "name": "approved-backup-store"
            }
          ],
          "raw_event": {
            "event_id": "evt-3-2",
            "hostname": "BACKUP-SRV-01",
            "username": "backup.ops@contoso.com",
            "observation": "归档目录和文件集合匹配维护工单，未发现超出备份范围的访问。",
            "approval_reference": "CHG-2026-1031"
          }
        },
        "confidence": {
          "score": 88
        },
        "risk": 96,
        "explanation": {
          "generatedAt": "2026-10-29T02:05:00.000Z",
          "summary": "归档目录和文件集合匹配维护工单，未发现超出备份范围的访问。 已核对维护工单、账号和操作范围，当前判断为预期行为。",
          "evidence": [
            "源记录 SEC-20261031-32",
            "规则 RULE-32",
            "对象 BACKUP-SRV-01、backup.ops@contoso.com、approved-backup-store"
          ],
          "gaps": [],
          "suggestedActions": [
            {
              "title": "保留工单与备份清单供复核",
              "rationale": "后续同类告警可按相同范围复核。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-29T02:04:00.000Z",
            "title": "告警发生",
            "description": "归档目录和文件集合匹配维护工单，未发现超出备份范围的访问。"
          },
          {
            "time": "2026-10-29T02:04:15.000Z",
            "title": "告警被检测到",
            "description": "文件访问审计 · RULE-32"
          },
          {
            "time": "2026-10-29T02:04:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-32"
          },
          {
            "time": "2026-10-29T02:05:00.000Z",
            "title": "告警关联到事件",
            "description": "已核实的授权备份与维护活动"
          },
          {
            "time": "2026-10-29T02:16:00.000Z",
            "title": "告警分配",
            "description": "负责人：Patti Fernandez"
          },
          {
            "time": "2026-10-29T02:32:00.000Z",
            "title": "人工复核并关闭告警",
            "description": "已核对 CHG-2026-1031、执行账号及备份清单，符合批准的维护范围。"
          }
        ],
        "runs": [],
        "responseRecommendations": []
      },
      "feedbackReason": "已核对 CHG-2026-1031、执行账号及备份清单，符合批准的维护范围。"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-alert-03-3",
      "title": "归档上传至批准的备份存储",
      "description": "目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。",
      "severity": "低",
      "source": "网络流量检测",
      "category": "数据外传",
      "entityIds": [
        "showcase-backup",
        "showcase-operator",
        "showcase-repository",
        "showcase-internal"
      ],
      "incidentId": "showcase-incident-03",
      "caseId": "showcase-case-03",
      "status": "Resolved",
      "owner": "Patti Fernandez",
      "classification": "Informational",
      "disposition": "benign",
      "tags": [
        "授权维护"
      ],
      "event_time": "2026-10-29T02:08:00.000Z",
      "first": "2026-10-29T02:08:00.000Z",
      "last": "2026-10-29T02:32:00.000Z",
      "hostNames": [
        "BACKUP-SRV-01"
      ],
      "tactics": [
        "数据外传"
      ],
      "iocKeys": [
        "ip:192.0.2.25"
      ],
      "investigation": "Not started",
      "comments": [],
      "detailMaterial": {
        "timelineVersion": 2,
        "tenantName": "Contoso",
        "techniques": [
          "T1567.002"
        ],
        "raw": {
          "id": "showcase-alert-03-3",
          "tenant_id": "showcase-contoso",
          "source": "网络流量检测",
          "source_ref": "SEC-20261031-33",
          "event_time": "2026-10-29T02:08:00.000Z",
          "title": "归档上传至批准的备份存储",
          "description": "目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。",
          "severity": "低",
          "status": "Resolved",
          "incident_id": "showcase-incident-03",
          "case_id": "showcase-case-03",
          "mitre_tactics": [
            "数据外传"
          ],
          "mitre_techniques": [
            "T1567.002"
          ],
          "rule_id": "RULE-33",
          "entities": [
            {
              "id": "showcase-backup",
              "type": "device",
              "name": "BACKUP-SRV-01"
            },
            {
              "id": "showcase-operator",
              "type": "user",
              "name": "backup.ops@contoso.com"
            },
            {
              "id": "showcase-repository",
              "type": "cloud",
              "name": "approved-backup-store"
            },
            {
              "id": "showcase-internal",
              "type": "ip",
              "name": "192.0.2.25"
            }
          ],
          "raw_event": {
            "event_id": "evt-3-3",
            "hostname": "BACKUP-SRV-01",
            "username": "backup.ops@contoso.com",
            "observation": "目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。",
            "approval_reference": "CHG-2026-1031"
          }
        },
        "confidence": {
          "score": 88
        },
        "risk": 96,
        "explanation": {
          "generatedAt": "2026-10-29T02:09:00.000Z",
          "summary": "目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。 已核对维护工单、账号和操作范围，当前判断为预期行为。",
          "evidence": [
            "源记录 SEC-20261031-33",
            "规则 RULE-33",
            "对象 BACKUP-SRV-01、backup.ops@contoso.com、approved-backup-store、192.0.2.25"
          ],
          "gaps": [],
          "suggestedActions": [
            {
              "title": "保留工单与备份清单供复核",
              "rationale": "后续同类告警可按相同范围复核。"
            }
          ]
        },
        "history": [
          {
            "time": "2026-10-29T02:08:00.000Z",
            "title": "告警发生",
            "description": "目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。"
          },
          {
            "time": "2026-10-29T02:08:15.000Z",
            "title": "告警被检测到",
            "description": "网络流量检测 · RULE-33"
          },
          {
            "time": "2026-10-29T02:08:30.000Z",
            "title": "告警入库",
            "description": "源记录 SEC-20261031-33"
          },
          {
            "time": "2026-10-29T02:09:00.000Z",
            "title": "告警关联到事件",
            "description": "已核实的授权备份与维护活动"
          },
          {
            "time": "2026-10-29T02:16:00.000Z",
            "title": "告警分配",
            "description": "负责人：Patti Fernandez"
          },
          {
            "time": "2026-10-29T02:32:00.000Z",
            "title": "人工复核并关闭告警",
            "description": "已核对 CHG-2026-1031、执行账号及备份清单，符合批准的维护范围。"
          }
        ],
        "runs": [],
        "responseRecommendations": []
      },
      "feedbackReason": "已核对 CHG-2026-1031、执行账号及备份清单，符合批准的维护范围。"
    }
  ],
  "assets": [
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-finance",
      "type": "device",
      "name": "FIN-LAPTOP-07",
      "tags": [
        "财务终端",
        "关键资产"
      ],
      "inventory": true,
      "domain": "CONTOSO",
      "os": "Windows 11",
      "risk": "高",
      "ip": "10.20.10.7",
      "critical": true
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-analyst",
      "type": "user",
      "name": "lin.chen@contoso.com",
      "tags": [],
      "inventory": true,
      "department": "财务部",
      "role": "财务分析员",
      "risk": "高"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-mailbox",
      "type": "mailbox",
      "name": "lin.chen@contoso.com",
      "tags": [],
      "inventory": true,
      "domain": "contoso.com",
      "kind": "用户邮箱",
      "risk": "中"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-external",
      "type": "ip",
      "name": "203.0.113.77",
      "tags": [],
      "inventory": true,
      "location": "文档示例地址",
      "provider": "外部连接目标",
      "risk": "高"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-attachment",
      "type": "file",
      "name": "quarterly-review.exe",
      "tags": [],
      "inventory": true,
      "hash": "46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af",
      "risk": "高"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-app",
      "type": "device",
      "name": "APP-SRV-02",
      "tags": [
        "应用服务器"
      ],
      "inventory": true,
      "domain": "CONTOSO",
      "os": "Windows Server 2022",
      "risk": "高",
      "ip": "10.20.20.2"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-share",
      "type": "device",
      "name": "FILE-SRV-03",
      "tags": [
        "文件服务器"
      ],
      "inventory": true,
      "domain": "CONTOSO",
      "os": "Windows Server 2022",
      "risk": "中",
      "ip": "10.20.20.3"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-jump",
      "type": "device",
      "name": "OPS-JUMP-01",
      "tags": [
        "运维跳板机"
      ],
      "inventory": true,
      "domain": "CONTOSO",
      "os": "Windows Server 2022",
      "risk": "中",
      "ip": "10.20.20.1"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-service",
      "type": "user",
      "name": "svc.reports@contoso.com",
      "tags": [],
      "inventory": true,
      "department": "数据平台",
      "role": "报表服务账号",
      "risk": "高"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-archive",
      "type": "file",
      "name": "finance-export.zip",
      "tags": [],
      "inventory": true,
      "hash": "aed14ebc5fd55e6fc3ce4a88d43ab8a87b638f493d0674231ea524271207f445",
      "risk": "中"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-upload",
      "type": "ip",
      "name": "198.51.100.42",
      "tags": [],
      "inventory": true,
      "location": "文档示例地址",
      "provider": "外部上传目标",
      "risk": "中"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-cloud",
      "type": "cloud",
      "name": "finance-reports-store",
      "tags": [
        "财务存储"
      ],
      "inventory": true,
      "provider": "Microsoft Azure",
      "region": "East Asia",
      "risk": "中"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-cloudapp",
      "type": "app",
      "name": "Report Transfer Client",
      "tags": [],
      "inventory": true,
      "publisher": "Contoso",
      "permissions": "Files.ReadWrite.All",
      "risk": "中"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-backup",
      "type": "device",
      "name": "BACKUP-SRV-01",
      "tags": [
        "备份服务器"
      ],
      "inventory": true,
      "domain": "CONTOSO",
      "os": "Windows Server 2022",
      "risk": "低",
      "ip": "10.20.30.1"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-operator",
      "type": "user",
      "name": "backup.ops@contoso.com",
      "tags": [],
      "inventory": true,
      "department": "基础设施",
      "role": "备份操作员",
      "risk": "低"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-repository",
      "type": "cloud",
      "name": "approved-backup-store",
      "tags": [
        "备份存储"
      ],
      "inventory": true,
      "provider": "Microsoft Azure",
      "region": "East Asia",
      "risk": "低"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-automation",
      "type": "robot",
      "name": "Backup Validation Assistant",
      "tags": [],
      "inventory": true,
      "publisher": "Contoso",
      "permissions": "只读备份任务",
      "risk": "低"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-internal",
      "type": "ip",
      "name": "192.0.2.25",
      "tags": [],
      "inventory": true,
      "location": "文档示例地址",
      "provider": "批准的备份目标",
      "risk": "低"
    }
  ],
  "cases": [
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-case-01",
      "title": "财务终端钓鱼附件与脚本外联调查",
      "description": "财务用户打开邮件附件后，同一终端先后出现脚本启动、凭据进程读取和外部连接告警。告警共享终端与账号，文件哈希贯穿附件和执行记录；事件用于呈现这些关联事实，联合研判及处置由关联 Case 承接。",
      "status": "In progress",
      "owner": "Alex Wilber",
      "severity": "高",
      "priority": 92,
      "classification": "Not set",
      "tags": [
        "联合核查"
      ],
      "incidentId": "showcase-incident-01",
      "alertIds": [
        "showcase-alert-01-1",
        "showcase-alert-01-2",
        "showcase-alert-01-3",
        "showcase-alert-01-4"
      ],
      "created": "2026-10-31T01:26:00.000Z",
      "updated": "2026-10-31T01:45:00.000Z",
      "tasks": []
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-case-03",
      "title": "已核实的授权备份与维护活动调查",
      "description": "备份服务器上的脚本、文件归档与存储上传告警对应批准的维护工单 CHG-2026-1031。分析员核对操作账号、目标存储和维护窗口后，确认属于预期备份行为并手动解决事件。",
      "status": "Resolved",
      "owner": "Patti Fernandez",
      "severity": "低",
      "priority": 24,
      "classification": "Informational",
      "tags": [
        "授权维护"
      ],
      "incidentId": "showcase-incident-03",
      "alertIds": [
        "showcase-alert-03-1",
        "showcase-alert-03-2",
        "showcase-alert-03-3"
      ],
      "created": "2026-10-29T02:16:00.000Z",
      "updated": "2026-10-29T02:35:00.000Z",
      "tasks": []
    }
  ],
  "evidence": [
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-01-1",
      "alertId": "showcase-alert-01-1",
      "entityId": "showcase-attachment",
      "name": "quarterly-review.exe",
      "type": "文件",
      "origin": "邮件安全网关",
      "verdict": "Suspicious",
      "remediation": "Pending approval",
      "threat": "初始访问"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-01-2",
      "alertId": "showcase-alert-01-2",
      "entityId": "showcase-attachment",
      "name": "quarterly-review.exe",
      "type": "文件",
      "origin": "终端检测与响应",
      "verdict": "Suspicious",
      "remediation": "Pending approval",
      "threat": "执行"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-01-3",
      "alertId": "showcase-alert-01-3",
      "entityId": "showcase-finance",
      "name": "FIN-LAPTOP-07",
      "type": "进程",
      "origin": "终端检测与响应",
      "verdict": "Suspicious",
      "remediation": "Pending approval",
      "threat": "凭据访问"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-01-4",
      "alertId": "showcase-alert-01-4",
      "entityId": "showcase-external",
      "name": "203.0.113.77",
      "type": "IP 地址",
      "origin": "网络流量检测",
      "verdict": "Suspicious",
      "remediation": "Pending approval",
      "threat": "命令与控制"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-02-1",
      "alertId": "showcase-alert-02-1",
      "entityId": "showcase-service",
      "name": "svc.reports@contoso.com",
      "type": "云登录会话",
      "origin": "身份与目录检测",
      "verdict": "Suspicious",
      "remediation": "Not started",
      "threat": "横向移动"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-02-2",
      "alertId": "showcase-alert-02-2",
      "entityId": "showcase-service",
      "name": "svc.reports@contoso.com",
      "type": "云登录会话",
      "origin": "文件访问审计",
      "verdict": "Suspicious",
      "remediation": "Not started",
      "threat": "收集"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-02-3",
      "alertId": "showcase-alert-02-3",
      "entityId": "showcase-archive",
      "name": "finance-export.zip",
      "type": "文件",
      "origin": "文件访问审计",
      "verdict": "Suspicious",
      "remediation": "Not started",
      "threat": "收集"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-02-4",
      "alertId": "showcase-alert-02-4",
      "entityId": "showcase-archive",
      "name": "finance-export.zip",
      "type": "文件",
      "origin": "网络流量检测",
      "verdict": "Suspicious",
      "remediation": "Not started",
      "threat": "数据外传"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-03-1",
      "alertId": "showcase-alert-03-1",
      "entityId": "showcase-backup",
      "name": "BACKUP-SRV-01",
      "type": "进程",
      "origin": "终端检测与响应",
      "verdict": "Clean",
      "remediation": "No action needed",
      "threat": "授权备份"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-03-2",
      "alertId": "showcase-alert-03-2",
      "entityId": "showcase-backup",
      "name": "BACKUP-SRV-01",
      "type": "进程",
      "origin": "文件访问审计",
      "verdict": "Clean",
      "remediation": "No action needed",
      "threat": "授权备份"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "evidence-showcase-alert-03-3",
      "alertId": "showcase-alert-03-3",
      "entityId": "showcase-internal",
      "name": "192.0.2.25",
      "type": "IP 地址",
      "origin": "网络流量检测",
      "verdict": "Clean",
      "remediation": "No action needed",
      "threat": "授权备份"
    }
  ],
  "activities": [
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-1-1",
      "title": "成员告警关联至事件",
      "type": "告警关联",
      "performedBy": "系统",
      "trigger": "自动",
      "status": "Completed",
      "target": "财务终端钓鱼附件与脚本外联",
      "time": "2026-10-31T01:23:00.000Z",
      "incidentId": "showcase-incident-01",
      "caseIds": [
        "showcase-case-01"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-1-2",
      "title": "事件分诊与优先级评估",
      "type": "分诊",
      "performedBy": "系统",
      "trigger": "自动",
      "status": "Completed",
      "target": "财务终端钓鱼附件与脚本外联",
      "time": "2026-10-31T01:24:00.000Z",
      "incidentId": "showcase-incident-01",
      "caseIds": [
        "showcase-case-01"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-1-3",
      "title": "自动处理结果已保存",
      "type": "调查",
      "performedBy": "自动处理",
      "trigger": "自动",
      "status": "Completed",
      "target": "财务终端钓鱼附件与脚本外联",
      "time": "2026-10-31T01:32:00.000Z",
      "incidentId": "showcase-incident-01",
      "caseIds": [
        "showcase-case-01"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-1-4",
      "title": "分配事件负责人",
      "type": "人员分派",
      "performedBy": "Alex Wilber",
      "trigger": "人工",
      "status": "Completed",
      "target": "财务终端钓鱼附件与脚本外联",
      "time": "2026-10-31T01:26:00.000Z",
      "incidentId": "showcase-incident-01",
      "caseIds": [
        "showcase-case-01"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-1-5",
      "title": "终端隔离建议等待审批",
      "type": "响应",
      "performedBy": "Alex Wilber",
      "trigger": "人工",
      "status": "Pending approval",
      "target": "财务终端钓鱼附件与脚本外联",
      "time": "2026-10-31T01:33:00.000Z",
      "incidentId": "showcase-incident-01",
      "caseIds": [
        "showcase-case-01"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-2-1",
      "title": "成员告警关联至事件",
      "type": "告警关联",
      "performedBy": "系统",
      "trigger": "自动",
      "status": "Completed",
      "target": "服务账号跨主机访问与归档上传",
      "time": "2026-10-31T03:13:00.000Z",
      "incidentId": "showcase-incident-02",
      "caseIds": []
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-2-2",
      "title": "事件分诊与优先级评估",
      "type": "分诊",
      "performedBy": "系统",
      "trigger": "自动",
      "status": "Completed",
      "target": "服务账号跨主机访问与归档上传",
      "time": "2026-10-31T03:14:00.000Z",
      "incidentId": "showcase-incident-02",
      "caseIds": []
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-2-3",
      "title": "自动处理结果已保存",
      "type": "调查",
      "performedBy": "自动处理",
      "trigger": "自动",
      "status": "Partial",
      "target": "服务账号跨主机访问与归档上传",
      "time": "2026-10-31T03:22:00.000Z",
      "incidentId": "showcase-incident-02",
      "caseIds": []
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-2-4",
      "title": "文件传输清单查询不可用",
      "type": "调查",
      "performedBy": "自动处理",
      "trigger": "自动",
      "status": "Failed",
      "target": "服务账号跨主机访问与归档上传",
      "time": "2026-10-31T03:18:00.000Z",
      "incidentId": "showcase-incident-02",
      "caseIds": []
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-3-1",
      "title": "成员告警关联至事件",
      "type": "告警关联",
      "performedBy": "系统",
      "trigger": "自动",
      "status": "Completed",
      "target": "已核实的授权备份与维护活动",
      "time": "2026-10-29T02:13:00.000Z",
      "incidentId": "showcase-incident-03",
      "caseIds": [
        "showcase-case-03"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-3-2",
      "title": "事件分诊与优先级评估",
      "type": "分诊",
      "performedBy": "系统",
      "trigger": "自动",
      "status": "Completed",
      "target": "已核实的授权备份与维护活动",
      "time": "2026-10-29T02:14:00.000Z",
      "incidentId": "showcase-incident-03",
      "caseIds": [
        "showcase-case-03"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-3-3",
      "title": "自动处理结果已保存",
      "type": "调查",
      "performedBy": "自动处理",
      "trigger": "自动",
      "status": "Completed",
      "target": "已核实的授权备份与维护活动",
      "time": "2026-10-29T02:22:00.000Z",
      "incidentId": "showcase-incident-03",
      "caseIds": [
        "showcase-case-03"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-3-4",
      "title": "分配事件负责人",
      "type": "人员分派",
      "performedBy": "Patti Fernandez",
      "trigger": "人工",
      "status": "Completed",
      "target": "已核实的授权备份与维护活动",
      "time": "2026-10-29T02:16:00.000Z",
      "incidentId": "showcase-incident-03",
      "caseIds": [
        "showcase-case-03"
      ]
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-activity-3-5",
      "title": "核对维护工单并手动解决事件",
      "type": "事件管理",
      "performedBy": "Patti Fernandez",
      "trigger": "人工",
      "status": "Completed",
      "target": "已核实的授权备份与维护活动",
      "time": "2026-10-29T02:35:00.000Z",
      "incidentId": "showcase-incident-03",
      "caseIds": [
        "showcase-case-03"
      ]
    }
  ],
  "comments": [
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "comment-showcase-case-01",
      "caseId": "showcase-case-01",
      "author": "Alex Wilber",
      "text": "财务用户打开邮件附件后，同一终端先后出现脚本启动、凭据进程读取和外部连接告警。告警共享终端与账号，文件哈希贯穿附件和执行记录；事件用于呈现这些关联事实，联合研判及处置由关联 Case 承接。",
      "time": "2026-10-31T01:35:00.000Z"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "comment-showcase-case-03",
      "caseId": "showcase-case-03",
      "author": "Patti Fernandez",
      "text": "备份服务器上的脚本、文件归档与存储上传告警对应批准的维护工单 CHG-2026-1031。分析员核对操作账号、目标存储和维护窗口后，确认属于预期备份行为并手动解决事件。",
      "time": "2026-10-29T02:25:00.000Z"
    }
  ],
  "relations": [
    {
      "id": "showcase-alert-01-1:showcase-analyst",
      "from": "showcase-finance",
      "to": "showcase-analyst",
      "label": "初始访问记录关联",
      "alertIds": [
        "showcase-alert-01-1"
      ],
      "kind": "association",
      "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。"
    },
    {
      "id": "showcase-alert-01-1:showcase-mailbox",
      "from": "showcase-finance",
      "to": "showcase-mailbox",
      "label": "初始访问记录关联",
      "alertIds": [
        "showcase-alert-01-1"
      ],
      "kind": "association",
      "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。"
    },
    {
      "id": "showcase-alert-01-1:showcase-attachment",
      "from": "showcase-finance",
      "to": "showcase-attachment",
      "label": "初始访问记录关联",
      "alertIds": [
        "showcase-alert-01-1"
      ],
      "kind": "association",
      "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。"
    },
    {
      "id": "showcase-alert-01-2:showcase-analyst",
      "from": "showcase-finance",
      "to": "showcase-analyst",
      "label": "执行记录关联",
      "alertIds": [
        "showcase-alert-01-2"
      ],
      "kind": "association",
      "description": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。"
    },
    {
      "id": "showcase-alert-01-2:showcase-attachment",
      "from": "showcase-finance",
      "to": "showcase-attachment",
      "label": "执行记录关联",
      "alertIds": [
        "showcase-alert-01-2"
      ],
      "kind": "association",
      "description": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。"
    },
    {
      "id": "showcase-alert-01-3:showcase-analyst",
      "from": "showcase-finance",
      "to": "showcase-analyst",
      "label": "凭据访问记录关联",
      "alertIds": [
        "showcase-alert-01-3"
      ],
      "kind": "association",
      "description": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。"
    },
    {
      "id": "showcase-alert-01-4:showcase-analyst",
      "from": "showcase-finance",
      "to": "showcase-analyst",
      "label": "命令与控制记录关联",
      "alertIds": [
        "showcase-alert-01-4"
      ],
      "kind": "association",
      "description": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。"
    },
    {
      "id": "showcase-alert-01-4:showcase-external",
      "from": "showcase-finance",
      "to": "showcase-external",
      "label": "命令与控制记录关联",
      "alertIds": [
        "showcase-alert-01-4"
      ],
      "kind": "association",
      "description": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。"
    },
    {
      "id": "showcase-alert-02-1:showcase-jump",
      "from": "showcase-service",
      "to": "showcase-jump",
      "label": "横向移动记录关联",
      "alertIds": [
        "showcase-alert-02-1"
      ],
      "kind": "association",
      "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。"
    },
    {
      "id": "showcase-alert-02-1:showcase-app",
      "from": "showcase-service",
      "to": "showcase-app",
      "label": "横向移动记录关联",
      "alertIds": [
        "showcase-alert-02-1"
      ],
      "kind": "association",
      "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。"
    },
    {
      "id": "showcase-alert-02-2:showcase-app",
      "from": "showcase-service",
      "to": "showcase-app",
      "label": "收集记录关联",
      "alertIds": [
        "showcase-alert-02-2"
      ],
      "kind": "association",
      "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。"
    },
    {
      "id": "showcase-alert-02-2:showcase-share",
      "from": "showcase-service",
      "to": "showcase-share",
      "label": "收集记录关联",
      "alertIds": [
        "showcase-alert-02-2"
      ],
      "kind": "association",
      "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。"
    },
    {
      "id": "showcase-alert-02-2:showcase-cloud",
      "from": "showcase-service",
      "to": "showcase-cloud",
      "label": "收集记录关联",
      "alertIds": [
        "showcase-alert-02-2"
      ],
      "kind": "association",
      "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。"
    },
    {
      "id": "showcase-alert-02-3:showcase-share",
      "from": "showcase-service",
      "to": "showcase-share",
      "label": "收集记录关联",
      "alertIds": [
        "showcase-alert-02-3"
      ],
      "kind": "association",
      "description": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。"
    },
    {
      "id": "showcase-alert-02-3:showcase-archive",
      "from": "showcase-service",
      "to": "showcase-archive",
      "label": "收集记录关联",
      "alertIds": [
        "showcase-alert-02-3"
      ],
      "kind": "association",
      "description": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。"
    },
    {
      "id": "showcase-alert-02-4:showcase-share",
      "from": "showcase-service",
      "to": "showcase-share",
      "label": "数据外传记录关联",
      "alertIds": [
        "showcase-alert-02-4"
      ],
      "kind": "association",
      "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。"
    },
    {
      "id": "showcase-alert-02-4:showcase-archive",
      "from": "showcase-service",
      "to": "showcase-archive",
      "label": "数据外传记录关联",
      "alertIds": [
        "showcase-alert-02-4"
      ],
      "kind": "association",
      "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。"
    },
    {
      "id": "showcase-alert-02-4:showcase-upload",
      "from": "showcase-service",
      "to": "showcase-upload",
      "label": "数据外传记录关联",
      "alertIds": [
        "showcase-alert-02-4"
      ],
      "kind": "association",
      "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。"
    },
    {
      "id": "showcase-alert-02-4:showcase-cloudapp",
      "from": "showcase-service",
      "to": "showcase-cloudapp",
      "label": "数据外传记录关联",
      "alertIds": [
        "showcase-alert-02-4"
      ],
      "kind": "association",
      "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。"
    },
    {
      "id": "showcase-alert-03-1:showcase-operator",
      "from": "showcase-backup",
      "to": "showcase-operator",
      "label": "执行记录关联",
      "alertIds": [
        "showcase-alert-03-1"
      ],
      "kind": "association",
      "description": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。"
    },
    {
      "id": "showcase-alert-03-1:showcase-automation",
      "from": "showcase-backup",
      "to": "showcase-automation",
      "label": "执行记录关联",
      "alertIds": [
        "showcase-alert-03-1"
      ],
      "kind": "association",
      "description": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。"
    },
    {
      "id": "showcase-alert-03-2:showcase-operator",
      "from": "showcase-backup",
      "to": "showcase-operator",
      "label": "收集记录关联",
      "alertIds": [
        "showcase-alert-03-2"
      ],
      "kind": "association",
      "description": "归档目录和文件集合匹配维护工单，未发现超出备份范围的访问。"
    },
    {
      "id": "showcase-alert-03-2:showcase-repository",
      "from": "showcase-backup",
      "to": "showcase-repository",
      "label": "收集记录关联",
      "alertIds": [
        "showcase-alert-03-2"
      ],
      "kind": "association",
      "description": "归档目录和文件集合匹配维护工单，未发现超出备份范围的访问。"
    },
    {
      "id": "showcase-alert-03-3:showcase-operator",
      "from": "showcase-backup",
      "to": "showcase-operator",
      "label": "数据外传记录关联",
      "alertIds": [
        "showcase-alert-03-3"
      ],
      "kind": "association",
      "description": "目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。"
    },
    {
      "id": "showcase-alert-03-3:showcase-repository",
      "from": "showcase-backup",
      "to": "showcase-repository",
      "label": "数据外传记录关联",
      "alertIds": [
        "showcase-alert-03-3"
      ],
      "kind": "association",
      "description": "目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。"
    },
    {
      "id": "showcase-alert-03-3:showcase-internal",
      "from": "showcase-backup",
      "to": "showcase-internal",
      "label": "数据外传记录关联",
      "alertIds": [
        "showcase-alert-03-3"
      ],
      "kind": "association",
      "description": "目标存储及访问凭据属于批准的备份任务，传输清单与备份清单一致。"
    }
  ],
  "runs": [
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-run-01",
      "title": "财务终端钓鱼附件与脚本外联自动处理",
      "alertIds": [
        "showcase-alert-01-1"
      ],
      "sourceCaseId": null,
      "status": "completed",
      "completion": "completed",
      "verdict": "true_positive",
      "triage": {
        "verdict": "true_positive",
        "confidence": 0.96,
        "auto_closed": false
      },
      "started": "2026-10-31T01:26:00.000Z",
      "ended": "2026-10-31T01:32:00.000Z",
      "input": {
        "id": "showcase-alert-01-1",
        "tenant_id": "showcase-contoso",
        "source": "邮件安全网关",
        "source_ref": "SEC-20261031-11",
        "event_time": "2026-10-31T01:10:00.000Z",
        "title": "可疑邮件附件在财务终端被打开",
        "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。",
        "severity": "高",
        "status": "New",
        "incident_id": "showcase-incident-01",
        "case_id": "showcase-case-01",
        "mitre_tactics": [
          "初始访问"
        ],
        "mitre_techniques": [
          "T1566.001"
        ],
        "rule_id": "RULE-11",
        "entities": [
          {
            "id": "showcase-finance",
            "type": "device",
            "name": "FIN-LAPTOP-07"
          },
          {
            "id": "showcase-analyst",
            "type": "user",
            "name": "lin.chen@contoso.com"
          },
          {
            "id": "showcase-mailbox",
            "type": "mailbox",
            "name": "lin.chen@contoso.com"
          },
          {
            "id": "showcase-attachment",
            "type": "file",
            "name": "quarterly-review.exe",
            "sha256": "46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af"
          }
        ],
        "raw_event": {
          "event_id": "evt-1-1",
          "hostname": "FIN-LAPTOP-07",
          "username": "lin.chen@contoso.com",
          "observation": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。",
          "approval_reference": null
        },
        "last": "2026-10-31T01:11:00.000Z"
      },
      "findings": [
        "邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。",
        "输入范围的材料已齐备，处置尚待审批。"
      ],
      "steps": [
        {
          "id": "showcase-run-01-triage",
          "seq": 1,
          "kind": "triage_verdict",
          "name": "自动分诊",
          "time": "2026-10-31T01:26:00.000Z",
          "summary": "进入自动调查核查材料",
          "payload": {
            "verdict": "true_positive",
            "confidence": 0.96,
            "auto_closed": false
          }
        },
        {
          "id": "showcase-run-01-query-1-event",
          "seq": 2,
          "kind": "tool_call",
          "name": "调查工具",
          "time": "2026-10-31T01:27:00.000Z",
          "summary": "asset_activity：已取得记录",
          "payload": {
            "tool": "asset_activity",
            "args": {
              "hostnames": [
                "FIN-LAPTOP-07"
              ],
              "username": "lin.chen@contoso.com",
              "start": "2026-10-31T01:10:00Z",
              "end": "2026-10-31T01:26:00.000Z"
            },
            "result": {
              "records": [
                {
                  "alert_id": "showcase-alert-01-1",
                  "time": "2026-10-31T01:10:00.000Z",
                  "hostnames": [
                    "FIN-LAPTOP-07"
                  ],
                  "username": "lin.chen@contoso.com",
                  "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。"
                },
                {
                  "alert_id": "showcase-alert-01-2",
                  "time": "2026-10-31T01:14:00.000Z",
                  "hostnames": [
                    "FIN-LAPTOP-07"
                  ],
                  "username": "lin.chen@contoso.com",
                  "description": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。"
                },
                {
                  "alert_id": "showcase-alert-01-3",
                  "time": "2026-10-31T01:18:00.000Z",
                  "hostnames": [
                    "FIN-LAPTOP-07"
                  ],
                  "username": "lin.chen@contoso.com",
                  "description": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。"
                },
                {
                  "alert_id": "showcase-alert-01-4",
                  "time": "2026-10-31T01:22:00.000Z",
                  "hostnames": [
                    "FIN-LAPTOP-07"
                  ],
                  "username": "lin.chen@contoso.com",
                  "description": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。"
                }
              ],
              "scope": {
                "hostnames": [
                  "FIN-LAPTOP-07"
                ],
                "username": "lin.chen@contoso.com",
                "start": "2026-10-31T01:10:00Z",
                "end": "2026-10-31T01:26:00.000Z"
              }
            }
          }
        },
        {
          "id": "showcase-run-01-query-2-event",
          "seq": 3,
          "kind": "tool_call",
          "name": "调查工具",
          "time": "2026-10-31T01:28:00.000Z",
          "summary": "process_and_file_context：已取得记录",
          "payload": {
            "tool": "process_and_file_context",
            "args": {
              "alert_id": "showcase-alert-01-1",
              "start": "2026-10-31T01:10:00Z",
              "end": "2026-10-31T01:26:00.000Z"
            },
            "result": {
              "status": "success",
              "parent_process": "WINWORD.EXE",
              "process": "powershell.exe",
              "sha256": "46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af",
              "host": "FIN-LAPTOP-07"
            }
          }
        },
        {
          "id": "showcase-run-01-recon",
          "seq": 4,
          "kind": "recon",
          "name": "侦察分析",
          "time": "2026-10-31T01:29:00.000Z",
          "summary": "保存输入范围内的材料与引用",
          "adopted": {
            "summary": "按当前输入及可用证据交付",
            "evidence_ids": [
              "showcase-run-01-query-1",
              "showcase-run-01-query-2"
            ]
          }
        },
        {
          "id": "showcase-run-01-forensic",
          "seq": 5,
          "kind": "forensic",
          "name": "取证分析",
          "time": "2026-10-31T01:30:00.000Z",
          "summary": "邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。；输入范围的材料已齐备，处置尚待审批。",
          "adopted": {
            "summary": "邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。；输入范围的材料已齐备，处置尚待审批。",
            "evidence_ids": [
              "showcase-run-01-query-1",
              "showcase-run-01-query-2"
            ]
          }
        },
        {
          "id": "showcase-run-01-responder",
          "seq": 6,
          "kind": "responder",
          "name": "响应分析",
          "time": "2026-10-31T01:31:00.000Z",
          "summary": "形成建议，未执行响应",
          "adopted": {
            "summary": "按当前输入及可用证据交付",
            "evidence_ids": [
              "showcase-run-01-query-1",
              "showcase-run-01-query-2"
            ]
          }
        },
        {
          "id": "showcase-run-01-report",
          "seq": 7,
          "kind": "report",
          "name": "报告整理",
          "time": "2026-10-31T01:32:00.000Z",
          "summary": "保存输入范围内的材料与引用",
          "adopted": {
            "summary": "按当前输入及可用证据交付",
            "evidence_ids": [
              "showcase-run-01-query-1",
              "showcase-run-01-query-2"
            ]
          }
        }
      ],
      "tools": [
        {
          "id": "showcase-run-01-query-1",
          "name": "asset_activity",
          "args": {
            "hostnames": [
              "FIN-LAPTOP-07"
            ],
            "username": "lin.chen@contoso.com",
            "start": "2026-10-31T01:10:00Z",
            "end": "2026-10-31T01:26:00.000Z"
          },
          "resultFormat": "saved_result",
          "time": "2026-10-31T01:27:00.000Z",
          "success": true,
          "result": "{\n  \"records\": [\n    {\n      \"alert_id\": \"showcase-alert-01-1\",\n      \"time\": \"2026-10-31T01:10:00.000Z\",\n      \"hostnames\": [\n        \"FIN-LAPTOP-07\"\n      ],\n      \"username\": \"lin.chen@contoso.com\",\n      \"description\": \"邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-01-2\",\n      \"time\": \"2026-10-31T01:14:00.000Z\",\n      \"hostnames\": [\n        \"FIN-LAPTOP-07\"\n      ],\n      \"username\": \"lin.chen@contoso.com\",\n      \"description\": \"父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-01-3\",\n      \"time\": \"2026-10-31T01:18:00.000Z\",\n      \"hostnames\": [\n        \"FIN-LAPTOP-07\"\n      ],\n      \"username\": \"lin.chen@contoso.com\",\n      \"description\": \"终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-01-4\",\n      \"time\": \"2026-10-31T01:22:00.000Z\",\n      \"hostnames\": [\n        \"FIN-LAPTOP-07\"\n      ],\n      \"username\": \"lin.chen@contoso.com\",\n      \"description\": \"FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。\"\n    }\n  ],\n  \"scope\": {\n    \"hostnames\": [\n      \"FIN-LAPTOP-07\"\n    ],\n    \"username\": \"lin.chen@contoso.com\",\n    \"start\": \"2026-10-31T01:10:00Z\",\n    \"end\": \"2026-10-31T01:26:00.000Z\"\n  }\n}"
        },
        {
          "id": "showcase-run-01-query-2",
          "name": "process_and_file_context",
          "args": {
            "alert_id": "showcase-alert-01-1",
            "start": "2026-10-31T01:10:00Z",
            "end": "2026-10-31T01:26:00.000Z"
          },
          "resultFormat": "saved_result",
          "time": "2026-10-31T01:28:00.000Z",
          "success": true,
          "result": "{\n  \"status\": \"success\",\n  \"parent_process\": \"WINWORD.EXE\",\n  \"process\": \"powershell.exe\",\n  \"sha256\": \"46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af\",\n  \"host\": \"FIN-LAPTOP-07\"\n}"
        }
      ],
      "graphs": {},
      "artifacts": [
        {
          "id": "showcase-run-01-artifact-1",
          "kind": "tool_result",
          "event_id": "showcase-run-01-query-1-event",
          "sha256": "8c2824bb238f52a34eab552b7559cda1124a3cd0a0f253f4b15b8f2e8883c445",
          "size_bytes": 1150,
          "created_at": "2026-10-31T01:27:00.000Z"
        },
        {
          "id": "showcase-run-01-artifact-2",
          "kind": "tool_result",
          "event_id": "showcase-run-01-query-2-event",
          "sha256": "c13d2a5c9ccc53341dcf279b4a01fc723f9c14e259396016497d70b6878a93af",
          "size_bytes": 177,
          "created_at": "2026-10-31T01:28:00.000Z"
        },
        {
          "id": "showcase-run-01-report",
          "kind": "report_md",
          "event_id": "showcase-run-01-report",
          "sha256": "5c3417d5d5e9c5acb9adcbb9427232f5d69ec69d6441d921d4db37741663aad2",
          "size_bytes": 643,
          "created_at": "2026-10-31T01:32:00.000Z"
        }
      ],
      "artifactBodies": {
        "showcase-run-01-artifact-1": {
          "mode": "full",
          "format": "json",
          "content": {
            "records": [
              {
                "alert_id": "showcase-alert-01-1",
                "time": "2026-10-31T01:10:00.000Z",
                "hostnames": [
                  "FIN-LAPTOP-07"
                ],
                "username": "lin.chen@contoso.com",
                "description": "邮件检测记录与终端文件打开记录命中同一附件哈希，账号为 lin.chen@contoso.com。"
              },
              {
                "alert_id": "showcase-alert-01-2",
                "time": "2026-10-31T01:14:00.000Z",
                "hostnames": [
                  "FIN-LAPTOP-07"
                ],
                "username": "lin.chen@contoso.com",
                "description": "父进程 WINWORD.EXE 启动 powershell.exe；已保存进程标识、启动时间和文件哈希。"
              },
              {
                "alert_id": "showcase-alert-01-3",
                "time": "2026-10-31T01:18:00.000Z",
                "hostnames": [
                  "FIN-LAPTOP-07"
                ],
                "username": "lin.chen@contoso.com",
                "description": "终端审计记录出现对凭据进程的读取访问；需结合进程关系与操作授权研判。"
              },
              {
                "alert_id": "showcase-alert-01-4",
                "time": "2026-10-31T01:22:00.000Z",
                "hostnames": [
                  "FIN-LAPTOP-07"
                ],
                "username": "lin.chen@contoso.com",
                "description": "FIN-LAPTOP-07 与 203.0.113.77:443 建立连接，记录了时间、进程和收发字节。"
              }
            ],
            "scope": {
              "hostnames": [
                "FIN-LAPTOP-07"
              ],
              "username": "lin.chen@contoso.com",
              "start": "2026-10-31T01:10:00Z",
              "end": "2026-10-31T01:26:00.000Z"
            }
          }
        },
        "showcase-run-01-artifact-2": {
          "mode": "full",
          "format": "json",
          "content": {
            "status": "success",
            "parent_process": "WINWORD.EXE",
            "process": "powershell.exe",
            "sha256": "46b04f3698c94ad525b8cfc9b059a952519764ba8faf9d03d0e6feab16f6d8af",
            "host": "FIN-LAPTOP-07"
          }
        },
        "showcase-run-01-report": {
          "mode": "full",
          "format": "markdown",
          "content": "# 财务终端钓鱼附件与脚本外联\n\n## 输入范围\n告警 showcase-alert-01-1；关联事件 showcase-incident-01。其余成员记录仅作查询上下文。\n\n## 调查发现\n邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。\n\n输入范围的材料已齐备，处置尚待审批。\n\n## 查询依据\n- showcase-run-01-query-1：asset_activity，已取得记录\n- showcase-run-01-query-2：process_and_file_context，已取得记录\n\n## 完整性\n本次输入范围的材料完整，事件仍处理中。\n\n## 建议与执行\n核对业务影响后隔离财务终端\n未执行真实响应。\n"
        }
      },
      "actions": [
        {
          "description": "核对业务影响后隔离财务终端",
          "target": "FIN-LAPTOP-07",
          "requires_approval": true,
          "rationale": "相关终端记录已齐备，隔离需确认业务影响。"
        }
      ],
      "executed": [],
      "report": "# 财务终端钓鱼附件与脚本外联\n\n## 输入范围\n告警 showcase-alert-01-1；关联事件 showcase-incident-01。其余成员记录仅作查询上下文。\n\n## 调查发现\n邮件附件、进程与网络记录可通过同一终端、账号及文件哈希相互核对。\n\n输入范围的材料已齐备，处置尚待审批。\n\n## 查询依据\n- showcase-run-01-query-1：asset_activity，已取得记录\n- showcase-run-01-query-2：process_and_file_context，已取得记录\n\n## 完整性\n本次输入范围的材料完整，事件仍处理中。\n\n## 建议与执行\n核对业务影响后隔离财务终端\n未执行真实响应。\n",
      "stop": ""
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-run-02",
      "title": "服务账号跨主机访问与归档上传自动处理",
      "alertIds": [
        "showcase-alert-02-1"
      ],
      "sourceCaseId": null,
      "status": "completed",
      "completion": "partial",
      "verdict": "needs_review",
      "triage": {
        "verdict": "needs_review",
        "confidence": 0.72,
        "auto_closed": false
      },
      "started": "2026-10-31T03:16:00.000Z",
      "ended": "2026-10-31T03:22:00.000Z",
      "input": {
        "id": "showcase-alert-02-1",
        "tenant_id": "showcase-contoso",
        "source": "身份与目录检测",
        "source_ref": "SEC-20261031-21",
        "event_time": "2026-10-31T03:00:00.000Z",
        "title": "服务账号从跳板机访问应用服务器",
        "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。",
        "severity": "中",
        "status": "New",
        "incident_id": "showcase-incident-02",
        "case_id": null,
        "mitre_tactics": [
          "横向移动"
        ],
        "mitre_techniques": [
          "T1021.002"
        ],
        "rule_id": "RULE-21",
        "entities": [
          {
            "id": "showcase-service",
            "type": "user",
            "name": "svc.reports@contoso.com"
          },
          {
            "id": "showcase-jump",
            "type": "device",
            "name": "OPS-JUMP-01"
          },
          {
            "id": "showcase-app",
            "type": "device",
            "name": "APP-SRV-02"
          }
        ],
        "raw_event": {
          "event_id": "evt-2-1",
          "hostname": "OPS-JUMP-01",
          "username": "svc.reports@contoso.com",
          "observation": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。",
          "approval_reference": null
        },
        "last": "2026-10-31T03:01:00.000Z"
      },
      "findings": [
        "已确认同一服务账号跨主机访问和归档操作。",
        "缺少完整传输清单，不能确认外传内容及范围。"
      ],
      "steps": [
        {
          "id": "showcase-run-02-triage",
          "seq": 1,
          "kind": "triage_verdict",
          "name": "自动分诊",
          "time": "2026-10-31T03:16:00.000Z",
          "summary": "进入自动调查核查材料",
          "payload": {
            "verdict": "needs_review",
            "confidence": 0.72,
            "auto_closed": false
          }
        },
        {
          "id": "showcase-run-02-query-1-event",
          "seq": 2,
          "kind": "tool_call",
          "name": "调查工具",
          "time": "2026-10-31T03:17:00.000Z",
          "summary": "asset_activity：已取得记录",
          "payload": {
            "tool": "asset_activity",
            "args": {
              "hostnames": [
                "OPS-JUMP-01",
                "APP-SRV-02",
                "FILE-SRV-03"
              ],
              "username": "svc.reports@contoso.com",
              "start": "2026-10-31T03:00:00Z",
              "end": "2026-10-31T03:16:00.000Z"
            },
            "result": {
              "records": [
                {
                  "alert_id": "showcase-alert-02-1",
                  "time": "2026-10-31T03:00:00.000Z",
                  "hostnames": [
                    "OPS-JUMP-01",
                    "APP-SRV-02"
                  ],
                  "username": "svc.reports@contoso.com",
                  "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。"
                },
                {
                  "alert_id": "showcase-alert-02-2",
                  "time": "2026-10-31T03:04:00.000Z",
                  "hostnames": [
                    "APP-SRV-02",
                    "FILE-SRV-03"
                  ],
                  "username": "svc.reports@contoso.com",
                  "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。"
                },
                {
                  "alert_id": "showcase-alert-02-3",
                  "time": "2026-10-31T03:08:00.000Z",
                  "hostnames": [
                    "FILE-SRV-03"
                  ],
                  "username": "svc.reports@contoso.com",
                  "description": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。"
                },
                {
                  "alert_id": "showcase-alert-02-4",
                  "time": "2026-10-31T03:12:00.000Z",
                  "hostnames": [
                    "FILE-SRV-03"
                  ],
                  "username": "svc.reports@contoso.com",
                  "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。"
                }
              ],
              "scope": {
                "hostnames": [
                  "OPS-JUMP-01",
                  "APP-SRV-02",
                  "FILE-SRV-03"
                ],
                "username": "svc.reports@contoso.com",
                "start": "2026-10-31T03:00:00Z",
                "end": "2026-10-31T03:16:00.000Z"
              }
            }
          }
        },
        {
          "id": "showcase-run-02-query-2-event",
          "seq": 3,
          "kind": "tool_call",
          "name": "调查工具",
          "time": "2026-10-31T03:18:00.000Z",
          "summary": "transfer_inventory：资料不可用",
          "payload": {
            "tool": "transfer_inventory",
            "args": {
              "alert_id": "showcase-alert-02-1",
              "start": "2026-10-31T03:00:00Z",
              "end": "2026-10-31T03:16:00.000Z"
            },
            "result": {
              "status": "unavailable",
              "reason": "未取得完整文件传输清单"
            }
          }
        },
        {
          "id": "showcase-run-02-recon",
          "seq": 4,
          "kind": "recon",
          "name": "侦察分析",
          "time": "2026-10-31T03:19:00.000Z",
          "summary": "保存输入范围内的材料与引用",
          "adopted": {
            "summary": "按当前输入及可用证据交付",
            "evidence_ids": [
              "showcase-run-02-query-1",
              "showcase-run-02-query-2"
            ]
          }
        },
        {
          "id": "showcase-run-02-forensic",
          "seq": 5,
          "kind": "forensic",
          "name": "取证分析",
          "time": "2026-10-31T03:20:00.000Z",
          "summary": "已确认同一服务账号跨主机访问和归档操作。；缺少完整传输清单，不能确认外传内容及范围。",
          "adopted": {
            "summary": "已确认同一服务账号跨主机访问和归档操作。；缺少完整传输清单，不能确认外传内容及范围。",
            "evidence_ids": [
              "showcase-run-02-query-1",
              "showcase-run-02-query-2"
            ]
          }
        },
        {
          "id": "showcase-run-02-responder",
          "seq": 6,
          "kind": "responder",
          "name": "响应分析",
          "time": "2026-10-31T03:21:00.000Z",
          "summary": "形成建议，未执行响应",
          "adopted": {
            "summary": "按当前输入及可用证据交付",
            "evidence_ids": [
              "showcase-run-02-query-1",
              "showcase-run-02-query-2"
            ]
          }
        },
        {
          "id": "showcase-run-02-report",
          "seq": 7,
          "kind": "report",
          "name": "报告整理",
          "time": "2026-10-31T03:22:00.000Z",
          "summary": "保存输入范围内的材料与引用",
          "adopted": {
            "summary": "按当前输入及可用证据交付",
            "evidence_ids": [
              "showcase-run-02-query-1",
              "showcase-run-02-query-2"
            ]
          }
        }
      ],
      "tools": [
        {
          "id": "showcase-run-02-query-1",
          "name": "asset_activity",
          "args": {
            "hostnames": [
              "OPS-JUMP-01",
              "APP-SRV-02",
              "FILE-SRV-03"
            ],
            "username": "svc.reports@contoso.com",
            "start": "2026-10-31T03:00:00Z",
            "end": "2026-10-31T03:16:00.000Z"
          },
          "resultFormat": "saved_result",
          "time": "2026-10-31T03:17:00.000Z",
          "success": true,
          "result": "{\n  \"records\": [\n    {\n      \"alert_id\": \"showcase-alert-02-1\",\n      \"time\": \"2026-10-31T03:00:00.000Z\",\n      \"hostnames\": [\n        \"OPS-JUMP-01\",\n        \"APP-SRV-02\"\n      ],\n      \"username\": \"svc.reports@contoso.com\",\n      \"description\": \"服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-02-2\",\n      \"time\": \"2026-10-31T03:04:00.000Z\",\n      \"hostnames\": [\n        \"APP-SRV-02\",\n        \"FILE-SRV-03\"\n      ],\n      \"username\": \"svc.reports@contoso.com\",\n      \"description\": \"应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-02-3\",\n      \"time\": \"2026-10-31T03:08:00.000Z\",\n      \"hostnames\": [\n        \"FILE-SRV-03\"\n      ],\n      \"username\": \"svc.reports@contoso.com\",\n      \"description\": \"文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。\"\n    },\n    {\n      \"alert_id\": \"showcase-alert-02-4\",\n      \"time\": \"2026-10-31T03:12:00.000Z\",\n      \"hostnames\": [\n        \"FILE-SRV-03\"\n      ],\n      \"username\": \"svc.reports@contoso.com\",\n      \"description\": \"上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。\"\n    }\n  ],\n  \"scope\": {\n    \"hostnames\": [\n      \"OPS-JUMP-01\",\n      \"APP-SRV-02\",\n      \"FILE-SRV-03\"\n    ],\n    \"username\": \"svc.reports@contoso.com\",\n    \"start\": \"2026-10-31T03:00:00Z\",\n    \"end\": \"2026-10-31T03:16:00.000Z\"\n  }\n}"
        },
        {
          "id": "showcase-run-02-query-2",
          "name": "transfer_inventory",
          "args": {
            "alert_id": "showcase-alert-02-1",
            "start": "2026-10-31T03:00:00Z",
            "end": "2026-10-31T03:16:00.000Z"
          },
          "resultFormat": "saved_result",
          "time": "2026-10-31T03:18:00.000Z",
          "success": false,
          "result": "{\n  \"status\": \"unavailable\",\n  \"reason\": \"未取得完整文件传输清单\"\n}"
        }
      ],
      "graphs": {},
      "artifacts": [
        {
          "id": "showcase-run-02-artifact-1",
          "kind": "tool_result",
          "event_id": "showcase-run-02-query-1-event",
          "sha256": "4904732453d7090d6abcc518d62ebfbe2087c449e9ce75c2994aa467b1d7af93",
          "size_bytes": 1211,
          "created_at": "2026-10-31T03:17:00.000Z"
        },
        {
          "id": "showcase-run-02-artifact-2",
          "kind": "tool_result",
          "event_id": "showcase-run-02-query-2-event",
          "sha256": "820b96b2bef05e1b2cc60c09838fdf42cac2551fdb6a8805d807cfeaae13b830",
          "size_bytes": 69,
          "created_at": "2026-10-31T03:18:00.000Z"
        },
        {
          "id": "showcase-run-02-report",
          "kind": "report_md",
          "event_id": "showcase-run-02-report",
          "sha256": "1001b725bd590d87e8728a116318178e421447fae508cdfa7f3e17bee2eaad0d",
          "size_bytes": 598,
          "created_at": "2026-10-31T03:22:00.000Z"
        }
      ],
      "artifactBodies": {
        "showcase-run-02-artifact-1": {
          "mode": "full",
          "format": "json",
          "content": {
            "records": [
              {
                "alert_id": "showcase-alert-02-1",
                "time": "2026-10-31T03:00:00.000Z",
                "hostnames": [
                  "OPS-JUMP-01",
                  "APP-SRV-02"
                ],
                "username": "svc.reports@contoso.com",
                "description": "服务账号从 OPS-JUMP-01 发起到 APP-SRV-02 的远程访问，已记录两端主机和账号。"
              },
              {
                "alert_id": "showcase-alert-02-2",
                "time": "2026-10-31T03:04:00.000Z",
                "hostnames": [
                  "APP-SRV-02",
                  "FILE-SRV-03"
                ],
                "username": "svc.reports@contoso.com",
                "description": "应用服务器使用同一服务账号批量读取 FILE-SRV-03 上的报表目录。"
              },
              {
                "alert_id": "showcase-alert-02-3",
                "time": "2026-10-31T03:08:00.000Z",
                "hostnames": [
                  "FILE-SRV-03"
                ],
                "username": "svc.reports@contoso.com",
                "description": "文件审计记录生成 finance-export.zip，记录了大小与哈希，内容清单尚待补齐。"
              },
              {
                "alert_id": "showcase-alert-02-4",
                "time": "2026-10-31T03:12:00.000Z",
                "hostnames": [
                  "FILE-SRV-03"
                ],
                "username": "svc.reports@contoso.com",
                "description": "上传进程连接 198.51.100.42:443；连接元数据存在，但不能单凭字节数确定上传了哪些文件。"
              }
            ],
            "scope": {
              "hostnames": [
                "OPS-JUMP-01",
                "APP-SRV-02",
                "FILE-SRV-03"
              ],
              "username": "svc.reports@contoso.com",
              "start": "2026-10-31T03:00:00Z",
              "end": "2026-10-31T03:16:00.000Z"
            }
          }
        },
        "showcase-run-02-artifact-2": {
          "mode": "full",
          "format": "json",
          "content": {
            "status": "unavailable",
            "reason": "未取得完整文件传输清单"
          }
        },
        "showcase-run-02-report": {
          "mode": "full",
          "format": "markdown",
          "content": "# 服务账号跨主机访问与归档上传\n\n## 输入范围\n告警 showcase-alert-02-1；关联事件 showcase-incident-02。其余成员记录仅作查询上下文。\n\n## 调查发现\n已确认同一服务账号跨主机访问和归档操作。\n\n缺少完整传输清单，不能确认外传内容及范围。\n\n## 查询依据\n- showcase-run-02-query-1：asset_activity，已取得记录\n- showcase-run-02-query-2：transfer_inventory，资料不可用\n\n## 完整性\n部分交付，缺少文件传输清单。\n\n## 建议与执行\n补查文件传输清单并核对授权\n未执行真实响应。\n"
        }
      },
      "actions": [
        {
          "description": "补查文件传输清单并核对授权",
          "target": "OPS-JUMP-01",
          "requires_approval": false,
          "rationale": "连接记录不足以确认具体传输对象。"
        }
      ],
      "executed": [],
      "report": "# 服务账号跨主机访问与归档上传\n\n## 输入范围\n告警 showcase-alert-02-1；关联事件 showcase-incident-02。其余成员记录仅作查询上下文。\n\n## 调查发现\n已确认同一服务账号跨主机访问和归档操作。\n\n缺少完整传输清单，不能确认外传内容及范围。\n\n## 查询依据\n- showcase-run-02-query-1：asset_activity，已取得记录\n- showcase-run-02-query-2：transfer_inventory，资料不可用\n\n## 完整性\n部分交付，缺少文件传输清单。\n\n## 建议与执行\n补查文件传输清单并核对授权\n未执行真实响应。\n",
      "stop": "文件传输清单不可用，保留部分结果供人工接手。"
    },
    {
      "fixture": true,
      "recorded": false,
      "fixtureSet": "incident-alert-20261031",
      "sourceEnvironment": "design-showcase",
      "sourceTenantId": "showcase-contoso",
      "id": "showcase-run-03",
      "title": "已核实的授权备份与维护活动自动处理",
      "alertIds": [
        "showcase-alert-03-1"
      ],
      "sourceCaseId": null,
      "status": "completed",
      "completion": "not_escalated",
      "verdict": "benign_true_positive",
      "triage": {
        "verdict": "benign_true_positive",
        "confidence": 0.96,
        "auto_closed": false
      },
      "started": "2026-10-29T02:16:00.000Z",
      "ended": "2026-10-29T02:22:00.000Z",
      "input": {
        "id": "showcase-alert-03-1",
        "tenant_id": "showcase-contoso",
        "source": "终端检测与响应",
        "source_ref": "SEC-20261031-31",
        "event_time": "2026-10-29T02:00:00.000Z",
        "title": "备份服务器在维护窗口运行脚本",
        "description": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。",
        "severity": "低",
        "status": "New",
        "incident_id": "showcase-incident-03",
        "case_id": "showcase-case-03",
        "mitre_tactics": [
          "执行"
        ],
        "mitre_techniques": [
          "T1059.001"
        ],
        "rule_id": "RULE-31",
        "entities": [
          {
            "id": "showcase-backup",
            "type": "device",
            "name": "BACKUP-SRV-01"
          },
          {
            "id": "showcase-operator",
            "type": "user",
            "name": "backup.ops@contoso.com"
          },
          {
            "id": "showcase-automation",
            "type": "robot",
            "name": "Backup Validation Assistant"
          }
        ],
        "raw_event": {
          "event_id": "evt-3-1",
          "hostname": "BACKUP-SRV-01",
          "username": "backup.ops@contoso.com",
          "observation": "脚本路径和签名与批准的备份任务一致，执行账号为 backup.ops@contoso.com。",
          "approval_reference": "CHG-2026-1031"
        },
        "last": "2026-10-29T02:01:00.000Z"
      },
      "findings": [
        "维护工单、账号、执行窗口与备份目标匹配，判为预期活动。"
      ],
      "steps": [
        {
          "id": "showcase-run-03-triage",
          "seq": 1,
          "kind": "triage_verdict",
          "name": "自动分诊",
          "time": "2026-10-29T02:16:00.000Z",
          "summary": "符合批准的维护任务，未升级调查",
          "payload": {
            "verdict": "benign_true_positive",
            "confidence": 0.96,
            "auto_closed": false
          }
        }
      ],
      "tools": [],
      "graphs": {},
      "artifacts": [],
      "artifactBodies": {},
      "actions": [],
      "executed": [],
      "report": null,
      "stop": "分诊判断为预期维护活动，未升级调查。"
    }
  ]
};
window.mergePageShowcases = function(store){
  const data=window.pageShowcaseData;
  for(const key of ['assets','alerts','incidents','cases','evidence','activities','comments']){
    store[key] ||= [];
    const known=new Set(store[key].map(row=>row.id));
    for(const row of data[key])if(!known.has(row.id)){store[key].push(structuredClone(row));known.add(row.id);}
  }
  store.designRelations ||= [];
  const known=new Set(store.designRelations.map(row=>row.id));
  for(const row of data.relations)if(!known.has(row.id)){store.designRelations.push(structuredClone(row));known.add(row.id);}
};
