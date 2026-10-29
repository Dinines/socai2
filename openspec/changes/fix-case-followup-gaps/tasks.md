- [x] Implement compact follow-up model view and recorded-budget reconstruction.
- [x] Add explicit required_tools/native tool_choice with compatible empty intent.
- [x] Clarify identifier, empty-result and saved-analysis semantics.
- [x] Run only affected direct examples; preserve all previous failures.
- [ ] Prepare a reviewable resident update and targeted live retest, then record actual outcome.

OpenSpec CLI unavailable; no strict CLI validation/archive claimed.

Local checkpoint (2026-10-29): six affected direct examples passed. The recorded
Office correction reconstruction falls from 19137 to 16786 allowance units,
below its recorded remaining 17018; this is offline reconstruction, not a new
model result. Full saved evidence and previous failures remain unchanged.
See [local evidence](../../../docs/operations/investigation-followup-fix-local-20261028.json).
The r2 installer/compose and required-Tool runner changes are preparation only;
no resident replacement, new credentials or live retest has occurred. The user
requested a local commit at this checkpoint, so the live task remains pending.
