## ADDED Requirements

### Requirement: Persisted Case investigation retains joint scope and saved artifacts
V2 SHALL display the saved historical Case and its joint investigation using original Case/Run identities and saved input members. It SHALL present adopted four-stage results, actual tool returns, saved chain/path/reachability artifacts and report without converting candidate alerts into Case members, Run completion into delivery completeness, or dry-run proposals into executions.

#### Scenario: Inspect the saved Case chain and path
- **WHEN** the historical three-alert Case is opened
- **THEN** its Run shows the five saved chain candidates, eleven path nodes and fifteen edges, and sixteen graph-reachable entities with their original sources and scope
- **AND** external candidates remain outside the Case and graph reachability is not presented as confirmed victim scope

#### Scenario: Inspect adopted analysis and missing metadata
- **WHEN** the user opens the historical stages or an input alert
- **THEN** four-stage results and the joint Case investigation remain distinguishable from individual alert triage, while missing status, scoring, completeness, attachments or inventory relationships are not filled from demo templates
