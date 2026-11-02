## ADDED Requirements

### Requirement: Unified Case overview preserves per-Run scope
V2 SHALL open every Case overview as a current-case summary with per-Run results and recorded next work side by side at wide widths and stacked at narrow widths, without changing existing Case navigation or Run detail capabilities.

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
