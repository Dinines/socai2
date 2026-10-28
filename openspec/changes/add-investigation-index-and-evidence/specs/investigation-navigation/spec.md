## ADDED Requirements

### Requirement: Investigation executions have a scope-aware shared index
The API SHALL list executions for exactly one Alert, Incident or Case filter and SHALL retain the native reader and known scope of each execution without guessing legacy Case ownership or completion.

#### Scenario: An alert is a Case member but was not selected in a Run
- **WHEN** its execution index is read
- **THEN** that Case Run is excluded unless its saved selection includes the alert

#### Scenario: An older Run explicitly names a source alert
- **WHEN** the source alert is in the requested business scope
- **THEN** the index links its original ledger reader and leaves unknown profile, Case ownership and report completeness unknown

### Requirement: Report citations navigate to saved evidence and source rows
The Case API SHALL expose evidence and source rows by Run-scoped identifiers and SHALL return recorded Tool request/result links and reuse provenance where available.

#### Scenario: A finding cites a Tool result
- **WHEN** its evidence link is followed
- **THEN** the caller can read the saved evidence, its recorded Tool steps and a selected source row without executing a new query

#### Scenario: A later Run reuses earlier query evidence
- **WHEN** the reused evidence is read
- **THEN** its current recorded steps remain separate from the original evidence link, and the old saved report remains unchanged
