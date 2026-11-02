## MODIFIED Requirements
### Requirement: Case relationship exploration preserves provenance and explicit adoption
V2 SHALL support alert and concrete-entity pivots only in the Case relationship workspace, using bounded loaded records and preserving the source Run and explicit relationship evidence.
#### Scenario: Explore a candidate and prepare further investigation
- **WHEN** a user selects a supported node or requests recommended leads
- **THEN** show ranked candidates and reasons separately from the base Path and direct-neighbor graph, allow preview, expansion, continuation, undo and saved exploration, and distinguish new nodes from existing scope and draft selections
- **AND** taxonomy nodes are view-only, expansion never changes membership or Run input, and saved investigation drafts disclose any proposed new membership before confirmation.
#### Scenario: Distinguish current exploration from historical source material
- **WHEN** any recorded or demonstration Case relationship workspace is opened
- **THEN** the common exploration controls are available and the page identifies its base provenance without repeating historical Chain/Path/Alert Graph source panels or their old skipped/no-Case status messages
- **AND** the linked read-only Run retains original source materials and execution statuses unchanged, while a context-only base remains identified as saved input relationships.
