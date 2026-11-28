## ADDED Requirements

### Requirement: Complete Case investigation history directory
The system SHALL provide a Case-scoped read-only investigation directory and exact Run lookup using the same verified association set as related Case story. It SHALL deduplicate by Run identity, preserve original subjects and all saved result references, and paginate the complete lawful set by requested_at and Run ID descending. Existing Case history, global directory, AlertFacts and investigation submission contracts SHALL remain unchanged.

#### Scenario: List and resolve an associated Run outside the loaded page
- **WHEN** an existing Case contains its own Run and verified associated alert or incident Runs
- **THEN** the directory returns one card per Run with full total and a Case-bound cursor
- **AND** exact lookup resolves an associated Run independently of loaded pages while an unrelated Run returns 404

#### Scenario: Preserve immutable input scope and explicit source proof
- **WHEN** a Run has explicit saved source proof but its actual frozen input cannot be verified
- **THEN** the card retains its real identity and source relations with input_member_count null
- **AND** a verified empty input reports zero while planned members never prove actual input

### Requirement: Saved history card content and execution measurements
Each card SHALL report the Run's actual type, state, delivery and times, a deterministic same-Run saved preview, full tool record count, and reported model usage. Missing values SHALL remain distinct from confirmed zero. The preview SHALL retain its exact result identity and source field without generating or rewriting analysis.

#### Scenario: Select the original baseline result and retain other saved results
- **WHEN** a baseline Run has its original E10 baseline result and later saved results
- **THEN** the card preview uses that original baseline result and retains every other real result reference
- **AND** when no original baseline exists the documented saved_at and result-ID ordering chooses a same-Run result with its real kind

#### Scenario: Distinguish tool records and incomplete model usage
- **WHEN** a Run has saved tool entries including planned or skipped entries and model steps with partly unknown usage
- **THEN** tool_record_count includes all saved tool entries while model_calls excludes planned and skipped model entries
- **AND** total_tokens is null with separate known_total_tokens and unknown_token_calls, and no row-limit projection is treated as a full total

### Requirement: Prototype-aligned history navigation
The Case history page SHALL render the prototype's vertical cards by default and SHALL open a fixed investigation only through an explicit Run or valid saved-result link. It SHALL preserve original Run/result identity and offer an explicit return to the history directory. Selecting another Run SHALL preserve the chosen view while clearing the previous Run's result selection.

#### Scenario: Default directory and explicit card actions
- **WHEN** the history route has no Run or result selection
- **THEN** it shows history cards, their saved summary and four metrics without automatically loading first-Run details
- **AND** Open investigation and tool-record actions target the same Run's overview and tools views respectively

#### Scenario: Deep link, switch and return
- **WHEN** a valid fixed Run or result-only link is opened, refreshed or reached with browser navigation
- **THEN** the page resolves its original Case-scoped identity, rejects mismatched result identity, and does not substitute another Run
- **AND** switching Runs preserves the view and returning restores the Case history directory

#### Scenario: Read failure is not empty history
- **WHEN** the directory or exact lookup fails
- **THEN** the page displays the actual read error and retry action without showing a successful empty state or selecting a fallback Run
