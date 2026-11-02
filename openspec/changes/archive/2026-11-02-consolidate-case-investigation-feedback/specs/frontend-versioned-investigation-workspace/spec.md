## ADDED Requirements

### Requirement: Case overview separates current work from delivered results
The shared Case overview SHALL expose the owned active Run and waiting drafts before delivered findings, while retaining cancelled and started drafts in a collapsed history.
#### Scenario: Inspect current work
- **WHEN** a Case has an active Run and a draft
- **THEN** both are visible as distinct work, progress and draft actions remain available, and prior delivered results remain readable
- **AND** merely viewing, opening or cancelling a form does not create or start an investigation.

### Requirement: Human task references are optional and distinct from origin
Human tasks SHALL explain the source investigation as origin and concrete optional references as reading material without requiring a work order or attachment.
#### Scenario: Prepare a human confirmation
- **WHEN** a user prepares a task from a Run
- **THEN** the Run is available as its source and is not offered again as a new whole-Run reference choice
- **AND** previously selected references remain preserved, completion accepts a written human result alone, and no model or investigation is started.

### Requirement: Run statistics use saved scope and missing-value semantics
Investigation history and detail SHALL share elapsed-time, saved-tool-record, model-call and token metrics for all data sources.
#### Scenario: Read saved execution statistics
- **WHEN** valid Run start and end times exist
- **THEN** elapsed time is computed from those timestamps, saved tool entries are counted as records, and calls and tokens use the saved Run totals
- **AND** missing or invalid values remain missing, explicit zero remains zero, Deep-stage latency is never treated as total duration, and reading does not modify records.
