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
- **AND** a skipped attack-path stage is shown as skipped; its Case graph uses the latest eligible completed Run and any explicitly labelled saved context is limited to that Run's original inputs.
#### Scenario: Inspect same-host alerts across environments
- **WHEN** related or similar alerts are shown for an imported alert
- **THEN** candidates are restricted to the same source environment and tenant, and raw entities without inventory relationships receive no invented inventory identifiers or scores.

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

### Requirement: Unified Case overview preserves per-Run scope
V2 SHALL open every Case overview as a current-case summary with per-Run results and recorded next work side by side at wide widths and stacked at narrow widths, while preserving access to Case and Run detail capabilities.

#### Scenario: Read a Case with independent alert results
- **WHEN** a Case contains saved single-alert analysis or no results
- **THEN** the overview presents current members separately from each Run's input, completeness and findings or an honest empty state
- **AND** it does not manufacture a joint conclusion, task, score, Run or response; historical inputs and source ownership stay unchanged.

#### Scenario: Open an existing Run deep link
- **WHEN** a user follows a Case Run link or opens a Run without a Case
- **THEN** the selected Run and all six detail views remain accessible, with a Case overview return link when applicable
- **AND** opening the Case overview does not silently select one Run as the whole-case result.

### Requirement: Analysis references resolve within the selected Run
V2 SHALL expose existing stage summaries and references in readable analysis, and allow exact navigation to saved queries or artifacts belonging to the selected Run without inferring absent adoption relationships.

#### Scenario: Inspect a referenced query
- **WHEN** a saved analysis references a query ID present in the same Run
- **THEN** the link shows that query with its original return and status, offers all queries and a return to analysis, and retains the selected Run
- **AND** unavailable returns remain distinguishable from no matches and from successful evidence.

#### Scenario: Invalid reference or changed Run
- **WHEN** a query ID is absent from the selected Run or the user switches Runs
- **THEN** an absent ID is reported without displaying another Run's content, and switching Runs clears the old detail selection while retaining the view
- **AND** viewing or navigating does not mutate stored materials, Case membership or source records.

### Requirement: Case objects and evidence share a workspace
V2 SHALL combine Case objects and evidence into one navigation entry while preserving prior object and evidence URLs, current member sources, all recorded evidence, and per-Run material access.
#### Scenario: Inspect consolidated materials
- **WHEN** a Case material workspace is opened
- **THEN** objects are deduplicated by recorded identity and expose linked member alerts and evidence, with unlinked evidence retained separately
- **AND** records are not promoted to malicious evidence or combined judgments; incident navigation and Run graph capabilities stay unchanged.

### Requirement: Case membership can be extended from within the Case
V2 SHALL allow explicit addition of selected alerts or the selected members of events within a coherent source and tenant scope.
#### Scenario: Add selected sources
- **WHEN** the user confirms addition
- **THEN** only eligible selected alerts are unioned into the current Case, duplicates are avoided, and other Cases and alert ownership are unchanged
- **AND** historic Run references and inputs remain accessible, while cancellation adds nothing and association starts no investigation.

### Requirement: Investigation preparation is separate from execution
V2 SHALL retain preparations separately from Runs, including explicit objectives, input alerts, entity targets and material references.
#### Scenario: Save an investigation preparation
- **WHEN** a user saves or revises a valid draft
- **THEN** historical Runs remain unchanged and saving never starts execution
- **AND** execution remains unavailable for real records; dedicated demonstration Cases may explicitly simulate a start and manual progress without claiming real model replies or backend execution.

### Requirement: Human follow-up and response decisions retain distinct effects
V2 SHALL let users record human follow-up results and review specific response proposals without treating task completion or approval as an investigation conclusion or executed response.
#### Scenario: Complete human follow-up
- **WHEN** a user completes a task
- **THEN** a result is required and recorded alongside owner, due date and optional existing source references
- **AND** current task counts and activities update locally but Run completeness, verdict, Case status and response approval do not change.
#### Scenario: Review a proposed response
- **WHEN** a user approves or rejects a specific Run action locally
- **THEN** the decision includes the concrete target and reason and remains separate from the saved proposal and execution receipts
- **AND** approval does not mark an object remediated, the response executed or the Case resolved; generic evidence approval is not offered.

### Requirement: Case entry prioritizes current case context
V2 SHALL use Case information as the default Case entry while retaining explicit investigation overview and Run views.
#### Scenario: Enter a Case from a general link
- **WHEN** a user opens a Case from its list, preview, alert, incident, switcher or newly associated Case, or opens a Case URL without a tab or selected Run
- **THEN** Case information is selected and is the first internal navigation entry
- **AND** explicit overview and Run links retain their prior results, six Run views and historical inputs; entering the page changes no stored data.

### Requirement: Case information displays current member attack stages
V2 SHALL display ATT&CK stage coverage using the recorded categories of current Case member alerts and the same presentation semantics as incidents.
#### Scenario: Inspect member stage coverage
- **WHEN** Case information is displayed
- **THEN** stage counts reflect only current members, missing categories remain unclassified and empty membership is shown honestly
- **AND** an information control explains that alert counts are not detection coverage or proof of attack success; historic Run inputs are not silently included.

### Requirement: Case materials provide an immediate reading context
V2 SHALL provide a selectable object list with a directly visible detail pane and a separate in-page investigation-material view within the consolidated materials workspace.
#### Scenario: Open or filter the object workspace
- **WHEN** a Case material page opens or the user selects, searches or filters an object
- **THEN** a matching object is visibly selected with its explicit evidence and source alerts, or a recoverable empty state is shown
- **AND** default ordering reflects member-alert counts rather than inferred risk, unlinked evidence remains accessible, and switching Cases clears prior viewing context.
#### Scenario: Inspect saved investigation materials
- **WHEN** the investigation-material view is selected or a Case has neither objects nor unlinked evidence but has saved Runs
- **THEN** each Run retains its own input scope, query/report links and artifact catalog with saved hashes and content access
- **AND** displaying, selecting or filtering writes no business records and never treats a source relationship as model adoption or a new judgment.

### Requirement: Case information uses a consistent presentation across sources
V2 SHALL use the same Case information layout and member-alert, object, alert-evidence and investigation metrics for illustrative and recorded Cases.
#### Scenario: Open Cases from different sources
- **WHEN** a user opens any Case information page
- **THEN** summary, details, member alerts, ATT&CK stages and objects use the same presentation structure, with actual values or missing states
- **AND** saved artifacts are not substituted for alert evidence and no overall AI conclusion is invented.

### Requirement: Case relationship views default to the latest finished investigation
V2 SHALL default the Case relationship base to its latest completed investigation, excluding triage-only results, and preserve its original input scope and provenance.
#### Scenario: Inspect or revise Case membership
- **WHEN** completed investigations exist
- **THEN** select the latest by end time with start time as a labelled fallback, disclose completeness, and link to its read-only Run
- **AND** default to Path and direct-neighbor relationships; saved exploration pins its base until explicitly reset and never merges historical Runs.
#### Scenario: Open a Case without a completed investigation
- **WHEN** no eligible completed investigation exists
- **THEN** use current member-to-object relationships as the identified base
- **AND** optional exploration remains an explicitly separate overlay with no implicit membership or investigation execution.

### Requirement: Investigation graph source navigation retains reading context
V2 SHALL expose Chain, Path and reachability selection before the graph and preserve explicit source disclosure state through same-Run redraws.
#### Scenario: Switch or inspect source material
- **WHEN** a user selects a source kind or opens and closes an alert preview from graph material
- **THEN** the selected material remains available without unintended collapse, same-Run kind switching retains the reading position, and manual collapse remains respected on redraw
- **AND** switching Runs does not carry old disclosure state or change stored investigation data.

### Requirement: Related alerts distinguish current membership from investigation input
V2 SHALL offer a related-alert list without duplicating Run input alerts, preserve unavailable source states, and disclose current Case membership separately from original Run input.
#### Scenario: Review a related alert outside the Case
- **WHEN** the user selects an alert from the related list or graph
- **THEN** the details show saved relationship evidence, available ranking/time difference and current Case membership
- **AND** eligible alerts can be preselected in the existing add-member form, whose explicit confirmation only adds current Case membership and never changes historical Run inputs, other Cases or starts an investigation.

### Requirement: Case relationship exploration preserves provenance and explicit adoption
V2 SHALL support alert and concrete-entity pivots only in the Case relationship workspace, using bounded loaded records and preserving the source Run and explicit relationship evidence.
#### Scenario: Explore a candidate and prepare further investigation
- **WHEN** a user selects a supported node or requests recommended leads
- **THEN** show ranked candidates and reasons separately from the base Path and direct-neighbor graph, allow preview, expansion, continuation, undo and saved exploration, and distinguish new nodes from existing scope and draft selections
- **AND** taxonomy nodes are view-only, expansion never changes membership or Run input, and saved investigation drafts disclose any proposed new membership before confirmation.
#### Scenario: Distinguish current exploration from historical source material
- **WHEN** any recorded or demonstration Case relationship workspace is opened
- **THEN** the common exploration controls are available and the page identifies its base provenance without repeating historical Chain/Path/Alert Graph source panels or their old skipped/no-Case status messages
- **AND** the linked read-only Run retains original source materials and execution statuses unchanged, while a context-only base remains identified as saved input relationships.

#### Scenario: Read object details and expansion candidates separately
- **WHEN** recommendations or an entity expansion is opened
- **THEN** the sidebar presents a dedicated leads view with compact candidate reasons and actions, while ranking rules, anchor time and complete shared objects remain accessible on demand
- **AND** selecting a graph node returns to object details without losing the existing leads context, and switching sidebar views does not change membership, historical Runs or saved exploration.

### Requirement: Case drafts and active investigation status are separate
V2 SHALL support cancelled drafts with retained records and persistent Case-level active-Run notices, while allowing at most one active Case investigation in local demonstrations.
#### Scenario: Save or start a draft while a Run is active
- **WHEN** a Case has an active or pending-start investigation
- **THEN** users may explore, add members and save or cancel drafts but cannot start a second Run or modify the active Run's frozen inputs
- **AND** only explicitly identified simulation Cases can simulate a start and progress; original recorded Cases never invoke or invent execution.

### Requirement: Case membership supports multiple incidents and actionable queue counts
V2 SHALL allow selecting multiple incidents with deduplicated member alerts and show all related incidents without changing their original membership or other Cases.
#### Scenario: Add events and inspect the Case queue
- **WHEN** incident selections are confirmed
- **THEN** selected current alerts are added once, event associations remain navigable, and historical Run inputs remain unchanged
- **AND** the former multi-alert percentage card is replaced by the count of Cases in progress.

### Requirement: Manual alert investigation enters Case preparation
The prototype SHALL route an alert investigation request into the scoped Case assistant rather than a separate draft form, without creating an alert-local pending Run.
#### Scenario: Prepare a linked alert
- **WHEN** a user requests investigation of an alert with one Case or selects one of multiple linked Cases
- **THEN** the selected Case assistant opens with that alert as context, without saving a task, Run or membership change
- **AND** closing the assistant preserves existing data.
#### Scenario: Associate before preparation
- **WHEN** an alert has no Case and the user explicitly confirms eligible association or Case creation
- **THEN** only the confirmed association is persisted, and the assistant opens with the selected alert
- **AND** real execution remains unconnected and documented; opening does not invent a result.

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

### Requirement: Case queue metrics describe actionable Case counts
The current Case queue SHALL show unassigned, in-progress, high-severity and pending-human-follow-up Case counts using one rule for all data sources. It SHALL exclude resolved and unknown-status Cases, count each Case once per metric, and explain scope and overlap through an information control. The queue SHALL omit nonfunctional Incident and Generic type tabs.
#### Scenario: Read counts and inspect matching Cases
- **WHEN** the queue is displayed
- **THEN** metrics count all loaded Cases with known New or In progress status, independently of table filters; pending follow-up counts Cases with at least one New or In progress task, not task totals
- **AND** selecting a metric replaces existing search and filters with that criterion while preserving columns and sort; toggling or removing it restores the remaining table scope
- **AND** metric filtering can be saved in a filter set, old sets clear a previously selected metric, and these operations do not update Case or Run business data.

### Requirement: Case overview separates current work from delivered results
The shared Case overview SHALL prioritize delivered findings, expose one active-progress entry only when a Run exists, and show human task summaries rather than a separate draft section.
#### Scenario: Inspect current work
- **WHEN** a Case has an active Run and manually prepared work
- **THEN** active progress is displayed once, pending manual work is readable through the human-task summary, and prior findings remain the main content
- **AND** original drafts and Runs are preserved, task editing requires explicit save, and viewing creates no task or investigation
- **AND** Cases without an active Run have no empty progress card.

### Requirement: Human task references are optional and distinct from origin
Human tasks SHALL explain the source investigation as origin and concrete optional references as reading material without requiring a work order or attachment.
#### Scenario: Prepare a human confirmation
- **WHEN** a user prepares a task from a Run
- **THEN** the Run is available as its source and is not offered again as a new whole-Run reference choice
- **AND** previously selected references remain preserved, completion accepts a written human result alone, and no model or investigation is started.

### Requirement: Run statistics use saved scope and missing-value semantics
Investigation history and detail SHALL share elapsed-time, saved-tool-record, model-call and token metrics for all data sources.
#### Scenario: Read saved execution statistics
- **WHEN** valid Run start and end times exist
- **THEN** elapsed time is computed from those timestamps, saved tool entries are counted as records, and calls and tokens use the saved Run totals
- **AND** missing or invalid values remain missing, explicit zero remains zero, Deep-stage latency is never treated as total duration, and reading does not modify records.

### Requirement: Case story provides a shared chronological reading surface
The prototype SHALL show all current deduplicated Case member alerts, saved investigations and completed human tasks through one story reader, newest first according to each record's actual timestamp, with missing times identified separately at the end.
#### Scenario: Read and select story context
- **WHEN** a user opens any Case story and selects alerts
- **THEN** the same layout displays actual members, objects and links to related saved investigations, and selected alerts can be brought to the Case assistant
- **AND** the latest timestamp appears at the top, the initial alert detail selects the latest available alert, and the summary range remains earliest to latest
- **AND** reading does not create causal claims, alter membership or change Run history.

### Requirement: Case assistant preview preserves explicit scoped context
The prototype SHALL offer one Case assistant preview from general and contextual entries, distinguish stored source excerpts from system guidance, and document that no live AI or tools are connected without requiring prototype badges in the product UI.
#### Scenario: Ask with local context
- **WHEN** a user opens or sends a question about a Case, Run, member alert, graph entity or completed human task
- **THEN** the context is validated within that Case, the local conversation retains its source references, and switching Cases does not carry another Case's conversation or selection
- **AND** opening, sending or viewing records creates no draft, Run, task, membership change or invented model result.

### Requirement: Assistant preview does not impose manual execution routing
The prototype SHALL expose manual preparations through human tasks while preserving their source records, and SHALL NOT offer fixed preparation or human-assignment buttons after every preview question.
#### Scenario: Read the unconnected assistant preview
- **WHEN** a user sends a question in the local assistant preview
- **THEN** the UI does not invent a response, execution or preparation/human-assignment prerequisite; real execution remains unconnected and explicitly documented
- **AND** the current product document distinguishes the target send-to-execution and result-adoption workflow from this unconnected preview; existing manual workflows and historical records remain available.

### Requirement: Case assistant distinguishes conversation roles and editable initial intent
The prototype SHALL present user questions on the right and actual system responses on the left, preserve a clear composer, and keep supporting context secondary. Without a real response it SHALL NOT insert a placeholder reply.
#### Scenario: Open an empty conversation
- **WHEN** a user first opens the Case assistant with no prior messages or typed draft
- **THEN** the composer contains an editable question based on the current Case or selected context; suggestions fill the composer without submitting
- **AND** typed drafts and historical messages are retained, opening creates no message or business record, and the unconnected execution boundary remains explicit in the product document.
#### Scenario: Read an existing exchange
- **WHEN** a user opens a conversation with saved questions
- **THEN** user questions remain right-aligned, actual response roles have a distinct left alignment, reference details are available on demand, and the input and all three scoped suggestion buttons stay available
- **AND** suggestions only fill editable input without sending; source excerpts remain identified as saved records, not newly generated answers.

### Requirement: Case human work and saved investigations share reading context
The shared model SHALL project pending manual preparations into human tasks without modifying their original records and SHALL expose completed human results beside saved investigations in the Case story and assistant references.
#### Scenario: Complete manual follow-up
- **WHEN** a user explicitly saves a task result originating from a pending preparation
- **THEN** one task is stored with its source preparation reference, the source preparation and historical Run inputs remain unchanged, and the story provides a contextual question entry for that result
- **AND** the result remains attributed to the person and is not an automatic change to Case conclusions.

### Requirement: Graph membership adoption marks baseline work without invented execution
The graph SHALL distinguish exploration from explicitly adopting outside alerts and SHALL mark baseline investigation scope as pending update only after actual new members are confirmed.
#### Scenario: Confirm an outside alert
- **WHEN** the user selects an outside alert and confirms joining it to the Case
- **THEN** membership is deduplicated, pending baseline-update scope records the new member, and historical Run inputs remain unchanged
- **AND** mere expansion, viewing or selecting does not create a Run; automatic execution and AI conclusion saving remain documented future integration rather than fabricated local results.

### Requirement: Shared membership change and pending analysis presentation
The local workspace SHALL apply the same scope validation, deduplication, history retention and pending analysis feedback to alert association, incident association, Case addition and movement.

#### Scenario: Cross-scope target is selected
- **WHEN** a different source scope is selected by any member association or move entry
- **THEN** the choice is absent and submission rejects it without mutation

#### Scenario: Members are moved
- **WHEN** a user confirms a valid move
- **THEN** both Cases retain historical Run inputs and display the actual membership change

### Requirement: Common outcomes and explicit AI conclusion retention
The workspace SHALL render per-record purpose, conclusion, limitations and Case impact with a shared model; missing real results SHALL remain missing. AI replies SHALL be distinct from questions and require explicit saving before becoming formal investigation records.

#### Scenario: An illustrative answer is saved
- **WHEN** a user confirms a conclusion from an independent complete example
- **THEN** a single scoped AI investigation record preserves the selected messages, input and references without changing Case judgment or creating an active Run

#### Scenario: Saved real result is sparse
- **WHEN** a source result has no conclusion or an AI service is unavailable
- **THEN** the page states that condition and does not substitute demonstration results
