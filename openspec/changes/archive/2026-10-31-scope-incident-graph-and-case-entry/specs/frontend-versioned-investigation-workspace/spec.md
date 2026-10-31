## MODIFIED Requirements

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
