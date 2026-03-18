---
id: sa-vtdu
status: closed
deps: [sa-26na]
links: []
created: 2026-03-18T14:59:36Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-i2w1
tags: [phase2c, cte]
---
# Implement CTE/subquery handling

Skip CTE sources in table registration, handle CTE references in alias resolution (Tasks 2C.1-2C.2)

## Acceptance Criteria

- CTE sources skipped correctly
- CTE references return None
- Alias resolution updated
- No CTEs in table list

