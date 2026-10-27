## ADDED Requirements
### Requirement: Simplified alert navigation
The alert preview SHALL omit the similar-alert action. The Case dialog SHALL provide mutually exclusive existing-link and new-Case tabs, defaulting to existing-link. Already linked alerts SHALL disable new-Case creation. Asset links in alert views SHALL open a placeholder detail page containing a large heading with the asset name.
#### Scenario: Choose a Case mode
- **WHEN** an unlinked alert opens the Case dialog
- **THEN** existing-link search and recent Cases appear by default
- **AND** switching to new-Case shows only the default description-based name field
- **AND** an already linked alert cannot select or submit new-Case creation.
#### Scenario: Open an affected asset
- **WHEN** an analyst follows an asset link from the alert table or detail
- **THEN** the asset placeholder page opens with its heading and no additional business features.
#### Scenario: Read the compact alert preview
- **WHEN** the analyst opens an alert preview
- **THEN** only overview remains and classification is absent
- **AND** alert information shows ID, occurrence time, assignee, detection source and asset tags, while severity, state and category remain at the top.
