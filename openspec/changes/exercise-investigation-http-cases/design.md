# Scope and evidence

Use four existing simulated cases with the resident 18010 API and core 18000 API, real PostgreSQL/ClickHouse and existing model. Preserve source Alerts, prior Runs and workers. Source/Fusion/triage provenance is read from existing records, not regenerated. Vendor HTTP and automatic Case policy remain outside this run.

The showcase hosts each have two lake rows but no normalized process_name/class4001 rows; current process/network Tools should return empty, which must remain an evidence gap. The network fixture has three matching network rows and no process rows. Do not add expected answers to model material or modify fixtures to force a pass.

Run Alert/Incident reads, Case create/attach, selected-member preview, main investigation, steps/evidence/source rows/report, three execution-index views, Case history, selected follow-ups and event overview. Include one subset Case and one query-reuse follow-up. Keep every request body, HTTP result, response and check in a new output directory. Do not retry failed POSTs or overwrite old batches. One failed case does not prevent independent cases from running.

For real HTTP authentication, prepare two short-lived test API keys scoped only to alerts:read, alerts:write, cases:read, cases:write and investigation:run for the two existing synthetic tenants, subject to explicit authorization. Do not modify users/roles. Keep raw keys only in a mode0600 file on21, expire within two hours, and revoke the exact new key IDs in the launcher finally block. Never include keys in evidence or model inputs.
