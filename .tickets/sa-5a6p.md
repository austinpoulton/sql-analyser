---
id: sa-5a6p
status: open
deps: [sa-0hcc]
links: []
created: 2026-03-17T14:52:22Z
type: task
priority: 0
assignee: Austin Poulton
parent: sa-tlx0
tags: [domain-model, pydantic, enums]
---
# Implement domain model enums and base classes

Implement core domain model classes in domain.py:
- ColumnUsage enum (6 values)
- ColumnClassification enum (3 values)
- QueriedColumn model with 3 fields
- QueriedTable model with qualified_name property
- Relationship model with canonical_key property
- DataModel class (without merge initially)
- OutputColumn model
- ComplexityMetrics model
- AnalysisResult model

All classes should have proper type hints and docstrings.

## Acceptance Criteria

- All 9 domain classes implemented
- ColumnUsage: SELECT, WHERE, HAVING, ORDER_BY, GROUP_BY, JOIN_ON
- QueriedTable.qualified_name property joins catalog.schema.name
- Relationship.canonical_key property enables symmetric deduplication
- All classes have Google-style docstrings
- All fields have type hints
- Pydantic Field() used for defaults where appropriate

