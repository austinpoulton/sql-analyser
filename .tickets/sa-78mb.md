---
id: sa-78mb
status: closed
deps: [sa-ymba, sa-4v14]
links: []
created: 2026-03-23T06:17:29Z
type: feature
priority: 2
assignee: Austin Poulton
---
# Create test_metrics.py with all test cases

Write comprehensive test suite for metrics module in tests/test_metrics.py. Cover all FR-004 test cases plus edge cases.

## Acceptance Criteria

- TC-004-01: Simple query baseline test
- TC-004-02: CTE scope count test
- TC-004-03: Nested CTE and correlated subquery test
- TC-004-04: UNION scope count test
- TC-METRICS-01: Empty SELECT minimal node count
- TC-METRICS-02: Complex JOIN increases node count
- TC-METRICS-03: Scope types are descriptive
- All tests use fixtures from conftest.py
- All tests pass
- Test coverage ≥95% for metrics.py

