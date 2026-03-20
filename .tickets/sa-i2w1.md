---
id: sa-i2w1
status: open
deps: []
links: []
created: 2026-03-18T14:58:11Z
type: epic
priority: 0
assignee: Austin Poulton
tags: [phase2, cte]
---
# Phase 2C: CTE & Subquery Handling

Handle CTEs and subqueries correctly, ensuring base tables are extracted and CTE aliases don't appear in output.

## Acceptance Criteria

- TC-001-07 (CTE) passes
- TC-001-08 (nested CTE) passes
- TC-001-09 (subquery) passes
- CTE aliases not in table list
- Columns attributed to base tables

