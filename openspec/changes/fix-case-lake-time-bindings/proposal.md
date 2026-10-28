# Fix Case lake time bindings

The real ClickHouse on development host 21 rejects the ISO timestamps with UTC offsets passed to `toDateTime64` by both Case lake tools. Serialize SQL time bindings as UTC calendar timestamps with microseconds, matching the existing activity-record reader. Keep public scope timestamps and the half-open window unchanged.

Verify both tools against the existing synthetic fixture, then use the previously configured model on 21 for a bounded functional example. No shared schema migration, worker activation, or response action is included.

The first live-model example returned prose claiming queries had happened without issuing native tool calls. A minimal forced-function request confirmed that the configured endpoint supports the protocol. Clarify the existing Case prompt: explicit requests for missing source data require actual native tool calls, and final output must be unfenced JSON referencing only received evidence. Keep validation and rejection behavior intact.
