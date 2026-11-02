## ADDED Requirements
### Requirement: Case story provides a shared chronological reading surface
The prototype SHALL show all current deduplicated Case member alerts through one story reader, in occurrence-time order with missing times identified separately.
#### Scenario: Read and select story context
- **WHEN** a user opens any Case story and selects alerts
- **THEN** the same layout displays actual members, objects and links to related saved investigations, and selected alerts can be brought to the Case assistant
- **AND** reading does not create causal claims, alter membership or change Run history.

### Requirement: Case assistant preview preserves explicit scoped context
The prototype SHALL offer one Case assistant preview from general and contextual entries, distinguish stored source excerpts from system guidance, and disclose that no live AI or tools are connected.
#### Scenario: Ask with local context
- **WHEN** a user opens or sends a question about a Case, Run, member alert, graph entity or completed human task
- **THEN** the context is validated within that Case, the local conversation retains its source references, and switching Cases does not carry another Case's conversation or selection
- **AND** opening, sending or viewing records creates no draft, Run, task, membership change or invented model result.

### Requirement: Assistant preview does not impose manual execution routing
The prototype SHALL keep manual drafts and human tasks as distinct existing workflows, and SHALL NOT offer fixed preparation or human-assignment buttons after every preview question.
#### Scenario: Read the unconnected assistant preview
- **WHEN** a user sends a question in the local assistant preview
- **THEN** the UI discloses that no AI execution has occurred and does not present a preparation or human-assignment prerequisite
- **AND** the current product document distinguishes the target send-to-execution and result-adoption workflow from this unconnected preview; existing manual workflows and historical records remain available.
