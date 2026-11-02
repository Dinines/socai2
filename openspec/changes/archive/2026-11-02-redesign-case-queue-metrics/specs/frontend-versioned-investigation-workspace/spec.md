## ADDED Requirements
### Requirement: Case queue metrics describe actionable Case counts
The current Case queue SHALL show unassigned, in-progress, high-severity and pending-human-follow-up Case counts using one rule for all data sources. It SHALL exclude resolved and unknown-status Cases, count each Case once per metric, and explain scope and overlap through an information control. The queue SHALL omit nonfunctional Incident and Generic type tabs.
#### Scenario: Read counts and inspect matching Cases
- **WHEN** the queue is displayed
- **THEN** metrics count all loaded Cases with known New or In progress status, independently of table filters; pending follow-up counts Cases with at least one New or In progress task, not task totals
- **AND** selecting a metric replaces existing search and filters with that criterion while preserving columns and sort; toggling or removing it restores the remaining table scope
- **AND** metric filtering can be saved in a filter set, old sets clear a previously selected metric, and these operations do not update Case or Run business data.
