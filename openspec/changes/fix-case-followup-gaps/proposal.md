# Fix the observed follow-up and source-description gaps

The four-case resident HTTP run exposed a long-history correction blocked by conservative input allowance, an explicitly requested query skipped by the model, and prose confusing source identifiers and successful-empty queries. Reduce redundant model input, add an explicit required_tools request field enforced through native tool_choice, and clarify source semantics. Preserve all saved evidence, old Runs, current budgets and validation; verify only affected examples and the recorded failed steps.
