## ADDED Requirements

### Requirement: Candidate reads have explicit source and object matching rules
The service SHALL provide one read-only Case candidate query, accepting a Case and an optional existing current alert or object as its seed. It MUST enforce tenant, Case source namespace and object namespace, use only current material objects, and preserve original facts and references. Exact source values for host/user/ip/domain/url and validated explicit algorithm plus hash value SHALL have distinct match meanings; other object kinds SHALL NOT be silently inferred.

#### Scenario: Hash algorithm is missing
- **WHEN** a selected hash has no supported explicit algorithm or a valid value
- **THEN** the service returns 422; a multi-object seed reports that object as excluded and does not match it by length alone.

#### Scenario: Source or object differs
- **WHEN** a candidate has a different namespace/type/value, or hash algorithm differs
- **THEN** it does not match; a same-name host from another namespace is not merged.

### Requirement: Candidates disclose evidence and support stable scoped paging
The service SHALL return original alert facts, matched source and candidate object/material references, shared-object count, nearest known seed time difference and current Case/incident membership. It SHALL apply an explicit or configured event-time window, aggregate before paging, sort by shared count then time gap then alert ID, and bind cursors to the actual query and seed scope.

#### Scenario: Default and explicit time windows
- **WHEN** no window is supplied
- **THEN** the service uses the known seed event-time range plus configured margins; a nonempty seed without known time requires explicit dates, and unknown-time candidates never receive invented timestamps.

#### Scenario: Page and source verification
- **WHEN** a caller pages through matches and reads the referenced material
- **THEN** the results remain deduplicated with stable ordering for unchanged data and each match points to the actual original source field; changed seed scope rejects the old cursor.

### Requirement: Exploration queries remain independent of investigation mutations
The external HTTP adapter SHALL invoke a dedicated core read use case without internal HTTP calls. Queries MUST NOT change members, Runs, Results, graph snapshots or source objects. Existing association commands SHALL remain the explicit path to adding a candidate; exploration persistence and AI conversations are outside this change.

#### Scenario: Preview then explicitly associate
- **WHEN** the user reads a candidate and later explicitly submits it through the existing Case association operation
- **THEN** the query itself writes nothing and only the later association changes membership, preserving other Cases and historical Runs.
