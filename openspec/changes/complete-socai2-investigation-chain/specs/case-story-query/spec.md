## ADDED Requirements

### Requirement: The related story view preserves the existing default contract
The service SHALL provide an explicitly selected related Case story view for the 4173-aligned product page. Requests without this selection SHALL retain the existing E65 source scope, response envelope, severity behavior, and cursor compatibility. Existing AlertFacts and saved source contracts SHALL remain unchanged. Both views SHALL read existing records without invoking models or changing business data.

#### Scenario: An existing client continues an old story cursor
- **WHEN** a client omits the new related-view selection and continues a cursor issued under the existing query contract
- **THEN** the service retains the original scope, filter interpretation, source fields and pagination behavior

### Requirement: Related story filtering and summaries use the complete Case scope
The related view SHALL resolve the complete current Case member set before filtering or paging. Its summary SHALL distinguish total member alerts, distinct saved current-material objects, known alert activity bounds, and matching alert count from the mixed story-entry total. Missing material coverage and unknown event times SHALL remain explicit. Search SHALL use saved business fields and preserved source text. An investigation or completed human revision SHALL match a keyword through its own saved text or its frozen overlap with matching alerts; when a severity is selected it SHALL also overlap those matching alerts.

#### Scenario: Filtering and paging do not turn a page count into a Case total
- **WHEN** the caller filters a multi-member Case and requests a one-entry page
- **THEN** the matching-alert count reflects the complete filtered alert set, the Case summary still reflects all current members, and the mixed story total and cursor represent the complete matching story scope

#### Scenario: A related work record matches through an alert
- **WHEN** a saved investigation or completed human revision contains a matching alert in its frozen input even though its own text does not match the keyword
- **THEN** it remains in the related view, while a selected severity excludes work records without a matching frozen member

### Requirement: Related investigations retain their original subjects and saved provenance
The related view SHALL distinguish Case-owned investigations, runs referenced by saved Case results or explicit saved sources, and related alert or incident runs whose validated frozen inputs overlap current Case members. It SHALL deduplicate by original run identity and retain subject identity, run kind, source relations, saved-result references and the correct native detail link. It SHALL NOT fabricate a Case Run or result for another subject or infer historical membership solely from current incident relationships. Unverifiable historical input SHALL remain a declared coverage limitation.

Pending or never-started Case runs MAY appear through their actual Case ownership, but mutable planned members SHALL NOT be treated as actual frozen inputs. Member-based filtering and focus relations SHALL use only input membership verified against the saved execution snapshot and its original subject.

#### Scenario: The same saved run has more than one relation to the Case
- **WHEN** a run is found through a saved source and a validated frozen-member overlap
- **THEN** it appears once with both recorded relations and opens its original subject's fixed-run detail

#### Scenario: A pending investigation has only planned members
- **WHEN** a Case run has no verifiable saved execution input and its planned member list is still mutable
- **THEN** the unfiltered story may display the real run state, but does not use that planned list to claim a frozen-member match or focused-alert investigation relation

### Requirement: Story focus is independent of checkbox selection
The related view SHALL resolve a valid current focus from the full matching alert set. The member-relations read SHALL verify that the focus is a current member, return shared objects between that alert and other current members using saved object identities, and return related investigations whose validated frozen input includes that alert. Shared objects and investigations SHALL have independent bounded pagination and complete counts. Checkbox selection SHALL remain a separate client-side state and SHALL NOT change the right panel into an intersection of selected alerts.

#### Scenario: Focus changes after several alerts have been checked
- **WHEN** the user checks multiple alerts and then focuses another visible alert
- **THEN** the right panel follows only the new focus, retains original source and fixed-run links, and leaves the independent checkbox selection intact

### Requirement: The product story page follows the agreed 4173 design
The product page SHALL present its heading and history link, Case scope and activity summary, search with a single severity selector and reset, independent checkbox selection, a descending mixed-source timeline with an unknown-time section, and a right panel for the focused alert. It SHALL distinguish loading, failed reads, valid empty results and partially loaded records. It SHALL use the authoritative E65 pagination and saved source identities; it SHALL NOT retain the old type tabs, multi-value severity controls or selected-alert intersection merely because they exist in the previous implementation.

#### Scenario: A story read fails
- **WHEN** the initial story request fails
- **THEN** the page displays the read failure and its explicit retry action without simultaneously presenting the failure as an empty timeline

#### Scenario: A saved source is opened from the timeline
- **WHEN** the user opens an alert, fixed run, saved result or completed human revision
- **THEN** the navigation retains the proper Case context and original source identity and returns to the same story without creating a new investigation
