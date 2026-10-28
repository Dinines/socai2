- [x] Implement the shared execution index with explicit current/legacy reader boundaries.
- [x] Add Run-scoped evidence/row reads and report/step/history navigation.
- [x] Verify the existing example through all three business filters and document the contract.

Evidence: `docs/investigation/execution-index-and-evidence-20261028.md`. Three new examples and fourteen affected examples pass using database/model/source doubles. Initial paging-fixture binding mismatch corrected; real PG/production deployment unverified. OpenSpec CLI unavailable; strict CLI validation and archive not performed.
