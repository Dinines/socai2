## ADDED Requirements

### Requirement: Case information uses a consistent presentation across sources
V2 SHALL use the same Case information layout and member-alert, object, alert-evidence and investigation metrics for illustrative and recorded Cases.
#### Scenario: Open Cases from different sources
- **WHEN** a user opens any Case information page
- **THEN** summary, details, member alerts, ATT&CK stages and objects use the same presentation structure, with actual values or missing states
- **AND** saved artifacts are not substituted for alert evidence and no overall AI conclusion is invented.

### Requirement: Case relationship views show current membership only
V2 SHALL show current member-alert-to-object relationships in the shared circular Case graph and retain Chain, Path and reachability results in their respective Runs.
#### Scenario: Inspect or revise Case membership
- **WHEN** the Case graph is opened with changed members or stale expansion controls
- **THEN** only current members and their recorded object links are shown, without associated-event or potential-path expansion
- **AND** historical Run inputs and saved graph materials remain unchanged and accessible.

### Requirement: Investigation graph source navigation retains reading context
V2 SHALL expose Chain, Path and reachability selection before the graph and preserve explicit source disclosure state through same-Run redraws.
#### Scenario: Switch or inspect source material
- **WHEN** a user selects a source kind or opens and closes an alert preview from graph material
- **THEN** the selected material remains available without unintended collapse, same-Run kind switching retains the reading position, and manual collapse remains respected on redraw
- **AND** switching Runs does not carry old disclosure state or change stored investigation data.
