---
id: sa-0ndu
status: closed
deps: [sa-r2y2]
links: []
created: 2026-03-20T07:42:49Z
type: task
priority: 2
assignee: Austin Poulton
parent: sa-syfb
tags: [phase-3, core]
---
# Extract implicit WHERE join relationships

Implement Step 2d.2: Find WHERE clause, extract EQ predicates, skip unqualified/same-table comparisons, create Relationships

## Acceptance Criteria

WHERE implicit joins extracted, filters skipped, logging shows relationships

