## RENAMED Requirements
- FROM: `### Requirement: Case relationship views show current membership only`
- TO: `### Requirement: Case relationship views default to the latest finished investigation`

## MODIFIED Requirements

### Requirement: Case relationship views default to the latest finished investigation
V2 SHALL default the Case relationship view to its latest completed-status investigation and preserve that Run's original input scope; current member relationships SHALL be the identified fallback only when no completed investigation exists.
#### Scenario: Inspect or revise Case membership
- **WHEN** completed investigations exist
- **THEN** select the latest by end time with start time as an explicitly labelled fallback, exclude triage-only records, and show completeness and a link to that Run
- **AND** do not combine Runs or silently select an older richer graph; changing current members does not alter historical inputs or source materials.
#### Scenario: Open a Case without a completed investigation
- **WHEN** no eligible completed investigation exists
- **THEN** show only current members and their recorded object links with that scope identified, without associated-event or potential-path expansion.

### Requirement: Recorded AiSOC examples preserve source relationships
V2 SHALL append the six saved AiSOC20 alert results and six Runs without replacing existing examples, and SHALL preserve the distinction between local presentation Cases and backend Case relationships in source data and handoff documentation. Partial completion, skipped stages, absent metadata and absent executed actions SHALL remain visible without fabricated values.
#### Scenario: Inspect an imported local Case
- **WHEN** a user opens a local AiSOC20 Case
- **THEN** the page shows its actual single-alert Runs and saved reports without extra import labels, and source data retains null source Case identities
- **AND** a skipped attack-path stage is shown as skipped; its Case graph uses the latest eligible completed Run and any explicitly labelled saved context is limited to that Run's original inputs.
#### Scenario: Inspect same-host alerts across environments
- **WHEN** related or similar alerts are shown for an imported alert
- **THEN** candidates are restricted to the same source environment and tenant, and raw entities without inventory relationships receive no invented inventory identifiers or scores.

## ADDED Requirements

### Requirement: Related alerts distinguish current membership from investigation input
V2 SHALL offer a related-alert list without duplicating Run input alerts, preserve unavailable source states, and disclose current Case membership separately from original Run input.
#### Scenario: Review a related alert outside the Case
- **WHEN** the user selects an alert from the related list or graph
- **THEN** the details show saved relationship evidence, available ranking/time difference and current Case membership
- **AND** eligible alerts can be preselected in the existing add-member form, whose explicit confirmation only adds current Case membership and never changes historical Run inputs, other Cases or starts an investigation.
