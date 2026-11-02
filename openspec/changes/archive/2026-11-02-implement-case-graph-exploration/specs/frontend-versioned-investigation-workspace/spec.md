## ADDED Requirements
### Requirement: Case relationship exploration preserves provenance and explicit adoption
V2 SHALL support alert and concrete-entity pivots only in the Case relationship workspace, using bounded loaded records and preserving the source Run and explicit relationship evidence.
#### Scenario: Explore a candidate and prepare further investigation
- **WHEN** a user selects a supported node or requests recommended leads
- **THEN** show ranked candidates and reasons separately from the base Path and direct-neighbor graph, allow preview, expansion, continuation, undo and saved exploration, and distinguish new nodes from existing scope and draft selections
- **AND** taxonomy nodes are view-only, expansion never changes membership or Run input, and saved investigation drafts disclose any proposed new membership before confirmation.
### Requirement: Case drafts and active investigation status are separate
V2 SHALL support cancelled drafts with retained records and persistent Case-level active-Run notices, while allowing at most one active Case investigation in local demonstrations.
#### Scenario: Save or start a draft while a Run is active
- **WHEN** a Case has an active or pending-start investigation
- **THEN** users may explore, add members and save or cancel drafts but cannot start a second Run or modify the active Run's frozen inputs
- **AND** only explicitly identified simulation Cases can simulate a start and progress; original recorded Cases never invoke or invent execution.
### Requirement: Case membership supports multiple incidents and actionable queue counts
V2 SHALL allow selecting multiple incidents with deduplicated member alerts and show all related incidents without changing their original membership or other Cases.
#### Scenario: Add events and inspect the Case queue
- **WHEN** incident selections are confirmed
- **THEN** selected current alerts are added once, event associations remain navigable, and historical Run inputs remain unchanged
- **AND** the former multi-alert percentage card is replaced by the count of Cases in progress.

## MODIFIED Requirements
### Requirement: Investigation preparation is separate from execution
V2 SHALL retain preparations separately from Runs, including explicit objectives, input alerts, entity targets and material references.
#### Scenario: Save an investigation preparation
- **WHEN** a user saves or revises a valid draft
- **THEN** historical Runs remain unchanged and saving never starts execution
- **AND** execution remains unavailable for real records; dedicated demonstration Cases may explicitly simulate a start and manual progress without claiming real model replies or backend execution.
### Requirement: Case relationship views default to the latest finished investigation
V2 SHALL default the Case relationship base to its latest completed investigation, excluding triage-only results, and preserve its original input scope and provenance.
#### Scenario: Inspect or revise Case membership
- **WHEN** completed investigations exist
- **THEN** select the latest by end time with start time as a labelled fallback, disclose completeness, and link to its read-only Run
- **AND** default to Path and direct-neighbor relationships; saved exploration pins its base until explicitly reset and never merges historical Runs.
#### Scenario: Open a Case without a completed investigation
- **WHEN** no eligible completed investigation exists
- **THEN** use current member-to-object relationships as the identified base
- **AND** optional exploration remains an explicitly separate overlay with no implicit membership or investigation execution.
