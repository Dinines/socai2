## ADDED Requirements
### Requirement: Consolidated Case data remains source coherent
V2 SHALL keep original examples and recorded AiSOC Cases accessible together while placing saved Cases prominently and linking Case, incident, member and investigation material by recorded identities. All saved Cases SHALL expose their available query, artifact, report and activity material without borrowing missing values or relationships from examples.

#### Scenario: Browse all Case data
- **WHEN** the user opens the Case list
- **THEN** saved AiSOC Cases and original examples remain accessible with distinguishable sources and statistics reflecting the selected list
- **AND** saved local Case collections expose all referenced Runs without rewriting their inputs or backend ownership.

#### Scenario: Follow recorded relationships
- **WHEN** the user moves between a saved Case and incident
- **THEN** only their actual member relationships determine links and selected material
- **AND** missing incident identities or unavailable detail IDs do not silently open an unrelated example.
