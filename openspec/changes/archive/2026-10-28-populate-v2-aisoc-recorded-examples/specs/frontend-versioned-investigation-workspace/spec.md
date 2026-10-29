## ADDED Requirements

### Requirement: Recorded AiSOC examples preserve source relationships
V2 SHALL append the six saved AiSOC20 alert results and six Runs without replacing existing examples, and SHALL distinguish three local presentation Cases from backend Case relationships. Synthetic input provenance, partial completion, skipped stages, absent metadata and absent executed actions SHALL remain visible without fabricated values.

#### Scenario: Inspect an imported local Case
- **WHEN** a user opens a local AiSOC20 Case
- **THEN** the page identifies it as a local grouping of historical demonstration alerts, shows the actual single-alert Runs and saved reports, and retains null source Case identities
- **AND** a skipped attack-path stage is shown as skipped, while the separate case graph contains only recorded direct relationships for its current members

#### Scenario: Inspect same-host alerts across environments
- **WHEN** related or similar alerts are shown for an imported alert
- **THEN** candidates are restricted to the same source environment and tenant, and raw entities without inventory relationships receive no invented inventory identifiers or scores
