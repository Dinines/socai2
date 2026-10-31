## MODIFIED Requirements

### Requirement: Saved alert-flow groups populate incident workspaces
V2 SHALL append incident rows grouped by saved Fusion incident identity and tenant while preserving prior fixtures and browser edits. Member facts and investigation links SHALL be available without fabricating incident management values, inventory relationships, executed actions, or a Case.

#### Scenario: Open a saved Fusion group
- **WHEN** the six saved socai2 alerts are loaded
- **THEN** their three groups each expose two actual members, source objects, times, basic assessments and matching Runs
- **AND** missing source management values remain preserved while local handling state follows the default and assignment rules; group statistics use the same source set and reading does not create a Case or launch an investigation.

### Requirement: Incident queue context uses explicit source meanings
V2 SHALL expose incident-linked investigations, member host names and asset tags without inventing incident priority or management state. Preview controls SHALL distinguish a side pane from row expansion. Its compact summary SHALL expose active, unassigned, recent-alert and high-severity incident counts instead of a missing-state count.

#### Scenario: Read incident queue context
- **WHEN** the incident queue and preview are opened
- **THEN** associated-investigation counts include each event with a started member investigation once and exclude triage-only Runs, tags come from member assets, and host names come from saved member context
- **AND** missing source incident state remains retained separately from local handling defaults and alert verdict confidence is never substituted for incident priority.

#### Scenario: Retain saved source records
- **WHEN** incident context is displayed or filtered
- **THEN** source event management tags, member records, source scores, historical Runs and browser edits remain unchanged
- **AND** the preview control opens the existing side pane while the incident title opens the incident page.

#### Scenario: Read the four summary metrics
- **WHEN** the incident queue renders or is refreshed
- **THEN** the recent-alert metric counts each incident once when a member alert occurred within the preceding 24 hours up to the current time, excluding future or invalid timestamps
- **AND** active, unassigned and high-severity counts retain their separate source meanings, all four remain visible at narrow widths, and historical timestamps are never shifted to create recent activity.

### Requirement: Incident preview presents whole-event context
The V2 saved-incident preview SHALL present an incident overview based on current member context and associated investigation progress instead of a per-alert triage-score panel. Missing incident-level assessments and priorities SHALL remain explicit and source data SHALL remain unchanged.

#### Scenario: Read a saved incident preview
- **WHEN** a user opens a saved incident preview
- **THEN** the overview summarizes its member count, known hosts, recorded alert clues and started investigations counted once per Run
- **AND** per-alert confidence and verdicts are not promoted to an incident score or overall verdict, partial delivery remains distinct, and triage-only Runs are excluded from started investigation counts.

#### Scenario: Read an incident with missing management state
- **WHEN** a saved incident has no recorded handling state
- **THEN** the preview uses New by default or In progress when assigned, retaining the missing source state separately
- **AND** the original source records, investigation outcomes and example content remain unchanged; a local handling default does not imply an investigation outcome.

## ADDED Requirements

### Requirement: Local incident lifecycle follows assignment and explicit resolution
V2 SHALL default incidents with missing handling state to New, transition New incidents assigned to a named person to In progress, and resolve incidents only on explicit user action. The incident label for In progress SHALL be 处理中. Source records and investigation results SHALL remain separate from browser-local handling state.

#### Scenario: Initialize or reload incident management
- **WHEN** an incident has missing source handling state
- **THEN** its local status becomes New or In progress if already assigned, retaining the original source status separately
- **AND** existing resolved or in-progress local states are preserved on reload and reset applies the same defaults to restored examples.

#### Scenario: Assign an unresolved incident
- **WHEN** a user assigns a New incident to a named person, individually or in a batch
- **THEN** saving transitions it to In progress and records the change locally
- **AND** empty, unrecorded or unassigned owner placeholders do not start processing; reassignment alone does not reopen a resolved incident.

#### Scenario: Explicitly resolve an incident
- **WHEN** a user explicitly selects Resolved and supplies a resolution note
- **THEN** the incident resolves using the existing member-alert synchronization
- **AND** missing notes block the operation, while investigation completion, partial results and member alerts never resolve the incident automatically.
