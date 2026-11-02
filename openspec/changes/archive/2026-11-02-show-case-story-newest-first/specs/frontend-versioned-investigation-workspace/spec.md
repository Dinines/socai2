## MODIFIED Requirements

### Requirement: Case story provides a shared chronological reading surface
The prototype SHALL show all current deduplicated Case member alerts, saved investigations and completed human tasks through one story reader, newest first according to each record's actual timestamp, with missing times identified separately at the end.
#### Scenario: Read and select story context
- **WHEN** a user opens any Case story and selects alerts
- **THEN** the same layout displays actual members, objects and links to related saved investigations, and selected alerts can be brought to the Case assistant
- **AND** the latest timestamp appears at the top, the initial alert detail selects the latest available alert, and the summary range remains earliest to latest
- **AND** reading does not create causal claims, alter membership or change Run history.
