# security-reference-ui-prototype Specification

## Purpose
Provide an independent browser-local AiSOC frontend prototype of the documented alert, incident and Case list/detail workflows, using mock data to review page structure and interactions before backend integration.

## Requirements

### Requirement: Three reference workspaces
The prototype SHALL provide alert, incident and Case workspaces using the selected official layouts and document examples or mock data.

#### Scenario: Navigate the three workspaces
- **WHEN** the user selects alerts, incidents or Cases
- **THEN** the corresponding workspace renders with working internal tabs and details
- **AND** unrelated global navigation labels do not open additional implemented modules.

### Requirement: Alert browsing and local management
The prototype SHALL support alert search, filters, sorting, pagination, column selection, details and local management. The main alerts table SHALL retain processing status, omit investigation status and classification columns, and show one alert occurrence time column instead of first and last activity columns. Column selection, time filtering, sorting and export SHALL follow this main table definition without changing embedded incident or Case alert tables.

#### Scenario: Save an alert classification
- **WHEN** a user updates an alert's owner, status or classification and saves
- **THEN** views that display the field show the same updated value
- **AND** classification remains available in alert details and management without a main-list classification column
- **AND** cancellation does not change saved values.

#### Scenario: Review the adapted main table
- **WHEN** a user opens the main alerts list
- **THEN** processing status and one alert occurrence time are available in the table and column selection
- **AND** investigation status, classification, first activity and last activity are not offered as main table columns
- **AND** date filtering, time sorting and CSV export use the same occurrence timestamp
- **AND** existing quick filters and embedded incident/Case alert tables retain their behavior.

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

### Requirement: Focused main-list alert management
The prototype SHALL offer status, assignee and comment in selected-alert management opened from the main alerts list, without a classification input. Saving SHALL preserve each alert's existing classification. Other workspaces and detail management SHALL retain their current fields.

#### Scenario: Manage selected main-list alerts
- **WHEN** the user selects one or more alerts in the main list and opens management
- **THEN** the form offers status, assignee and comment but no classification
- **AND** saving applies the selected values without changing classification
- **AND** cancelling leaves all alert data unchanged.

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

### Requirement: Integrated alert detail workspace
The prototype SHALL provide overview, timeline, raw data and response tabs in the existing light style. Pregenerated explanation SHALL appear in What happened without a generation trigger. Original Overview confidence summary, metadata, MITRE, IOC, Case and analyst-feedback functions SHALL be combined with equivalent sections. The response tab SHALL distinguish execution status, completeness, performed steps, tool results, proposed actions and reports using local mock data.
#### Scenario: Inspect and act on an alert
- **WHEN** the analyst opens an alert detail
- **THEN** four tabs show that alert's material, occurrence and management history, raw fixture and run records
- **AND** missing material is identified without inventing successful execution
- **AND** Case association, simulated investigation and analyst feedback update only browser-local mock state.

#### Scenario: Choose Case association mode
- **WHEN** the analyst selects an existing Case
- **THEN** a name or ID search lists the seven most recently active Cases by default and hides the new Case name input
- **AND** the header investigation action uses the selected Case, while new mode offers a title and creates a Case.

#### Scenario: Review lifecycle and asset context
- **WHEN** the analyst reviews the alert
- **THEN** the timeline shows occurrence, detection, ingestion, investigation, evidence collection and recorded assignment or closure events
- **AND** processing inputs and outputs remain in the response processing section
- **AND** asset tags use related asset roles including Windows domain controller, file server and web server.

#### Scenario: Simplified Case picker
- **WHEN** the user opens the Case association dialog
- **THEN** recent Cases and search are shown only in the dialog
- **AND** an alert already linked to a Case cannot create another new Case
- **AND** an unlinked alert may create a Case using the alert description as the default name.

#### Scenario: Final detail presentation
- **WHEN** the user views the detail workspace
- **THEN** response recommendations precede the retained automatic process and distinguish pending approval from execution
- **AND** lifecycle events are ordered newest first with seconds
- **AND** related alert rows retain severity and occurrence time
- **AND** the standalone confidence and handoff cards are absent.

#### Scenario: Unlinked Case fixture
- **WHEN** the user opens alert-unassigned-case-001
- **THEN** it belongs to incident 262144 but no Case and has no automatic Run
- **AND** every fixture alert belongs to an existing incident.

#### Scenario: Locate the newly added alert
- **WHEN** the user opens the main alert list with default filters
- **THEN** alerts are sorted by occurrence time descending and the updated unlinked alert appears first
- **AND** this default sort does not change embedded incident or Case tables.

### Requirement: Stable main alert table sorting
The main alert table SHALL place severity and alert time second and third after alert name, excluding selection. Only severity and alert time SHALL be sortable. Indicators and accessible sort state SHALL distinguish inactive, ascending and descending states. Each visible column SHALL have a fixed width independent of row content, with horizontal scrolling when needed.
#### Scenario: Sort without layout shift
- **WHEN** the analyst sorts by severity or alert time
- **THEN** the rows and direction indicator update while column widths remain unchanged
- **AND** other main table headers have no sort button or indicator
- **AND** incident and Case tables retain their existing behavior.

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

### Requirement: Real replayed alert snapshot
The prototype SHALL preserve the approved layout, existing sample data and interactions. When explicitly authorized to demonstrate a new replay, it SHALL additionally display actual host21 alert records using the confirmed field contract, without snapshot labels, data-gap panels, replacement layouts, or fabricated missing values. Server-side mutation integration remains a separate scope.

#### Scenario: Display authorized replay data
- **WHEN** the analyst opens the alert list after an explicitly authorized replay
- **THEN** the new persisted alert records are available alongside the approved samples and use the existing columns, filters, sidebar and detail tabs
- **AND** severity, processing status, source, timestamps, ownership, asset tags, score and confidence follow the confirmed database mapping
- **AND** absent ownership or asset inventory matches remain empty rather than receiving sample values

#### Scenario: Present actual explanation and investigation materials
- **WHEN** the analyst opens a replayed alert detail
- **THEN** the existing happened-what region presents the actual Explain response summary and suggested actions without requiring a fixed open-questions field
- **AND** timeline and response materials use recorded events and artifacts without invented timestamps or successful actions
- **AND** a completed Run and partial investigation remain distinct

#### Scenario: Preserve unrelated reference pages
- **WHEN** new real alert data is added
- **THEN** existing incident and Case reference pages keep their approved design and data
- **AND** a real incident ID or an alert-owned Run identifier is not presented as a fabricated Case association

#### Scenario: Preserve the approved alert workspace
- **WHEN** a field-mapping exercise has not explicitly authorized new displayed records
- **THEN** the approved layout, sample data and interactions remain unchanged
- **AND** mappings and gaps are recorded separately in documentation

#### Scenario: Inspect a replayed alert
- **WHEN** the analyst reviews retained mapping documentation
- **THEN** actual host21 values, their source fields, missing data and raw evidence remain available
- **AND** displaying additional actual records requires explicit replay/display authorization

### Requirement: Explicit graph context and relationships
The reference incident and Case workspaces SHALL derive graph scope from their member alerts, use explicit fixture relationships with meaning and provenance, and separate potential reach from recorded associations.

#### Scenario: Inspect and expand context
- **WHEN** an analyst selects an alert, entity, relationship or associated-incidents view
- **THEN** the graph and context panel explain the selected object and its scope
- **AND** viewing, filtering, grouping or replay does not change alert membership or trigger an investigation
- **AND** moving to a different incident or Case clears stale graph state.

#### Scenario: Inspect a potential path
- **WHEN** an entity has a defined potential path
- **THEN** the workspace can show its target and typed connections as potential impact
- **AND** entities without paths show a normal empty state instead of invented connections.

### Requirement: Case work tracking without alert closure
The Case workspace SHALL support browser-local tasks and management fields grounded in the selected official documentation, while preserving the existing alert workspace and records.

#### Scenario: Close a Case
- **WHEN** an analyst saves a Case status, classification, closing note or due date
- **THEN** the Case reflects those fields and records the management activity
- **AND** its alerts retain their individual statuses.

#### Scenario: Review investigation scope
- **WHEN** an analyst opens investigations or changes Case alert membership
- **THEN** investigations shown correspond to the current member alert IDs
- **AND** a scope without investigation records shows an empty state.

#### Scenario: Keep alert pages intact
- **WHEN** the main alert list, preview or detail opens with the same input state
- **THEN** its existing presentation and behavior remain unchanged
- **AND** the six actual replay records receive no invented graph or investigation material.
