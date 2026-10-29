## ADDED Requirements

### Requirement: Follow-up model input avoids redundant retained material
The follow-up model view SHALL compact duplicate derived information with explicit omission metadata, preserve full evidence on readback, and retain the existing budget and canonical intent encoding.

#### Scenario: The recorded Office follow-up needs correction
- **WHEN** the saved request is rebuilt with the updated model view
- **THEN** required preflight allowance fits the recorded remaining allowance without raising limits, and full source/H1 data remains unchanged.

### Requirement: Explicit Tool requirements are enforced
Case analysis SHALL accept optional required_tools and use native tool_choice for each offered required function before accepting a conclusion.

#### Scenario: Recheck a previously queried source
- **WHEN** a follow-up explicitly requires network_connections and its materials/arguments permit reuse
- **THEN** the model must issue that native call, the normal scoped dispatcher may reuse the saved query, and the report cites the new Run's evidence reference.

#### Scenario: Required call is absent
- **WHEN** the provider returns a final answer or unrelated call while a function is required
- **THEN** the Run fails explicitly without accepting that answer as a completed investigation.

### Requirement: Tool messages distinguish empty success from unavailability
Tool model messages SHALL label successful rows, successful-empty results and unavailable sources distinctly, while preserving their existing saved evidence.
