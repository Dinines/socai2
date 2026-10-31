## ADDED Requirements

### Requirement: Incident preview presents whole-event context
The V2 saved-incident preview SHALL present an incident overview based on current member context and associated investigation progress instead of a per-alert triage-score panel. Missing incident-level assessments and priorities SHALL remain explicit and source data SHALL remain unchanged.

#### Scenario: Read a saved incident preview
- **WHEN** a user opens a saved incident preview
- **THEN** the overview summarizes its member count, known hosts, recorded alert clues and started investigations counted once per Run
- **AND** per-alert confidence and verdicts are not promoted to an incident score or overall verdict, partial delivery remains distinct, and triage-only Runs are excluded from started investigation counts.

#### Scenario: Read an incident with missing management state
- **WHEN** a saved incident has no recorded handling state
- **THEN** the preview identifies the handling state as unrecorded and explains that this does not establish an absence of investigation or response
- **AND** the existing New, In progress and Resolved state values, source records and original design examples remain unchanged.
