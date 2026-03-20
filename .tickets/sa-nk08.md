---
id: sa-nk08
status: open
deps: [sa-k5e5]
links: []
created: 2026-03-20T07:43:23Z
type: task
priority: 2
assignee: Austin Poulton
parent: sa-rdw3
tags: [phase-3, core]
---
# Implement CTE resolution helper function

Implement _resolve_cte_to_base_table() with direct and nested CTE support (recursive), add logging, add unit-level testing

## Acceptance Criteria

Function handles basic and nested CTEs, no infinite loops, logging shows resolution path

