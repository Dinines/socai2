## ADDED Requirements

### Requirement: Focused main-list alert management
The prototype SHALL offer status, assignee and comment in selected-alert management opened from the main alerts list, without a classification input. Saving SHALL preserve each alert's existing classification. Other workspaces and detail management SHALL retain their current fields.

#### Scenario: Manage selected main-list alerts
- **WHEN** the user selects one or more alerts in the main list and opens management
- **THEN** the form offers status, assignee and comment but no classification
- **AND** saving applies the selected values without changing classification
- **AND** cancelling leaves all alert data unchanged.
