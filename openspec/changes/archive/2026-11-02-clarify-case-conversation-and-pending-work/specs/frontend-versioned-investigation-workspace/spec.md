## MODIFIED Requirements

### Requirement: Case overview separates current work from delivered results
The shared Case overview SHALL prioritize delivered findings, expose one active-progress entry only when a Run exists, and show human task summaries rather than a separate draft section.
#### Scenario: Inspect current work
- **WHEN** a Case has an active Run and manually prepared work
- **THEN** active progress is displayed once, pending manual work is readable through the human-task summary, and prior findings remain the main content
- **AND** original drafts and Runs are preserved, task editing requires explicit save, and viewing creates no task or investigation
- **AND** Cases without an active Run have no empty progress card.

### Requirement: Case assistant preview preserves explicit scoped context
The prototype SHALL offer one Case assistant preview from general and contextual entries, distinguish stored source excerpts from system guidance, and document that no live AI or tools are connected without requiring prototype badges in the product UI.
#### Scenario: Ask with local context
- **WHEN** a user opens or sends a question about a Case, Run, member alert, graph entity or completed human task
- **THEN** the context is validated within that Case, the local conversation retains its source references, and switching Cases does not carry another Case's conversation or selection
- **AND** opening, sending or viewing records creates no draft, Run, task, membership change or invented model result.

### Requirement: Assistant preview does not impose manual execution routing
The prototype SHALL expose manual preparations through human tasks while preserving their source records, and SHALL NOT offer fixed preparation or human-assignment buttons after every preview question.
#### Scenario: Read the unconnected assistant preview
- **WHEN** a user sends a question in the local assistant preview
- **THEN** the UI does not invent a response, execution or preparation/human-assignment prerequisite; real execution remains unconnected and explicitly documented
- **AND** the current product document distinguishes the target send-to-execution and result-adoption workflow from this unconnected preview; existing manual workflows and historical records remain available.

### Requirement: Case assistant distinguishes conversation roles and editable initial intent
The prototype SHALL present user questions on the right and actual system responses on the left, preserve a clear composer, and keep supporting context secondary. Without a real response it SHALL NOT insert a placeholder reply.
#### Scenario: Open an empty conversation
- **WHEN** a user first opens the Case assistant with no prior messages or typed draft
- **THEN** the composer contains an editable question based on the current Case or selected context; suggestions fill the composer without submitting
- **AND** typed drafts and historical messages are retained, opening creates no message or business record, and the unconnected execution boundary remains explicit in the product document.
#### Scenario: Read an existing exchange
- **WHEN** a user opens a conversation with saved questions
- **THEN** user questions remain right-aligned, actual response roles have a distinct left alignment, reference details are available on demand, and the input and all three scoped suggestion buttons stay available
- **AND** suggestions only fill editable input without sending; source excerpts remain identified as saved records, not newly generated answers.

### Requirement: Manual alert investigation enters Case preparation
The prototype SHALL route an alert investigation request into the scoped Case assistant rather than a separate draft form, without creating an alert-local pending Run.
#### Scenario: Prepare a linked alert
- **WHEN** a user requests investigation of an alert with one Case or selects one of multiple linked Cases
- **THEN** the selected Case assistant opens with that alert as context, without saving a task, Run or membership change
- **AND** closing the assistant preserves existing data.
#### Scenario: Associate before preparation
- **WHEN** an alert has no Case and the user explicitly confirms eligible association or Case creation
- **THEN** only the confirmed association is persisted, and the assistant opens with the selected alert
- **AND** real execution remains unconnected and documented; opening does not invent a result.

## ADDED Requirements

### Requirement: Case human work and saved investigations share reading context
The shared model SHALL project pending manual preparations into human tasks without modifying their original records and SHALL expose completed human results beside saved investigations in the Case story and assistant references.
#### Scenario: Complete manual follow-up
- **WHEN** a user explicitly saves a task result originating from a pending preparation
- **THEN** one task is stored with its source preparation reference, the source preparation and historical Run inputs remain unchanged, and the story provides a contextual question entry for that result
- **AND** the result remains attributed to the person and is not an automatic change to Case conclusions.

### Requirement: Graph membership adoption marks baseline work without invented execution
The graph SHALL distinguish exploration from explicitly adopting outside alerts and SHALL mark baseline investigation scope as pending update only after actual new members are confirmed.
#### Scenario: Confirm an outside alert
- **WHEN** the user selects an outside alert and confirms joining it to the Case
- **THEN** membership is deduplicated, pending baseline-update scope records the new member, and historical Run inputs remain unchanged
- **AND** mere expansion, viewing or selecting does not create a Run; automatic execution and AI conclusion saving remain documented future integration rather than fabricated local results.
