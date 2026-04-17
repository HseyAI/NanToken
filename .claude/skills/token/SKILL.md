---
name: token
description: Show token usage dashboard with budget, session stats, and per-project history
---

# /token — Token Usage Dashboard

When the user runs `/token`, provide a comprehensive token usage dashboard.

## Steps

1. Call the `token_session` MCP tool to get current session statistics
2. Call the `token_budget` MCP tool to get budget status
3. Call the `token_history` MCP tool with `days=1` to get today's per-project breakdown

## Output Format

Combine the results into a clean dashboard. Example:

```
Session
  Calls: 12 | Tokens: 45,230 | Cost: $0.34
  Source: auto-tracked (hook active)

Budget
  Daily: 45,230 / 100,000 (45.2%)
  Monthly: 234,500 / 3,000,000 (7.8%)

Today by Project
  NanToken: 23,400 tokens ($0.18)
  my-app: 21,830 tokens ($0.16)
```

## Notes

- If token_session says "No usage recorded", note that the auto-tracking hook may not be installed and suggest: `python -m nantoken.hooks.install`
- If token_history returns no data, skip the project breakdown section
- Keep the output concise — this is a quick-glance dashboard
