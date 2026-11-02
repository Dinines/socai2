## ADDED Requirements

### Requirement: Case entry prioritizes current case context
V2 SHALL use Case information as the default Case entry while retaining explicit investigation overview and Run views.
#### Scenario: Enter a Case from a general link
- **WHEN** a user opens a Case from its list, preview, alert, incident, switcher or newly associated Case, or opens a Case URL without a tab or selected Run
- **THEN** Case information is selected and is the first internal navigation entry
- **AND** explicit overview and Run links retain their prior results, six Run views and historical inputs; entering the page changes no stored data.

### Requirement: Case information displays current member attack stages
V2 SHALL display ATT&CK stage coverage using the recorded categories of current Case member alerts and the same presentation semantics as incidents.
#### Scenario: Inspect member stage coverage
- **WHEN** Case information is displayed
- **THEN** stage counts reflect only current members, missing categories remain unclassified and empty membership is shown honestly
- **AND** an information control explains that alert counts are not detection coverage or proof of attack success; historic Run inputs are not silently included.
