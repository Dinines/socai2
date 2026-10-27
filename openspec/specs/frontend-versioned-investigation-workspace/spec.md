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
