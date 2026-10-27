## ADDED Requirements

### Requirement: Main alert assignee quick filter
The main alert list SHALL offer All alerts and Assigned to me beside its existing quick filters using the same style. Assigned to me SHALL select the current mock user's owner value, while All alerts SHALL clear only that owner condition. Switching SHALL reset pagination and combine with existing filters and search.

#### Scenario: Filter alerts assigned to the current user
- **WHEN** the user chooses Assigned to me
- **THEN** only alerts assigned to the current mock user match the owner condition
- **AND** the owner filter dialog reflects the same value
- **AND** selecting All alerts clears only owner and returns to the first page.

#### Scenario: Select another assignee
- **WHEN** another owner is selected in the filter dialog
- **THEN** that condition remains visible as a filter chip
- **AND** neither assignee quick option falsely indicates that no owner condition or the current user's condition is active.
