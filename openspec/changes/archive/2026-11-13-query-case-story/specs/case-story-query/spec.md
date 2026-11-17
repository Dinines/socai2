## ADDED Requirements

### Requirement: Read existing Case story sources without execution
The service SHALL expose a read-only Case story containing current member alerts, baseline investigation runs with saved results, and completed human task revisions. It SHALL preserve source identities, text and statuses and SHALL NOT invoke models or mutate investigation data.

#### Scenario: Read investigation and historical human results
- **WHEN** a Case has a running investigation and an older completed task revision followed by a reopened revision
- **THEN** the story shows the running state without a premature result and retains the completed revision marked as not current, with identities for existing detail APIs

### Requirement: Search and paginate the complete story scope
The service SHALL filter the complete Case story before pagination, using literal keyword matching and alert severity filtering. Investigation and human result entries SHALL remain context when filtering alert severity. Ordering SHALL use actual source times descending, unknown times last, and stable source keys. Cursors SHALL be bound to tenant, Case and filters.

#### Scenario: Continue mixed source pagination
- **WHEN** a caller reads multiple pages containing equal and unknown source times
- **THEN** unchanged matching sources appear once in deterministic order and unknown timestamps remain null

#### Scenario: Reject a cursor from another scope
- **WHEN** a caller reuses a cursor with another Case or changed search filters
- **THEN** the service rejects the request with 422 without reading another Case's records
