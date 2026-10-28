## ADDED Requirements

### Requirement: Case reports distinguish selected materials from member judgments
The Case report SHALL retain an explicit result for each selected member, distinguish addressed, unresolved, not_assessed and source_unavailable, and SHALL NOT equate reading an alert with completing its analysis.

#### Scenario: One of three selected members has no model judgment
- **WHEN** the model returns judgments for only two members
- **THEN** the third member remains not_assessed and the report retains an open question and partial completion

### Requirement: Cross-alert relationships and open questions retain scope and evidence
The model SHALL distinguish shared context from behavioral links and contradictions, identify the participating selected alerts, and cite actual evidence. The server SHALL reject references outside the selected scope or unknown evidence.

#### Scenario: Two alerts share a host and a third is background
- **WHEN** the model assesses the three alerts and relates only the first two
- **THEN** the report preserves that relationship, its basis and references without extending it to the third alert

### Requirement: The report timeline is derived from saved source records
The report SHALL derive timeline timestamps from alert and successful tool records, retain provenance, and distinguish current product snapshots from historical events.

#### Scenario: A current product snapshot accompanies historical records
- **WHEN** the report includes alert events, event-lake rows and a product host read
- **THEN** the timeline orders known timestamps, labels the snapshot observation time separately, and does not fabricate times for records whose timestamp is unknown
