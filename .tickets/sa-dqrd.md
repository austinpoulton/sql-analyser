---
id: sa-dqrd
status: open
deps: [sa-n0n3]
links: []
created: 2026-03-25T08:38:21Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-qp1j
---
# Implement security scan of artifacts

Scan built wheel with pip-audit, fail on HIGH/CRITICAL vulnerabilities.

## Acceptance Criteria

- Scans built wheel
- Blocks release on vulnerabilities
- Clear error output

