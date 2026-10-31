# Design

For follow-up model input, remove only duplicate generated gap strings already present in member judgments/relationships/open questions. Alias the prior scope to the current scope only when the full scopes are equal. When unchanged materials permit prior-query reuse, omit the current Alert's legacy saved_analysis from the model view because current triage and the prior report are supplied; mark omitted fields. Keep complete Alert/H1 evidence in PG. Serialize the model context compactly without changing canonical intent/hash encoding or the 24000-token preflight calculation.

Add optional unique required_tools (at most4) to CaseAnalysisRequest, default empty. Empty requests keep the existing intent shape. The required names must be offered by the current scoped CaseTools; otherwise save a failed Run without a model call. For each outstanding required name, send a native function tool_choice without response_format. Do not accept a final answer or dispatch other calls if the provider omits the required call. After actual attempts (including successful reuse), continue normal analysis/correction within existing limits. No keyword parser infers this requirement from natural language.

Clarify that T references triage rather than a member, member UUIDs are not hostnames, successful zero-row queries are not failures, and saved_analysis_truncated refers only to saved analysis. Tool messages add a derived query_status enum; full evidence fields remain unchanged. This improves model grounding without claiming general natural-language semantic validation.

Prepare local fixes and direct evidence first. Any resident image replacement and new live test credentials are a separate concrete approval step; do not overwrite prior test output or replay failed Runs.

Documentation clarification (2026-10-29): the [four-case report](../../../docs/investigation/multi-case-http-20261028.md) and its four case pages now explain business intent, manual/automatic triggers, recorded internal steps and HTTP readback separately, including why each evidence link is followed. This uses the original batch only; no test replay, frozen evidence rewrite or runtime behavior change.
