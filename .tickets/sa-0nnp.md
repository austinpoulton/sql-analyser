---
id: sa-0nnp
status: open
deps: [sa-5a6p]
links: []
created: 2026-03-17T14:52:22Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-tlx0
tags: [api, exports]
---
# Implement public API exports

Create public API in src/sql_analyser/__init__.py:
- Import all domain classes from .domain
- Define __all__ list with 9 exports
- Verify imports work: from sql_analyser import QueriedTable

## Acceptance Criteria

- All domain classes importable from sql_analyser package
- __all__ contains 9 items
- No import errors

