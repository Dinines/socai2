# Design

Normalize `start` and `end` to UTC at the SQL binding boundary and format them as `YYYY-MM-DD HH:MM:SS.ffffff`. The SQL already specifies UTC and microsecond precision. JSON evidence keeps its timezone-bearing timestamps. This changes only the two Case lake queries; the existing records reader already uses this representation.

Clarify native `tool_calls` versus text and final JSON formatting in the existing system prompt. Do not force queries for every Case, accept invented evidence, strip validation, or introduce retries/budget changes.
