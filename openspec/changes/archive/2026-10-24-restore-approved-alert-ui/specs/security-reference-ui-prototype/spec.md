## MODIFIED Requirements
### Requirement: Real replayed alert snapshot
The replayed host21 data SHALL be retained as offline field-mapping evidence and documentation. The previously approved alert workspace design, sample display data and interactions SHALL remain unchanged by this mapping exercise. Real snapshot rendering, data-gap panels and disabled interactions introduced solely for that snapshot SHALL NOT replace the approved interface.
#### Scenario: Preserve the approved alert workspace
- **WHEN** the analyst opens the alert list or detail after the mapping exercise
- **THEN** the previously approved layout, sample data and interactions are restored
- **AND** actual database mappings and missing data are recorded in documentation separately
- **AND** previously replayed server records and evidence are retained without further writes or replay.

#### Scenario: Inspect a replayed alert
- **WHEN** the analyst reviews the separately retained mapping documentation
- **THEN** actual host21 values, their source fields and missing data remain available as evidence
- **AND** that evidence does not replace the approved prototype display data or design.
