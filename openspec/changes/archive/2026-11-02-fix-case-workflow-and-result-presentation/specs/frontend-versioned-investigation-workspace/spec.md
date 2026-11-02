## ADDED Requirements

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
