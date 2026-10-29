## ADDED Requirements
### Requirement: Unified investigation graph preserves relationship semantics
V2 SHALL present saved Run chain candidates and path relationships in one alert-list and entity-graph workspace while retaining source statuses, scope, relationship predicates and raw materials. Selecting alerts, entities, techniques or edges SHALL focus only supported relationships without changing Run inputs, query seeds or Case members.

#### Scenario: Focus an alert and inspect an edge
- **WHEN** an analyst selects an input alert or one of its relationships
- **THEN** the graph emphasizes its saved direct relationships or only the selected edge and its endpoints, respectively, and related alerts remain discoverable
- **AND** selection does not reposition nodes or create new relationships and hidden selection is cleared when its layer is disabled

#### Scenario: Combine candidates with path material
- **WHEN** a saved chain includes external or disconnected candidates
- **THEN** candidates retain their scores, distance, original ordering and external identity without becoming members; missing intermediate paths are identified rather than drawn
- **AND** same-endpoint lines retain each source predicate and relational fallback Case-level techniques do not become exact per-alert mappings

#### Scenario: Change Run or inspect missing path data
- **WHEN** the selected Run changes or has no recorded path
- **THEN** graph selection and material use only that Run, with separate status and context explanations for missing, skipped, unlinked or failed sources
- **AND** filters, grouping and zoom only affect the local presentation
