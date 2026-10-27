## ADDED Requirements
### Requirement: Stable main alert table sorting
The main alert table SHALL place severity and alert time second and third after alert name, excluding selection. Only severity and alert time SHALL be sortable. Indicators and accessible sort state SHALL distinguish inactive, ascending and descending states. Each visible column SHALL have a fixed width independent of row content, with horizontal scrolling when needed.
#### Scenario: Sort without layout shift
- **WHEN** the analyst sorts by severity or alert time
- **THEN** the rows and direction indicator update while column widths remain unchanged
- **AND** other main table headers have no sort button or indicator
- **AND** incident and Case tables retain their existing behavior.
