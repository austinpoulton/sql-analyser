---
id: sa-qdjl
status: closed
deps: [sa-0kit]
links: []
created: 2026-03-18T14:59:56Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-5gn6
tags: [phase2d, wildcard]
---
# Implement wildcard detection

Detect SELECT * and table.* patterns, set has_wildcard flags (Tasks 2D.1-2D.2)

## Acceptance Criteria

- Unqualified wildcard detection works
- Qualified wildcard detection works
- has_wildcard flag set correctly
- No columns invented

