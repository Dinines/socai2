# Design

After a final-answer schema/reference failure, record error types/locations, currently available evidence IDs and selected member UUIDs. If one correction and model-call capacity remain, append these diagnostics and concise field rules as a user-level correction request and continue the existing loop. Do not repeat the full schema: a real follow-up showed that this consumes the remaining input allowance even for an empty-citation error. The model may issue normal scoped Tool calls before answering again.

The full rejected response stays in its original ledger step but is removed from the next model input. The correction uses diagnostics and original source material, avoiding repeated invented claims and unnecessary input growth within the unchanged budget.

Do not include Pydantic raw input/context in diagnostic feedback. Do not expand budgets, retry HTTP failures, replay a saved Run, silently rewrite member IDs, or turn invalid evidence into accepted conclusions. A second invalid conclusion retains the current terminal failure. Valid responses incur no extra model call.

Use a 60-second HTTP response timeout (10-second connect) for the existing 3000-output-token model call. The outer 120-second analysis deadline still cancels work, so this does not extend total Run duration.

The real follow-up hit the input allowance after an invalid reference. For model input only, omit the previous report's generated timeline/member coverage tables and explicitly list omitted fields. Preserve the full H1 evidence and original report in PG. This avoids unnecessary repeated data while retaining narrative, findings, member judgments, relationships, gaps and open questions; it does not raise the token budget.
