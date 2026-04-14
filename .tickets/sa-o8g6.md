---
id: sa-o8g6
status: closed
deps: [sa-lp6u, sa-elgs]
links: []
created: 2026-03-25T08:34:00Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-y1fa
---
# Create build validation job

Build wheel and sdist, install in clean env, run smoke test. Upload artifacts.

## Acceptance Criteria

- Build succeeds without errors
- Wheel installs cleanly
- Smoke test imports all public API classes
- Artifacts stored with 30-day retention

