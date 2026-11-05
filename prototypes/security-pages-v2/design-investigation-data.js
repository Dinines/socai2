/* Design-only material. No actual queries, model calls or executed responses. */
'use strict';
window.designInvestigationRuns = [
  {
    "id": "INV-20261024-001",
    "title": "身份与终端活动调查",
    "alertIds": [
      "da63896004100",
      "da63896004102",
      "da63896004103"
    ],
    "completion": "completed",
    "status": "completed",
    "remediation": "待审批",
    "findings": [
      "同一账户的登录、终端脚本启动和文件检测记录在所选时间窗内出现。",
      "进程记录显示 WINWORD.EXE 启动 powershell.exe；文件元数据包含未签名可执行文件。",
      "共享账户与设备构成关联线索，图中关系不单独证明攻击因果。",
      "已完成本次输入范围的材料核对，处置建议等待审批。"
    ],
    "steps": [
      {
        "id": "INV-20261024-001-event-query-1",
        "seq": 1,
        "kind": "tool_call",
        "name": "调查工具",
        "time": "2026-10-24T01:13:00.000Z",
        "summary": "identity_signins：已取得记录",
        "payload": {
          "tool_id": "INV-20261024-001-query-1",
          "name": "identity_signins",
          "arguments": {
            "user": "hcook@contoso.com",
            "start": "2026-10-24T00:30:00Z",
            "end": "2026-10-24T01:10:00Z"
          },
          "result": {
            "records": [
              {
                "time": "2026-10-24T00:51:00Z",
                "user": "hcook@contoso.com",
                "source_ip": "203.0.113.50",
                "result": "success",
                "device": "cont-adrianbrad"
              }
            ],
            "coverage": "所选账户及时间窗内登录记录。"
          }
        }
      },
      {
        "id": "INV-20261024-001-event-query-2",
        "seq": 2,
        "kind": "tool_call",
        "name": "调查工具",
        "time": "2026-10-24T01:14:00.000Z",
        "summary": "process_activity：已取得记录",
        "payload": {
          "tool_id": "INV-20261024-001-query-2",
          "name": "process_activity",
          "arguments": {
            "hostname": "cont-adrianbrad",
            "start": "2026-10-24T00:50:00Z",
            "end": "2026-10-24T01:10:00Z"
          },
          "result": {
            "records": [
              {
                "time": "2026-10-24T00:58:00Z",
                "hostname": "cont-adrianbrad",
                "user": "hcook@contoso.com",
                "process": "powershell.exe",
                "parent": "WINWORD.EXE",
                "command_line": "powershell.exe -NoProfile -EncodedCommand VwByAGkAdABlAC0ATwB1AHQAcAB1AHQAIAAnAHIAZQB2AGkAZQB3ACcA"
              }
            ],
            "coverage": "该终端的进程启动记录；命令行不证明脚本全部行为。"
          }
        }
      },
      {
        "id": "INV-20261024-001-event-query-3",
        "seq": 3,
        "kind": "tool_call",
        "name": "调查工具",
        "time": "2026-10-24T01:15:00.000Z",
        "summary": "file_metadata：已取得记录",
        "payload": {
          "tool_id": "INV-20261024-001-query-3",
          "name": "file_metadata",
          "arguments": {
            "hostname": "cont-adrianbrad",
            "filename": "invoice_2026.pdf.exe"
          },
          "result": {
            "records": [
              {
                "filename": "invoice_2026.pdf.exe",
                "sha256": "b604e516f760ed4b3bf2cc96a21d3c746d6f8a808c5713fb4d142c01d487ed0a",
                "signature": "unsigned",
                "detection": "Trojan:Win32/Example"
              }
            ],
            "coverage": "文件检测与元数据；未据此推断文件外传。"
          }
        }
      },
      {
        "id": "INV-20261024-001-event-stage-1",
        "seq": 4,
        "kind": "recon",
        "name": "侦察分析",
        "time": "2026-10-24T01:16:00.000Z",
        "summary": "核对输入、账户与设备范围",
        "adopted": {
          "summary": "范围限定为本次输入，不自动扩大到所有 Case 成员。",
          "evidence_ids": [
            "INV-20261024-001-query-1",
            "INV-20261024-001-query-2",
            "INV-20261024-001-query-3"
          ]
        }
      },
      {
        "id": "INV-20261024-001-event-stage-2",
        "seq": 5,
        "kind": "forensic",
        "name": "取证分析",
        "time": "2026-10-24T01:17:00.000Z",
        "summary": "同一账户的登录、终端脚本启动和文件检测记录在所选时间窗内出现。",
        "adopted": {
          "summary": "同一账户的登录、终端脚本启动和文件检测记录在所选时间窗内出现。；进程记录显示 WINWORD.EXE 启动 powershell.exe；文件元数据包含未签名可执行文件。；共享账户与设备构成关联线索，图中关系不单独证明攻击因果。；已完成本次输入范围的材料核对，处置建议等待审批。",
          "evidence_ids": [
            "INV-20261024-001-query-1",
            "INV-20261024-001-query-2",
            "INV-20261024-001-query-3"
          ]
        }
      },
      {
        "id": "INV-20261024-001-event-stage-3",
        "seq": 6,
        "kind": "responder",
        "name": "响应分析",
        "time": "2026-10-24T01:18:00.000Z",
        "summary": "形成建议，执行与审批独立跟踪",
        "adopted": {
          "summary": "复核并撤销可疑账户会话；审核终端隔离及可疑文件处置",
          "evidence_ids": [
            "INV-20261024-001-query-1",
            "INV-20261024-001-query-2",
            "INV-20261024-001-query-3"
          ]
        }
      },
      {
        "id": "INV-20261024-001-event-stage-4",
        "seq": 7,
        "kind": "report",
        "name": "报告整理",
        "time": "2026-10-24T01:19:00.000Z",
        "summary": "保存本次结果及材料引用",
        "adopted": {
          "summary": "报告引用本次查询及范围限制。",
          "evidence_ids": [
            "INV-20261024-001-query-1",
            "INV-20261024-001-query-2",
            "INV-20261024-001-query-3"
          ]
        }
      }
    ],
    "recorded": false,
    "fixture": true,
    "sourceEnvironment": "design",
    "sourceTenantId": "design",
    "sourceCaseId": "17420",
    "verdict": "reviewed",
    "started": "2026-10-24T01:12:00.000Z",
    "ended": "2026-10-24T01:19:00.000Z",
    "input": {
      "case_id": "17420",
      "alerts": [
        {
          "id": "da63896004100",
          "title": "Authentication request from AiTM-related phishing page",
          "severity": "高",
          "status": "In progress",
          "classification": "Not set",
          "owner": "未分配",
          "source": "Microsoft Defender for Office 365",
          "category": "初始访问",
          "tags": [
            "AiTM attack",
            "Credential Phish"
          ],
          "investigation": "In progress",
          "first": "2026-10-24T00:40:00.000Z",
          "last": "2026-10-24T00:43:00.000Z",
          "incidentId": "262144",
          "entityIds": [
            "u1",
            "m1",
            "ip1"
          ],
          "description": "Authentication request from AiTM-related phishing page。安全检测发现与当前事件相关的活动，请结合实体上下文、事件时间线和关联证据进一步评估。",
          "comments": []
        },
        {
          "id": "da63896004102",
          "title": "Unfamiliar sign-in properties",
          "severity": "中",
          "status": "New",
          "classification": "Not set",
          "owner": "Alex Wilber",
          "source": "Microsoft Entra ID Protection",
          "category": "初始访问",
          "tags": [],
          "investigation": "Pending",
          "first": "2026-10-24T00:52:00.000Z",
          "last": "2026-10-24T00:55:00.000Z",
          "incidentId": "262144",
          "entityIds": [
            "u1",
            "m1",
            "ip1"
          ],
          "description": "Unfamiliar sign-in properties。安全检测发现与当前事件相关的活动，请结合实体上下文、事件时间线和关联证据进一步评估。",
          "comments": []
        },
        {
          "id": "da63896004103",
          "title": "检测到可疑的 PowerShell 命令行",
          "severity": "高",
          "status": "New",
          "classification": "Not set",
          "owner": "未分配",
          "source": "Microsoft Defender for Endpoint",
          "category": "执行",
          "tags": [],
          "investigation": "In progress",
          "first": "2026-10-24T00:58:00.000Z",
          "last": "2026-10-24T01:01:00.000Z",
          "incidentId": "262144",
          "entityIds": [
            "d1",
            "u1",
            "ip1",
            "f1"
          ],
          "description": "检测到可疑的 PowerShell 命令行。安全检测发现与当前事件相关的活动，请结合实体上下文、事件时间线和关联证据进一步评估。",
          "comments": []
        }
      ]
    },
    "tools": [
      {
        "id": "INV-20261024-001-query-1",
        "name": "identity_signins",
        "args": {
          "user": "hcook@contoso.com",
          "start": "2026-10-24T00:30:00Z",
          "end": "2026-10-24T01:10:00Z"
        },
        "time": "2026-10-24T01:13:00.000Z",
        "success": true,
        "resultFormat": "saved_result",
        "result": "{\n  \"records\": [\n    {\n      \"time\": \"2026-10-24T00:51:00Z\",\n      \"user\": \"hcook@contoso.com\",\n      \"source_ip\": \"203.0.113.50\",\n      \"result\": \"success\",\n      \"device\": \"cont-adrianbrad\"\n    }\n  ],\n  \"coverage\": \"所选账户及时间窗内登录记录。\"\n}"
      },
      {
        "id": "INV-20261024-001-query-2",
        "name": "process_activity",
        "args": {
          "hostname": "cont-adrianbrad",
          "start": "2026-10-24T00:50:00Z",
          "end": "2026-10-24T01:10:00Z"
        },
        "time": "2026-10-24T01:14:00.000Z",
        "success": true,
        "resultFormat": "saved_result",
        "result": "{\n  \"records\": [\n    {\n      \"time\": \"2026-10-24T00:58:00Z\",\n      \"hostname\": \"cont-adrianbrad\",\n      \"user\": \"hcook@contoso.com\",\n      \"process\": \"powershell.exe\",\n      \"parent\": \"WINWORD.EXE\",\n      \"command_line\": \"powershell.exe -NoProfile -EncodedCommand VwByAGkAdABlAC0ATwB1AHQAcAB1AHQAIAAnAHIAZQB2AGkAZQB3ACcA\"\n    }\n  ],\n  \"coverage\": \"该终端的进程启动记录；命令行不证明脚本全部行为。\"\n}"
      },
      {
        "id": "INV-20261024-001-query-3",
        "name": "file_metadata",
        "args": {
          "hostname": "cont-adrianbrad",
          "filename": "invoice_2026.pdf.exe"
        },
        "time": "2026-10-24T01:15:00.000Z",
        "success": true,
        "resultFormat": "saved_result",
        "result": "{\n  \"records\": [\n    {\n      \"filename\": \"invoice_2026.pdf.exe\",\n      \"sha256\": \"b604e516f760ed4b3bf2cc96a21d3c746d6f8a808c5713fb4d142c01d487ed0a\",\n      \"signature\": \"unsigned\",\n      \"detection\": \"Trojan:Win32/Example\"\n    }\n  ],\n  \"coverage\": \"文件检测与元数据；未据此推断文件外传。\"\n}"
      }
    ],
    "graphs": {
      "attack_chain": {
        "status": "success",
        "source": "design_fixture",
        "queried_at": "2026-10-24T01:16:00.000Z",
        "data": {
          "case_id": "17420",
          "seed_alert_id": "da63896004100",
          "window": "40m",
          "chain": [
            {
              "alert_id": "da63896004102",
              "title": "Unfamiliar sign-in properties",
              "event_time": "2026-10-24T00:52:00.000Z",
              "severity": "中",
              "shared_entities": [
                {
                  "kind": "Entity",
                  "value": "hcook@contoso.com"
                },
                {
                  "kind": "Entity",
                  "value": "hcook@contoso.com"
                },
                {
                  "kind": "Entity",
                  "value": "203.0.113.50"
                }
              ],
              "distance": 1
            },
            {
              "alert_id": "da63896004103",
              "title": "检测到可疑的 PowerShell 命令行",
              "event_time": "2026-10-24T00:58:00.000Z",
              "severity": "高",
              "shared_entities": [
                {
                  "kind": "Entity",
                  "value": "hcook@contoso.com"
                },
                {
                  "kind": "Entity",
                  "value": "203.0.113.50"
                }
              ],
              "distance": 1
            }
          ]
        }
      },
      "attack_path": {
        "status": "success",
        "source": "design_fixture",
        "queried_at": "2026-10-24T01:16:00.000Z",
        "data": {
          "nodes": [
            {
              "id": "da63896004100",
              "label": "Alert",
              "properties": {
                "title": "Authentication request from AiTM-related phishing page",
                "source_alert_id": "da63896004100"
              }
            },
            {
              "id": "da63896004102",
              "label": "Alert",
              "properties": {
                "title": "Unfamiliar sign-in properties",
                "source_alert_id": "da63896004102"
              }
            },
            {
              "id": "da63896004103",
              "label": "Alert",
              "properties": {
                "title": "检测到可疑的 PowerShell 命令行",
                "source_alert_id": "da63896004103"
              }
            },
            {
              "id": "u1",
              "label": "User",
              "properties": {
                "name": "hcook@contoso.com"
              }
            },
            {
              "id": "m1",
              "label": "Entity",
              "properties": {
                "name": "hcook@contoso.com"
              }
            },
            {
              "id": "ip1",
              "label": "IOC",
              "properties": {
                "name": "203.0.113.50"
              }
            },
            {
              "id": "d1",
              "label": "Host",
              "properties": {
                "name": "cont-adrianbrad"
              }
            },
            {
              "id": "f1",
              "label": "Entity",
              "properties": {
                "name": "invoice_2026.pdf.exe"
              }
            }
          ],
          "edges": [
            {
              "source": "da63896004100",
              "target": "u1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004100",
              "target": "m1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004100",
              "target": "ip1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004102",
              "target": "u1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004102",
              "target": "m1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004102",
              "target": "ip1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004103",
              "target": "d1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004103",
              "target": "u1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004103",
              "target": "ip1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004103",
              "target": "f1",
              "type": "OBSERVED_WITH"
            }
          ]
        }
      },
      "alert_graph": {
        "status": "success",
        "source": "design_fixture",
        "queried_at": "2026-10-24T01:16:00.000Z",
        "data": {
          "neighbors": {
            "neighbor_count": 5,
            "neighbors": [
              {
                "label": "user",
                "properties": {
                  "name": "hcook@contoso.com"
                },
                "rel_type": "OBSERVED_WITH"
              },
              {
                "label": "mailbox",
                "properties": {
                  "name": "hcook@contoso.com"
                },
                "rel_type": "OBSERVED_WITH"
              },
              {
                "label": "ip",
                "properties": {
                  "name": "203.0.113.50"
                },
                "rel_type": "OBSERVED_WITH"
              },
              {
                "label": "device",
                "properties": {
                  "name": "cont-adrianbrad"
                },
                "rel_type": "OBSERVED_WITH"
              },
              {
                "label": "file",
                "properties": {
                  "name": "invoice_2026.pdf.exe"
                },
                "rel_type": "OBSERVED_WITH"
              }
            ]
          },
          "blast_radius": {
            "total_affected": 5,
            "hops": 1
          }
        }
      }
    },
    "artifacts": [
      {
        "id": "INV-20261024-001-artifact-1",
        "kind": "tool_result",
        "event_id": "INV-20261024-001-event-query-1",
        "size_bytes": 201,
        "sha256": "6c1363ed9dfca46aeca2b3b5fd39f8cfd8a77334cec49a5ef29a88b87bf121b6",
        "created_at": "2026-10-24T01:19:00.000Z"
      },
      {
        "id": "INV-20261024-001-artifact-2",
        "kind": "tool_result",
        "event_id": "INV-20261024-001-event-query-2",
        "size_bytes": 353,
        "sha256": "ba00478ae7ef5cf81e17388326391c0d77330aae6714d10166cd0073e369f29d",
        "created_at": "2026-10-24T01:19:00.000Z"
      },
      {
        "id": "INV-20261024-001-artifact-3",
        "kind": "tool_result",
        "event_id": "INV-20261024-001-event-query-3",
        "size_bytes": 254,
        "sha256": "f191150b7b1086aacfeb0fae1aac6a0db7223db0e890a0b3d9264cb3a75c8de6",
        "created_at": "2026-10-24T01:19:00.000Z"
      },
      {
        "id": "INV-20261024-001-artifact-4",
        "kind": "relationship_graph",
        "event_id": "INV-20261024-001-event-stage-2",
        "size_bytes": 2903,
        "sha256": "cecc40d71578378be96494f1db64f7bef4a865c3c079c49a8ed945c6954fcf9b",
        "created_at": "2026-10-24T01:19:00.000Z"
      },
      {
        "id": "INV-20261024-001-artifact-5",
        "kind": "report_md",
        "event_id": "INV-20261024-001-event-stage-4",
        "size_bytes": 1054,
        "sha256": "d7cf409f35f1110263be3018352005874c9d3dbf56805c4fe72c3c77bdc55d46",
        "created_at": "2026-10-24T01:19:00.000Z"
      }
    ],
    "artifactBodies": {
      "INV-20261024-001-artifact-1": {
        "mode": "full",
        "format": "json",
        "content": {
          "records": [
            {
              "time": "2026-10-24T00:51:00Z",
              "user": "hcook@contoso.com",
              "source_ip": "203.0.113.50",
              "result": "success",
              "device": "cont-adrianbrad"
            }
          ],
          "coverage": "所选账户及时间窗内登录记录。"
        }
      },
      "INV-20261024-001-artifact-2": {
        "mode": "full",
        "format": "json",
        "content": {
          "records": [
            {
              "time": "2026-10-24T00:58:00Z",
              "hostname": "cont-adrianbrad",
              "user": "hcook@contoso.com",
              "process": "powershell.exe",
              "parent": "WINWORD.EXE",
              "command_line": "powershell.exe -NoProfile -EncodedCommand VwByAGkAdABlAC0ATwB1AHQAcAB1AHQAIAAnAHIAZQB2AGkAZQB3ACcA"
            }
          ],
          "coverage": "该终端的进程启动记录；命令行不证明脚本全部行为。"
        }
      },
      "INV-20261024-001-artifact-3": {
        "mode": "full",
        "format": "json",
        "content": {
          "records": [
            {
              "filename": "invoice_2026.pdf.exe",
              "sha256": "b604e516f760ed4b3bf2cc96a21d3c746d6f8a808c5713fb4d142c01d487ed0a",
              "signature": "unsigned",
              "detection": "Trojan:Win32/Example"
            }
          ],
          "coverage": "文件检测与元数据；未据此推断文件外传。"
        }
      },
      "INV-20261024-001-artifact-4": {
        "mode": "full",
        "format": "json",
        "content": {
          "attack_chain": {
            "status": "success",
            "source": "design_fixture",
            "queried_at": "2026-10-24T01:16:00.000Z",
            "data": {
              "case_id": "17420",
              "seed_alert_id": "da63896004100",
              "window": "40m",
              "chain": [
                {
                  "alert_id": "da63896004102",
                  "title": "Unfamiliar sign-in properties",
                  "event_time": "2026-10-24T00:52:00.000Z",
                  "severity": "中",
                  "shared_entities": [
                    {
                      "kind": "Entity",
                      "value": "hcook@contoso.com"
                    },
                    {
                      "kind": "Entity",
                      "value": "hcook@contoso.com"
                    },
                    {
                      "kind": "Entity",
                      "value": "203.0.113.50"
                    }
                  ],
                  "distance": 1
                },
                {
                  "alert_id": "da63896004103",
                  "title": "检测到可疑的 PowerShell 命令行",
                  "event_time": "2026-10-24T00:58:00.000Z",
                  "severity": "高",
                  "shared_entities": [
                    {
                      "kind": "Entity",
                      "value": "hcook@contoso.com"
                    },
                    {
                      "kind": "Entity",
                      "value": "203.0.113.50"
                    }
                  ],
                  "distance": 1
                }
              ]
            }
          },
          "attack_path": {
            "status": "success",
            "source": "design_fixture",
            "queried_at": "2026-10-24T01:16:00.000Z",
            "data": {
              "nodes": [
                {
                  "id": "da63896004100",
                  "label": "Alert",
                  "properties": {
                    "title": "Authentication request from AiTM-related phishing page",
                    "source_alert_id": "da63896004100"
                  }
                },
                {
                  "id": "da63896004102",
                  "label": "Alert",
                  "properties": {
                    "title": "Unfamiliar sign-in properties",
                    "source_alert_id": "da63896004102"
                  }
                },
                {
                  "id": "da63896004103",
                  "label": "Alert",
                  "properties": {
                    "title": "检测到可疑的 PowerShell 命令行",
                    "source_alert_id": "da63896004103"
                  }
                },
                {
                  "id": "u1",
                  "label": "User",
                  "properties": {
                    "name": "hcook@contoso.com"
                  }
                },
                {
                  "id": "m1",
                  "label": "Entity",
                  "properties": {
                    "name": "hcook@contoso.com"
                  }
                },
                {
                  "id": "ip1",
                  "label": "IOC",
                  "properties": {
                    "name": "203.0.113.50"
                  }
                },
                {
                  "id": "d1",
                  "label": "Host",
                  "properties": {
                    "name": "cont-adrianbrad"
                  }
                },
                {
                  "id": "f1",
                  "label": "Entity",
                  "properties": {
                    "name": "invoice_2026.pdf.exe"
                  }
                }
              ],
              "edges": [
                {
                  "source": "da63896004100",
                  "target": "u1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004100",
                  "target": "m1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004100",
                  "target": "ip1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004102",
                  "target": "u1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004102",
                  "target": "m1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004102",
                  "target": "ip1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004103",
                  "target": "d1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004103",
                  "target": "u1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004103",
                  "target": "ip1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004103",
                  "target": "f1",
                  "type": "OBSERVED_WITH"
                }
              ]
            }
          },
          "alert_graph": {
            "status": "success",
            "source": "design_fixture",
            "queried_at": "2026-10-24T01:16:00.000Z",
            "data": {
              "neighbors": {
                "neighbor_count": 5,
                "neighbors": [
                  {
                    "label": "user",
                    "properties": {
                      "name": "hcook@contoso.com"
                    },
                    "rel_type": "OBSERVED_WITH"
                  },
                  {
                    "label": "mailbox",
                    "properties": {
                      "name": "hcook@contoso.com"
                    },
                    "rel_type": "OBSERVED_WITH"
                  },
                  {
                    "label": "ip",
                    "properties": {
                      "name": "203.0.113.50"
                    },
                    "rel_type": "OBSERVED_WITH"
                  },
                  {
                    "label": "device",
                    "properties": {
                      "name": "cont-adrianbrad"
                    },
                    "rel_type": "OBSERVED_WITH"
                  },
                  {
                    "label": "file",
                    "properties": {
                      "name": "invoice_2026.pdf.exe"
                    },
                    "rel_type": "OBSERVED_WITH"
                  }
                ]
              },
              "blast_radius": {
                "total_affected": 5,
                "hops": 1
              }
            }
          }
        }
      },
      "INV-20261024-001-artifact-5": {
        "mode": "full",
        "format": "markdown",
        "content": "# 身份与终端活动调查\n\n## 范围\nCase 17420；输入告警 da63896004100、da63896004102、da63896004103。仅覆盖本次输入及查询窗口。\n\n## 结论\n同一账户的登录、终端脚本启动和文件检测记录在所选时间窗内出现。\n\n进程记录显示 WINWORD.EXE 启动 powershell.exe；文件元数据包含未签名可执行文件。\n\n共享账户与设备构成关联线索，图中关系不单独证明攻击因果。\n\n已完成本次输入范围的材料核对，处置建议等待审批。\n\n## 查询与依据\n- identity_signins：已取得记录；引用 INV-20261024-001-query-1\n- process_activity：已取得记录；引用 INV-20261024-001-query-2\n- file_metadata：已取得记录；引用 INV-20261024-001-query-3\n\n## 完整性\n本次输入范围内的调查材料已齐备。调查结束不代表案件关闭或处置完成。\n\n## 后续处理\n- 复核并撤销可疑账户会话（待审批）\n- 审核终端隔离及可疑文件处置（待审批）\n\n## 执行记录\n未执行隔离、封禁或会话撤销。\n"
      }
    },
    "actions": [
      {
        "description": "复核并撤销可疑账户会话",
        "target": "hcook@contoso.com",
        "requires_approval": true,
        "rationale": "登录记录与所选异常活动存在关联。"
      },
      {
        "description": "审核终端隔离及可疑文件处置",
        "target": "cont-adrianbrad",
        "requires_approval": true,
        "rationale": "进程与文件检测需结合业务影响审批。"
      }
    ],
    "executed": [],
    "report": "# 身份与终端活动调查\n\n## 范围\nCase 17420；输入告警 da63896004100、da63896004102、da63896004103。仅覆盖本次输入及查询窗口。\n\n## 结论\n同一账户的登录、终端脚本启动和文件检测记录在所选时间窗内出现。\n\n进程记录显示 WINWORD.EXE 启动 powershell.exe；文件元数据包含未签名可执行文件。\n\n共享账户与设备构成关联线索，图中关系不单独证明攻击因果。\n\n已完成本次输入范围的材料核对，处置建议等待审批。\n\n## 查询与依据\n- identity_signins：已取得记录；引用 INV-20261024-001-query-1\n- process_activity：已取得记录；引用 INV-20261024-001-query-2\n- file_metadata：已取得记录；引用 INV-20261024-001-query-3\n\n## 完整性\n本次输入范围内的调查材料已齐备。调查结束不代表案件关闭或处置完成。\n\n## 后续处理\n- 复核并撤销可疑账户会话（待审批）\n- 审核终端隔离及可疑文件处置（待审批）\n\n## 执行记录\n未执行隔离、封禁或会话撤销。\n",
    "stop": null,
    "depth": {
      "iterations": 3,
      "distinct_pivots": 3,
      "truncated": false,
      "pivots": [
        "identity_signins",
        "process_activity",
        "file_metadata"
      ],
      "unavailable_data": [],
      "coverage_notes": [
        "限定于输入告警的账户、设备及绝对时间窗口。"
      ],
      "strategy_id": "design-material-review"
    }
  },
  {
    "id": "INV-20261024-002",
    "title": "异常外联与数据传输调查",
    "alertIds": [
      "da63896004106",
      "da63896004108"
    ],
    "completion": "partial",
    "status": "completed",
    "remediation": "尚未处置",
    "findings": [
      "终端与 203.0.113.50:443 存在 TLS 连接，已取得连接时间和发送字节数。",
      "没有文件级传输清单，不能确认传输对象或完整范围。",
      "本次保留部分结果，等待补充资料后复核。"
    ],
    "steps": [
      {
        "id": "INV-20261024-002-event-query-1",
        "seq": 1,
        "kind": "tool_call",
        "name": "调查工具",
        "time": "2026-10-24T01:33:00.000Z",
        "summary": "network_connections：已取得记录",
        "payload": {
          "tool_id": "INV-20261024-002-query-1",
          "name": "network_connections",
          "arguments": {
            "hostname": "cont-adrianbrad",
            "start": "2026-10-24T01:00:00Z",
            "end": "2026-10-24T01:32:00Z"
          },
          "result": {
            "records": [
              {
                "time": "2026-10-24T01:16:00Z",
                "hostname": "cont-adrianbrad",
                "remote_ip": "203.0.113.50",
                "remote_port": 443,
                "protocol": "TLS",
                "bytes_sent": 20480
              }
            ],
            "coverage": "连接及流量元数据，不包含传输内容。"
          }
        }
      },
      {
        "id": "INV-20261024-002-event-query-2",
        "seq": 2,
        "kind": "tool_call",
        "name": "调查工具",
        "time": "2026-10-24T01:34:00.000Z",
        "summary": "transfer_inventory：资料不可用",
        "payload": {
          "tool_id": "INV-20261024-002-query-2",
          "name": "transfer_inventory",
          "arguments": {
            "hostname": "cont-adrianbrad",
            "destination": "203.0.113.50"
          },
          "result": {
            "status": "unavailable",
            "reason": "未取得文件级传输清单；不能根据连接字节数认定具体文件外泄。"
          }
        }
      },
      {
        "id": "INV-20261024-002-event-stage-1",
        "seq": 3,
        "kind": "recon",
        "name": "侦察分析",
        "time": "2026-10-24T01:35:00.000Z",
        "summary": "核对输入、账户与设备范围",
        "adopted": {
          "summary": "范围限定为本次输入，不自动扩大到所有 Case 成员。",
          "evidence_ids": [
            "INV-20261024-002-query-1",
            "INV-20261024-002-query-2"
          ]
        }
      },
      {
        "id": "INV-20261024-002-event-stage-2",
        "seq": 4,
        "kind": "forensic",
        "name": "取证分析",
        "time": "2026-10-24T01:36:00.000Z",
        "summary": "终端与 203.0.113.50:443 存在 TLS 连接，已取得连接时间和发送字节数。",
        "adopted": {
          "summary": "终端与 203.0.113.50:443 存在 TLS 连接，已取得连接时间和发送字节数。；没有文件级传输清单，不能确认传输对象或完整范围。；本次保留部分结果，等待补充资料后复核。",
          "evidence_ids": [
            "INV-20261024-002-query-1",
            "INV-20261024-002-query-2"
          ]
        }
      },
      {
        "id": "INV-20261024-002-event-stage-3",
        "seq": 5,
        "kind": "responder",
        "name": "响应分析",
        "time": "2026-10-24T01:37:00.000Z",
        "summary": "形成建议，执行与审批独立跟踪",
        "adopted": {
          "summary": "补充文件传输清单并复核范围",
          "evidence_ids": [
            "INV-20261024-002-query-1",
            "INV-20261024-002-query-2"
          ]
        }
      },
      {
        "id": "INV-20261024-002-event-stage-4",
        "seq": 6,
        "kind": "report",
        "name": "报告整理",
        "time": "2026-10-24T01:38:00.000Z",
        "summary": "保存本次结果及材料引用",
        "adopted": {
          "summary": "报告引用本次查询及范围限制。",
          "evidence_ids": [
            "INV-20261024-002-query-1",
            "INV-20261024-002-query-2"
          ]
        }
      }
    ],
    "recorded": false,
    "fixture": true,
    "sourceEnvironment": "design",
    "sourceTenantId": "design",
    "sourceCaseId": "17420",
    "verdict": "needs_review",
    "started": "2026-10-24T01:32:00.000Z",
    "ended": "2026-10-24T01:38:00.000Z",
    "input": {
      "case_id": "17420",
      "alerts": [
        {
          "id": "da63896004106",
          "title": "异常外部 IP 的出站连接",
          "severity": "低",
          "status": "New",
          "classification": "Not set",
          "owner": "Alex Wilber",
          "source": "Microsoft Sentinel",
          "category": "命令与控制",
          "tags": [],
          "investigation": "In progress",
          "first": "2026-10-24T01:16:00.000Z",
          "last": "2026-10-24T01:19:00.000Z",
          "incidentId": "262144",
          "entityIds": [
            "d1",
            "u1",
            "ip1",
            "f1"
          ],
          "description": "异常外部 IP 的出站连接。安全检测发现与当前事件相关的活动，请结合实体上下文、事件时间线和关联证据进一步评估。",
          "comments": []
        },
        {
          "id": "da63896004108",
          "title": "向未知云应用上传敏感文件",
          "severity": "高",
          "status": "In progress",
          "classification": "Not set",
          "owner": "未分配",
          "source": "Microsoft Sentinel",
          "category": "数据外泄",
          "tags": [],
          "investigation": "New",
          "first": "2026-10-24T01:28:00.000Z",
          "last": "2026-10-24T01:31:00.000Z",
          "incidentId": "262144",
          "entityIds": [
            "d1",
            "u1",
            "ip1",
            "f1"
          ],
          "description": "向未知云应用上传敏感文件。安全检测发现与当前事件相关的活动，请结合实体上下文、事件时间线和关联证据进一步评估。",
          "comments": []
        }
      ]
    },
    "tools": [
      {
        "id": "INV-20261024-002-query-1",
        "name": "network_connections",
        "args": {
          "hostname": "cont-adrianbrad",
          "start": "2026-10-24T01:00:00Z",
          "end": "2026-10-24T01:32:00Z"
        },
        "time": "2026-10-24T01:33:00.000Z",
        "success": true,
        "resultFormat": "saved_result",
        "result": "{\n  \"records\": [\n    {\n      \"time\": \"2026-10-24T01:16:00Z\",\n      \"hostname\": \"cont-adrianbrad\",\n      \"remote_ip\": \"203.0.113.50\",\n      \"remote_port\": 443,\n      \"protocol\": \"TLS\",\n      \"bytes_sent\": 20480\n    }\n  ],\n  \"coverage\": \"连接及流量元数据，不包含传输内容。\"\n}"
      },
      {
        "id": "INV-20261024-002-query-2",
        "name": "transfer_inventory",
        "args": {
          "hostname": "cont-adrianbrad",
          "destination": "203.0.113.50"
        },
        "time": "2026-10-24T01:34:00.000Z",
        "success": false,
        "resultFormat": "saved_result",
        "result": "{\n  \"status\": \"unavailable\",\n  \"reason\": \"未取得文件级传输清单；不能根据连接字节数认定具体文件外泄。\"\n}"
      }
    ],
    "graphs": {
      "attack_chain": {
        "status": "success",
        "source": "design_fixture",
        "queried_at": "2026-10-24T01:36:00.000Z",
        "data": {
          "case_id": "17420",
          "seed_alert_id": "da63896004106",
          "window": "40m",
          "chain": [
            {
              "alert_id": "da63896004108",
              "title": "向未知云应用上传敏感文件",
              "event_time": "2026-10-24T01:28:00.000Z",
              "severity": "高",
              "shared_entities": [
                {
                  "kind": "Entity",
                  "value": "cont-adrianbrad"
                },
                {
                  "kind": "Entity",
                  "value": "hcook@contoso.com"
                },
                {
                  "kind": "Entity",
                  "value": "203.0.113.50"
                },
                {
                  "kind": "Entity",
                  "value": "invoice_2026.pdf.exe"
                }
              ],
              "distance": 1
            }
          ]
        }
      },
      "attack_path": {
        "status": "success",
        "source": "design_fixture",
        "queried_at": "2026-10-24T01:36:00.000Z",
        "data": {
          "nodes": [
            {
              "id": "da63896004106",
              "label": "Alert",
              "properties": {
                "title": "异常外部 IP 的出站连接",
                "source_alert_id": "da63896004106"
              }
            },
            {
              "id": "da63896004108",
              "label": "Alert",
              "properties": {
                "title": "向未知云应用上传敏感文件",
                "source_alert_id": "da63896004108"
              }
            },
            {
              "id": "d1",
              "label": "Host",
              "properties": {
                "name": "cont-adrianbrad"
              }
            },
            {
              "id": "u1",
              "label": "User",
              "properties": {
                "name": "hcook@contoso.com"
              }
            },
            {
              "id": "ip1",
              "label": "IOC",
              "properties": {
                "name": "203.0.113.50"
              }
            },
            {
              "id": "f1",
              "label": "Entity",
              "properties": {
                "name": "invoice_2026.pdf.exe"
              }
            }
          ],
          "edges": [
            {
              "source": "da63896004106",
              "target": "d1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004106",
              "target": "u1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004106",
              "target": "ip1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004106",
              "target": "f1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004108",
              "target": "d1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004108",
              "target": "u1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004108",
              "target": "ip1",
              "type": "OBSERVED_WITH"
            },
            {
              "source": "da63896004108",
              "target": "f1",
              "type": "OBSERVED_WITH"
            }
          ]
        }
      },
      "alert_graph": {
        "status": "success",
        "source": "design_fixture",
        "queried_at": "2026-10-24T01:36:00.000Z",
        "data": {
          "neighbors": {
            "neighbor_count": 4,
            "neighbors": [
              {
                "label": "device",
                "properties": {
                  "name": "cont-adrianbrad"
                },
                "rel_type": "OBSERVED_WITH"
              },
              {
                "label": "user",
                "properties": {
                  "name": "hcook@contoso.com"
                },
                "rel_type": "OBSERVED_WITH"
              },
              {
                "label": "ip",
                "properties": {
                  "name": "203.0.113.50"
                },
                "rel_type": "OBSERVED_WITH"
              },
              {
                "label": "file",
                "properties": {
                  "name": "invoice_2026.pdf.exe"
                },
                "rel_type": "OBSERVED_WITH"
              }
            ]
          },
          "blast_radius": {
            "total_affected": 4,
            "hops": 1
          }
        }
      }
    },
    "artifacts": [
      {
        "id": "INV-20261024-002-artifact-1",
        "kind": "tool_result",
        "event_id": "INV-20261024-002-event-query-1",
        "size_bytes": 220,
        "sha256": "935a99d57b3e3c4f05e9d6fadc5e83b21f5442c9a167c41bb6cd6fe8448f823d",
        "created_at": "2026-10-24T01:38:00.000Z"
      },
      {
        "id": "INV-20261024-002-artifact-2",
        "kind": "tool_result",
        "event_id": "INV-20261024-002-event-query-2",
        "size_bytes": 123,
        "sha256": "108bf4fff54ab64e27d376ac32c7fe0b08db8b73738501a5f4c15d42d4edfb73",
        "created_at": "2026-10-24T01:38:00.000Z"
      },
      {
        "id": "INV-20261024-002-artifact-3",
        "kind": "relationship_graph",
        "event_id": "INV-20261024-002-event-stage-2",
        "size_bytes": 2258,
        "sha256": "86a239ca55a3c0e5fa8bab9fe38d9c23b94ace2c8acae7e70b4cbc51ad4472c1",
        "created_at": "2026-10-24T01:38:00.000Z"
      },
      {
        "id": "INV-20261024-002-artifact-4",
        "kind": "report_md",
        "event_id": "INV-20261024-002-event-stage-4",
        "size_bytes": 761,
        "sha256": "698b3654d40309ef34957354480229c85c26de301954552101396c990c67a45a",
        "created_at": "2026-10-24T01:38:00.000Z"
      }
    ],
    "artifactBodies": {
      "INV-20261024-002-artifact-1": {
        "mode": "full",
        "format": "json",
        "content": {
          "records": [
            {
              "time": "2026-10-24T01:16:00Z",
              "hostname": "cont-adrianbrad",
              "remote_ip": "203.0.113.50",
              "remote_port": 443,
              "protocol": "TLS",
              "bytes_sent": 20480
            }
          ],
          "coverage": "连接及流量元数据，不包含传输内容。"
        }
      },
      "INV-20261024-002-artifact-2": {
        "mode": "full",
        "format": "json",
        "content": {
          "status": "unavailable",
          "reason": "未取得文件级传输清单；不能根据连接字节数认定具体文件外泄。"
        }
      },
      "INV-20261024-002-artifact-3": {
        "mode": "full",
        "format": "json",
        "content": {
          "attack_chain": {
            "status": "success",
            "source": "design_fixture",
            "queried_at": "2026-10-24T01:36:00.000Z",
            "data": {
              "case_id": "17420",
              "seed_alert_id": "da63896004106",
              "window": "40m",
              "chain": [
                {
                  "alert_id": "da63896004108",
                  "title": "向未知云应用上传敏感文件",
                  "event_time": "2026-10-24T01:28:00.000Z",
                  "severity": "高",
                  "shared_entities": [
                    {
                      "kind": "Entity",
                      "value": "cont-adrianbrad"
                    },
                    {
                      "kind": "Entity",
                      "value": "hcook@contoso.com"
                    },
                    {
                      "kind": "Entity",
                      "value": "203.0.113.50"
                    },
                    {
                      "kind": "Entity",
                      "value": "invoice_2026.pdf.exe"
                    }
                  ],
                  "distance": 1
                }
              ]
            }
          },
          "attack_path": {
            "status": "success",
            "source": "design_fixture",
            "queried_at": "2026-10-24T01:36:00.000Z",
            "data": {
              "nodes": [
                {
                  "id": "da63896004106",
                  "label": "Alert",
                  "properties": {
                    "title": "异常外部 IP 的出站连接",
                    "source_alert_id": "da63896004106"
                  }
                },
                {
                  "id": "da63896004108",
                  "label": "Alert",
                  "properties": {
                    "title": "向未知云应用上传敏感文件",
                    "source_alert_id": "da63896004108"
                  }
                },
                {
                  "id": "d1",
                  "label": "Host",
                  "properties": {
                    "name": "cont-adrianbrad"
                  }
                },
                {
                  "id": "u1",
                  "label": "User",
                  "properties": {
                    "name": "hcook@contoso.com"
                  }
                },
                {
                  "id": "ip1",
                  "label": "IOC",
                  "properties": {
                    "name": "203.0.113.50"
                  }
                },
                {
                  "id": "f1",
                  "label": "Entity",
                  "properties": {
                    "name": "invoice_2026.pdf.exe"
                  }
                }
              ],
              "edges": [
                {
                  "source": "da63896004106",
                  "target": "d1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004106",
                  "target": "u1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004106",
                  "target": "ip1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004106",
                  "target": "f1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004108",
                  "target": "d1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004108",
                  "target": "u1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004108",
                  "target": "ip1",
                  "type": "OBSERVED_WITH"
                },
                {
                  "source": "da63896004108",
                  "target": "f1",
                  "type": "OBSERVED_WITH"
                }
              ]
            }
          },
          "alert_graph": {
            "status": "success",
            "source": "design_fixture",
            "queried_at": "2026-10-24T01:36:00.000Z",
            "data": {
              "neighbors": {
                "neighbor_count": 4,
                "neighbors": [
                  {
                    "label": "device",
                    "properties": {
                      "name": "cont-adrianbrad"
                    },
                    "rel_type": "OBSERVED_WITH"
                  },
                  {
                    "label": "user",
                    "properties": {
                      "name": "hcook@contoso.com"
                    },
                    "rel_type": "OBSERVED_WITH"
                  },
                  {
                    "label": "ip",
                    "properties": {
                      "name": "203.0.113.50"
                    },
                    "rel_type": "OBSERVED_WITH"
                  },
                  {
                    "label": "file",
                    "properties": {
                      "name": "invoice_2026.pdf.exe"
                    },
                    "rel_type": "OBSERVED_WITH"
                  }
                ]
              },
              "blast_radius": {
                "total_affected": 4,
                "hops": 1
              }
            }
          }
        }
      },
      "INV-20261024-002-artifact-4": {
        "mode": "full",
        "format": "markdown",
        "content": "# 异常外联与数据传输调查\n\n## 范围\nCase 17420；输入告警 da63896004106、da63896004108。仅覆盖本次输入及查询窗口。\n\n## 结论\n终端与 203.0.113.50:443 存在 TLS 连接，已取得连接时间和发送字节数。\n\n没有文件级传输清单，不能确认传输对象或完整范围。\n\n本次保留部分结果，等待补充资料后复核。\n\n## 查询与依据\n- network_connections：已取得记录；引用 INV-20261024-002-query-1\n- transfer_inventory：资料不可用；引用 INV-20261024-002-query-2\n\n## 完整性\n部分交付。未取得完整传输文件清单，等待补充后继续调查。\n\n## 后续处理\n- 补充文件传输清单并复核范围\n\n## 执行记录\n未执行隔离、封禁或会话撤销。\n"
      }
    },
    "actions": [
      {
        "description": "补充文件传输清单并复核范围",
        "target": "cont-adrianbrad",
        "requires_approval": false,
        "rationale": "连接元数据不足以确定文件内容。"
      }
    ],
    "executed": [],
    "report": "# 异常外联与数据传输调查\n\n## 范围\nCase 17420；输入告警 da63896004106、da63896004108。仅覆盖本次输入及查询窗口。\n\n## 结论\n终端与 203.0.113.50:443 存在 TLS 连接，已取得连接时间和发送字节数。\n\n没有文件级传输清单，不能确认传输对象或完整范围。\n\n本次保留部分结果，等待补充资料后复核。\n\n## 查询与依据\n- network_connections：已取得记录；引用 INV-20261024-002-query-1\n- transfer_inventory：资料不可用；引用 INV-20261024-002-query-2\n\n## 完整性\n部分交付。未取得完整传输文件清单，等待补充后继续调查。\n\n## 后续处理\n- 补充文件传输清单并复核范围\n\n## 执行记录\n未执行隔离、封禁或会话撤销。\n",
    "stop": "未取得完整传输文件清单，需继续核查传输范围。",
    "depth": {
      "iterations": 2,
      "distinct_pivots": 2,
      "truncated": false,
      "pivots": [
        "network_connections",
        "transfer_inventory"
      ],
      "unavailable_data": [
        "文件级传输清单"
      ],
      "coverage_notes": [
        "限定于输入告警的账户、设备及绝对时间窗口。"
      ],
      "strategy_id": "design-material-review"
    }
  }
];
window.mergeDesignWorkspace = function(store){
  const c=store.cases.find(c=>c.id==='17420'&&!c.localCollection&&!c.recordedCase);
  if(c&&c.tasks===undefined)c.tasks=[
    {id:'design-task-review',title:'审核账户会话与终端处置建议',owner:'Alex Wilber',due:'2026-10-25T12:00',status:'In progress'},
    {id:'design-task-transfer',title:'补充文件级传输清单',owner:'Megan Bowen',due:'2026-10-26T18:00',status:'New'}
  ];
};
