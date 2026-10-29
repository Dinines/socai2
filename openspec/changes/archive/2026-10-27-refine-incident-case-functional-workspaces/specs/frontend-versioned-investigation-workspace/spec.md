## ADDED Requirements

### Requirement: Incident assessment summaries retain provenance
The V2 incident workspace SHALL summarize member alerts, their existing dispositions and basic investigation material, and linked Runs without assigning a Run-wide finding to individual alerts or generating missing material.

#### Scenario: Inspect basic investigation coverage
- **WHEN** an incident contains alerts with saved triage, Explain, or linked investigations
- **THEN** the summary exposes their alert or Run sources and counts each covered member alert once
- **AND** missing findings remain missing and reading or filtering does not alter membership or material.

### Requirement: Investigation overview prioritizes analyst outcomes
The V2 investigation overview SHALL present findings, inspectable material, recorded work, available limitations and response information for the selected Run before expanded execution metadata.

#### Scenario: Review a partial investigation
- **WHEN** an analyst selects a partial Run
- **THEN** its findings, saved queries, stop reason, available missing-data details, and proposed versus executed actions are presented separately
- **AND** input-alert evidence is not asserted to have been adopted by the model without a recorded adoption relationship.

### Requirement: Case context and Run material have distinct navigation
The V2 Case workspace SHALL distinguish current case materials, selected investigation results and collaboration while retaining existing routes and interactions.

#### Scenario: Switch an investigation
- **WHEN** an analyst switches Runs from an investigation detail view
- **THEN** all investigation contents use that Run and the current detail section remains selected
- **AND** current Case membership does not rewrite historical Run inputs or imply that all Case members were investigated.

#### Scenario: Combine foundational Case work with AiSOC investigation functions
- **WHEN** an analyst opens a selected Run within a Case
- **THEN** stage analysis, query evidence, attack chain and path material, filterable investigation records, and report and response views are available beside the existing Case materials and collaboration
- **AND** only recorded stages and payloads are shown; missing role output, evidence adoption, and response execution are not invented.
