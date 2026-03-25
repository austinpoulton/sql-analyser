---
id: sa-lp6u
status: open
deps: [sa-ipqb]
links: []
created: 2026-03-25T08:34:00Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-y1fa
---
# Create lint and type check job

Implement ci.yml with lint-and-type-check job running ruff and mypy.

## Acceptance Criteria

- Job runs on every commit
- Fails on linting/formatting/type errors
- Completes in < 1 minute

