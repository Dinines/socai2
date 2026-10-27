## ADDED Requirements
### Requirement: Real replayed alert snapshot
The alert workspace SHALL display a timestamped snapshot read from host21 after bounded replay of selected synthetic alerts from host20. Each displayed data item SHALL map to an actual database field or explicitly documented derivation. Missing data SHALL remain absent rather than using fixture values. Snapshot interactions SHALL NOT imply server writes. Incident and Case workspaces SHALL remain outside the data integration scope.
#### Scenario: Inspect a replayed alert
- **WHEN** the analyst opens the alert list or detail
- **THEN** the title, timestamp, raw status, verdict and linked processing records derive from host21 persisted records
- **AND** new and triaged appear in the new/pending display group without changing stored status
- **AND** Run completion, missing reports, assets and Case associations reflect actual data rather than generated mock history.
