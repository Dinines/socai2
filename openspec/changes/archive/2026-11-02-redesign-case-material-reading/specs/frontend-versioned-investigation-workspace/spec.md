## ADDED Requirements

### Requirement: Case materials provide an immediate reading context
V2 SHALL provide a selectable object list with a directly visible detail pane and a separate in-page investigation-material view within the consolidated materials workspace.
#### Scenario: Open or filter the object workspace
- **WHEN** a Case material page opens or the user selects, searches or filters an object
- **THEN** a matching object is visibly selected with its explicit evidence and source alerts, or a recoverable empty state is shown
- **AND** default ordering reflects member-alert counts rather than inferred risk, unlinked evidence remains accessible, and switching Cases clears prior viewing context.
#### Scenario: Inspect saved investigation materials
- **WHEN** the investigation-material view is selected or a Case has neither objects nor unlinked evidence but has saved Runs
- **THEN** each Run retains its own input scope, query/report links and artifact catalog with saved hashes and content access
- **AND** displaying, selecting or filtering writes no business records and never treats a source relationship as model adoption or a new judgment.
