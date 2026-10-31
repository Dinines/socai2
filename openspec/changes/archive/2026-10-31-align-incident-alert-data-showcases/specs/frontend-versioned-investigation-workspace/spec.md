## ADDED Requirements

### Requirement: Incident and alert showcases preserve recorded data boundaries
V2 SHALL retain saved AiSOC records and existing examples while providing separate, coherent incident-and-alert demonstration scenarios with fixed identities, complete available materials and explicit internal fixture provenance. Documentation SHALL identify actual records, source paths, missing fields and local-only actions.

#### Scenario: Align recorded fields
- **WHEN** a user opens a saved AiSOC alert or incident
- **THEN** available source, severity, timestamps, scores, membership and processing materials follow the saved source mapping
- **AND** absent Explain, inventory, ownership, incident scoring, merge rules and response receipts remain absent and documented rather than supplemented with fixture values.

#### Scenario: Explore complete demonstrations
- **WHEN** the user opens the new in-progress, unassigned or resolved scenarios
- **THEN** the incident's five tabs and alert's four tabs have coherent descriptions, objects, relationships, raw records, timelines and relevant processing material, with linked-Case and no-Case entry branches
- **AND** full, partial and triage-only execution are distinguished from handling status, judgment, approval and execution.

#### Scenario: Reload without replacing edits
- **WHEN** the fixtures are merged into a new or saved browser workspace more than once
- **THEN** stable identities prevent duplicates, prior records and edits remain intact, and source records or historical Runs are never enriched by demonstration materials.
