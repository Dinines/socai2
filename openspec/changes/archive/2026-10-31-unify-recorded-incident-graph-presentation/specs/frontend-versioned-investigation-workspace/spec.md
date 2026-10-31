## ADDED Requirements

### Requirement: Incident graphs share presentation without borrowing source relationships
V2 SHALL render recorded and illustrative incidents in the same reference graph workspace with circular nodes, alert list, graph controls and contextual details. Recorded incident graphs SHALL retain source alert-to-object associations and SHALL NOT acquire illustrative relationships, paths, risk or inventory values.

#### Scenario: Inspect a recorded incident graph
- **WHEN** the user opens a recorded incident overview or relationship analysis
- **THEN** existing member alerts and their recorded objects appear in the common graph with filtering, grouping, layout, zoom, playback and source drill-down
- **AND** grouping retains original endpoints and alert sources, absent event times remain absent, and absent paths are not interpreted as confirmed negative findings.

#### Scenario: Expand source relationships
- **WHEN** a user expands the graph to associated incidents
- **THEN** only loaded recorded incidents with the same known environment and tenant and exact shared object identities are included
- **AND** missing identities prevent expansion; viewing does not change incident membership, alert records or historical Runs.
