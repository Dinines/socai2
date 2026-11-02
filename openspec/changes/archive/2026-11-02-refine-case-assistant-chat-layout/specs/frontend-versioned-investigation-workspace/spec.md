## ADDED Requirements
### Requirement: Case assistant distinguishes conversation roles and editable initial intent
The prototype SHALL present user questions on the right and actual system responses on the left, preserve a clear composer, and keep supporting context secondary. Without a real response it SHALL NOT insert a placeholder reply.
#### Scenario: Open an empty conversation
- **WHEN** a user first opens the Case assistant with no prior messages or typed draft
- **THEN** the composer contains an editable question based on the current Case or selected context; suggestions fill the composer without submitting
- **AND** typed drafts and historical messages are retained, opening creates no message or business record, and the unconnected preview remains explicit.
#### Scenario: Read an existing exchange
- **WHEN** a user opens a conversation with saved questions
- **THEN** user questions remain right-aligned, actual response roles have a distinct left alignment, reference details are available on demand, and the input stays available
- **AND** source excerpts are identified as saved records, not newly generated answers.
