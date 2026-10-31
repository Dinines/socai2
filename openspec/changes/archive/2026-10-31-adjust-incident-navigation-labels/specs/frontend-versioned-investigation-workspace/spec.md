## MODIFIED Requirements

### Requirement: Incident layout prioritizes context and relationship space
V2 SHALL present the approved incident capabilities with a compact overview, a graph-focused relationship analysis and core default list columns while preserving data, the five incident tabs ordered as overview, relationship analysis, member alerts, objects and activities, queue metrics and Case investigation boundaries.

#### Scenario: Read a compact incident overview
- **WHEN** a user opens an incident overview
- **THEN** ATT&CK stage coverage appears above the event description card, and the description, occurrence range and compact member/host counts remain visible without repeating header handling metadata or separate object/shared-object metric cards
- **AND** object totals remain on the object tab, shared-object counts and source alerts remain in association evidence, and no value or membership changes.

#### Scenario: Use the incident relationship graph
- **WHEN** a user opens incident relationship analysis
- **THEN** counts and filters occupy a compact toolbar with the source filter labeled 数据来源 and no 仅此事件 scope label above the existing three-column circular graph, without a repeated large page title
- **AND** graph controls, current-incident boundaries and Case/Run graph presentation remain unchanged.

#### Scenario: Read and customize incident tables
- **WHEN** a user opens an incident list or member-alert list without a custom column selection
- **THEN** core identification, severity, handling, asset, ownership and time information are prioritized; all original optional columns remain available through customization
- **AND** an incident ID column uses a compact display with its full value available and copyable, existing custom selections and export values remain intact, and queue metric values and alignment stay unchanged.
