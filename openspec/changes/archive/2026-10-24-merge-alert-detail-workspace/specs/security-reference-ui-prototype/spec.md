## ADDED Requirements
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
