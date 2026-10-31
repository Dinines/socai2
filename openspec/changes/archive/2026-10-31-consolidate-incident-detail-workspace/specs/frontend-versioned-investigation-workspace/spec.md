## ADDED Requirements

### Requirement: Incident detail consolidates overview and relationship navigation
V2 SHALL provide a single incident overview containing event description and information, alert-stage distribution, chronological member-alert activity and an expanded incident story graph. It SHALL remove the incident-switch dialog entry while preserving navigation back to the incident list. It SHALL consolidate relationship and alert-chain navigation without changing their underlying meanings or source data.

#### Scenario: Open the incident overview
- **WHEN** a user opens an incident summary or its former context link
- **THEN** event information, member-alert stages and timeline, and an expanded story graph are directly available in the overview
- **AND** member/assessment/investigation/material features remain accessible, missing actual timestamps remain missing, and no extra investigation or source data is generated.

#### Scenario: Explore relationships and candidate chains
- **WHEN** a user opens relationship analysis or a former chain link
- **THEN** the relationship graph and alert chain are views of one navigation area, preserving seed/window selection and saved Run sources
- **AND** current membership relationships remain distinguishable from candidate chain results and neither is represented as verified attack causality.

#### Scenario: Explain membership and hand off judgment to Case
- **WHEN** a user opens an incident
- **THEN** the overview explains the incident, shows shared-object associations with source-alert links and an expanded relationship graph, without presenting per-alert scores as an incident judgment
- **AND** absent grouping rules are not inferred from common entities or timestamps.

#### Scenario: Continue in a Case
- **WHEN** a user continues from an incident to deeper judgment
- **THEN** existing business Cases can be opened, or an incident with no Case can explicitly create or associate a Case with its current member alerts
- **AND** local confirmation preserves other memberships and historical Runs, does not start an investigation, and prevents duplicate creation when a Case already exists.
