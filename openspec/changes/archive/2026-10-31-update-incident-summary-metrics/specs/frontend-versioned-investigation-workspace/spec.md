## MODIFIED Requirements

### Requirement: Incident queue context uses explicit source meanings
V2 SHALL expose incident-linked investigations, member host names and asset tags without inventing incident priority or management state. Preview controls SHALL distinguish a side pane from row expansion. Its compact summary SHALL expose active, unassigned, recent-alert and high-severity incident counts instead of a missing-state count.

#### Scenario: Read incident queue context
- **WHEN** the incident queue and preview are opened
- **THEN** associated-investigation counts include each event with a started member investigation once and exclude triage-only Runs, tags come from member assets, and host names come from saved member context
- **AND** missing incident state is identified as missing state and alert verdict confidence is never substituted for incident priority.

#### Scenario: Retain saved source records
- **WHEN** incident context is displayed or filtered
- **THEN** source event management tags, member records, source scores, historical Runs and browser edits remain unchanged
- **AND** the preview control opens the existing side pane while the incident title opens the incident page.

#### Scenario: Read the four summary metrics
- **WHEN** the incident queue renders or is refreshed
- **THEN** the recent-alert metric counts each incident once when a member alert occurred within the preceding 24 hours up to the current time, excluding future or invalid timestamps
- **AND** active, unassigned and high-severity counts retain their separate source meanings, all four remain visible at narrow widths, and historical timestamps are never shifted to create recent activity.
