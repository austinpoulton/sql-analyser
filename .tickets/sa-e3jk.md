---
id: sa-e3jk
status: closed
deps: [sa-nk08]
links: []
created: 2026-03-20T07:43:27Z
type: task
priority: 2
assignee: Austin Poulton
parent: sa-rdw3
tags: [phase-3, core]
---
# Integrate CTE resolution into JOIN extraction

Update Step 2d.1 to call _resolve_cte_to_base_table when _resolve_alias returns None for CTE references

## Acceptance Criteria

CTE JOINs resolve to base tables, non-CTE JOINs still work (no regression)

