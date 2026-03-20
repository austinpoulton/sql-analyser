---
id: sa-5gn6
status: open
deps: []
links: []
created: 2026-03-18T14:58:15Z
type: epic
priority: 0
assignee: Austin Poulton
tags: [phase2, wildcard]
---
# Phase 2D: Wildcard Detection

Implement wildcard detection for SELECT * and table.* patterns without inventing columns.

## Acceptance Criteria

- TC-008-01, TC-008-02, TC-008-03 pass
- has_wildcard flag correctly set
- No columns invented
- Explicit columns still captured

