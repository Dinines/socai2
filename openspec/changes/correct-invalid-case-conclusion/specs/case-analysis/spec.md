## ADDED Requirements

### Requirement: One bounded conclusion correction
Case analysis SHALL permit at most one correction of an invalid conclusion within the existing model, tool, token and duration limits, without relaxing schema, member scope or evidence checks.

#### Scenario: Invalid reference before the source is queried
- **WHEN** the model references evidence that has not been provided and a correction fits the existing limits
- **THEN** the ledger retains the rejected response and validation feedback, and the next model turn may invoke the offered Tool and return a valid conclusion.

#### Scenario: The correction is still invalid
- **WHEN** the model produces a second invalid conclusion
- **THEN** analysis ends with the existing invalid-conclusion failure and partial report.

### Requirement: Report response waits fit the overall analysis deadline
The model HTTP request SHALL allow up to 60 seconds of response waiting with a 10-second connect timeout, while remaining subject to the existing 120-second enclosing analysis deadline and without automatic HTTP retries.

#### Scenario: The configured model needs more than 30 seconds for its report
- **WHEN** a report response arrives within the request and enclosing deadlines
- **THEN** analysis processes and validates the response normally.

### Requirement: Follow-up model input avoids duplicate derived tables
The follow-up model view SHALL omit the prior report's generated timeline and member coverage tables with explicit omission metadata, while preserving complete H1 evidence and the original saved report.

#### Scenario: A follow-up refers to a saved multi-alert report
- **WHEN** the model receives H1 historical context
- **THEN** it receives the report's analysis fields and omission metadata, and evidence/report GETs still return the complete saved contents.
