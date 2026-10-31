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
V2 SHALL append the six saved AiSOC20 alert results and six Runs without replacing existing examples, and SHALL preserve the distinction between local presentation Cases and backend Case relationships in source data and handoff documentation. Partial completion, skipped stages, absent metadata and absent executed actions SHALL remain visible without fabricated values.

#### Scenario: Inspect an imported local Case
- **WHEN** a user opens a local AiSOC20 Case
- **THEN** the page shows its actual single-alert Runs and saved reports without extra import labels, and source data retains null source Case identities
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
- **AND** missing source management values remain preserved while local handling state follows the default and assignment rules; group statistics use the same source set and reading does not create a Case or launch an investigation.

### Requirement: Saved Run records and readable materials retain provenance
V2 SHALL display all saved event records in the selected socai2 Run and offer its available artifact contents with source identity and retention limits. Public projections SHALL exclude prompts and hidden reasoning, escape content, and distinguish filtered extracts from full originals.

#### Scenario: Inspect records and materials
- **WHEN** the user selects one of the saved Runs or an artifact within it
- **THEN** the Run's saved event rows include model-call and usage records, and any displayed artifact belongs to that Run
- **AND** original hashes identify source content; filtered or unavailable bodies, partial completion and absent executions remain explicit.

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

### Requirement: Incident queue context uses explicit source meanings
V2 SHALL expose in-progress incident counts, member host names and asset tags under the neutral shared asset label 涉及资产 without inventing incident priority or management state. Preview controls SHALL distinguish a side pane from row expansion. Its compact summary SHALL expose active, unassigned, recent-alert and high-severity incident counts instead of a missing-state count.

#### Scenario: Read incident queue context
- **WHEN** the incident queue and preview are opened
- **THEN** the primary card is labeled 处理中的事件 and counts each incident whose effective local handling status is In progress once, independent of Run state; its caption is 已开始处理，尚未解决, tags come from member assets, and host names come from saved member context
- **AND** alert and incident asset labels use 涉及资产 without changing values or claiming confirmed impact; missing source incident state remains retained separately from local handling defaults and alert verdict confidence is never substituted for incident priority.

#### Scenario: Retain saved source records
- **WHEN** incident context is displayed or filtered
- **THEN** source event management tags, member records, source scores, historical Runs and browser edits remain unchanged
- **AND** the preview control opens the existing side pane while the incident title opens the incident page.

#### Scenario: Read the four summary metrics
- **WHEN** the incident queue renders or is refreshed
- **THEN** the recent-alert metric counts each incident once when a member alert occurred within the preceding 24 hours up to the current time, excluding future or invalid timestamps
- **AND** active, unassigned and high-severity counts retain their separate source meanings, all four remain visible at narrow widths, and historical timestamps are never shifted to create recent activity.

### Requirement: Incident preview presents whole-event context
The V2 saved-incident preview SHALL present an incident overview based on current member context and associated investigation progress instead of a per-alert triage-score panel. Missing incident-level assessments and priorities SHALL remain explicit and source data SHALL remain unchanged.

#### Scenario: Read a saved incident preview
- **WHEN** a user opens a saved incident preview
- **THEN** the overview summarizes its member count, known hosts, recorded alert clues and started investigations counted once per Run
- **AND** per-alert confidence and verdicts are not promoted to an incident score or overall verdict, partial delivery remains distinct, and triage-only Runs are excluded from started investigation counts.

#### Scenario: Read an incident with missing management state
- **WHEN** a saved incident has no recorded handling state
- **THEN** the preview uses New by default or In progress when assigned, retaining the missing source state separately
- **AND** the original source records, investigation outcomes and example content remain unchanged; a local handling default does not imply an investigation outcome.

### Requirement: Local incident lifecycle follows assignment and explicit resolution
V2 SHALL default incidents with missing handling state to New, transition New incidents assigned to a named person to In progress, and resolve incidents only on explicit user action. The incident label for In progress SHALL be 处理中. Source records and investigation results SHALL remain separate from browser-local handling state.

#### Scenario: Initialize or reload incident management
- **WHEN** an incident has missing source handling state
- **THEN** its local status becomes New or In progress if already assigned, retaining the original source status separately
- **AND** existing resolved or in-progress local states are preserved on reload and reset applies the same defaults to restored examples.

#### Scenario: Assign an unresolved incident
- **WHEN** a user assigns a New incident to a named person, individually or in a batch
- **THEN** saving transitions it to In progress and records the change locally
- **AND** empty, unrecorded or unassigned owner placeholders do not start processing; reassignment alone does not reopen a resolved incident.

#### Scenario: Explicitly resolve an incident
- **WHEN** a user explicitly selects Resolved and supplies a resolution note
- **THEN** the incident resolves using the existing member-alert synchronization
- **AND** missing notes block the operation, while investigation completion, partial results and member alerts never resolve the incident automatically.

### Requirement: Incident detail consolidates overview and relationship navigation
V2 SHALL provide a single incident overview containing event description and information, alert-stage distribution, chronological member-alert activity and association evidence. It SHALL remove the incident-switch dialog entry while preserving navigation back to the incident list. It SHALL expose only a current-incident relationship graph; Attack Chain and Attack Path SHALL remain Case investigation capabilities. Legacy incident chain links SHALL open the current-incident graph without rendering candidate-chain results.

#### Scenario: Open the incident overview
- **WHEN** a user opens an incident summary or its former context link
- **THEN** event information, member-alert stages and timeline, and association evidence are directly available in the overview; the relationship graph is shown only in the relationship-analysis tab without a duplicate overview graph
- **AND** member/assessment/investigation/material features remain accessible, missing actual timestamps remain missing, and no extra investigation or source data is generated.

#### Scenario: Explore relationships and candidate chains
- **WHEN** a user opens the relationship graph or a former incident chain link
- **THEN** only current member alerts and their recorded relationships are displayed, with no chain selector, associated-incident expansion or potential-path exploration
- **AND** Case investigation Chain and Path results remain accessible with their original sources and completeness.

#### Scenario: Explain membership and hand off judgment to Case
- **WHEN** a user opens an incident
- **THEN** the overview explains the incident, shows shared-object associations with source-alert links and links to its relationship-analysis tab, without presenting per-alert scores as an incident judgment
- **AND** absent grouping rules are not inferred from common entities or timestamps.

#### Scenario: Continue in a Case
- **WHEN** a user continues from an incident to deeper judgment
- **THEN** existing business Cases can be opened, or an incident with no Case offers a New Case action that opens the new-case form by default with its incident title and all current member alerts; association with an existing Case remains an alternative
- **AND** local confirmation preserves other memberships and historical Runs, does not start an investigation, and prevents duplicate creation when a Case already exists.

### Requirement: Incident graphs share presentation without borrowing source relationships
V2 SHALL render recorded and illustrative incidents in the same reference graph workspace with circular nodes, alert list, graph controls and contextual details. Recorded incident graphs SHALL retain source alert-to-object associations and SHALL NOT acquire illustrative relationships, paths, risk or inventory values.

#### Scenario: Inspect a recorded incident graph
- **WHEN** the user opens a recorded incident relationship analysis
- **THEN** existing member alerts and their recorded objects appear in the common graph restricted to the current incident, with filtering, grouping, layout, zoom, playback and source drill-down
- **AND** grouping retains original endpoints and alert sources, absent event times remain absent, and Case path material remains separate from the incident graph.

#### Scenario: Expand source relationships
- **WHEN** a user opens or filters an incident graph, including with stale graph controls from an earlier view
- **THEN** the graph remains limited to current incident members and their objects, without associated-incident or potential-path controls
- **AND** viewing does not change incident membership, alert records or historical Runs.

### Requirement: Incident layout prioritizes context and relationship space
V2 SHALL present the approved incident capabilities with a compact overview, a graph-focused relationship analysis and core default list columns while preserving data, the five incident tabs ordered as overview, relationship analysis, member alerts, objects and activities, queue metrics and Case investigation boundaries.

#### Scenario: Read a compact incident overview
- **WHEN** a user opens an incident overview
- **THEN** ATT&CK stage coverage appears above the event description card, and the description, occurrence range and compact member/host counts remain visible without repeating header handling metadata or separate object/shared-object metric cards
- **AND** object totals remain on the object tab, shared-object counts and source alerts remain in association evidence, and no value or membership changes.

#### Scenario: Use the incident relationship graph
- **WHEN** a user opens incident relationship analysis
- **THEN** counts and filters occupy a compact toolbar with the source filter labeled 数据来源 and no 仅此事件 scope label above the existing three-column circular graph, without a repeated large page title
- **AND** graph controls, current-incident boundaries and Case/Run graph presentation remain unchanged.

#### Scenario: Read and customize incident tables
- **WHEN** a user opens an incident list or member-alert list without a custom column selection
- **THEN** core identification, severity, handling, asset, ownership and time information are prioritized; all original optional columns remain available through customization
- **AND** an incident ID column uses a compact display with its full value available and copyable, existing custom selections and export values remain intact, and queue metric values and alignment stay unchanged.

### Requirement: Incident and alert showcases preserve recorded data boundaries
V2 SHALL retain saved AiSOC records and existing examples while providing separate, coherent incident-and-alert demonstration scenarios with fixed identities, complete available materials and explicit internal fixture provenance. Documentation SHALL identify actual records, source paths, missing fields and local-only actions.

#### Scenario: Align recorded fields
- **WHEN** a user opens a saved AiSOC alert or incident
- **THEN** available source, severity, timestamps, scores, membership and processing materials follow the saved source mapping
- **AND** absent Explain, inventory, ownership, incident scoring, merge rules and response receipts remain absent and documented rather than supplemented with fixture values.

#### Scenario: Explore complete demonstrations
- **WHEN** the user opens the new in-progress, unassigned or resolved scenarios
- **THEN** the incident's five tabs and alert's four tabs have coherent descriptions, objects, relationships, raw records, timelines and relevant processing material, with linked-Case and no-Case entry branches
- **AND** full, partial and triage-only execution are distinguished from handling status, judgment, approval and execution.

#### Scenario: Reload without replacing edits
- **WHEN** the fixtures are merged into a new or saved browser workspace more than once
- **THEN** stable identities prevent duplicates, prior records and edits remain intact, and source records or historical Runs are never enriched by demonstration materials.
