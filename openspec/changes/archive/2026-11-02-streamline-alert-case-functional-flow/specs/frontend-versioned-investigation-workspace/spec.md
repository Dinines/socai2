## ADDED Requirements

### Requirement: Manual alert investigation enters Case preparation
V2 SHALL route manual investigation from an alert into the common Case preparation workflow without creating an alert-local pending Run.
#### Scenario: Prepare a linked alert
- **WHEN** the user selects preparation on an alert with one Case, or explicitly chooses among multiple linked Cases
- **THEN** the selected Case draft form preselects that alert without saving a draft, changing membership or adding history merely on entry
- **AND** cancellation writes nothing; real execution remains unavailable and simulation retains its one-active-Run rule.
#### Scenario: Associate before preparation
- **WHEN** the alert has no Case and the user explicitly confirms an eligible association or Case creation
- **THEN** the association is saved and the Case draft form opens with that alert selected
- **AND** source and tenant scope are preserved, only explicit draft saving creates preparation, and no Run is started or invented.

### Requirement: Incident management excludes independent security classification
V2 SHALL keep incident lifecycle management separate from alert and Case judgments.
#### Scenario: Edit an incident
- **WHEN** the user edits a single incident or a batch
- **THEN** no independent true-threat/false-positive classification control is offered, and the incident header does not present an independent classification
- **AND** historical classification fields are preserved, while existing status, ownership and resolution behavior remains unchanged.

### Requirement: Run response proposals have one review location
V2 SHALL present each response proposal once in the response control section with its target, rationale and applicable review decision.
#### Scenario: Read or review an action
- **WHEN** a user opens report and response or reviews a specific proposal
- **THEN** the original action index and content determine the decision, the decision does not imply execution, and targetless or approval-free suggestions remain readable
- **AND** report text and all execution records remain intact; execution is associated with a proposal only by an explicit unambiguous identifier.

### Requirement: Investigation reading prioritizes results over repeated technical detail
V2 SHALL retain Case results and next work while replacing the repeated overview history list with a history entry, and expose execution details through a secondary analysis entry.
#### Scenario: Read overview and execution details
- **WHEN** users open Case overview, AI analysis or an existing ledger deep link
- **THEN** per-Run scope and full history remain accessible, five primary detail tabs remain, and original ledger records and technical statistics are available under execution details
- **AND** failures, stopping reasons and key limitations remain visible without requiring technical-log inspection.

### Requirement: Exploration selection does not claim draft creation
V2 SHALL distinguish selecting investigation material and saving exploration progress from saving an investigation draft.
#### Scenario: Select graph material
- **WHEN** users select nodes or save exploration
- **THEN** labels describe selected material or exploration progress, without claiming a draft has already been saved
- **AND** existing explicit preparation, membership and Run boundaries remain unchanged.

### Requirement: All Case sources share one presentation pipeline
V2 SHALL normalize investigation records through one reader and use the same Case routes, graph components and preparation workflow for reference, saved and newly created Cases.
#### Scenario: Open different data sources
- **WHEN** a Case or Run has complete, partial or missing material
- **THEN** the same navigation and components render the available data, with shared empty states for missing fields and no legacy page fallback
- **AND** source adapters preserve original records and tenant ownership, without copying demonstration results into saved records.
