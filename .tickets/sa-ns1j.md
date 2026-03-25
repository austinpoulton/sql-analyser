---
id: sa-ns1j
status: open
deps: [sa-hw9t]
links: []
created: 2026-03-25T08:36:13Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-8ywn
---
# Implement dependency vulnerability scan (pip-audit)

Add job to scan dependencies with pip-audit, generate SARIF, fail on HIGH/CRITICAL.

## Acceptance Criteria

- Scan runs successfully
- SARIF in Security tab
- HIGH/CRITICAL vulnerabilities block
- MEDIUM vulnerabilities warn

