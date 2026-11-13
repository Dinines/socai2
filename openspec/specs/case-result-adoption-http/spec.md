# case-result-adoption-http Specification

## Purpose
让业务后端通过独立HTTP预览、人工采用合格的既有调查结果并读取判断历史；资格与保存复用调查核心，保留原结果、未完工作和案件状态。

## Requirements

### Requirement: Preview and explicitly adopt an existing Case result
The external HTTP API SHALL expose adoption preview and explicit adoption using the existing investigation core, with a required review token, nonblank reason and operation key. Only an eligible current whole-case baseline result SHALL be adopted. Unfinished work SHALL require acknowledgement and SHALL remain unchanged.

#### Scenario: Adoption with unfinished work
- **WHEN** a user previews an eligible result and submits its current token, reason, operation key and acknowledgement
- **THEN** a new assessment, sources, coverage and activity are saved atomically and the Case pointer is updated without closing the Case, changing tasks or starting/cancelling Runs

#### Scenario: Stale preview or ineligible result
- **WHEN** the reviewed state changed or the core refuses the candidate
- **THEN** HTTP409 reports the core reason and no adoption is saved

#### Scenario: Retry a completed adoption
- **WHEN** the same actor retries the same intent with the same key
- **THEN** the original receipt is returned without replacing a subsequently adopted judgment

### Requirement: Read assessment history
The API SHALL return descending assessment revisions with original result references, conclusion origin, adopting actor, reason, total and pagination. The public HTTP implementation SHALL remain separate from internal investigation calls.

#### Scenario: Read after adoption
- **WHEN** the backend reads Case details and assessment history after a successful adoption
- **THEN** the current pointer matches the receipt and both new and earlier judgments remain readable
