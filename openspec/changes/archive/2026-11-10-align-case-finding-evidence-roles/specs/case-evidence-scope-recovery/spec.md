## ADDED Requirements

### Requirement: Case finding generation distinguishes evidence roles
C3 and C6 generation SHALL constrain each finding state with a complete schema branch while preserving original input and persisted contracts. Observed support SHALL use only available member-owned observations, excluding query-binding-only sources; inferred findings SHALL have supporting references, and unresolved findings SHALL name limitations. Provider constraints MUST NOT replace receiving validation or semantic review.

#### Scenario: No eligible direct observation is available
- **WHEN** the visible source catalog has only labels, previous analyses, human statements, execution receipts, or query-binding-only rows
- **THEN** generation does not offer observed findings and the model can report inference or explicitly unresolved gaps without inventing observations

#### Scenario: A claim combines activity with a source label
- **WHEN** a model needs to describe an activity together with a detection label, source declaration, previous judgment or human statement
- **THEN** instructions distinguish the activity finding from attributed contextual statements, keep their original sources available, and prohibit turning those statements into independent observation or business authorization

#### Scenario: A saved finding uses timestamp context with valid observations
- **WHEN** an existing reply includes a legitimate frozen event-time context alongside sufficient member observations
- **THEN** the established receiving contract remains compatible and neither its original contents nor stored references are rewritten by the generation change

## MODIFIED Requirements

### Requirement: Complete Case replies receive one bounded citation correction
The system SHALL diagnose correctable source, member, evidence-role and local finding-reference errors in structurally complete C3/C6 replies, preserve the original reply, and permit at most one correction under the same Run limits. The program MUST NOT invent findings, expand scopes or rewrite factual prose to pass validation.

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


#### Scenario: An observed finding mixes observations with labels or reports
- **WHEN** a complete C3/C6 finding uses an ineligible role, lacks member-specific direct observation, has only query binding, or uses the same source as support and counterevidence
- **THEN** its one bounded correction reports exact paths and source roles/scopes, asks the model to re-evaluate the claim and its evidence, and preserves independent valid units if correction still fails without rewriting the original reply
