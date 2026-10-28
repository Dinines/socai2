## ADDED Requirements

### Requirement: ClickHouse-compatible Case time bindings
Case lake tools SHALL bind the absolute investigation window in a format accepted by the configured ClickHouse `toDateTime64` function, preserving UTC instants, microseconds, and the inclusive-start/exclusive-end semantics.

#### Scenario: Query a timezone-aware Case window
- **WHEN** a Case process or network query receives timezone-aware boundaries
- **THEN** the database receives UTC calendar timestamp strings and the returned evidence retains the explicit timezone in its query scope.

### Requirement: Case model instructions distinguish actual queries from narration
The Case prompt SHALL require native tool calls for explicit requests for missing source data and SHALL require final conclusions as a JSON object using only supplied evidence identifiers.

#### Scenario: The user requests source queries
- **WHEN** matching evidence is not already available and an appropriate tool is offered
- **THEN** the model is instructed to issue native tool calls, wait for their results, and avoid inventing E references or empty-result claims.
