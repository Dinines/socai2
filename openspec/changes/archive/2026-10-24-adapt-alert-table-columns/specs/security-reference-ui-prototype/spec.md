## MODIFIED Requirements

### Requirement: Alert browsing and local management
The prototype SHALL support alert search, filters, sorting, pagination, column selection, details and local management. The main alerts table SHALL retain processing status, omit investigation status and classification columns, and show one alert occurrence time column instead of first and last activity columns. Column selection, time filtering, sorting and export SHALL follow this main table definition without changing embedded incident or Case alert tables.

#### Scenario: Save an alert classification
- **WHEN** a user updates an alert's owner, status or classification and saves
- **THEN** views that display the field show the same updated value
- **AND** classification remains available in alert details and management without a main-list classification column
- **AND** cancellation does not change saved values.

#### Scenario: Review the adapted main table
- **WHEN** a user opens the main alerts list
- **THEN** processing status and one alert occurrence time are available in the table and column selection
- **AND** investigation status, classification, first activity and last activity are not offered as main table columns
- **AND** date filtering, time sorting and CSV export use the same occurrence timestamp
- **AND** existing quick filters and embedded incident/Case alert tables retain their behavior.
