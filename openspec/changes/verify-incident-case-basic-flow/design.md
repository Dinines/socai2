# Execution scope

Target the existing `aisoc` database on `sting-infra21`. Read-only preflight found both target tables absent and the two existing synthetic incident members intact. Use the already-authored 120/121 SQL, under the existing `aisoc` owner, in one transaction with the migration-name ledger entries. Stop if either table or selected ledger name already exists; do not reset a partially completed test or run the whole migration directory. The only grants are the existing migration's privileges on its new tables for `aisoc_app`; no roles, credentials or RBAC policy are changed.

Use one temporary current-API process, existing `aisoc_app` connection and tenant RLS. Inject CurrentUser as before; JWT/RBAC are outside this check. Create one tagged test Case from one member, attach both members to distinguish added/already-linked, read receipts/history and preview only the selected member. All these operations must make zero model calls and create no investigation Run.

Refresh the same incident overview once with `include_investigations=true`, using the existing model and already-saved test reports. Verify saved text, source Run/scope references and ordinary GET readback, with no additional model call or investigation dispatch. Preserve original reports and synthetic alert states. Retain any failure and stop at the failed functional step.
