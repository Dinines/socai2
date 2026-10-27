## ADDED Requirements

### Requirement: Explicit graph context and relationships
The reference incident and Case workspaces SHALL derive graph scope from their member alerts, use explicit fixture relationships with meaning and provenance, and separate potential reach from recorded associations.

#### Scenario: Inspect and expand context
- **WHEN** an analyst selects an alert, entity, relationship or associated-incidents view
- **THEN** the graph and context panel explain the selected object and its scope
- **AND** viewing, filtering, grouping or replay does not change alert membership or trigger an investigation
- **AND** moving to a different incident or Case clears stale graph state.

#### Scenario: Inspect a potential path
- **WHEN** an entity has a defined potential path
- **THEN** the workspace can show its target and typed connections as potential impact
- **AND** entities without paths show a normal empty state instead of invented connections.

### Requirement: Case work tracking without alert closure
The Case workspace SHALL support browser-local tasks and management fields grounded in the selected official documentation, while preserving the existing alert workspace and records.

#### Scenario: Close a Case
- **WHEN** an analyst saves a Case status, classification, closing note or due date
- **THEN** the Case reflects those fields and records the management activity
- **AND** its alerts retain their individual statuses.

#### Scenario: Review investigation scope
- **WHEN** an analyst opens investigations or changes Case alert membership
- **THEN** investigations shown correspond to the current member alert IDs
- **AND** a scope without investigation records shows an empty state.

#### Scenario: Keep alert pages intact
- **WHEN** the main alert list, preview or detail opens with the same input state
- **THEN** its existing presentation and behavior remain unchanged
- **AND** the six actual replay records receive no invented graph or investigation material.
