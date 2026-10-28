## ADDED Requirements

### Requirement: Case reads a host from the selected alert's product instance
The Case runtime SHALL expose a read-only product host tool for supported enabled source connectors and SHALL bind each invocation to a selected alert, its host and its exact tenant-owned connector.

#### Scenario: The model requests a supported source host
- **WHEN** the model selects product_host_details with an eligible source_alert_id and hostname
- **THEN** the server sends crowdstrike/get_host through the existing Actions HTTP client with that connector's credentials and retains the normalized result, source identity and request identifier as report-addressable evidence

#### Scenario: The product has no matching host or fails to read it
- **WHEN** a read returns no match or a failure
- **THEN** a successful empty result remains distinct from unavailable evidence and neither is described as proof of safety

#### Scenario: A new run asks for the current snapshot
- **WHEN** a later Case run requests product_host_details
- **THEN** it performs a new read and marks its result as a current snapshot rather than reusing a previous run's snapshot as a historical window query
