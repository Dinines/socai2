## ADDED Requirements

### Requirement: Local Cases collect saved alert-flow materials without rewriting source ownership
V2 SHALL present explicitly local Case collections for the saved Fusion groups and make their existing assessments, investigation records, queries, artifacts, reports and source relations accessible. Source Case identity and Run inputs SHALL remain unchanged, and collection management SHALL remain separate from saved analysis and executed responses.

#### Scenario: Inspect a local Case from the six saved alerts
- **WHEN** the saved alert-flow records are loaded
- **THEN** three local Cases each collect two original members and reference their existing single-alert Runs
- **AND** the Case overview summarizes per-Run results and partial delivery without inventing a joint conclusion, backend Case, attack path, classified evidence, task or executed action.

#### Scenario: Revise current membership
- **WHEN** current members of a local Case are changed
- **THEN** member facts and the current relationship view follow that membership while saved Run references retain their original input and same-environment tenant scope
- **AND** reload preserves browser edits and source records remain unchanged.
