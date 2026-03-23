---
id: sa-ymba
status: closed
deps: [sa-ti6t]
links: []
created: 2026-03-23T06:17:12Z
type: feature
priority: 2
assignee: Austin Poulton
---
# Implement metrics.py module

Create src/sql_analyser/metrics.py with node counting and scope analysis. Use sqlglot.optimizer.scope.traverse_scope() and expression.walk() for AST traversal.

## Acceptance Criteria

- Module created with proper imports (from __future__ import annotations)
- compute_metrics(expression) function implemented
- _count_nodes(expression) helper using expression.walk()
- _extract_scope_types(scopes) helper extracting scope type names
- All functions have Google-style docstrings
- All functions have type hints
- No linting errors

