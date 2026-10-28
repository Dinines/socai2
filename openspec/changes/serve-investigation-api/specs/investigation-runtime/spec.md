## ADDED Requirements

### Requirement: Independent investigation HTTP entry
The current investigation application SHALL expose a liveness response and its actual OpenAPI contract, and SHALL remain independently startable without the legacy application or background workers.

#### Scenario: Inspect the running entry
- **WHEN** a caller requests liveness and the investigation schema
- **THEN** it receives process liveness and the registered Alert/Incident/Case route definitions, without a model call or business write.

### Requirement: Caller preserves the selected API and request identity
The HTTP caller SHALL use the operator-selected investigation/core base, read its Bearer token from environment, send JSON without generating an operation key, and make no automatic POST retry or redirect.

#### Scenario: Follow existing API-relative links
- **WHEN** the operator passes a returned investigation path or core Case path
- **THEN** the caller sends it to the corresponding configured API base with the original body and reports the HTTP result.
