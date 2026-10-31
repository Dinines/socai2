## ADDED Requirements

### Requirement: Current workspace and historical versions remain distinct
The frontend SHALL use the current V2 workspace as its single active design entry and preserve previous frontend files and verification history without deleting examples.

#### Scenario: Open the latest workspace after refresh
- **WHEN** a user opens the current Case list or a former source-filter URL
- **THEN** all original and recorded examples remain accessible in the same list without source-category tabs or extra import banners
- **AND** stored source identities, browser edits, historical inputs and actual incomplete outcomes are preserved.

### Requirement: Illustrative materials cover current workspace views
The frontend SHALL provide complete illustrative material for the existing design example without representing it as actual AiSOC execution or supplementing recorded Runs.

#### Scenario: Inspect the complete design example
- **WHEN** a user selects the designated design Run
- **THEN** inputs, stages, queries, evidence, graph, activity, report and proposed responses are inspectable using coherent fixture identities
- **AND** the fixture remains recorded=false, has no invented real usage, and is identified in the handoff documentation.

#### Scenario: Inspect an actual Run with missing material
- **WHEN** a user selects any recorded AiSOC Run
- **THEN** its original saved material and unavailable values remain unchanged
- **AND** design fixtures are never used to fill its report, tools, graph, actions or completeness.

## MODIFIED Requirements

### Requirement: Recorded AiSOC examples preserve source relationships
V2 SHALL append the six saved AiSOC20 alert results and six Runs without replacing existing examples, and SHALL preserve the distinction between local presentation Cases and backend Case relationships in source data and handoff documentation. Partial completion, skipped stages, absent metadata and absent executed actions SHALL remain visible without fabricated values.

#### Scenario: Inspect an imported local Case
- **WHEN** a user opens a local AiSOC20 Case
- **THEN** the page shows its actual single-alert Runs and saved reports without extra import labels, and source data retains null source Case identities
- **AND** a skipped attack-path stage is shown as skipped, while the separate case graph contains only recorded direct relationships for its current members

#### Scenario: Inspect same-host alerts across environments
- **WHEN** related or similar alerts are shown for an imported alert
- **THEN** candidates are restricted to the same source environment and tenant, and raw entities without inventory relationships receive no invented inventory identifiers or scores

### Requirement: Local Cases collect saved alert-flow materials without rewriting source ownership
V2 SHALL present local Case collections whose provenance remains in source data and handoff documentation for the saved Fusion groups and make their existing assessments, investigation records, queries, artifacts, reports and source relations accessible. Source Case identity and Run inputs SHALL remain unchanged, and collection management SHALL remain separate from saved analysis and executed responses.

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
- **THEN** saved AiSOC Cases and original examples remain accessible without source-category tabs or import banners, with sources retained in data and handoff documentation and statistics reflecting the selected list
- **AND** saved local Case collections expose all referenced Runs without rewriting their inputs or backend ownership.

#### Scenario: Follow recorded relationships
- **WHEN** the user moves between a saved Case and incident
- **THEN** only their actual member relationships determine links and selected material
- **AND** missing incident identities or unavailable detail IDs do not silently open an unrelated example.
