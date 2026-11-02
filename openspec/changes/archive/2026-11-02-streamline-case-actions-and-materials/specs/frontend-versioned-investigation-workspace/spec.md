## ADDED Requirements

### Requirement: Case objects and evidence share a workspace
V2 SHALL combine Case objects and evidence into one navigation entry while preserving prior object and evidence URLs, current member sources, all recorded evidence, and per-Run material access.
#### Scenario: Inspect consolidated materials
- **WHEN** a Case material workspace is opened
- **THEN** objects are deduplicated by recorded identity and expose linked member alerts and evidence, with unlinked evidence retained separately
- **AND** records are not promoted to malicious evidence or combined judgments; incident navigation and Run graph capabilities stay unchanged.

### Requirement: Case membership can be extended from within the Case
V2 SHALL allow explicit addition of selected alerts or the selected members of events within a coherent source and tenant scope.
#### Scenario: Add selected sources
- **WHEN** the user confirms addition
- **THEN** only eligible selected alerts are unioned into the current Case, duplicates are avoided, and other Cases and alert ownership are unchanged
- **AND** historic Run references and inputs remain accessible, while cancellation adds nothing and association starts no investigation.

### Requirement: Investigation preparation is separate from execution
V2 SHALL expose new and continuation preparation with an objective, input selection and existing material references, retaining the preparation separately from actual Runs.
#### Scenario: Save an investigation preparation
- **WHEN** a user saves a valid preparation or revises an existing one
- **THEN** the Case retains the explicit input and material selection, with historical Runs unchanged
- **AND** the prototype clearly identifies the preparation as not started, disables unavailable execution, and does not manufacture a queued Run, model reply, adopted evidence or execution progress.

### Requirement: Human follow-up and response decisions retain distinct effects
V2 SHALL let users record human follow-up results and review specific response proposals without treating task completion or approval as an investigation conclusion or executed response.
#### Scenario: Complete human follow-up
- **WHEN** a user completes a task
- **THEN** a result is required and recorded alongside owner, due date and optional existing source references
- **AND** current task counts and activities update locally but Run completeness, verdict, Case status and response approval do not change.
#### Scenario: Review a proposed response
- **WHEN** a user approves or rejects a specific Run action locally
- **THEN** the decision includes the concrete target and reason and remains separate from the saved proposal and execution receipts
- **AND** approval does not mark an object remediated, the response executed or the Case resolved; generic evidence approval is not offered.

## MODIFIED Requirements

### Requirement: Unified Case overview preserves per-Run scope
V2 SHALL open every Case overview as a current-case summary with per-Run results and recorded next work side by side at wide widths and stacked at narrow widths, while preserving access to Case and Run detail capabilities.

#### Scenario: Read a Case with independent alert results
- **WHEN** a Case contains saved single-alert analysis or no results
- **THEN** the overview presents current members separately from each Run's input, completeness and findings or an honest empty state
- **AND** it does not manufacture a joint conclusion, task, score, Run or response; historical inputs and source ownership stay unchanged.

#### Scenario: Open an existing Run deep link
- **WHEN** a user follows a Case Run link or opens a Run without a Case
- **THEN** the selected Run and all six detail views remain accessible, with a Case overview return link when applicable
- **AND** opening the Case overview does not silently select one Run as the whole-case result.
