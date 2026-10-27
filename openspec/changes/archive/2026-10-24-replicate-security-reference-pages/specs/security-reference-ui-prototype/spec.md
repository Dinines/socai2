## ADDED Requirements

### Requirement: Three reference workspaces
The prototype SHALL provide alert, incident and Case workspaces using the selected official layouts and document examples or mock data.

#### Scenario: Navigate the three workspaces
- **WHEN** the user selects alerts, incidents or Cases
- **THEN** the corresponding workspace renders with working internal tabs and details
- **AND** unrelated global navigation labels do not open additional implemented modules.

### Requirement: Alert browsing and local management
The prototype SHALL support alert search, filters, sorting, pagination, column selection, details and local management.

#### Scenario: Save an alert classification
- **WHEN** a user updates an alert's owner, status or classification and saves
- **THEN** its list and detail show the same updated values
- **AND** cancellation does not change saved values.

### Requirement: Incident context and graph
The prototype SHALL provide an attack story, linked graph, summary and incident tabs for alerts, activities, assets, investigations, evidence and recommendations.

#### Scenario: Focus a graph entity
- **WHEN** a user selects an alert or graph node and applies filters
- **THEN** the context panel and visible graph correspond to that selection
- **AND** potential blast-radius paths are identified separately from observed activity.

### Requirement: Incident queue and focused navigation
The prototype SHALL provide an incident queue as the default incident entry, separate from incident detail, and SHALL use AiSOC branding with alerts and incidents as separate primary navigation items.

#### Scenario: Open an incident from the queue
- **WHEN** the user opens Incidents from navigation
- **THEN** multiple mock incidents are shown with search, filters, priority, status, ownership and linked alert counts
- **AND** selecting an incident name opens its detail while previewing its row opens a summary pane.

#### Scenario: Manage selected incidents
- **WHEN** the user saves owner, classification, tags or resolution for one or more selected incidents
- **THEN** the queue and detail reflect the same local values
- **AND** new owner assignments and incident resolution update linked mock alerts according to the reference workflow.

### Requirement: Case material workspace
The prototype SHALL provide Case overview, alerts, assets, evidence, investigations, activities and comments/attachments in an internal directory.

#### Scenario: Review or move a Case alert
- **WHEN** the user views a Case alert or moves it to another mock Case
- **THEN** the referenced alert is reused and both Case membership counts update
- **AND** no backend or model is called.

### Requirement: Documented Case list entry
The prototype SHALL open a Case list at the Cases navigation entry using the official Prioritize incident cases screenshots and prose, with Incident and Generic labels, four summary cards, list tools, filter sets and case rows.

#### Scenario: Browse cases before opening details
- **WHEN** the user selects Cases
- **THEN** multiple cases are listed with search, filters, sorting, pagination, time ranges and column customization
- **AND** row preview remains in the list while selecting a case name opens the detail workspace
- **AND** its Cases breadcrumb returns to the list.

#### Scenario: Apply documented case prioritization
- **WHEN** the user filters by priority score or saves a filter set
- **THEN** top priority means above 85, medium means 15 through 85, and low means below 15
- **AND** a saved filter set can be reapplied after reload.

#### Scenario: Preserve reference scope
- **WHEN** the user sees Generic, create, settings or the Similar cases directory entry
- **THEN** those labels do not introduce additional modules or an invented similarity workflow.

### Requirement: Browser-local mock operations
The prototype MUST limit all management, approval, comments and simulated response actions to local mock state and offer a reset.

#### Scenario: Approve a mock response
- **WHEN** a user approves or rejects a pending mock action
- **THEN** the evidence and activity views reflect the result
- **AND** no real security action, account access or external service request occurs.
