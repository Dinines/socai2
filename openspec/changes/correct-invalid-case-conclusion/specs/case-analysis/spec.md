## ADDED Requirements

### Requirement: One bounded conclusion correction
Case analysis SHALL permit at most one correction of an invalid conclusion within the existing model, tool, token and duration limits, without relaxing schema, member scope or evidence checks.

#### Scenario: Invalid reference in a proposed final answer
- **WHEN** the model references evidence that has not been provided and a correction fits the existing limits
- **THEN** the ledger retains the rejected response and validation feedback, and one schema-constrained correction uses only received evidence, reporting absent evidence as a gap without additional Tool dispatch.

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

### Requirement: Model requests declare the conclusion output contract
Final-conclusion correction requests, and analysis requests with no offered Tools, SHALL include a strict JSON Schema response format derived from the conclusion model and current evidence/member scope. Ordinary Tool-capable turns SHALL omit this response format. Application-side validation remains mandatory in both phases.

#### Scenario: Tool results add evidence
- **WHEN** final-conclusion correction is prepared after a Tool result
- **THEN** its evidence enums include the newly received evidence, its schema is saved in the preparation step, schema bytes count toward the existing input allowance, and no Tools are offered or dispatched.

#### Scenario: The question requires a source query
- **WHEN** normal analysis is prepared with available Tools
- **THEN** the native Tool definitions are offered without a JSON Schema response format, so this provider can choose a Tool before producing a final answer.
