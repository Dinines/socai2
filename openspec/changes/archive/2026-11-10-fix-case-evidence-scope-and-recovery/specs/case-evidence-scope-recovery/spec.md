## ADDED Requirements

### Requirement: Case query provenance and record subject remain distinct
The system SHALL retain immutable query provenance separately from a verified historical row subject in Case model inputs and SHALL preserve that distinction across C3, Deep and C6 without changing alert handoff fields or stored originals.

#### Scenario: One member query returns another Case member's history
- **WHEN** a verified frozen history receipt for A3 contains a record whose consistent program-owned IDs identify A1
- **THEN** the source remains traceable to A3's query while member citations use A1, and its prior-analysis or label role is unchanged

#### Scenario: A returned identity is outside the Case or inconsistent
- **WHEN** a history row has no unambiguous current Case member identity
- **THEN** it remains explicit background with its query origin and identity limitation, without assigning the query member as its factual subject or inventing a new identity

#### Scenario: A nonhistorical row has only query binding
- **WHEN** a query row has no independently verified alert subject
- **THEN** its binding is labelled as query-only and cannot establish direct observed membership

### Requirement: Complete Case replies receive one bounded citation correction
The system SHALL diagnose correctable source, member and local finding-reference errors in structurally complete C3/C6 replies, preserve the original reply, and permit at most one correction under the same Run limits. The program MUST NOT invent findings, expand scopes or rewrite factual prose to pass validation.

#### Scenario: Final conclusion or impact omits a declared member's evidence
- **WHEN** a complete final reply lacks qualifying source coverage for a declared conclusion or impact member
- **THEN** feedback identifies the uncovered member and field, with direct-evidence rules matching final acceptance, without automatically adding citations or narrowing the claim

#### Scenario: A final reply references an absent finding
- **WHEN** a domain or conflict cites a finding absent from the same reply's analysis
- **THEN** feedback identifies the exact path, invalid reference and existing local finding IDs, and a correction is fully validated before adoption

#### Scenario: A cross-member claim declares only one member
- **WHEN** a structured claim cites sources outside its declared members
- **THEN** feedback reports the source's actual scope and requests an evidence-supported correction without automatically expanding the claim

#### Scenario: Correction cannot safely dispatch or still fails
- **WHEN** the original reply was incomplete or unknown, remaining resources are insufficient, or the single correction remains invalid
- **THEN** no extra retry occurs, original responses remain saved, independent valid units remain readable, and invalid final conclusions are not adopted

### Requirement: Deep generation and acceptance agree on action contracts
The system SHALL constrain the Deep generation schema to the same query, answer and handoff shape requirements used on receipt.

#### Scenario: Deep requires human confirmation
- **WHEN** Deep selects handoff for a question whose missing evidence requires human confirmation
- **THEN** the generation schema requires a non-null unresolved answer with explicit limitations and a null binding, and does not treat handoff as confirmed business authorization

#### Scenario: Deep selects a query
- **WHEN** a query binding is offered and Deep selects query
- **THEN** the binding must be from the offered set and answer must be null; when no binding is offered query cannot be generated

### Requirement: Background source selection is configured and records coverage
Configured Case enrichment SHALL use explicit source priorities and paired-query coverage to prefer missing context, retain the configured downstream tool reservation within the existing total budget, and record selections and skipped sources truthfully.

#### Scenario: Prior runs already supplied paired background receipts
- **WHEN** applicable sources have complete paired A query receipts while other applicable background is missing
- **THEN** configured coverage penalties lower repeated-source priority without claiming those receipts establish complete current evidence

#### Scenario: Knowledge is selected or the budget is exhausted
- **WHEN** the ranked source plan reaches a connected knowledge source or the background budget boundary
- **THEN** an actual query and its result are recorded if dispatched, otherwise an explicit skip reason is recorded; retrieval does not prove model use or business truth

### Requirement: One change completes validation before unified delivery
This change SHALL finish local implementation, complete workflow checks, handoff updates and independent audit before its unified deployment and Git/parent publication. Model-quality, database-readback and substitute-test outcomes MUST be distinguished.

#### Scenario: A local iteration fixes a failing check
- **WHEN** an implementation or test needs another edit
- **THEN** the iteration remains local until the complete change is ready, rather than producing a deployment or remote push per small fix
