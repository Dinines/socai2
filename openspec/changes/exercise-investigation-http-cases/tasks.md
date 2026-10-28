- [x] Inventory sources and clarify simulated-data use with the user.
- [x] Prepare four-case manifest, sequential HTTP caller runner and output document.
- [x] Authorize/setup bounded test credentials and run the real HTTP cases (207 requests, 4 Cases, 6 Runs).
- [x] Record each case's inputs, intermediate calls, final objects and pass/fail/unexecuted steps (2/4 automatic flow checks passed; semantic issue also retained).
- [x] Revoke both test credentials, remove the private token file and record remaining functional gaps.

Evidence: `docs/investigation/multi-case-http-20261028.md` with four individual case pages and raw evidence. Four main Runs completed; Office follow-up failed input allowance, network follow-up did not invoke the requested Tool, and LSASS prose misdescribed successful-empty Tool results. This task list records completed testing, not full functional acceptance. No business API change/redeployment or retries were made. OpenSpec CLI unavailable; strict CLI validation/archive not claimed.
