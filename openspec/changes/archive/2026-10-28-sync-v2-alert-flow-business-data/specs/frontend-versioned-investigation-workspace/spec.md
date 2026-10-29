## ADDED Requirements

### Requirement: Saved alert-flow groups populate incident workspaces
V2 SHALL append incident rows grouped by saved Fusion incident identity and tenant while preserving prior fixtures and browser edits. Member facts and investigation links SHALL be available without fabricating incident management values, inventory relationships, executed actions, or a Case.

#### Scenario: Open a saved Fusion group
- **WHEN** the six saved socai2 alerts are loaded
- **THEN** their three groups each expose two actual members, source objects, times, basic assessments and matching Runs
- **AND** missing incident management values remain unknown; group statistics use the same source set and reading does not create a Case or launch an investigation.

### Requirement: Saved Run records and readable materials retain provenance
V2 SHALL display all saved event records in the selected socai2 Run and offer its available artifact contents with source identity and retention limits. Public projections SHALL exclude prompts and hidden reasoning, escape content, and distinguish filtered extracts from full originals.

#### Scenario: Inspect records and materials
- **WHEN** the user selects one of the saved Runs or an artifact within it
- **THEN** the Run's saved event rows include model-call and usage records, and any displayed artifact belongs to that Run
- **AND** original hashes identify source content; filtered or unavailable bodies, partial completion and absent executions remain explicit.
