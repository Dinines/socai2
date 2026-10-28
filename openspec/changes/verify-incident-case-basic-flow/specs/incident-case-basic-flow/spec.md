## ADDED Requirements

### Requirement: Existing incident and Case entry functions run with their declared storage
The selected development database SHALL install only migrations 120 and 121 for this functional check, retaining existing business data and recording the applied migration filenames.

#### Scenario: Explicit member selection creates and extends a Case
- **WHEN** the synthetic incident's first member creates a Case and both members are subsequently attached
- **THEN** the receipt identifies one newly added member and one already-linked member, repeated request keys return saved receipts, and preview preserves the explicitly selected subset without creating a Run.

#### Scenario: Incident overview references saved investigation results
- **WHEN** the user explicitly refreshes the synthetic incident with existing Case reports included
- **THEN** one model request produces saved overview text and source references, ordinary GET reads that same overview without another model request, and existing reports remain unchanged.
