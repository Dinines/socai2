# frontend-versioned-investigation-workspace Specification

## Purpose
Preserve a frozen frontend V1 for comparison while evolving a separate local V2 prototype that distinguishes incident context from Run-scoped AI investigation material, keeps alert presentation stable, and accurately represents saved inputs, completeness, graphs and response outcomes.

## Requirements

### Requirement: Frozen V1 and isolated V2
The frontend SHALL preserve the current version byte-for-byte as V1 and run V2 from a separate directory, loopback port and browser-state key.

#### Scenario: Compare versions
- **WHEN** the user opens V1 and V2
- **THEN** V1 retains its original frontend and fixtures
- **AND** changes or resets in V2 do not overwrite V1 files or browser state.

### Requirement: Incident context and investigation separation
V2 SHALL retain incident materials and management while presenting investigation detail in a Run-scoped workspace. Existing alert pages and records SHALL remain unchanged for equivalent input state.

#### Scenario: Open an incident investigation
- **WHEN** an analyst follows a recorded investigation from an incident
- **THEN** the workspace opens the matching Run with its scope, steps, outputs and completeness
- **AND** viewing or filtering does not trigger a new investigation or change membership.

### Requirement: Run-scoped investigation material
V2 SHALL expose Run selection, actual inputs, execution state, completeness, verdict, steps, tools, findings, source materials, chain graphs, reports and usage when available. Missing information SHALL remain missing and automatic Runs without Cases SHALL remain accessible.

#### Scenario: Change the selected Run
- **WHEN** an analyst selects another Run or opens an automatic Run without a Case
- **THEN** all displayed investigation material belongs to the selected Run
- **AND** no Case or successful step is fabricated.

#### Scenario: Read chain and path materials
- **WHEN** a saved Chain is empty, a Path is not linked, and an Alert Graph succeeded
- **THEN** their statuses are displayed separately with available source and query context
- **AND** graph associations or reachable entities are not described as confirmed attack causality.

#### Scenario: Review a partial result
- **WHEN** a Run has ended but its investigation is partial
- **THEN** the workspace separately shows the Run state, partial delivery, verdict and recorded stop reasons
- **AND** a report or proposed action is not treated as complete investigation or executed response.

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

### Requirement: Recorded AiSOC examples preserve source relationships
V2 SHALL append the six saved AiSOC20 alert results and six Runs without replacing existing examples, and SHALL distinguish three local presentation Cases from backend Case relationships. Synthetic input provenance, partial completion, skipped stages, absent metadata and absent executed actions SHALL remain visible without fabricated values.

#### Scenario: Inspect an imported local Case
- **WHEN** a user opens a local AiSOC20 Case
- **THEN** the page identifies it as a local grouping of historical demonstration alerts, shows the actual single-alert Runs and saved reports, and retains null source Case identities
- **AND** a skipped attack-path stage is shown as skipped, while the separate case graph contains only recorded direct relationships for its current members

#### Scenario: Inspect same-host alerts across environments
- **WHEN** related or similar alerts are shown for an imported alert
- **THEN** candidates are restricted to the same source environment and tenant, and raw entities without inventory relationships receive no invented inventory identifiers or scores

### Requirement: Persisted Case investigation retains joint scope and saved artifacts
V2 SHALL display the saved historical Case and its joint investigation using original Case/Run identities and saved input members. It SHALL present adopted four-stage results, actual tool returns, saved chain/path/reachability artifacts and report without converting candidate alerts into Case members, Run completion into delivery completeness, or dry-run proposals into executions.

#### Scenario: Inspect the saved Case chain and path
- **WHEN** the historical three-alert Case is opened
- **THEN** its Run shows the five saved chain candidates, eleven path nodes and fifteen edges, and sixteen graph-reachable entities with their original sources and scope
- **AND** external candidates remain outside the Case and graph reachability is not presented as confirmed victim scope

#### Scenario: Inspect adopted analysis and missing metadata
- **WHEN** the user opens the historical stages or an input alert
- **THEN** four-stage results and the joint Case investigation remain distinguishable from individual alert triage, while missing status, scoring, completeness, attachments or inventory relationships are not filled from demo templates

### Requirement: Saved alert-flow groups populate incident workspaces
V2 SHALL append incident rows grouped by saved Fusion incident identity and tenant while preserving prior fixtures and browser edits. Member facts and investigation links SHALL be available without fabricating incident management values, inventory relationships, executed actions, or a Case.

#### Scenario: Open a saved Fusion group
- **WHEN** the six saved socai2 alerts are loaded
- **THEN** their three groups each expose two actual members, source objects, times, basic assessments and matching Runs
- **AND** missing incident management values remain unknown; group statistics use the same source set and reading does not create a Case or launch an investigation.

### Requirement: Saved Run records and readable materials retain provenance
V2 SHALL display all saved event records in the selected socai2 Run and offer its available artifact contents with source identity and retention limits. Public projections SHALL exclude prompts and hidden reasoning, escape content, and distinguish filtered extracts from full originals.

#### Scenario: Inspect records and materials
- **WHEN** the user selects one of the saved Runs or an artifact within it
- **THEN** the Run's saved event rows include model-call and usage records, and any displayed artifact belongs to that Run
- **AND** original hashes identify source content; filtered or unavailable bodies, partial completion and absent executions remain explicit.

### Requirement: Local Cases collect saved alert-flow materials without rewriting source ownership
V2 SHALL present explicitly local Case collections for the saved Fusion groups and make their existing assessments, investigation records, queries, artifacts, reports and source relations accessible. Source Case identity and Run inputs SHALL remain unchanged, and collection management SHALL remain separate from saved analysis and executed responses.

#### Scenario: Inspect a local Case from the six saved alerts
- **WHEN** the saved alert-flow records are loaded
- **THEN** three local Cases each collect two original members and reference their existing single-alert Runs
- **AND** the Case overview summarizes per-Run results and partial delivery without inventing a joint conclusion, backend Case, attack path, classified evidence, task or executed action.

#### Scenario: Revise current membership
- **WHEN** current members of a local Case are changed
- **THEN** member facts and the current relationship view follow that membership while saved Run references retain their original input and same-environment tenant scope
- **AND** reload preserves browser edits and source records remain unchanged.

### Requirement: Consolidated Case data remains source coherent
V2 SHALL keep original examples and recorded AiSOC Cases accessible together while placing saved Cases prominently and linking Case, incident, member and investigation material by recorded identities. All saved Cases SHALL expose their available query, artifact, report and activity material without borrowing missing values or relationships from examples.

#### Scenario: Browse all Case data
- **WHEN** the user opens the Case list
- **THEN** saved AiSOC Cases and original examples remain accessible with distinguishable sources and statistics reflecting the selected list
- **AND** saved local Case collections expose all referenced Runs without rewriting their inputs or backend ownership.

#### Scenario: Follow recorded relationships
- **WHEN** the user moves between a saved Case and incident
- **THEN** only their actual member relationships determine links and selected material
- **AND** missing incident identities or unavailable detail IDs do not silently open an unrelated example.
